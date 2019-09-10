from pathlib import Path

from ..tools import HLINE, INDENT, printf_block, prompt
from ..types import AnyByStrDict, StrOrPath


__all__ = ("load_config_data", "query_user_data")


class InvalidConfigFileError(ValueError):
    def __init__(self, msg: str, quiet: bool):
        printf_block(self, "INVALID", msg=msg, quiet=quiet)
        super().__init__(msg)


def load_toml_data(
    src_path: StrOrPath, quiet: bool = False, _warning: bool = True
) -> AnyByStrDict:
    toml_path = Path(src_path) / "copier.toml"
    if not toml_path.exists():
        return {}

    import toml

    toml_src = toml_path.read_text()
    try:
        return dict(toml.loads(toml_src))
    except toml.TomlDecodeError as e:
        raise InvalidConfigFileError(str(toml_path), quiet) from e


def load_yaml_data(
    src_path: StrOrPath, quiet: bool = False, _warning: bool = True
) -> AnyByStrDict:
    yaml_path = Path(src_path) / "copier.yml"
    if not yaml_path.exists():
        yaml_path = Path(src_path) / "copier.yaml"
        if not yaml_path.exists():
            return {}

    from ruamel.yaml import YAML, YAMLError

    yaml = YAML(typ="safe")

    try:
        return dict(yaml.load(yaml_path))
    except YAMLError as e:
        raise InvalidConfigFileError(str(yaml_path), quiet) from e


def load_json_data(
    src_path: StrOrPath, quiet: bool = False, _warning: bool = True
) -> AnyByStrDict:
    json_path = Path(src_path) / "copier.json"
    if not json_path.exists():
        return {}

    import json

    json_src = json_path.read_text()
    try:
        return dict(json.loads(json_src))
    except json.JSONDecodeError as e:
        raise InvalidConfigFileError(json_src, quiet) from e


def load_config_data(
    src_path: StrOrPath, quiet: bool = False, _warning: bool = True
) -> AnyByStrDict:
    """Try to load the content from a `copier.yml`, a `copier.toml`, a `copier.json`,
    or the deprecated `voodoo.json`, in that order.
    """
    loaders = (load_yaml_data, load_toml_data, load_json_data)
    for l in loaders:
        # The `_warning` argument is for easier testing
        data = l(src_path, quiet=quiet, _warning=_warning)
        if data:
            return data
    else:
        return {}


def query_user_data(default_user_data: AnyByStrDict) -> AnyByStrDict:  # pragma:no cover
    """Query to user about the data of the config file.
    """
    if not default_user_data:
        return {}
    print("")
    user_data = {}
    for key in default_user_data:
        default = default_user_data[key]
        user_data[key] = prompt(INDENT + f" {key}?", default)

    print(f"\n {INDENT} {HLINE}")
    return user_data
