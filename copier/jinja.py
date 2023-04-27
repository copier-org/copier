from platform import system
from typing import Any, ClassVar, Optional
from urllib.parse import urlparse
from urllib.request import url2pathname, urlopen

import jsonschema
import yaml
from jinja2 import Environment, TemplateNotFound
from jinja2.ext import Extension


class JsonSchemaExtension(Extension):
    """Jinja extension for validating data against a JSON Schema document."""

    # HACK https://github.com/python-jsonschema/jsonschema/issues/98#issuecomment-105475109
    _FILE_SCHEME: ClassVar[str] = "file:///" if system() == "Windows" else "file://"

    def __init__(self, environment: Environment) -> None:
        super().__init__(environment)
        environment.filters["jsonschema"] = self

    def __call__(
        self, instance: Any, schema_uri: str
    ) -> Optional[jsonschema.ValidationError]:
        if schema_uri.startswith(("http://", "https://")):
            schema = {"$ref": schema_uri}
        else:
            if not schema_uri.startswith("/"):
                schema_uri = f"/{schema_uri}"
            schema = {"$ref": f"{self._FILE_SCHEME}{schema_uri}"}
        try:
            return jsonschema.validate(
                instance,
                schema,
                resolver=jsonschema.RefResolver(
                    "",
                    {},
                    handlers={
                        "file": self._resolve_local_schema,
                        "http": self._resolve_remote_schema,
                        "https": self._resolve_remote_schema,
                    },
                ),
            )
        except jsonschema.ValidationError as exc:
            return exc

    def _resolve_local_schema(self, uri: str) -> Any:
        schema_file = url2pathname(urlparse(uri).path)
        if not self.environment.loader:
            raise RuntimeError("JSON Schema extension requires a loader")
        try:
            schema, *_ = self.environment.loader.get_source(
                self.environment, schema_file
            )
        except TemplateNotFound as exc:
            raise FileNotFoundError(f'Schema file "{schema_file}" not found') from exc
        return yaml.safe_load(schema)

    def _resolve_remote_schema(self, uri: str) -> Any:
        with urlopen(uri) as response:
            raw_schema = response.read().decode("utf-8")
        return yaml.safe_load(raw_schema)
