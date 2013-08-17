# -*- coding: utf-8 -*-
from os.path import exists, join

import pytest
import shutil
import voodoo


def test_get_vcs_from_url():
    get = voodoo.download.get_vcs_from_url

    assert get('git+git://git.myproject.org/MyProject').name == 'git'
    assert get('git+https://git.myproject.org/MyProject').name == 'git'
    assert get('git+ssh://git.myproject.org/MyProject').name == 'git'
    assert get('git+git@git.myproject.org:MyProject').name == 'git'
    assert get('git://git.myproject.org/MyProject.git@master').name == 'git'
    assert get('git://git.myproject.org/MyProject.git@v1.0').name == 'git'
    assert get('git://git.myproject.org/MyProject.git@da39a3ee5e6b4b0d3255bfef95601890afd80709').name == 'git'

    assert get('hg+http://hg.myproject.org/MyProject').name == 'hg'
    assert get('hg+https://hg.myproject.org/MyProject').name == 'hg'
    assert get('hg+ssh://hg.myproject.org/MyProject').name == 'hg'
    assert get('hg+http://hg.myproject.org/MyProject@da39a3ee5e6b').name == 'hg'
    assert get('hg+http://hg.myproject.org/MyProject@2019').name == 'hg'
    assert get('hg+http://hg.myproject.org/MyProject@v1.0').name == 'hg'
    assert get('hg+http://hg.myproject.org/MyProject@special_feature').name == 'hg'

    assert get('svn+svn://svn.myproject.org/svn/MyProject').name == 'svn'
    assert get('svn+http://svn.myproject.org/svn/MyProject/trunk@2019').name == 'svn'
    
    assert get('bzr+http://bzr.myproject.org/MyProject/trunk').name == 'bzr'
    assert get('bzr+sftp://user@myproject.org/MyProject/trunk').name == 'bzr'
    assert get('bzr+ssh://user@myproject.org/MyProject/trunk').name == 'bzr'
    assert get('bzr+ftp://user@myproject.org/MyProject/trunk').name == 'bzr'
    assert get('bzr+lp:MyProject').name == 'bzr'
    assert get('bzr+https://bzr.myproject.org/MyProject/trunk@2019').name == 'bzr'
    assert get('bzr+http://bzr.myproject.org/MyProject/trunk@v1.0').name == 'bzr'

    assert get('http://google.com') == None
    assert get('git.myproject.org/MyProject') == None


@pytest.mark.slow
def test_download_full():
    urls = [
        'git+git@github.com:lucuma/Voodoo.git',
        'git+https://github.com/lucuma/Voodoo.git',
    ]
    for url in urls:
        vcs = voodoo.download.get_vcs_from_url(url)
        tmp = voodoo.download.download(vcs)
        assert exists(join(tmp, 'tests', 'test_render.py'))
        shutil.rmtree(tmp)
