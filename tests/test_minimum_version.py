import pytest
from plumbum import local
from plumbum.cmd import git

import copier
from copier.config.factory import make_config
from copier.config.objects import UserMessageError


def test_version_less_than_required(monkeypatch):
    monkeypatch.setattr("copier.__version__", "0.0.0a0")
    with pytest.raises(UserMessageError):
        make_config("./tests/demo_minimum_version")


def test_version_equal_required(monkeypatch):
    monkeypatch.setattr("copier.__version__", "10.5.1")
    # assert no error
    make_config("./tests/demo_minimum_version")


def test_version_greater_than_required(monkeypatch):
    monkeypatch.setattr("copier.__version__", "99.99.99")
    # assert no error
    make_config("./tests/demo_minimum_version")


def test_minimum_version_update(tmp_path, monkeypatch):
    monkeypatch.setattr("copier.__version__", "99.99.99")
    copier.copy("./tests/demo_minimum_version", tmp_path)

    with local.cwd(tmp_path):
        git("init")
        git("config", "user.name", "Copier Test")
        git("config", "user.email", "test@copier")
        git("add", ".")
        git("commit", "-m", "hello world")

    monkeypatch.setattr("copier.__version__", "0.0.0.post0")
    with pytest.raises(UserMessageError):
        make_config("./tests/demo_minimum_version", tmp_path)

    monkeypatch.setattr("copier.__version__", "10.5.1")
    # assert no error
    make_config("./tests/demo_minimum_version", tmp_path)

    monkeypatch.setattr("copier.__version__", "99.99.99")
    # assert no error
    make_config("./tests/demo_minimum_version", tmp_path)


def test_version_0_0_0_ignored(monkeypatch):
    monkeypatch.setattr("copier.__version__", "0.0.0")
    # assert no error
    make_config("./tests/demo_minimum_version")
