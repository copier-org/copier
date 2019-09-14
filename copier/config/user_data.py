from pathlib import Path

from ..tools import HLINE, INDENT, printf_block, prompt
from ..types import AnyByStrDict, StrOrPath

__all__ = ("load_config_data", "query_user_data")


class InvalidConfigFileError(ValueError):
    def __init__(self, msg: str, quiet: bool):
        printf_block(self, "INVALID", msg=msg, quiet=quiet)
        super().__init__(msg)


def load_toml_data(
    conf_path: Path, quiet: bool = False, _warning: bool = True
) -> AnyByStrDict:
    import toml

    toml_src = conf_path.read_text()
    try:
        return dict(toml.loads(toml_src))
    except toml.TomlDecodeError as e:
        raise InvalidConfigFileError(str(conf_path), quiet) from e


def load_yaml_data(
    conf_path: Path, quiet: bool = False, _warning: bool = True
) -> AnyByStrDict:
    from ruamel.yaml import YAML, YAMLError

    yaml = YAML(typ="safe")

    try:
        return dict(yaml.load(conf_path))
    except YAMLError as e:
        raise InvalidConfigFileError(str(conf_path), quiet) from e


def load_json_data(
    conf_path: Path, quiet: bool = False, _warning: bool = True
) -> AnyByStrDict:
    import json

    json_src = conf_path.read_text()
    try:
        return dict(json.loads(json_src))
    except json.JSONDecodeError as e:
        raise InvalidConfigFileError(str(conf_path), quiet) from e


LOADER_BY_EXT = {
    "yaml": load_yaml_data,
    "yml": load_yaml_data,
    "toml": load_toml_data,
    "json": load_json_data,
}


def load_config_data(
    src_path: StrOrPath, quiet: bool = False, _warning: bool = True
) -> AnyByStrDict:
    """Try to load the content from a `copier.yml`, a `copier.toml`,
    or a `copier.json` in that order of precedence.
    """
    for ext, loader in LOADER_BY_EXT.items():
        conf_path = Path(src_path).joinpath(f"copier.{ext}")
        if conf_path.exists() and conf_path.is_file():
            data = loader(conf_path, quiet=quiet, _warning=_warning)
            if data:
                return data
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
