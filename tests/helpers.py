# -*- coding: utf-8 -*-
from hashlib import sha1
from os import urandom
from os.path import join, dirname
import filecmp
import io

import voodoo


SKELETON_PATH = join(dirname(__file__), 'demo')

DATA = {
    'package': 'demo',
    'py3': True,
    'make_secret': lambda: sha1(urandom(48)).hexdigest(),
    'myvar': 'awesome'
}


def render(dst, **kwargs):
    kwargs.setdefault('quiet', True)
    voodoo.render_skeleton(SKELETON_PATH, dst, data=DATA, **kwargs)


def read_content(path):
    with io.open(path, mode='rt', encoding='utf8') as f:
        return f.read()


def write_content(path, content):
    with io.open(path, mode='wt', encoding='utf8') as f:
        return f.write(content)


def assert_file(dst, *path):
    p1 = join(dst, *path)
    p2 = join(SKELETON_PATH, *path)
    assert filecmp.cmp(p1, p2)
