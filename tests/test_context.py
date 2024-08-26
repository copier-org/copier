import pytest
from plumbum import local

import copier

from .helpers import build_file_tree, git_save


@pytest.mark.parametrize("operation", ("recopy", "update"))
def test_operation_in_context_matches(
    operation: str, tmp_path_factory: pytest.TempPathFactory
) -> None:
    """
    Ensure that the _copier_conf.operation context variable is set
    as expected during template rendering.
    """
    src, dst = map(tmp_path_factory.mktemp, ("src", "dst"))
    with local.cwd(src):
        build_file_tree(
            {
                # Ensure the file is regenerated on update.
                "copier.yml": "_skip_if_exists: [foo]",
                "{{ _copier_conf.answers_file }}.jinja": "{{ _copier_answers|to_yaml }}",
                "foo.jinja": "{{ _copier_conf.operation }}",
            }
        )
        git_save(tag="1.0.0")

    copier.run_copy(str(src), dst, defaults=True, overwrite=True)
    ctx_file = dst / "foo"
    assert ctx_file.read_text() == "copy"
    # Ensure the file is regenerated on update.
    # If we left it, an update would detect custom changes
    # that would be reapplied, i.e. an update would leave us with `copy`.
    ctx_file.unlink()
    with local.cwd(dst):
        git_save()
    getattr(copier, f"run_{operation}")(str(dst), overwrite=True)
    expected = "copy" if operation == "recopy" else operation
    assert ctx_file.read_text() == expected


def test_exclude_templating_with_operation(tmp_path_factory: pytest.TempPathFactory) -> None:
    """
    Ensure it's possible to create one-off boilerplate files
    that are not managed during updates.
    """
    src, dst = map(tmp_path_factory.mktemp, ("src", "dst"))
    exclude = r"{%- if _copier_conf.operation == 'update' %}dumb_boilerplate{%- endif %}"
    with local.cwd(src):
        build_file_tree(
            {
                "copier.yml": f"_exclude:\n - \"{exclude}\"",
                "{{ _copier_conf.answers_file }}.jinja": "{{ _copier_answers|to_yaml }}",
                "dumb_boilerplate": "foo",
                "other_file": "foo",
            }
        )
        git_save(tag="1.0.0")
        build_file_tree(
            {
                "dumb_boilerplate": "bar",
                "other_file": "bar",
            }
        )
        git_save(tag="2.0.0")
    copier.run_copy(str(src), dst, defaults=True, overwrite=True, vcs_ref="1.0.0")
    boilerplate = dst / "dumb_boilerplate"
    other_file = dst / "other_file"
    for file in (boilerplate, other_file):
        assert file.exists()
        assert file.read_text() == "foo"
    with local.cwd(dst):
        git_save()
    copier.run_update(str(dst), overwrite=True)
    assert boilerplate.read_text() == "foo"
    assert other_file.read_text() == "bar"
