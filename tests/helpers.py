from hashlib import sha1
from os import urandom
from os.path import join, dirname
import filecmp
import io

from .. import copier


PROJECT_TEMPLATE = join(dirname(__file__), 'demo')

DATA = {
    'py3': True,
    'make_secret': lambda: sha1(urandom(48)).hexdigest(),
    'myvar': 'awesome',
    'what': 'world',
    'project_name': 'Copier',
    'version': '2.0.0',
    'description': 'A library for rendering projects templates',
}


def render(dst, **kwargs):
    kwargs.setdefault('quiet', True)
    copier.copy(PROJECT_TEMPLATE, dst, data=DATA, **kwargs)


def read_content(path):
    with io.open(path, mode='rt') as f:
        return f.read()


def write_content(path, content):
    with io.open(path, mode='wt') as f:
        return f.write(content)


def assert_file(dst, *path):
    p1 = join(dst, *path)
    p2 = join(PROJECT_TEMPLATE, *path)
    assert filecmp.cmp(p1, p2)
