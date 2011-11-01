#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
    # Voodoo

    Reanimates an application skeleton, just for you.
    
    ---------------------------------------
    Copyright © 2010-2011 by Lúcuma labs (http://lucumalabs.com).
    MIT License. (http://www.opensource.org/licenses/mit-license.php)

"""
import datetime
import errno
import os
import re

import jinja2


COLOR_OKGREEN = '\033[92m'
COLOR_END = '\033[0m'

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


def make_dirs(*lpath):
    path = os.path.join(*lpath)
    try:
        os.makedirs(os.path.dirname(path))
    except (OSError), e:
        if e.errno != errno.EEXIST:
            raise
    return path


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
    
    print 'Using skeleton:', skeleton_path
    print '\n  %s/' % new_app_path
    
    jinja_env = jinja2.Environment(**env_options)

    for folder, subs, files in os.walk(skeleton_path):
        ffolder = os.path.relpath(folder, skeleton_path)
        
        for filename in files:
            if filename.endswith(filter_ext):
                continue
            src_path = os.path.join(folder, filename)
            f = open(src_path, 'rb')
            try:
                content = f.read()
            finally:
                f.close()
            
            if filename.endswith('.tmpl'):
                if not isinstance(content, unicode):
                    content = unicode(content, 'utf-8')
                filename = re.sub(r'\.tmpl$', '', filename)
                tmpl = jinja_env.from_string(content)
                content = tmpl.render(data).encode('utf-8')
            filename = re.sub(r'%PNAME%', pname, filename)
            
            msg = ''.join([
                COLOR_OKGREEN, '    create', COLOR_END, '  ',
                os.path.join(ffolder, filename).lstrip('.').lstrip('/'),
                ])
            print msg
            
            final_path = make_dirs(new_app_path, ffolder, filename)
            f = open(final_path, 'wb')
            try:
                f.write(content)
            finally:
                f.close()

