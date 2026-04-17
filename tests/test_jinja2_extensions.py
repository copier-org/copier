import json
from pathlib import Path
from typing import Any

import pytest
from jinja2 import Environment
from jinja2.ext import Extension
from plumbum import local

import copier

from .helpers import PROJECT_TEMPLATE, build_file_tree, git_save


class FilterExtension(Extension):
    """Jinja2 extension to add a filter to the Jinja2 environment."""

    def __init__(self, environment: Environment) -> None:
        super().__init__(environment)

        def super_filter(obj: Any) -> str:
            return str(obj) + " super filter!"

        environment.filters["super_filter"] = super_filter


class GlobalsExtension(Extension):
    """Jinja2 extension to add global variables to the Jinja2 environment."""

    def __init__(self, environment: Environment) -> None:
        super().__init__(environment)

        def super_func(argument: Any) -> str:
            return str(argument) + " super func!"

        environment.globals.update(super_func=super_func)
        environment.globals.update(super_var="super var!")


@pytest.fixture
def template_with_extension(tmp_path_factory: pytest.TempPathFactory) -> Path:
    src = tmp_path_factory.mktemp("src")
    build_file_tree(
        {
            src / "extensions" / "__init__.py": "",
            src / "extensions" / "data.py": """\
                DATA_VALUE = "hello from data module"
                """,
            src / "extensions" / "filters.py": """\
                from jinja2 import Environment
                from jinja2.ext import Extension

                from extensions import data


                class DataFilter(Extension):
                    def __init__(self, environment: Environment) -> None:
                        super().__init__(environment)
                        environment.filters["data_value"] = lambda _: data.DATA_VALUE
                """,
            src / "copier.yml": """\
                _jinja_extensions:
                    - extensions.filters.DataFilter
                """,
            src
            / "{{ _copier_conf.answers_file }}.jinja": "{{ _copier_answers|to_yaml }}",
            src / "result.txt.jinja": "{{ '' | data_value }}",
        }
    )
    return src


def test_default_jinja2_extensions(tmp_path: Path) -> None:
    copier.run_copy(str(PROJECT_TEMPLATE) + "_extensions_default", tmp_path)
    super_file = tmp_path / "super_file.md"
    assert super_file.exists()
    assert super_file.read_text() == "path\n"


def test_additional_jinja2_extensions(tmp_path: Path) -> None:
    copier.run_copy(
        str(PROJECT_TEMPLATE) + "_extensions_additional", tmp_path, unsafe=True
    )
    super_file = tmp_path / "super_file.md"
    assert super_file.exists()
    assert super_file.read_text() == "super var! super func! super filter!\n"


def test_to_json_filter_with_conf(tmp_path_factory: pytest.TempPathFactory) -> None:
    src, dst = map(tmp_path_factory.mktemp, ("src", "dst"))
    build_file_tree(
        {
            src / "conf.json.jinja": "{{ _copier_conf|to_json }}",
        }
    )
    copier.run_copy(str(src), dst)
    conf_file = dst / "conf.json"
    assert conf_file.exists()
    # must not raise an error
    assert json.loads(conf_file.read_text())


def test_extension_from_copy_with_vcs_ref(
    template_with_extension: Path, tmp_path_factory: pytest.TempPathFactory
) -> None:
    dst = tmp_path_factory.mktemp("dst")
    with local.cwd(template_with_extension):
        git_save(tag="1.0.0")
    copier.run_copy(str(template_with_extension), dst, unsafe=True, vcs_ref="HEAD")
    result = dst / "result.txt"
    assert result.exists()
    assert result.read_text() == "hello from data module"


def test_extension_on_update(
    template_with_extension: Path, tmp_path_factory: pytest.TempPathFactory
) -> None:
    dst = tmp_path_factory.mktemp("dst")
    with local.cwd(template_with_extension):
        git_save(tag="1.0.0")
    # Initial copy
    copier.run_copy(
        str(template_with_extension),
        dst,
        unsafe=True,
        vcs_ref="1.0.0",
        defaults=True,
        overwrite=True,
    )
    assert (dst / "result.txt").read_text() == "hello from data module"
    with local.cwd(dst):
        git_save()
    # Add a new file in v2 (extension stays the same)
    build_file_tree({template_with_extension / "v2.txt": "new in v2"})
    with local.cwd(template_with_extension):
        git_save(tag="2.0.0")
    # Run update — extension should work because template is trusted
    copier.run_update(dst, unsafe=True, defaults=True, overwrite=True)
    # Extension still works during update rendering
    assert (dst / "result.txt").read_text() == "hello from data module"
    assert (dst / "v2.txt").read_text() == "new in v2"
