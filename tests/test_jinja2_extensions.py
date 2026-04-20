import json
from pathlib import Path
from typing import Any

import pytest
from jinja2 import Environment
from jinja2.ext import Extension

import copier

from .helpers import PROJECT_TEMPLATE, build_file_tree


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
