# -*- coding: utf-8 -*-
from os.path import join, dirname, exists

import pytest
import voodoo

from .helpers import (read_content, write_content, assert_file, render,
                      SKELETON_PATH, DATA, filecmp)


def test_skeleton_not_found(dst):
    with pytest.raises(ValueError):
        voodoo.render_skeleton('foobar', dst)
    with pytest.raises(ValueError):
        voodoo.render_skeleton(__file__, dst)


def test_render(dst):
    render(dst)

    generated = read_content(join(dst, 'setup.py')).strip()
    control = read_content(join(dirname(__file__), 'ref.txt')).strip()
    assert generated == control

    assert_file(dst, u'doc', u'mañana.txt')
    assert_file(dst, u'doc', u'images', u'nslogo.gif')

    p1 = join(dst, u'awesome', u'hello.txt')
    p2 = join(SKELETON_PATH, u'[[ myvar ]]', u'hello.txt')
    assert filecmp.cmp(p1, p2)

    p1 = join(dst, u'awesome.txt')
    p2 = join(SKELETON_PATH, u'[[ myvar ]].txt')
    assert filecmp.cmp(p1, p2)

    p1 = join(dst, u'awesome_', u'hello.txt')
    p2 = join(SKELETON_PATH, u'{{ myvar }}_', u'hello.txt')
    assert filecmp.cmp(p1, p2)

    p1 = join(dst, u'awesome_.txt')
    assert exists(p1)


def test_default_filter(dst):
    render(dst)
    assert not exists(join(dst, '.gitignore'))
    assert not exists(join(dst, 'build', '.gittouch'))


def test_include_file(dst):
    render(dst, include_this=['.gitignore'])
    assert_file(dst, '.gitignore')
    assert not exists(join(dst, 'build', '.gittouch'))


def test_include_pattern(dst):
    render(dst, include_this=['build/.git*'])
    assert not exists(join(dst, '.gitignore'))
    assert_file(dst, 'build', '.gittouch')


def test_filter_file(dst):
    render(dst, filter_this=[u'mañana.txt'])
    copied = exists(join(dst, 'doc', u'mañana.txt'))
    assert not copied


def test_skip_option(dst):
    render(dst)
    path = join(dst, 'setup.py')
    content = u'lorem ipsum'
    write_content(path, content)
    render(dst, skip=True)
    assert read_content(path) == content


def test_force_option(dst):
    render(dst)
    path = join(dst, 'setup.py')
    content = u'lorem ipsum'
    write_content(path, content)
    render(dst, force=True)
    assert read_content(path) != content


def test_pretend_option(dst):
    render(dst, pretend=True)
    assert not exists(join(dst, 'doc'))
    assert not exists(join(dst, 'config.py'))
    assert not exists(join(dst, 'setup.py'))
