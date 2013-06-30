# -*- coding: utf-8 -*-
from __future__ import print_function
from os.path import join, dirname, exists
import unittest

from .helpers import read_content, write_content, RenderMixin


class RenderTests(RenderMixin, unittest.TestCase):

    def test_render(self):
        self.render_skeleton()

        generated = read_content(join(self.dst_path, 'setup.py')).strip()
        control = read_content(join(dirname(__file__), 'ref.txt')).strip()
        assert generated == control

        self.assert_file('doc', u'mañana.txt')
        self.assert_file('doc', 'images', 'nslogo.gif')

    def test_default_filter(self):
        self.render_skeleton()
        assert not exists(join(self.dst_path, '.gitignore'))
        assert not exists(join(self.dst_path, 'build', '.gittouch'))

    def test_include_file(self):
        self.render_skeleton(include_this=['.gitignore'])
        self.assert_file('.gitignore')
        assert not exists(join(self.dst_path, 'build', '.gittouch'))

    def test_include_pattern(self):
        self.render_skeleton(include_this=['build/.git*'])
        assert not exists(join(self.dst_path, '.gitignore'))
        self.assert_file('build', '.gittouch')

    def test_filter_file(self):
        self.render_skeleton(filter_this=[u'mañana.txt'])
        copied = exists(join(self.dst_path, 'doc', u'mañana.txt'))
        assert not copied

    def test_skip_option(self):
        self.render_skeleton()
        path = join(self.dst_path, 'setup.py')
        content = u'lorem ipsum'
        write_content(path, content)
        self.render_skeleton(skip=True)
        assert read_content(path) == content

    def test_force_option(self):
        self.render_skeleton()
        path = join(self.dst_path, 'setup.py')
        content = u'lorem ipsum'
        write_content(path, content)
        self.render_skeleton(force=True)
        assert read_content(path) != content

    def test_pretend_option(self):
        self.render_skeleton(pretend=True)
        assert not exists(join(self.dst_path, 'doc'))
        assert not exists(join(self.dst_path, 'config.py'))
        assert not exists(join(self.dst_path, 'setup.py'))

