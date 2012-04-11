#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
# Voodoo

Reanimates an application skeleton, just for you.

------------
Copyright © 2011 by [Lúcuma labs] (http://lucumalabs.com).  
See `AUTHORS.md` for more details.  
License: [MIT License] (http://www.opensource.org/licenses/mit-license.php).

"""
import datetime
import errno
import io
import os
import re

import jinja2
from colorama import init, Fore, Back, Style


__version__ = '1.0.0'


DEFAULT_DATA = {
    'PS': os.path.sep,
    'NOW': datetime.datetime.utcnow(),
}

DEFAULT_FILTER_EXT = ('.pyc', '.DS_Store', '.pyo')

DEFAULT_ENV_OPTIONS = {
    'autoescape': False,
    'block_start_string': '[%',
    'block_end_string': '%]',
    'variable_start_string': '[[',
    'variable_end_string': ']]',
}


def formatm(action, msg='', color='', on_color='', bright=True, indent=12):
    action = action.rjust(indent, ' ')
    color = getattr(Fore, color.upper(), '')
    on_color = getattr(Back, on_color.upper(), '')
    style = Style.BRIGHT if bright else Style.DIM if bright is False else ''

    lparts = [
        color, on_color, style,
        action,
        Fore.RESET, Back.RESET, Style.RESET_ALL,
        '  ',
        msg,
    ]
    return ''.join(lparts)


def make_dirs(*lpath):
    path = os.path.join(*lpath)
    try:
        os.makedirs(os.path.dirname(path))
    except (OSError), e:
        if e.errno != errno.EEXIST:
            raise
    return os.path.abspath(path)


def read_from(filepath, binary=True):
    mode = 'rb' if binary else 'r'
    with io.open(filepath, mode) as f:
        source = f.read()
    return source


def write_to(filepath, content, binary=True):
    if not binary:
        if not isinstance(content, unicode):
            try:
                content = unicode(content, 'utf-8')
            except:
                pass
    mode = 'wb' if binary else 'w'
    with io.open(filepath, mode) as f:
        f.write(content)


def prompt(text, default=None, _test=None):
    """Ask a question via raw_input() and return their answer.
    
    param text: prompt text
    param default: default value if no answer is provided.
    """
    
    text += ' [%s]' % default if default else ''
    while True:
        if _test is not None:
            print text
            resp = _test
        else:
            resp = raw_input(text)
        if resp:
            return resp
        if default is not None:
            return default


def prompt_bool(text, default=False, yes_choices=None, no_choices=None,
      _test=None):
    """Ask a yes/no question via raw_input() and return their answer.
    
    :param text: prompt text
    :param default: default value if no answer is provided.
    :param yes_choices: default 'y', 'yes', '1', 'on', 'true', 't'
    :param no_choices: default 'n', 'no', '0', 'off', 'false', 'f'
    """
    
    yes_choices = yes_choices or ('y', 'yes', 't', 'true', 'on', '1')
    no_choices = no_choices or ('n', 'no', 'f', 'false', 'off', '0')
    
    default = yes_choices[0] if default else no_choices[0]
    while True:
        if _test is not None:
            print text
            resp = _test
        else:
            resp = prompt(text, default)
        if not resp:
            return default
        resp = str(resp).lower()
        if resp in yes_choices:
            return True
        if resp in no_choices:
            return False


def make_file(dst_path, ffolder, filename, content, options):
    pretend = options.get('pretend', False)
    force = options.get('force', False)
    skip = options.get('skip', False)
    quiet = options.get('quiet', False)

    mode ='wb'
    created_path = os.path.join(ffolder, filename).lstrip('.').lstrip('/')
    
    if pretend:
        final_path = os.path.join(dst_path, ffolder, filename)
    else:
        final_path = make_dirs(dst_path, ffolder, filename)
    
    if not os.path.exists(final_path):
        if not quiet:
            print formatm('create', created_path, color='green')
        if not pretend:
            with io.open(final_path, mode) as f:
                f.write(content)
        return
    
    # An identical file already exists.
    if content == read_from(final_path):
        if not quiet:
            print formatm('identical', created_path, color='cyan', bright=None)
        return
    
    # A different file already exists.
    if not quiet:
        print formatm('conflict', created_path, color='red')
    if force:
        overwrite = True
    elif skip:
        overwrite = False
    else:
        msg = '  Overwrite %s? (y/n)' % final_path
        overwrite = prompt_bool(msg, default=True)
    
    action = 'force' if overwrite else 'skip'
    if not quiet:
        print formatm(action, created_path, color='yellow')
    if overwrite and not pretend:
        with io.open(final_path, mode) as f:
            f.write(content)    


def reanimate_skeleton(src_path, dst_path, data=None, filter_ext=None,
        env_options=None, **options):
    """
    src_path
    :   Absolute path to the files to copy

    dst_path
    :   

    data
    :   Data to be passed to the templates
    
    filter_ext
    :   Don't copy files with extensions in this list
    
    env_options
    :   Extra options for the template environment.

    options
    :   General options:
        -p, [--pretend]
        :   Run but do not make any changes
        -f, [--force]
        :   Overwrite files that already exist
        -s, [--skip]
        :   Skip files that already exist
        -q, [--quiet]
        :   Suppress status output
    """
    options['pretend'] = options.get('pretend', options.get('p', False))
    options['force'] = options.get('force', options.get('f', False))
    options['skip'] = options.get('skip', options.get('s', False))
    options['quiet'] = options.get('quiet', options.get('q', False))

    ppath, pname = os.path.split(dst_path)
    jinja_loader = jinja2.FileSystemLoader(src_path)

    data = data or {}
    _data = DEFAULT_DATA.copy()
    _data.update(data)
    _data.setdefault('PNAME', pname)
    data = _data

    filter_ext = filter_ext or DEFAULT_FILTER_EXT

    env_options = env_options or {}
    _env_options = DEFAULT_ENV_OPTIONS.copy()
    _env_options.update(env_options)
    _env_options.setdefault('loader', jinja_loader)
    env_options = _env_options
    
    jinja_env = jinja2.Environment(**env_options)

    for folder, subs, files in os.walk(src_path):
        ffolder = folder.replace(src_path, '').lstrip(os.path.sep)
        
        for filename in files:
            if filename.endswith(filter_ext):
                continue
            file_path = os.path.join(folder, filename)
            content = read_from(file_path)

            if filename.endswith('.tmpl'):
                if not isinstance(content, unicode):
                    content = unicode(content, 'utf-8')
                filename = re.sub(r'\.tmpl$', '', filename)
                tmpl = jinja_env.from_string(content)
                content = tmpl.render(data).encode('utf-8')
            filename = re.sub(r'%PNAME%', pname, filename)

            make_file(dst_path, ffolder, filename, content, options)
            

