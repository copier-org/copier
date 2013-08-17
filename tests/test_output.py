# -*- coding: utf-8 -*-
from __future__ import print_function
import re

from .helpers import render


def test_output(capsys, dst):
    render(dst, quiet=False)
    out, err = capsys.readouterr()

    assert re.search(r'create[^\s]+  config\.py', out)
    assert re.search(r'create[^\s]+  setup\.py', out)
    assert re.search(r'create[^\s]+  doc/images/nslogo\.gif', out)


def test_output_pretend(capsys, dst):
    render(dst, quiet=False, pretend=True)
    out, err = capsys.readouterr()

    assert re.search(r'create[^\s]+  config\.py', out)
    assert re.search(r'create[^\s]+  setup\.py', out)
    assert re.search(r'create[^\s]+  doc/images/nslogo\.gif', out)


def test_output_force(capsys, dst):
    render(dst)
    out, err = capsys.readouterr()
    render(dst, quiet=False, force=True)
    out, err = capsys.readouterr()
    print(out)

    assert re.search(r'conflict[^\s]+  config\.py', out)
    assert re.search(r'force[^\s]+  config\.py', out)
    assert re.search(r'identical[^\s]+  setup\.py', out)
    assert re.search(r'identical[^\s]+  doc/images/nslogo\.gif', out)


def test_output_skip(capsys, dst):
    render(dst)
    out, err = capsys.readouterr()
    render(dst, quiet=False, skip=True)
    out, err = capsys.readouterr()
    print(out)

    assert re.search(r'conflict[^\s]+  config\.py', out)
    assert re.search(r'skip[^\s]+  config\.py', out)
    assert re.search(r'identical[^\s]+  setup\.py', out)
    assert re.search(r'identical[^\s]+  doc/images/nslogo\.gif', out)


def test_output_quiet(capsys, dst):
    render(dst, quiet=True)
    out, err = capsys.readouterr()
    assert out == u''

