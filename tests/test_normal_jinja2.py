import warnings

import pytest

import copier

from .helpers import build_file_tree


def test_normal_jinja2(tmp_path_factory):
    src, dst = map(tmp_path_factory.mktemp, ("src", "dst"))
    build_file_tree(
        {
            src
            / "copier.yml": """\
                _templates_suffix: .jinja
                _envops:
                    autoescape: false
                    variable_start_string: "{{"
                    variable_end_string: "}}"
                    block_start_string: "{%"
                    block_end_string: "%}"
                    comment_start_string: "{#"
                    comment_end_string: "#}"
                    lstrip_blocks: true
                    trim_blocks: true
                name: Guybrush
                todo: Become a pirate
            """,
            src
            / "TODO.txt.jinja": """\
                [[ {{ name }} TODO LIST]]
                {# Let's put an ugly not-comment below #}
                [# GROG #]
                    {% if name == 'Guybrush' %}
                    - {{ todo }}
                    {% endif %}
            """,
        }
    )
    # No warnings, because template is explicit
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        copier.run_auto(str(src), dst, force=True)
    todo = (dst / "TODO.txt").read_text()
    expected = "[[ Guybrush TODO LIST]]\n[# GROG #]\n    - Become a pirate\n"
    assert todo == expected


def test_future_jinja_defaults_warning(tmp_path_factory):
    src, dst = map(tmp_path_factory.mktemp, ("src", "dst"))
    build_file_tree(
        {
            src
            / "copier.yml": """\
                _min_copier_version: "5"
                q: a
            """,
            src / "result.tmpl": "[[ q ]]",
        }
    )
    # Make sure the future warning is raised
    with warnings.catch_warnings():
        warnings.simplefilter("error", FutureWarning)
        with pytest.raises(FutureWarning):
            copier.run_copy(str(src), dst, force=True)
    # Run again without capturing warning, to see how it renders properly
    copier.run_copy(str(src), dst, force=True)
    assert (dst / "result").read_text() == "a"


def test_jinja_defaults_v6_min_version(tmp_path_factory):
    src, dst = map(tmp_path_factory.mktemp, ("src", "dst"))
    build_file_tree(
        {
            src / "copier.yml": "{_min_copier_version: '6.0.0a5.post1', q: a}",
            src / "result.jinja": "{{ q }}",
        }
    )
    # Make sure the future warning is not raised
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        copier.run_copy(str(src), dst, force=True)
    assert (dst / "result").read_text() == "a"
