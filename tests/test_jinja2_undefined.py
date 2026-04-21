import pytest
from jinja2.exceptions import UndefinedError

import copier
from copier.errors import ConfigFileError

from .helpers import build_file_tree


def test_default(tmp_path_factory: pytest.TempPathFactory) -> None:
    src, dst = map(tmp_path_factory.mktemp, ("src", "dst"))

    build_file_tree(
        {
            (src / "copier.yaml"): "",
            (src / "test.jinja"): "{{ undefined_variable }}",
        }
    )

    copier.run_copy(str(src), dst)
    assert (dst / "test").read_text() == ""


def test_invalid_value(tmp_path_factory: pytest.TempPathFactory) -> None:
    src, dst = map(tmp_path_factory.mktemp, ("src", "dst"))

    build_file_tree(
        {
            (src / "copier.yaml"): (
                """\
                _envops:
                    undefined: jinja2.ChainableUndefined
                """
            ),
        }
    )

    with pytest.raises(
        ConfigFileError,
        match="Unsupported envops.undefined value specified: jinja2.ChainableUndefined.",
    ):
        copier.run_copy(str(src), dst)


def test_undefined(tmp_path_factory: pytest.TempPathFactory) -> None:
    src, dst = map(tmp_path_factory.mktemp, ("src", "dst"))

    build_file_tree(
        {
            (src / "copier.yaml"): (
                """\
                _envops:
                    undefined: jinja2.Undefined
                """
            ),
            (src / "test.jinja"): "{{ undefined_variable }}",
        }
    )

    copier.run_copy(str(src), dst)
    assert (dst / "test").read_text() == ""


def test_strictundefined_undefined_variable(
    tmp_path_factory: pytest.TempPathFactory,
) -> None:
    src, dst = map(tmp_path_factory.mktemp, ("src", "dst"))

    build_file_tree(
        {
            (src / "copier.yaml"): (
                """\
                _envops:
                    undefined: jinja2.StrictUndefined
                """
            ),
            (src / "test.jinja"): "{{ undefined_variable }}",
        }
    )

    with pytest.raises(UndefinedError, match="'undefined_variable' is undefined"):
        copier.run_copy(str(src), dst)
