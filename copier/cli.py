#!/usr/bin/env python
from argparse import ArgumentParser
from copy import deepcopy
import sys

from .types import AnyByStrDict
from .main import copy
from .version import __version__


PARSER_BASE_CONFIG = {
    "description": "Create a new project from a template.",
    "usage": "copier project_template_path destination_path [options]",
    "epilog": (
        "Warning! Use only trusted project templates as they might "
        "execute code with the same level of access as your user."
    ),
}

PARSER_ARG_CONFIG = (
    # BASIC ARGS
    {"args": ("--version",), "action": "version", "version": __version__},
    {"args": ("source",), "help": "The path of the project template."},
    {"args": ("dest",), "help": "The path of where to create the new project."},
    # PATHS
    {
        "args": ("--extra-paths",),
        "nargs": "*",
        "help": "Additional directories to find parent templates in.",
    },
    {
        "args": ("--exclude",),
        "nargs": "*",
        "help": (
            "A list of names or shell-style patterns matching files or folders "
            "that must not be copied."
        ),
    },
    {
        "args": ("--include",),
        "nargs": "*",
        "help": (
            "A list of names or shell-style patterns matching files or folders that "
            "must be included, even if its name are in the `exclude` list."
        ),
    },
    # FLAGS
    {
        "args": ("--pretend",),
        "action": "store_true",
        "help": "Run but do not make any changes."
    },
    {
        "args": ("--force",),
        "action": "store_true",
        "help": "Overwrite files that already exist, without asking."
    },
    {
        "args": ("--skip",),
        "action": "store_true",
        "help": "Skip files that already exist, without asking."
    },
    {
        "args": ("--quiet",),
        "action": "store_true",
        "help": "Suppress status output."
    },
)


def make_parser(base_config, arg_config) -> ArgumentParser:
    parser = ArgumentParser(**base_config)
    arg_config = deepcopy(arg_config)
    for c in arg_config:
        args = c.pop("args")
        parser.add_argument(*args, **c)
    return parser


def get_cli_args(args_) -> AnyByStrDict:
    parser = make_parser(PARSER_BASE_CONFIG, PARSER_ARG_CONFIG)
    ns = parser.parse_args(args_)
    return vars(ns)


def run() -> None:  # pragma:no cover
    kwargs = get_cli_args(sys.argv[1:])
    copy(kwargs.pop("source"), kwargs.pop("dest"), **kwargs)


if __name__ == "__main__":
    run()
