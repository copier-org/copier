# -*- coding: utf-8 -*-
from os.path import join, dirname
from tempfile import mkdtemp
from uuid import uuid4
import filecmp
import io
import shutil

from voodoo import render_skeleton


SKELETON_PATH = join(dirname(__file__), 'demo')


def read_content(path):
    with io.open(path, mode='rt', encoding='utf8') as f:
        return f.read()


def write_content(path, content):
    with io.open(path, mode='wt', encoding='utf8') as f:
        return f.write(content)


class RenderMixin(object):

    def setUp(self):
        self.dst_path = mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.dst_path)

    def assert_file(self, *path):
        p1 = join(self.dst_path, *path)
        p2 = join(SKELETON_PATH, *path)
        assert filecmp.cmp(p1, p2)

    def render_skeleton(self, **kwargs):
        data = {
            'package': 'demo',
            'py3': True,
            'make_uid': lambda: str(uuid4())
        }
        kwargs.setdefault('quiet', True)
        render_skeleton(SKELETON_PATH, self.dst_path, data=data, **kwargs)
