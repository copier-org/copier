from __future__ import annotations

from contextlib import AbstractContextManager, nullcontext as does_not_raise
from pathlib import Path

import pytest
import yaml
from jinja2.ext import Extension
from plumbum import local

from copier._cli import CopierApp
from copier._main import run_copy, run_update
from copier._types import AnyByStrDict
from copier._user_data import load_answersfile_data
from copier.errors import UnsafeTemplateError

from .helpers import build_file_tree, git


class JinjaExtension(Extension): ...


@pytest.mark.parametrize(
    ("spec", "expected"),
    [
        (
            {},
            does_not_raise(),
        ),
        (
            {"_tasks": []},
            does_not_raise(),
        ),
        (
            {"_tasks": ["touch task.txt"]},
            pytest.raises(
                UnsafeTemplateError,
                match="Template uses potentially unsafe feature: tasks.",
            ),
        ),
        (
            {"_migrations": []},
            does_not_raise(),
        ),
        (
            {
                "_migrations": [
                    {
                        "version": "v1",
                        "when": "{{ _stage == 'before' }}",
                        "command": "touch v1-before.txt",
                    },
                    {
                        "version": "v1",
                        "when": "{{ _stage == 'after' }}",
                        "command": "touch v1-after.txt",
                    },
                ]
            },
            does_not_raise(),
        ),
        (
            {"_jinja_extensions": []},
            does_not_raise(),
        ),
        (
            {"_jinja_extensions": ["tests.test_unsafe.JinjaExtension"]},
            pytest.raises(
                UnsafeTemplateError,
                match="Template uses potentially unsafe feature: jinja_extensions.",
            ),
        ),
        (
            {
                "_tasks": ["touch task.txt"],
                "_jinja_extensions": ["tests.test_unsafe.JinjaExtension"],
            },
            pytest.raises(
                UnsafeTemplateError,
                match="Template uses potentially unsafe features: jinja_extensions, tasks.",
            ),
        ),
    ],
)
@pytest.mark.parametrize("unsafe", [False, True])
def test_copy(
    tmp_path_factory: pytest.TempPathFactory,
    unsafe: bool,
    spec: AnyByStrDict,
    expected: AbstractContextManager[None],
) -> None:
    src, dst = map(tmp_path_factory.mktemp, ["src", "dst"])
    build_file_tree({(src / "copier.yaml"): yaml.safe_dump(spec)})
    with does_not_raise() if unsafe else expected:
        run_copy(str(src), dst, unsafe=unsafe)


@pytest.mark.parametrize("unsafe", [False, True])
@pytest.mark.parametrize("trusted_from_settings", [False, True])
def test_copy_cli(
    tmp_path_factory: pytest.TempPathFactory,
    capsys: pytest.CaptureFixture[str],
    unsafe: bool,
    trusted_from_settings: bool,
    settings_path: Path,
) -> None:
    src, dst = map(tmp_path_factory.mktemp, ["src", "dst"])
    build_file_tree(
        {(src / "copier.yaml"): yaml.safe_dump({"_tasks": ["touch task.txt"]})}
    )
    if trusted_from_settings:
        settings_path.write_text(f"trust: ['{src}']")

    _, retcode = CopierApp.run(
        ["copier", "copy", *(["--UNSAFE"] if unsafe else []), str(src), str(dst)],
        exit=False,
    )
    if unsafe or trusted_from_settings:
        assert retcode == 0
    else:
        assert retcode == 4
        _, err = capsys.readouterr()
        assert "Template uses potentially unsafe feature: tasks." in err


@pytest.mark.parametrize(
    ("spec_old", "spec_new", "expected"),
    [
        (
            {},
            {},
            does_not_raise(),
        ),
        (
            {"_tasks": []},
            {"_tasks": []},
            does_not_raise(),
        ),
        (
            {"_tasks": ["touch task-old.txt"]},
            {},
            pytest.raises(
                UnsafeTemplateError,
                match="Template uses potentially unsafe feature: tasks.",
            ),
        ),
        (
            {},
            {"_tasks": ["touch task-new.txt"]},
            pytest.raises(
                UnsafeTemplateError,
                match="Template uses potentially unsafe feature: tasks.",
            ),
        ),
        (
            {"_tasks": ["touch task-old.txt"]},
            {"_tasks": ["touch task-new.txt"]},
            pytest.raises(
                UnsafeTemplateError,
                match="Template uses potentially unsafe feature: tasks.",
            ),
        ),
        (
            {"_migrations": []},
            {"_migrations": []},
            does_not_raise(),
        ),
        (
            {},
            {
                "_migrations": [
                    {
                        "version": "v0",
                        "command": "touch v0-before.txt",
                        "when": "{{ _stage == 'before' }}",
                    },
                    {
                        "version": "v0",
                        "command": "touch v0-after.txt",
                        "when": "{{ _stage == 'after' }}",
                    },
                ]
            },
            does_not_raise(),
        ),
        (
            {},
            {
                "_migrations": [
                    {
                        "version": "v2",
                        "before": [],
                        "after": [],
                    }
                ]
            },
            # This case only exists on legacy migrations and raises a DeprecationWarning
            pytest.deprecated_call(),
        ),
        (
            {},
            {
                "_migrations": [
                    {
                        "version": "v2",
                        "when": "{{ _stage == 'before' }}",
                        "command": "touch v2-before.txt",
                    }
                ]
            },
            pytest.raises(
                UnsafeTemplateError,
                match="Template uses potentially unsafe feature: migrations.",
            ),
        ),
        (
            {},
            {
                "_migrations": [
                    {
                        "version": "v2",
                        "when": "{{ _stage == 'after' }}",
                        "command": "touch v2-after.txt",
                    }
                ]
            },
            pytest.raises(
                UnsafeTemplateError,
                match="Template uses potentially unsafe feature: migrations.",
            ),
        ),
        (
            {},
            {
                "_migrations": [
                    {
                        "version": "v2",
                        "when": "{{ _stage == 'before' }}",
                        "command": "touch v2-before.txt",
                    },
                    {
                        "version": "v2",
                        "when": "{{ _stage == 'after' }}",
                        "command": "touch v2-after.txt",
                    },
                ]
            },
            pytest.raises(
                UnsafeTemplateError,
                match="Template uses potentially unsafe feature: migrations.",
            ),
        ),
        (
            {"_jinja_extensions": []},
            {"_jinja_extensions": []},
            does_not_raise(),
        ),
        (
            {"_jinja_extensions": ["tests.test_unsafe.JinjaExtension"]},
            {},
            pytest.raises(
                UnsafeTemplateError,
                match="Template uses potentially unsafe feature: jinja_extensions.",
            ),
        ),
        (
            {},
            {"_jinja_extensions": ["tests.test_unsafe.JinjaExtension"]},
            pytest.raises(
                UnsafeTemplateError,
                match="Template uses potentially unsafe feature: jinja_extensions.",
            ),
        ),
        (
            {"_jinja_extensions": ["tests.test_unsafe.JinjaExtension"]},
            {"_jinja_extensions": ["tests.test_unsafe.JinjaExtension"]},
            pytest.raises(
                UnsafeTemplateError,
                match="Template uses potentially unsafe feature: jinja_extensions",
            ),
        ),
        (
            {},
            {
                "_tasks": ["touch task-new.txt"],
                "_migrations": [
                    {
                        "version": "v2",
                        "when": "{{ _stage == 'before' }}",
                        "command": "touch v2-before.txt",
                    },
                    {
                        "version": "v2",
                        "when": "{{ _stage == 'after' }}",
                        "command": "touch v2-after.txt",
                    },
                ],
                "_jinja_extensions": ["tests.test_unsafe.JinjaExtension"],
            },
            pytest.raises(
                UnsafeTemplateError,
                match=(
                    "Template uses potentially unsafe features: "
                    "jinja_extensions, migrations, tasks."
                ),
            ),
        ),
    ],
)
@pytest.mark.parametrize("unsafe", [False, True])
def test_update(
    tmp_path_factory: pytest.TempPathFactory,
    unsafe: bool,
    spec_old: AnyByStrDict,
    spec_new: AnyByStrDict,
    expected: AbstractContextManager[None],
) -> None:
    src, dst = map(tmp_path_factory.mktemp, ["src", "dst"])

    with local.cwd(src):
        build_file_tree(
            {
                "{{ _copier_conf.answers_file }}.jinja": "{{ _copier_answers | to_nice_yaml }}",
                "copier.yaml": yaml.safe_dump(spec_old),
            }
        )
        git("init")
        git("add", ".")
        git("commit", "-m1")
        git("tag", "v1")

    run_copy(str(src), dst, unsafe=True)
    assert load_answersfile_data(dst).get("_commit") == "v1"

    with local.cwd(dst):
        git("init")
        git("add", ".")
        git("commit", "-m1")

    with local.cwd(src):
        build_file_tree(
            {
                "copier.yaml": yaml.safe_dump(spec_new),
            }
        )
        git("add", ".")
        git("commit", "-m2", "--allow-empty")
        git("tag", "v2")

    with does_not_raise() if unsafe else expected:
        run_update(dst, overwrite=True, unsafe=unsafe)


@pytest.mark.parametrize("unsafe", [False, "--trust", "--UNSAFE"])
@pytest.mark.parametrize("trusted_from_settings", [False, True])
def test_update_cli(
    tmp_path_factory: pytest.TempPathFactory,
    capsys: pytest.CaptureFixture[str],
    unsafe: bool | str,
    trusted_from_settings: bool,
    settings_path: Path,
) -> None:
    src, dst = map(tmp_path_factory.mktemp, ["src", "dst"])
    unsafe_args = [unsafe] if unsafe else []

    with local.cwd(src):
        build_file_tree(
            {
                "{{ _copier_conf.answers_file }}.jinja": "{{ _copier_answers | to_nice_yaml }}",
                "copier.yaml": "",
            }
        )
        git("init")
        git("add", ".")
        git("commit", "-m1")
        git("tag", "v1")

    if trusted_from_settings:
        settings_path.write_text(f"trust: ['{src}']")

    _, retcode = CopierApp.run(
        ["copier", "copy", str(src), str(dst)] + unsafe_args,
        exit=False,
    )
    assert retcode == 0
    assert load_answersfile_data(dst).get("_commit") == "v1"
    capsys.readouterr()

    with local.cwd(dst):
        git("init")
        git("add", ".")
        git("commit", "-m1")

    with local.cwd(src):
        build_file_tree(
            {
                "copier.yaml": yaml.safe_dump({"_tasks": ["touch task-new.txt"]}),
            }
        )
        git("add", ".")
        git("commit", "-m2")
        git("tag", "v2")

    _, retcode = CopierApp.run(
        [
            "copier",
            "update",
            str(dst),
        ]
        + unsafe_args,
        exit=False,
    )
    if unsafe or trusted_from_settings:
        assert retcode == 0
    else:
        assert retcode == 4
        _, err = capsys.readouterr()
        assert "Template uses potentially unsafe feature: tasks." in err
