# -*- coding: utf-8 -*-
from os import makedirs, listdir
from os.path import exists, isdir, abspath, join

def ensure_directory(d):
    if not exists(d):
        makedirs(d)

def list_dirs(d):
    """Return the directories in `d`."""
    dirpath = abspath(d)
    for filename in listdir(d):
        fullpath = join(dirpath, filename)
        if isdir(fullpath):
            yield fullpath
