import json
import sys
from pathlib import Path
from uuid import uuid4

import pytest
from plumbum import local

import copier

from .helpers import build_file_tree, git_save


def test_no_path_variables(
    tmp_path_factory: pytest.TempPathFactory, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test that there are no context variables of type `pathlib.Path`."""
    src, dst = map(tmp_path_factory.mktemp, ("src", "dst"))
    ext_module_name = uuid4()
    build_file_tree(
        {
            src / f"{ext_module_name}.py": (
                """\
                from pathlib import Path
                from typing import Any, Mapping

                from jinja2 import Environment, pass_context
                from jinja2.ext import Extension
                from jinja2.runtime import Context
                from pydantic import BaseModel


                class ContextExtension(Extension):
                    def __init__(self, environment: Environment) -> None:
                        super().__init__(environment)
                        environment.globals["__assert"] = self._assert

                    @pass_context
                    def _assert(self, ctx: Context) -> None:
                        items: list[tuple[str, Any]] = list(dict(ctx).items())
                        for k, v in items:
                            if isinstance(v, Path):
                                raise AssertionError(
                                    f"{k} must not be a `pathlib.Path` object"
                                )
                            if isinstance(v, BaseModel):
                                v = dict(v)
                            if isinstance(v, Mapping):
                                items.extend((f"{k}.{k2}", v2) for k2, v2 in v.items())
                            elif isinstance(v, (list, tuple, set)):
                                items.extend((f"{k}[{i}]", v2) for i, v2 in enumerate(v))
                """
            ),
            src / "copier.yml": (
                f"""\
                _jinja_extensions:
                    - {ext_module_name}.ContextExtension
                """
            ),
            src / "test.txt.jinja": "{{ __assert() | default('', true) }}",
        }
    )
    monkeypatch.setattr("sys.path", [str(src), *sys.path])
    copier.run_copy(str(src), dst, unsafe=True)
    assert (dst / "test.txt").read_text("utf-8") == ""


def test_exclude_templating_with_operation(
    tmp_path_factory: pytest.TempPathFactory,
) -> None:
    """
    Ensure it's possible to create one-off boilerplate files that are not
    managed during updates via `_exclude` using the `_copier_operation` context variable.
    """
    src, dst = map(tmp_path_factory.mktemp, ("src", "dst"))

    template = "{% if _copier_operation == 'update' %}copy-only{% endif %}"
    with local.cwd(src):
        build_file_tree(
            {
                "copier.yml": f'_exclude:\n - "{template}"',
                "{{ _copier_conf.answers_file }}.jinja": "{{ _copier_answers|to_yaml }}",
                "copy-only": "foo",
                "copy-and-update": "foo",
            }
        )
        git_save(tag="1.0.0")
        build_file_tree(
            {
                "copy-only": "bar",
                "copy-and-update": "bar",
            }
        )
        git_save(tag="2.0.0")
    copy_only = dst / "copy-only"
    copy_and_update = dst / "copy-and-update"

    copier.run_copy(str(src), dst, defaults=True, overwrite=True, vcs_ref="1.0.0")
    for file in (copy_only, copy_and_update):
        assert file.exists()
        assert file.read_text() == "foo"

    with local.cwd(dst):
        git_save()

    copier.run_update(str(dst), overwrite=True)
    assert copy_only.read_text() == "foo"
    assert copy_and_update.read_text() == "bar"


def test_task_templating_with_operation(
    tmp_path_factory: pytest.TempPathFactory, tmp_path: Path
) -> None:
    """
    Ensure that it is possible to define tasks that are only executed when copying.
    """
    src, dst = map(tmp_path_factory.mktemp, ("src", "dst"))
    # Use a file outside the Copier working directories to ensure accurate tracking
    task_counter = tmp_path / "task_calls.txt"
    with local.cwd(src):
        build_file_tree(
            {
                "copier.yml": (
                    f"""\
                    _tasks:
                        -   command: echo {{{{ _copier_operation }}}} >> {json.dumps(str(task_counter))}
                            when: "{{{{ _copier_operation == 'copy' }}}}"
                    """
                ),
                "{{ _copier_conf.answers_file }}.jinja": "{{ _copier_answers|to_yaml }}",
            }
        )
        git_save(tag="1.0.0")

    copier.run_copy(str(src), dst, defaults=True, overwrite=True, unsafe=True)
    assert task_counter.exists()
    assert len(task_counter.read_text().splitlines()) == 1

    with local.cwd(dst):
        git_save()

    copier.run_recopy(dst, defaults=True, overwrite=True, unsafe=True)
    assert len(task_counter.read_text().splitlines()) == 2

    copier.run_update(dst, defaults=True, overwrite=True, unsafe=True)
    assert len(task_counter.read_text().splitlines()) == 2
