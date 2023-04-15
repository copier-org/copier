import json
import re
from contextlib import nullcontext as does_not_raise
from textwrap import dedent, indent
from typing import Any

import pexpect
import pytest
import yaml
from prompt_toolkit.validation import ValidationError

from copier import run_copy
from copier.types import AnyByStrDict

from .helpers import (
    BRACKET_ENVOPS_JSON,
    COPIER_PATH,
    Spawn,
    build_file_tree,
    expect_prompt,
)


@pytest.mark.parametrize(
    "schema, value, message",
    [
        (
            {
                "$schema": "https://json-schema.org/draft-07/schema#",
                "type": "object",
            },
            {},
            "",
        ),
        (
            {
                "$schema": "https://json-schema.org/draft-07/schema#",
                "type": "object",
            },
            [],
            "[] is not of type 'object'",
        ),
        (
            {
                "$schema": "https://json-schema.org/draft-07/schema#",
                "type": "object",
                "properties": {
                    "age": {
                        "type": "integer",
                        "minimum": 0,
                    },
                },
            },
            {"age": -1},
            dedent(
                """
                -1 is less than the minimum of 0

                Failed validating 'minimum' in schema['properties']['age']:
                    {'minimum': 0, 'type': 'integer'}

                On instance['age']:
                    -1
                """
            ).strip(),
        ),
    ],
)
@pytest.mark.parametrize("schema_ext", ["json", "yaml", "yml"])
@pytest.mark.parametrize("interactive", [False, True])
def test_jsonschema_local_schema(
    tmp_path_factory: pytest.TempPathFactory,
    spawn: Spawn,
    interactive: bool,
    schema_ext: str,
    schema: AnyByStrDict,
    value: Any,
    message: str,
) -> None:
    src, dst = map(tmp_path_factory.mktemp, ("src", "dst"))
    build_file_tree(
        {
            (src / "copier.yml"): (
                f"""\
                _envops: {BRACKET_ENVOPS_JSON}
                _exclude:
                    - schemas
                q:
                    type: yaml
                    validator: >-
                        [[
                            q
                            | jsonschema('schemas/schema.{schema_ext}')
                            | default('', true)
                        ]]
                """
            ),
            (src / "schemas" / f"schema.{schema_ext}"): (
                json.dumps(schema) if schema_ext == "json" else yaml.safe_dump(schema)
            ),
        }
    )
    if interactive:
        tui = spawn(COPIER_PATH + (str(src), str(dst)), timeout=10)
        expect_prompt(tui, "q", "yaml")
        tui.sendline(yaml.safe_dump(value))
        if message:
            # Only the first line of the error message is shown during
            # interactive prompting.
            tui.expect_exact(message.splitlines()[0])
        else:
            tui.expect_exact(pexpect.EOF)
    else:
        with (
            pytest.raises(ValidationError, match=re.escape(message))
            if message
            else does_not_raise()
        ):
            run_copy(str(src), dst, data={"q": yaml.safe_dump(value)})


@pytest.mark.parametrize(
    "validator",
    [
        """\
        validator: "[[ q | jsonschema('schemas/schema.yaml') | default('', true) ]]"
        """,
        """\
        validator: >-
            [[
                q
                | jsonschema('schemas/schema.yaml')
                | default('', true)
            ]]
        """,
        """\
        validator: |-
            [% with error = q | jsonschema('schemas/schema.yaml') %]
            [[ error | default('', true) ]]
            [% endwith %]
        """,
        """\
        validator: |-
            [% with error = q | jsonschema('schemas/schema.yaml') %]
            [% if error %][[ error ]][% endif %]
            [% endwith %]
        """,
    ],
)
def test_jsonschema_validator_variants(
    tmp_path_factory: pytest.TempPathFactory, validator: str
) -> None:
    src, dst = map(tmp_path_factory.mktemp, ("src", "dst"))
    build_file_tree(
        {
            (src / "copier.yml"): (
                dedent(
                    f"""\
                    _envops: {BRACKET_ENVOPS_JSON}
                    _exclude:
                        - schemas
                    q:
                        type: yaml
                    """
                )
                + indent(dedent(validator), " " * 4)
            ),
            (src / "schemas" / "schema.yaml"): (
                """\
                $schema: "https://json-schema.org/draft-07/schema#"
                type: object
                properties:
                    age:
                        type: integer
                        minimum: 0
                """
            ),
        }
    )
    with pytest.raises(
        ValidationError,
        match=re.escape(
            dedent(
                """
                -1 is less than the minimum of 0

                Failed validating 'minimum' in schema['properties']['age']:
                    {'minimum': 0, 'type': 'integer'}

                On instance['age']:
                    -1
                """
            ).strip()
        ),
    ):
        run_copy(str(src), dst, data={"q": yaml.safe_dump({"age": -1})})


@pytest.mark.parametrize(
    "value, message",
    [
        (
            {"type": "object"},
            "",
        ),
        (
            {"type": "invalid"},
            "'invalid' is not valid under any of the given schemas",
        ),
    ],
)
@pytest.mark.impure
def test_jsonschema_remote_schema(
    tmp_path_factory: pytest.TempPathFactory, value: Any, message: str
) -> None:
    src, dst = map(tmp_path_factory.mktemp, ("src", "dst"))
    build_file_tree(
        {
            (src / "copier.yml"): (
                f"""\
                _envops: {BRACKET_ENVOPS_JSON}
                q:
                    type: yaml
                    validator: >-
                        [[
                            q
                            | jsonschema('https://json-schema.org/draft-07/schema#')
                            | default('', true)
                        ]]
                """
            )
        }
    )
    with (
        pytest.raises(ValidationError, match=re.escape(message))
        if message
        else does_not_raise()
    ):
        run_copy(str(src), dst, data={"q": yaml.safe_dump(value)})


@pytest.mark.parametrize(
    "value, message",
    [
        (
            {},
            "",
        ),
        (
            [],
            "[] is not of type 'object'",
        ),
    ],
)
@pytest.mark.parametrize("path_prefix", ["", "./"])
@pytest.mark.parametrize("schema_ext", ["json", "yaml"])
def test_jsonschema_local_ref(
    tmp_path_factory: pytest.TempPathFactory,
    schema_ext: str,
    path_prefix: str,
    value: Any,
    message: str,
) -> None:
    src, dst = map(tmp_path_factory.mktemp, ("src", "dst"))
    build_file_tree(
        {
            (src / "copier.yml"): (
                f"""\
                _envops: {BRACKET_ENVOPS_JSON}
                _exclude:
                    - schemas
                q:
                    type: yaml
                    validator: >-
                        [[
                            q
                            | jsonschema('schemas/schema.{schema_ext}')
                            | default('', true)
                        ]]
                """
            ),
            (src / "schemas" / "schema.yaml"): yaml.safe_dump(
                {"$ref": f"{path_prefix}sub/schema.json"}
            ),
            (src / "schemas" / "schema.json"): json.dumps(
                {"$ref": f"{path_prefix}sub/schema.yaml"}
            ),
            (src / "schemas" / "sub" / "schema.yaml"): yaml.safe_dump(
                {"$ref": f"{path_prefix}sub/schema.json"}
            ),
            (src / "schemas" / "sub" / "schema.json"): json.dumps(
                {"$ref": f"{path_prefix}sub/schema.yaml"}
            ),
            (src / "schemas" / "sub" / "sub" / "schema.yaml"): yaml.safe_dump(
                {"type": "object"}
            ),
            (src / "schemas" / "sub" / "sub" / "schema.json"): json.dumps(
                {"type": "object"}
            ),
        }
    )
    with (
        pytest.raises(ValidationError, match=re.escape(message))
        if message
        else does_not_raise()
    ):
        run_copy(str(src), dst, data={"q": yaml.safe_dump(value)})


@pytest.mark.parametrize(
    "path, message",
    [
        (
            "schemas/schema.yml",
            'Schema file path ".+" must resolve to a path under the template root ".+"',
        ),
        (
            "../schema.yml",
            'Schema file path ".+" must resolve to a path under the template root ".+"',
        ),
        (
            "/schemas/schema.yml",
            '".+" is not a relative path',
        ),
    ],
)
def test_jsonschema_local_invalid(
    tmp_path_factory: pytest.TempPathFactory, path: str, message: str
) -> None:
    src, dst = map(tmp_path_factory.mktemp, ("src", "dst"))
    build_file_tree(
        {
            (src / "root" / "copier.yml"): (
                f"""\
                _envops: {BRACKET_ENVOPS_JSON}
                _exclude:
                    - schemas
                q:
                    type: yaml
                    validator: >-
                        [[
                            q
                            | jsonschema('{path}')
                            | default('', true)
                        ]]
                """
            ),
            (src / "root" / "schemas" / "schema.yml"): (
                """\
                $ref: "../../schema.yml"
                """
            ),
            (src / "schema.yml"): (
                """\
                type: object
                """
            ),
        }
    )
    with pytest.raises(ValidationError, match=message):
        run_copy(str(src / "root"), dst, data={"q": "{}"})


@pytest.mark.parametrize(
    "value, message",
    [
        (
            {"type": "object"},
            "",
        ),
        (
            {"type": "invalid"},
            "'invalid' is not valid under any of the given schemas",
        ),
    ],
)
@pytest.mark.impure
def test_jsonschema_remote_ref(
    tmp_path_factory: pytest.TempPathFactory, value: Any, message: str
) -> None:
    src, dst = map(tmp_path_factory.mktemp, ("src", "dst"))
    build_file_tree(
        {
            (src / "copier.yml"): (
                f"""\
                _envops: {BRACKET_ENVOPS_JSON}
                _exclude:
                    - schemas
                q:
                    type: yaml
                    validator: >-
                        [[
                            q
                            | jsonschema('schemas/schema.yml')
                            | default('', true)
                        ]]
                """
            ),
            (src / "schemas" / "schema.yml"): (
                """\
                $ref: "https://json-schema.org/draft-07/schema#"
                """
            ),
        }
    )
    with (
        pytest.raises(ValidationError, match=re.escape(message))
        if message
        else does_not_raise()
    ):
        run_copy(str(src), dst, data={"q": yaml.safe_dump(value)})


@pytest.mark.parametrize(
    "value, message",
    [
        (1, ""),
        ("no-int", "'no-int' is not of type 'integer'"),
    ],
)
@pytest.mark.parametrize("fragment", ["/definitions/int", "/definitions/intRef"])
def test_jsonschema_local_schema_with_fragment(
    tmp_path_factory: pytest.TempPathFactory, fragment: str, value: Any, message: str
) -> None:
    src, dst = map(tmp_path_factory.mktemp, ("src", "dst"))
    build_file_tree(
        {
            (src / "copier.yml"): (
                f"""\
                _envops: {BRACKET_ENVOPS_JSON}
                _exclude:
                    - schemas
                q:
                    type: yaml
                    validator: >-
                        [[
                            q
                            | jsonschema('schemas/schema.yml#{fragment}')
                            | default('', true)
                        ]]
                """
            ),
            (src / "schemas" / "schema.yml"): (
                """\
                definitions:
                    int:
                        type: integer
                    intRef:
                        $ref: sub/schema.yml#/definitions/int
                """
            ),
            (src / "schemas" / "sub" / "schema.yml"): (
                """\
                definitions:
                    int:
                        type: integer
                """
            ),
        }
    )
    with (
        pytest.raises(ValidationError, match=re.escape(message))
        if message
        else does_not_raise()
    ):
        run_copy(str(src), dst, data={"q": yaml.safe_dump(value)})


@pytest.mark.parametrize(
    "value, message",
    [
        (1, ""),
        ("no-int", "'no-int' is not of type 'integer'"),
    ],
)
@pytest.mark.impure
def test_jsonschema_remote_schema_with_fragment(
    tmp_path_factory: pytest.TempPathFactory, value: Any, message: str
) -> None:
    src, dst = map(tmp_path_factory.mktemp, ("src", "dst"))
    build_file_tree(
        {
            (src / "copier.yml"): (
                f"""\
                _envops: {BRACKET_ENVOPS_JSON}
                q:
                    type: yaml
                    validator: >-
                        [[
                            q
                            | jsonschema('https://json-schema.org/draft-07/schema#/definitions/nonNegativeInteger')
                            | default('', true)
                        ]]
                """
            )
        }
    )
    with (
        pytest.raises(ValidationError, match=re.escape(message))
        if message
        else does_not_raise()
    ):
        run_copy(str(src), dst, data={"q": yaml.safe_dump(value)})
