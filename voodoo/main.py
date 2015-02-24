# -*- coding: utf-8 -*-
from __future__ import print_function

from fnmatch import fnmatch
from functools import reduce
from collections import OrderedDict
import datetime
import json
import os
import re
import shutil

import jinja2

from ._compat import to_unicode
from .cli import prompt_bool, prompt
from .vcs import get_vcs_from_url, clone
from .helpers import (
    print_format, make_dirs, create_file, copy_file, normalize, read_file,
    file_has_this_content, files_are_identical)


DEFAULT_DATA = {
    'now': datetime.datetime.utcnow,
}

DEFAULT_FILTER = ('.*', '~*', '*.py[co]') # Files to ignore in the folders
DEFAULT_INCLUDE = ()

# The default env options for jinja2
DEFAULT_ENV_OPTIONS = {
    'autoescape': True,
    'block_start_string': '[%',
    'block_end_string': '%]',
    'variable_start_string': '[[',
    'variable_end_string': ']]',
}


# Variables that need user input when rendering the template.
VOODOO_JSON_FILE = 'voodoo.json'

COLOR_OK = 'green'
COLOR_WARNING = 'yellow'
COLOR_IGNORE = 'cyan'
COLOR_DANGER = 'red'

RX_PARAM_PATH = re.compile(r'\[\[\s*(\w+)\s*\]\]', flags=re.IGNORECASE)
RX_PARAM_PATH_COOKIECUTTER = re.compile(r'\{\{\s*(\w+)\s*\}\}', flags=re.IGNORECASE)


def render_skeleton(
        src_path, dst_path, data=None, filter_this=None, include_this=None,
        pretend=False, force=False, skip=False, quiet=False, envops=None):
    """
    Uses the template in src_path to generate the scaffold/skeleton at the dst_path

    src_path:
        Absolute path to the project skeleton. May be a URL.

    dst_path:
        Absolute path to where to render the skeleton

    data:
        Data to be passed to the templates, as context.

    filter_this:
        A list of names or shell-style patterns matching files or folders
        that musn't be copied. The default is: ``['.*', '~*', '*.py[co]']``

    include_this:
        A list of names or shell-style patterns matching files or folders that
        must be included, even if its name are in the `filter_this` list.
        Eg: ``['.gitignore']``. The default is an empty list.

    pretend:
        Run but do not make any changes

    force:
        Overwrite files that already exist, without asking

    skip:
        Skip files that already exist, without asking

    quiet:
        Suppress the status output

    envops:
        Extra options for the Jinja template environment.

    """
    src_path = to_unicode(src_path)
    vcs = get_vcs_from_url(src_path)
    try:
        if vcs:
            src_path = clone(vcs, quiet)
            if not src_path:
                return

        data = data or {}
        user_data = get_user_data(src_path, force, quiet)
        data.update(user_data)

        render_local_skeleton(
            src_path, dst_path, data=data,
            filter_this=filter_this, include_this=include_this,
            pretend=pretend, force=force, skip=skip, quiet=quiet, envops=envops)
    finally:
        if src_path and vcs:
            shutil.rmtree(src_path)


def get_user_data(src_path, force, quiet):
    """Query to user for information needed as per the template's vooodoo.json"""
    json_path = os.path.join(src_path, VOODOO_JSON_FILE)
    if not os.path.exists(json_path):
        return {}
    json_src = read_file(json_path)
    try:
        # Load the default user data in order
        def_user_data = json.loads(json_src, object_pairs_hook=OrderedDict)
    except ValueError as e:
        if not quiet:
            print_format('Invalid `voodoo.json`', color=COLOR_WARNING)
            print(e)
            def_user_data = {}

    user_data = {}
    if force:
        return def_user_data
    print('\n' + '-' * 50 + '\n')
    for key, value in def_user_data.items():
        resp = prompt('{0}?'.format(key), value)
        user_data[key] = resp.decode('utf8')
    print('\n' + '-' * 50 + '\n')
    return user_data


def render_local_skeleton(src_path, dst_path, data=None, filter_this=None,
                          include_this=None, pretend=False, force=False,
                          skip=False, quiet=False, envops=None):
    """Same as render_skeleton but src_path must be a directory, not a URL.
    """

    src_path = to_unicode(src_path)
    if not os.path.exists(src_path):
        raise ValueError('Project skeleton not found')
    if not os.path.isdir(src_path):
        raise ValueError('Project skeleton must be a folder')
    data = clean_data(data)
    data.setdefault('folder_name', os.path.basename(dst_path))
    must_filter = get_name_filter(filter_this, include_this)
    render_tmpl = get_jinja_renderer(src_path, data, envops)

    for folder, subs, files in os.walk(src_path):
        rel_folder = folder.replace(src_path, '').lstrip(os.path.sep)
        rel_folder = parametrize_path(rel_folder, data)
        if must_filter(rel_folder):
            continue
        for src_name in files:
            dst_name = re.sub(r'\.tmpl$', '', src_name)
            dst_name = parametrize_path(dst_name, data)
            rel_path = os.path.join(rel_folder, dst_name)
            if must_filter(rel_path):
                continue
            render_file(
                dst_path, rel_folder, folder,
                src_name, dst_name, render_tmpl,
                pretend=pretend, force=force, skip=skip, quiet=quiet
            )


def clean_data(data):
    """Ensure default values are present in the dict if the keys are missing.
    """
    data = data or {}
    _data = DEFAULT_DATA.copy()
    _data.update(data)
    return _data


def get_jinja_renderer(src_path, data, envops=None):
    """Returns a function that can render a Jinja template.
    """
    envops = envops or {}
    _envops = DEFAULT_ENV_OPTIONS.copy()
    _envops.update(envops)
    _envops.setdefault('loader',
                       jinja2.FileSystemLoader(src_path, encoding='utf8'))
    env = jinja2.Environment(**_envops)

    def render_tmpl(fullpath):
        relpath = fullpath.replace(src_path, '').lstrip(os.path.sep)
        tmpl = env.get_template(relpath)
        return tmpl.render(data)

    return render_tmpl


def get_name_filter(filter_this, include_this):
    """Returns a function that evaluates if a file or folder name must be
    filtered out.

    The compared paths are first converted to unicode and decomposed.  This is
    neccesary because the way PY2.* `os.walk` read unicode paths in different
    filesystems. For instance, in OSX, it returns a decomposed unicode
    string. In those systems, u'ñ' is read as `\u0303` instead of `\xf1`.
    """
    filter_this = [normalize(to_unicode(f)) for f in
                   filter_this or DEFAULT_FILTER]
    include_this = [normalize(to_unicode(f)) for f in
                    include_this or DEFAULT_INCLUDE]

    def fullmatch(path, pattern):
        path = normalize(path)
        name = os.path.basename(path)
        return fnmatch(name, pattern) or fnmatch(path, pattern)

    def must_be_filtered(name):
        return reduce(lambda r, pattern: r or
                      fullmatch(name, pattern), filter_this, False)

    def must_be_included(name):
        return reduce(lambda r, pattern: r or
                      fullmatch(name, pattern), include_this, False)

    def must_filter(path):
        return must_be_filtered(path) and not must_be_included(path)

    return must_filter


def parametrize_path(path, data):
    """Replace the {{varname}} slots in the path with its real values.
    """
    def get_data_value(match):
        return data.get(match.group(1), match.group(0))
    path = RX_PARAM_PATH.sub(get_data_value, path)
    path = RX_PARAM_PATH_COOKIECUTTER.sub(get_data_value, path)
    return path


def render_file(dst_path, rel_folder, folder, src_name, dst_name, render_tmpl,
                pretend=False, force=False, skip=False, quiet=False):
    """Process or copy a file of the skeleton.
    """
    fullpath = os.path.join(folder, src_name)
    created_path = os.path.join(rel_folder, dst_name).lstrip('.').lstrip('/')

    if pretend:
        final_path = os.path.join(dst_path, rel_folder, dst_name)
    else:
        final_path = make_dirs(dst_path, rel_folder, dst_name)

    if not os.path.exists(final_path):
        if not quiet:
            print_format('create', created_path, color=COLOR_OK)
        if not pretend:
            make_file(src_name, render_tmpl, fullpath, final_path)
        return

    # A file with this name already exists
    content = None
    if src_name.endswith('.tmpl'):
        content = render_tmpl(fullpath)
        identical = file_has_this_content(final_path, content)
    else:
        identical = files_are_identical(fullpath, final_path)

    # The existing file is identical.
    if identical:
        if not quiet:
            print_format('identical', created_path, color=COLOR_IGNORE, bright=None)
        return

    # The existing file is different.
    if not quiet:
        print_format('conflict', created_path, color=COLOR_DANGER)
    if force:
        overwrite = True
    elif skip:
        overwrite = False
    else:
        msg = '  Overwrite %s? (y/n)' % final_path
        overwrite = prompt_bool(msg, default=True)

    if not quiet:
        print_format('force' if overwrite else 'skip', created_path, color=COLOR_WARNING)

    if overwrite and not pretend:
        if content is None:
            copy_file(fullpath, final_path)
        else:
            create_file(final_path, content)


def make_file(src_name, render_tmpl, fullpath, final_path):
    """If src_name is a template, render it and place it at final_path, otherwise
    just copy the file to the final_path.
    """
    if src_name.endswith('.tmpl'):
        content = render_tmpl(fullpath)
        create_file(final_path, content)
    else:
        copy_file(fullpath, final_path)
