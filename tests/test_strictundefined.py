from pathlib import Path

import pytest
from jinja2.exceptions import UndefinedError

import copier
from copier._template import Template
from copier.errors import UserMessageError

from .helpers import build_file_tree


def test_strictundefined_default() -> None:
    tpl = Template("./tests/demo")

    # not enabled by default
    assert "undefined" not in tpl.envops


def test_strictundefined_warning(tmp_path: Path) -> None:
    with pytest.warns(
        FutureWarning,
        match="Copier does not detect undefined variables in templates unless `undefined: jinja2.StrictUndefined` is specified.",
    ):
        copier.run_copy("./tests/demo_config_empty", tmp_path)


def test_strictundefined_invalid_value(
    tmp_path_factory: pytest.TempPathFactory,
) -> None:
    src, dst = map(tmp_path_factory.mktemp, ("src", "dst"))

    build_file_tree(
        {
            (src / ".copier-answers.yml.jinja"): (
                """\
                # Changes here will be overwritten by Copier
                {{ _copier_answers|to_nice_yaml }}
                """
            ),
            (src / "copier.yaml"): (
                """\
                _envops:
                    undefined: jinja2.ChainableUndefined
                """
            ),
            (src / "test.jinja"): "{{ undefined_variable }}",
        }
    )

    with pytest.raises(
        UserMessageError,
        match='Unsupported envops.undefined value specified: jinja2.ChainableUndefined. Supported values are "jinja2.Undefined" and "jinja2.StrictUndefined".',
    ):
        copier.run_copy(str(src), dst)


# fail on warnings
@pytest.mark.filterwarnings("error")
def test_strictundefined_silenced_warning(
    tmp_path_factory: pytest.TempPathFactory,
) -> None:
    src, dst = map(tmp_path_factory.mktemp, ("src", "dst"))

    build_file_tree(
        {
            (src / ".copier-answers.yml.jinja"): (
                """\
                # Changes here will be overwritten by Copier
                {{ _copier_answers|to_nice_yaml }}
                """
            ),
            (src / "copier.yaml"): (
                """\
                _envops:
                    undefined: jinja2.Undefined
                """
            ),
        }
    )

    copier.run_copy(str(src), dst)


def test_strictundefined_undefined_variable(
    tmp_path_factory: pytest.TempPathFactory,
) -> None:
    src, dst = map(tmp_path_factory.mktemp, ("src", "dst"))

    build_file_tree(
        {
            (src / ".copier-answers.yml.jinja"): (
                """\
                # Changes here will be overwritten by Copier
                {{ _copier_answers|to_nice_yaml }}
                """
            ),
            (src / "copier.yaml"): (
                """\
                _envops:
                    undefined: jinja2.StrictUndefined
                """
            ),
            (src / "test.jinja"): "{{ undefined_variable }}",
        }
    )

    with pytest.raises(
        UndefinedError,
        match="'undefined_variable' is undefined",
    ):
        copier.run_copy(str(src), dst)
