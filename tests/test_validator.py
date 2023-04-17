import json
import re
import socket
import sys
from contextlib import closing, nullcontext as does_not_raise
from functools import partial
from http.server import SimpleHTTPRequestHandler
from os import PathLike
from socketserver import TCPServer
from textwrap import dedent, indent
from threading import Thread
from time import sleep
from typing import Any, Callable, Iterator, List, Literal
from urllib.error import URLError
from urllib.request import Request, urlopen

import pexpect
import pytest
import yaml
from prompt_toolkit.validation import ValidationError

from copier import run_copy

from .helpers import (
    BRACKET_ENVOPS_JSON,
    COPIER_PATH,
    Spawn,
    build_file_tree,
    expect_prompt,
)

# HACK https://github.com/python/mypy/issues/8520#issuecomment-772081075
if sys.version_info >= (3, 10):
    from typing import TypeAlias
else:
    from typing_extensions import TypeAlias


def serialize(data: Any, format=Literal["json", "yaml"]) -> str:
    return json.dumps(data) if format == "json" else yaml.safe_dump(data)


def get_unused_tcp_port() -> int:
    with closing(socket.socket(type=socket.SOCK_STREAM)) as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


HTTPServerFactory: TypeAlias = Callable[[PathLike], str]


@pytest.fixture
def http_server_factory() -> Iterator[HTTPServerFactory]:
    server_host = "127.0.0.1"
    server_disposers: List[Callable[[], None]] = []

    def create(directory: PathLike) -> str:
        server_port = get_unused_tcp_port()
        server = TCPServer(
            (server_host, server_port),
            partial(SimpleHTTPRequestHandler, directory=directory),
        )
        server_disposers.append(server.shutdown)
        server_thread = Thread(target=server.serve_forever)
        server_thread.daemon = True
        server_thread.start()
        server_url = f"http://{server_host}:{server_port}"

        # Wait until the server has booted.
        request = Request(server_url, method="HEAD")
        while True:
            try:
                urlopen(request)
            except URLError as exc:
                if isinstance(exc.reason, ConnectionRefusedError):
                    sleep(0.1)
                else:
                    raise
            else:
                break

        return server_url

    yield create

    while server_disposers:
        dispose = server_disposers.pop()
        dispose()


SCHEMA = {
    "$schema": "https://json-schema.org/draft-07/schema#",
    "type": "object",
    "properties": {
        "age": {
            "type": "integer",
            "minimum": 0,
        },
    },
}


@pytest.mark.parametrize(
    "value, message",
    [
        (
            {"age": 30},
            "",
        ),
        (
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
@pytest.mark.parametrize("format", ["json", "yaml"])
@pytest.mark.parametrize("interactive", [False, True])
def test_jsonschema_basic(
    tmp_path_factory: pytest.TempPathFactory,
    spawn: Spawn,
    interactive: bool,
    format: str,
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
                            | jsonschema('schemas/schema.{format}')
                            | default('', true)
                        ]]
                """
            ),
            (src / "schemas" / f"schema.{format}"): serialize(SCHEMA, format),
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
            (src / "schemas" / "schema.yaml"): serialize(SCHEMA, "yaml"),
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
            {"age": 30},
            "",
        ),
        (
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
@pytest.mark.parametrize("format", ["json", "yaml"])
def test_jsonschema_remote_schema(
    tmp_path_factory: pytest.TempPathFactory,
    http_server_factory: HTTPServerFactory,
    format: Literal["json", "yaml"],
    value: Any,
    message: str,
) -> None:
    src, dst, srv = map(tmp_path_factory.mktemp, ("src", "dst", "srv"))
    url = http_server_factory(srv)
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
                            | jsonschema('{url}/schema.{format}')
                            | default('', true)
                        ]]
                """
            ),
            (srv / f"schema.{format}"): serialize(SCHEMA, format),
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
            {"age": 30},
            "",
        ),
        (
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
@pytest.mark.parametrize("prefix", ["", "./"])
@pytest.mark.parametrize("format", ["json", "yaml"])
def test_jsonschema_local_ref(
    tmp_path_factory: pytest.TempPathFactory,
    prefix: str,
    format: str,
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
                            | jsonschema('schemas/schema.{format}')
                            | default('', true)
                        ]]
                """
            ),
            (src / "schemas" / "schema.yaml"): serialize(
                {"$ref": f"{prefix}sub/schema.json"}, "yaml"
            ),
            (src / "schemas" / "schema.json"): serialize(
                {"$ref": f"{prefix}sub/schema.yaml"}, "json"
            ),
            (src / "schemas" / "sub" / "schema.yaml"): serialize(
                {"$ref": f"{prefix}sub/schema.json"}, "yaml"
            ),
            (src / "schemas" / "sub" / "schema.json"): serialize(
                {"$ref": f"{prefix}sub/schema.yaml"}, "json"
            ),
            (src / "schemas" / "sub" / "sub" / "schema.yaml"): serialize(
                SCHEMA, "yaml"
            ),
            (src / "schemas" / "sub" / "sub" / "schema.json"): serialize(
                SCHEMA, "json"
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
            "schemas/schema.yaml",
            'Schema file path ".+" must resolve to a path under the template root ".+"',
        ),
        (
            "../schema.yaml",
            'Schema file path ".+" must resolve to a path under the template root ".+"',
        ),
        (
            "/schemas/schema.yaml",
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
            (src / "root" / "schemas" / "schema.yaml"): serialize(
                {"$ref": "../../schema.yaml"}, "yaml"
            ),
            (src / "schema.yaml"): serialize(SCHEMA, "yaml"),
        }
    )
    with pytest.raises(ValidationError, match=message):
        run_copy(str(src / "root"), dst, data={"q": "{}"})


@pytest.mark.parametrize(
    "value, message",
    [
        (
            {"age": 30},
            "",
        ),
        (
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
@pytest.mark.parametrize("prefix", ["", "./"])
@pytest.mark.parametrize("format", ["json", "yaml"])
def test_jsonschema_remote_ref(
    tmp_path_factory: pytest.TempPathFactory,
    http_server_factory: HTTPServerFactory,
    format: Literal["json", "yaml"],
    prefix: str,
    value: Any,
    message: str,
) -> None:
    src, dst, srv = map(tmp_path_factory.mktemp, ("src", "dst", "srv"))
    url = http_server_factory(srv)
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
                            | jsonschema('{url}/schema.{format}')
                            | default('', true)
                        ]]
                """
            ),
            (srv / "schema.yaml"): serialize(
                {"$ref": f"{prefix}sub/schema.json"}, "yaml"
            ),
            (srv / "schema.json"): serialize(
                {"$ref": f"{prefix}sub/schema.yaml"}, "json"
            ),
            (srv / "sub" / "schema.yaml"): serialize(
                {"$ref": f"{prefix}sub/schema.json"}, "yaml"
            ),
            (srv / "sub" / "schema.json"): serialize(
                {"$ref": f"{prefix}sub/schema.yaml"}, "json"
            ),
            (srv / "sub" / "sub" / "schema.yaml"): serialize(SCHEMA, "yaml"),
            (srv / "sub" / "sub" / "schema.json"): serialize(SCHEMA, "json"),
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
            {"age": 30},
            "",
        ),
        (
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
@pytest.mark.parametrize("fragment", ["/definitions/person", "/definitions/personRef"])
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
                            | jsonschema('schemas/schema.yaml#{fragment}')
                            | default('', true)
                        ]]
                """
            ),
            (src / "schemas" / "schema.yaml"): serialize(
                {
                    "definitions": {
                        "person": SCHEMA,
                        "personRef": {
                            "$ref": "sub/schema.yaml#/definitions/person",
                        },
                    }
                },
                "yaml",
            ),
            (src / "schemas" / "sub" / "schema.yaml"): serialize(
                {
                    "definitions": {
                        "person": SCHEMA,
                    }
                },
                "yaml",
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
        (
            {"age": 30},
            "",
        ),
        (
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
@pytest.mark.parametrize("fragment", ["/definitions/person", "/definitions/personRef"])
def test_jsonschema_local_schema_with_remote_fragment(
    tmp_path_factory: pytest.TempPathFactory,
    http_server_factory: HTTPServerFactory,
    fragment: str,
    value: Any,
    message: str,
) -> None:
    src, dst, srv = map(tmp_path_factory.mktemp, ("src", "dst", "srv"))
    url = http_server_factory(srv)
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
                            | jsonschema('{url}/schema.yaml#{fragment}')
                            | default('', true)
                        ]]
                """
            ),
            (srv / "schema.yaml"): serialize(
                {
                    "definitions": {
                        "person": SCHEMA,
                        "personRef": {
                            "$ref": "sub/schema.yaml#/definitions/person",
                        },
                    }
                },
                "yaml",
            ),
            (srv / "sub" / "schema.yaml"): serialize(
                {
                    "definitions": {
                        "person": SCHEMA,
                    }
                },
                "yaml",
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
        (
            {"age": 30},
            "",
        ),
        (
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
@pytest.mark.parametrize("fragment", ["/definitions/person", "/definitions/personRef"])
def test_jsonschema_remote_schema_with_fragment(
    tmp_path_factory: pytest.TempPathFactory,
    http_server_factory: HTTPServerFactory,
    fragment: str,
    value: Any,
    message: str,
) -> None:
    src, dst, srv = map(tmp_path_factory.mktemp, ("src", "dst", "srv"))
    url = http_server_factory(srv)
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
                            | jsonschema('{url}/schema.yaml#{fragment}')
                            | default('', true)
                        ]]
                """
            ),
            (srv / "schema.yaml"): serialize(
                {
                    "definitions": {
                        "person": SCHEMA,
                        "personRef": {
                            "$ref": "sub/schema.yaml#/definitions/person",
                        },
                    }
                },
                "yaml",
            ),
            (srv / "sub" / "schema.yaml"): serialize(
                {
                    "definitions": {
                        "person": SCHEMA,
                    }
                },
                "yaml",
            ),
        }
    )
    with (
        pytest.raises(ValidationError, match=re.escape(message))
        if message
        else does_not_raise()
    ):
        run_copy(str(src), dst, data={"q": yaml.safe_dump(value)})
