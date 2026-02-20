from __future__ import annotations

import os
import platform
from collections.abc import Sequence
from pathlib import Path

import pytest
import yaml

from copier import Settings, load_settings, run_copy
from copier._settings import _default_settings_path, is_trusted_repository
from copier.errors import MissingSettingsWarning, SettingsError
from tests.helpers import build_file_tree


def test_default_settings() -> None:
    settings = Settings()

    assert settings.defaults == {}
    assert settings.trust == []


def test_load_settings_from_default_location(settings_path: Path) -> None:
    settings_path.write_text("defaults:\n  foo: bar")

    settings = load_settings()

    assert settings.defaults == {"foo": "bar"}


@pytest.mark.skipif(platform.system() != "Windows", reason="Windows-only test")
def test_default_windows_settings_path() -> None:
    assert _default_settings_path() == Path(
        os.getenv("USERPROFILE", default=""),
        "AppData",
        "Local",
        "copier",
        "settings.yml",
    )


@pytest.mark.usefixtures("config_path")
def test_load_settings_from_default_location_dont_exist() -> None:
    settings = load_settings()

    assert settings.defaults == {}


def test_settings_from_env_location(
    settings_path: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    settings_path.write_text("defaults:\n  foo: bar")

    settings_from_env_path = tmp_path / "settings.yml"
    settings_from_env_path.write_text("defaults:\n  foo: baz")

    monkeypatch.setenv("COPIER_SETTINGS_PATH", str(settings_from_env_path))

    settings = load_settings()

    assert settings.defaults == {"foo": "baz"}


def test_load_settings_from_param(
    settings_path: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    settings_path.write_text("defaults:\n  foo: bar")

    settings_from_env_path = tmp_path / "settings.yml"
    settings_from_env_path.write_text("defaults:\n  foo: baz")

    monkeypatch.setenv("COPIER_SETTINGS_PATH", str(settings_from_env_path))

    file_path = tmp_path / "file.yml"
    file_path.write_text("defaults:\n  from: file")

    settings = load_settings(file_path)

    assert settings.defaults == {"from": "file"}


def test_load_settings_env_defined_but_missing(
    settings_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("COPIER_SETTINGS_PATH", str(settings_path))

    with pytest.warns(MissingSettingsWarning):
        load_settings()


@pytest.mark.parametrize(
    "encoding",
    ["utf-8", "utf-8-sig", "utf-16-le", "utf-16-be"],
)
def test_load_settings_from_utf_file(
    settings_path: Path, monkeypatch: pytest.MonkeyPatch, encoding: str
) -> None:
    def _encode(data: str) -> bytes:
        if encoding.startswith("utf-16"):
            data = f"\ufeff{data}"
        return data.encode(encoding)

    defaults = {
        "foo": "\u3053\u3093\u306b\u3061\u306f",  # japanese hiragana
        "bar": "\U0001f60e",  # smiling face with sunglasses
    }

    settings_path.write_bytes(
        _encode(yaml.dump({"defaults": defaults}, allow_unicode=True))
    )

    with monkeypatch.context() as m:
        # Override the factor that determines the default encoding when opening files.
        m.setattr("io.text_encoding", lambda *_args: "cp932")
        settings = load_settings()

    assert settings.defaults == defaults


@pytest.mark.parametrize(
    ("data", "error"),
    [
        (
            b"\x00",
            "^Invalid YAML data: unacceptable character",
        ),
        (
            b"defaults: should be an object",
            "^Invalid format:\n  defaults:\n    Input should be a valid dictionary",
        ),
        (
            b"trust: should be an array",
            "^Invalid format:\n  trust:\n    Input should be a valid set",
        ),
    ],
)
def test_load_settings_with_invalid_data(
    settings_path: Path, data: bytes, error: str
) -> None:
    settings_path.write_bytes(data)

    with pytest.raises(SettingsError, match=error):
        load_settings(settings_path)


@pytest.mark.parametrize(
    ("repository", "trust", "expected"),
    [
        ("https://github.com/user/repo.git", [], False),
        (
            "https://github.com/user/repo.git",
            {"https://github.com/user/repo.git"},
            True,
        ),
        ("https://github.com/user/repo", {"https://github.com/user/repo.git"}, False),
        ("https://github.com/user/repo.git", {"https://github.com/user/"}, True),
        ("https://github.com/user/repo.git", {"https://github.com/user/repo"}, False),
        ("https://github.com/user/repo.git", {"https://github.com/user"}, False),
        ("https://github.com/user/repo.git", {"https://github.com/"}, True),
        ("https://github.com/user/repo.git", {"https://github.com"}, False),
        (f"{Path.home()}/template", [], False),
        (f"{Path.home()}/template", {f"{Path.home()}/template"}, True),
        (f"{Path.home()}/template", {"~/template"}, True),
        (f"{Path.home()}/path/to/template", {"~/path/to/template"}, True),
        (f"{Path.home()}/path/to/template", {"~/path/to/"}, True),
        (f"{Path.home()}/path/to/template", {"~/path/to"}, False),
    ],
)
def test_is_trusted(repository: str, trust: Sequence[str], expected: bool) -> None:
    assert is_trusted_repository(trust, repository) == expected


def test_copy_with_defaults(tmp_path_factory: pytest.TempPathFactory) -> None:
    src, dst = map(tmp_path_factory.mktemp, ("src", "dst"))
    build_file_tree(
        {
            src / "copier.yml": "project_name: foo",
            src / "result.txt.jinja": "{{ project_name }}",
        }
    )
    run_copy(
        str(src),
        dst,
        defaults=True,
        settings=Settings(defaults={"project_name": "bar"}),
    )
    assert (dst / "result.txt").read_text() == "bar"
