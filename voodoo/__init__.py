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


__version__ = '0.6'


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

COLORS = {
    'OKGREEN': '\033[92m',
    'INFO': '\033[93m',
    'FAIL': '\033[91m',
    'BOLD': '\033[1m',
    'ENDC': '\033[0m',
}


def formatm(action, msg='', color='OKGREEN'):
    color = COLORS.get(color, '')
    lparts = [color, action, COLORS['ENDC'], msg]
    return ''.join(lparts)


def make_dirs(*lpath):
    path = os.path.join(*lpath)
    try:
        os.makedirs(os.path.dirname(path))
    except (OSError), e:
        if e.errno != errno.EEXIST:
            raise
    return path


def read_from(filepath, mode='rb'):
    with io.open(filepath, mode) as f:
        source = f.read()
    return source


def make_file(filepath, content, mode='wb'):
    if not isinstance(content, unicode):
        content = unicode(content, 'utf-8')
    with io.open(filepath, mode) as f:
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
            
            created_path = os.path.join(ffolder, filename) \
                .lstrip('.').lstrip('/')
            print formatm('    create', created_path)
            
            final_path = make_dirs(new_app_path, ffolder, filename)
            make_file(final_path, content)

