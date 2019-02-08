from os.path import join, dirname, exists

import pytest

from .. import copier

from .helpers import (
    read_content,
    write_content,
    assert_file,
    render,
    PROJECT_TEMPLATE,
    DATA,
    filecmp,
)


def test_project_not_found(dst):
    with pytest.raises(ValueError):
        copier.copy('foobar', dst)

    with pytest.raises(ValueError):
        copier.copy(__file__, dst)


def test_copy(dst):
    render(dst)

    generated = read_content(join(dst, 'pyproject.toml'))
    control = read_content(join(dirname(__file__), 'pyproject.toml.ref'))
    assert generated == control

    assert_file(dst, 'doc', 'mañana.txt')
    assert_file(dst, 'doc', 'images', 'nslogo.gif')

    p1 = join(dst, 'awesome', 'hello.txt')
    p2 = join(PROJECT_TEMPLATE, '[[ myvar ]]', 'hello.txt')
    assert filecmp.cmp(p1, p2)

    p1 = join(dst, 'awesome.txt')
    p2 = join(PROJECT_TEMPLATE, '[[ myvar ]].txt')
    assert filecmp.cmp(p1, p2)


@pytest.mark.slow
def test_copy_repo(dst):
    copier.copy('gh:jpscaletti/siht.git', dst, quiet=True)
    assert exists(join(dst, 'setup.py'))


def test_default_exclude(dst):
    render(dst)
    assert not exists(join(dst, '.svn'))


def test_include_file(dst):
    render(dst, include=['.svn'])
    assert_file(dst, '.svn')


def test_include_pattern(dst):
    render(dst, include=['.*'])
    assert exists(join(dst, '.svn'))


def test_exclude_file(dst):
    render(dst, exclude=['mañana.txt'])
    assert not exists(join(dst, 'doc', 'mañana.txt'))


def test_config_exclude(dst):
    def fake_data(*_args, **_kw):
        return {
            '_exclude': ['*.txt']
        }
    copier.main._get_user_data = copier.main.get_user_data
    copier.main.get_user_data = fake_data
    copier.copy(PROJECT_TEMPLATE, dst, data=DATA, quiet=True)
    assert not exists(join(dst, 'aaaa.txt'))
    copier.main.get_user_data = copier.main._get_user_data


def test_config_exclude_overwrited(dst):
    def fake_data(*_args, **_kw):
        return {
            '_exclude': ['*.txt']
        }
    copier.main._get_user_data = copier.main.get_user_data
    copier.main.get_user_data = fake_data
    copier.copy(PROJECT_TEMPLATE, dst, data=DATA, quiet=True, exclude=[])
    assert exists(join(dst, 'aaaa.txt'))
    copier.main.get_user_data = copier.main._get_user_data


def test_config_include(dst):
    def fake_data(*_args, **_kw):
        return {
            '_include': ['.svn']
        }
    copier.main._get_user_data = copier.main.get_user_data
    copier.main.get_user_data = fake_data
    copier.copy(PROJECT_TEMPLATE, dst, data=DATA, quiet=True)
    assert exists(join(dst, '.svn'))
    copier.main.get_user_data = copier.main._get_user_data


def test_skip_option(dst):
    render(dst)
    path = join(dst, 'pyproject.toml')
    content = 'lorem ipsum'
    write_content(path, content)
    render(dst, skip=True)
    assert read_content(path) == content


def test_force_option(dst):
    render(dst)
    path = join(dst, 'pyproject.toml')
    content = 'lorem ipsum'
    write_content(path, content)
    render(dst, force=True)
    assert read_content(path) != content


def test_pretend_option(dst):
    render(dst, pretend=True)
    assert not exists(join(dst, 'doc'))
    assert not exists(join(dst, 'config.py'))
    assert not exists(join(dst, 'pyproject.toml'))
