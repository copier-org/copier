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
from termcolor import colored


__version__ = '0.7'


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


def formatm(action, msg='', color='green', on_color=None, attrs=None,
        indent=12):
    if attrs is None:
        attrs = ['bold']
    action = action.rjust(indent, ' ')
    lparts = [
        colored(action, color=color, on_color=on_color, attrs=attrs),
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


def read_from(filepath, mode='rb'):
    with io.open(filepath, mode) as f:
        source = f.read()
    return source


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


def make_file(new_app_path, ffolder, filename, content, mode='wb'):
    created_path = os.path.join(ffolder, filename).lstrip('.').lstrip('/')
    final_path = make_dirs(new_app_path, ffolder, filename)

    if not os.path.exists(final_path):
        print formatm('create', created_path, color='green')
        with io.open(final_path, mode) as f:
            f.write(content)
        return
    
    # An identical file already exists.
    if content == read_from(final_path):
        print formatm('identical', created_path, color='magenta', attrs=[])
        return
    
    # A different file already exists.
    print formatm('conflict', created_path, color='red')
    msg = '  Overwrite %s? (y/n)' % final_path
    overwrite = prompt_bool(msg, default=True)
    action = 'force' if overwrite else 'skip' 
    print formatm(action, created_path, color='yellow')
    if overwrite:
        with io.open(final_path, mode) as f:
            f.write(content)    


def reanimate_skeleton(skeleton_path, new_app_path, data=None, filter_ext=None,
        env_options=None):
    
    ppath, pname = os.path.split(new_app_path)
    jinja_loader = jinja2.FileSystemLoader(skeleton_path)

    data = {} if data is None else data
    _data = DEFAULT_DATA.copy()
    _data.update(data)
    _data.setdefault('PNAME', pname)
    data = _data

    filter_ext = DEFAULT_FILTER_EXT if filter_ext is None else filter_ext

    env_options = {} if env_options is None else {}
    _env_options = DEFAULT_ENV_OPTIONS.copy()
    _env_options.update(env_options)
    _env_options.setdefault('loader', jinja_loader)
    env_options = _env_options
    
    jinja_env = jinja2.Environment(**env_options)

    for folder, subs, files in os.walk(skeleton_path):
        ffolder = os.path.relpath(folder, skeleton_path)
        
        for filename in files:
            if filename.endswith(filter_ext):
                continue
            src_path = os.path.join(folder, filename)
            content = read_from(src_path)
            
            if filename.endswith('.tmpl'):
                if not isinstance(content, unicode):
                    content = unicode(content, 'utf-8')
                filename = re.sub(r'\.tmpl$', '', filename)
                tmpl = jinja_env.from_string(content)
                content = tmpl.render(data).encode('utf-8')
            filename = re.sub(r'%PNAME%', pname, filename)
            
            make_file(new_app_path, ffolder, filename, content)
            

