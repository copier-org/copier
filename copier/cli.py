#!/usr/bin/env python
import argparse
from hashlib import sha512
from os import urandom
import sys

try:
    from .main import copy
    from .version import __version__
except Exception:
    from copier.main import copy
    from copier.version import __version__


parser = argparse.ArgumentParser(
    description="Create a new project from a template",
    usage="copier project_template_path destination_path [options]",
    epilog=(
        "Warning! Use only trusted project templates as they might "
        "execute code with the same level of access as your user."
    ),
)

parser.add_argument("--version", action="version", version=__version__)

parser.add_argument("source", help="The path of the project template")
parser.add_argument("dest", help="The path of where to create the new project")

parser.add_argument(
    "--exclude",
    nargs="*",
    help=(
        "A list of names or shell-style patterns matching files or folders "
        "that must not be copied."
    ),
)
parser.add_argument(
    "--include",
    nargs="*",
    help=(
        "A list of names or shell-style patterns matching files or folders that "
        "must be included, even if its name are in the `exclude` list."
    ),
)

parser.add_argument(
    "--pretend",
    action="store_true",
    dest="pretend",
    help="Run but do not make any changes",
)
parser.add_argument(
    "--force",
    action="store_true",
    dest="force",
    help="Overwrite files that already exist, without asking",
)
parser.add_argument(
    "--skip",
    action="store_true",
    dest="skip",
    help="Skip files that already exist, without asking",
)
parser.add_argument(
    "--quiet", action="store_true", dest="quiet", help="Suppress status output"
)


def run():  # pragma:no cover
    if len(sys.argv) == 1 or sys.argv[1] == "help":
        parser.print_help(sys.stderr)
        print()
        sys.exit(1)

    if sys.argv[1] == "version":
        sys.stdout.write(__version__)
        print()
        sys.exit(1)

    args = parser.parse_args()
    kwargs = vars(args)
    data = {"make_secret": lambda: sha512(urandom(48)).hexdigest()}
    copy(kwargs.pop("source"), kwargs.pop("dest"), data=data, **kwargs)


if __name__ == "__main__":
    run()
