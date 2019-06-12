from pathlib import Path

from .tools import printf, printf_block, prompt, STYLE_WARNING


__all__ = ("load_config_data", "query_user_data")

INDENT = "  "


def load_toml_data(src_path, quiet=False):
    toml_path = Path(src_path) / "copier.toml"
    if not toml_path.exists():
        return {}

    import toml

    toml_src = toml_path.read_text()
    try:
        return toml.loads(toml_src)
    except Exception as e:
        printf_block(e, "INVALID", msg=toml_path, quiet=quiet)
        return {}


def load_yaml_data(src_path, quiet=False):
    yaml_path = Path(src_path) / "copier.yml"
    if not yaml_path.exists():
        yaml_path = Path(src_path) / "copier.yaml"
        if not yaml_path.exists():
            return {}

    from ruamel.yaml import YAML

    yaml = YAML(typ="safe")

    try:
        return yaml.load(yaml_path)
    except Exception as e:
        printf_block(e, "INVALID", msg=yaml_path, quiet=quiet)
        return {}


def load_json_data(src_path, quiet=False, _warning=True):
    json_path = Path(src_path) / "copier.json"
    if not json_path.exists():
        return load_old_json_data(src_path, quiet=quiet, _warning=_warning)

    import json

    json_src = json_path.read_text()
    try:
        return json.loads(json_src)
    except ValueError as e:
        printf_block(e, "INVALID", msg=json_path, quiet=quiet)
        return {}


def load_old_json_data(src_path, quiet=False, _warning=True):
    # TODO: Remove on version 3.0
    json_path = Path(src_path) / "voodoo.json"
    if not json_path.exists():
        return {}

    if _warning and not quiet:
        print("")
        printf(
            "WARNING",
            msg="`voodoo.json` is deprecated. "
            + "Replace it with a `copier.yaml`, `copier.toml`, or `copier.json`.",
            style=STYLE_WARNING,
            indent=10,
        )

    import json

    json_src = json_path.read_text()
    try:
        return json.loads(json_src)
    except ValueError as e:
        printf_block(e, "INVALID", msg=json_path, quiet=quiet)
        return {}


def load_config_data(src_path, quiet=False, _warning=True):
    """Try to load the content from a `copier.yml`, a `copier.toml`, a `copier.json`,
    or the deprecated `voodoo.json`, in that order.
    """
    data = load_yaml_data(src_path, quiet=quiet)
    if not data:
        data = load_toml_data(src_path, quiet=quiet)
    if not data:
        # The `_warning` argument is for easier testing
        data = load_json_data(src_path, quiet=quiet, _warning=_warning)
    return data


def query_user_data(default_user_data):  # pragma:no cover
    """Query to user about the data of the config file.
    """
    if not default_user_data:
        return {}
    print("")
    user_data = {}
    for key in default_user_data:
        default = default_user_data[key]
        user_data[key] = prompt(INDENT + " {0}?".format(key), default)

    print("\n" + INDENT + "-" * 42)
    return user_data
