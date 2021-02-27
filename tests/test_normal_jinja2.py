import warnings

import pytest

import copier

from .helpers import PROJECT_TEMPLATE, build_file_tree


def test_normal_jinja2(tmp_path):
    copier.copy(f"{PROJECT_TEMPLATE}_normal_jinja2", tmp_path, force=True)
    todo = (tmp_path / "TODO.txt").read_text()
    expected = "[[ Guybrush TODO LIST]]\n[# GROG #]\n    - Become a pirate\n"
    assert todo == expected


def test_future_jinja_defaults_warning(tmp_path_factory):
    src, dst = map(tmp_path_factory.mktemp, ("src", "dst"))
    build_file_tree({src / "copier.yml": "q: a", src / "result.tmpl": "[[ q ]]"})
    # Make sure the future warning is raised
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        with pytest.raises(FutureWarning):
            copier.run_copy(str(src), dst, force=True)
    # Run again without capturing warning, to see how it renders properly
    copier.run_copy(str(src), dst, force=True)
    assert (dst / "result").read_text() == "a"


def test_jinja_defaults_v6_min_version(tmp_path_factory):
    src, dst = map(tmp_path_factory.mktemp, ("src", "dst"))
    build_file_tree(
        {
            src / "copier.yml": "{_min_copier_version: '6.0.0a5', q: a}",
            src / "result.tmpl": "{{ q }}",
        }
    )
    # Make sure the future warning is not raised
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        copier.run_copy(str(src), dst, force=True)
    assert (dst / "result").read_text() == "a"
