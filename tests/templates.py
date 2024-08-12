import shutil
from pathlib import Path
from typing import Generator

import pytest

from .helpers import build_file_tree, git_save


@pytest.fixture(params=("copy", "recopy", "update"))
def operation_context_template(tmp_path_factory: pytest.TempPathFactory, request: pytest.FixtureRequest) -> Generator[Path, None, None]:
    src = tmp_path_factory.mktemp(f"operation_template_{request.param}")
    try:
        build_file_tree(
            {
                (src / f"{{% if _copier_conf.operation == '{request.param}' %}}foo{{% endif %}}"): "foo",
                (src / "bar"): "bar",
                (src / "{{ _copier_conf.answers_file }}.jinja"): "{{ _copier_answers|to_nice_yaml }}",
            }
        )
        git_save(src, tag="1.0.0")
        yield src
    finally:
        shutil.rmtree(src, ignore_errors=True)


@pytest.fixture
def operation_context_template_v2(operation_context_template: Path) -> Path:
    conditional_file = next(iter(operation_context_template.glob("*foo*")))
    build_file_tree(
        {
            conditional_file: "foo_update",
            (operation_context_template / "bar"): "bar_update",
        }
    )
    git_save(operation_context_template, tag="2.0.0")
    return operation_context_template
