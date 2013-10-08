# -*- coding: utf-8 -*-
from os.path import exists, join

import pytest
import shutil
import voodoo


def test_get_vcs_from_url():
    get = voodoo.vcs.get_vcs_from_url

    assert get('git@git.myproject.org:MyProject').type == 'git'
    assert get('git://git.myproject.org/MyProject').type == 'git'
    assert get('git+https://git.myproject.org/MyProject').type == 'git'
    assert get('git+ssh://git.myproject.org/MyProject').type == 'git'
    assert get('https://github.com/lucuma/voodoo-flask.git').type == 'git'
    assert get('git://git.myproject.org/MyProject.git@master').type == 'git'
    assert get('git://git.myproject.org/MyProject.git@v1.0').type == 'git'
    assert get('git://git.myproject.org/MyProject.git@da39a3ee5e6b4b0d3255bfef95601890afd80709').type == 'git'

    assert get('hg+http://hg.myproject.org/MyProject').type == 'hg'
    assert get('hg+https://hg.myproject.org/MyProject').type == 'hg'
    assert get('hg+ssh://hg.myproject.org/MyProject').type == 'hg'
    assert get('hg+http://hg.myproject.org/MyProject@da39a3ee5e6b').type == 'hg'
    assert get('hg+http://hg.myproject.org/MyProject@2019').type == 'hg'
    assert get('hg+http://hg.myproject.org/MyProject@v1.0').type == 'hg'
    assert get('hg+http://hg.myproject.org/MyProject@special_feature').type == 'hg'

    assert get('http://google.com') == None
    assert get('git.myproject.org/MyProject') == None


@pytest.mark.slow
def test_clone():
    urls = [
        'git@github.com:lucuma/Voodoo.git',
    ]
    for url in urls:
        vcs = voodoo.vcs.get_vcs_from_url(url)
        tmp = voodoo.vcs.clone(vcs)
        assert exists(join(tmp, 'setup.py'))
        shutil.rmtree(tmp)
