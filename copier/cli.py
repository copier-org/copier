#!/usr/bin/env python
from plumbum import cli, colors
import sys

from .types import OptStr, AnyByStrDict
from .main import copy
from .version import __version__


class CopierApp(cli.Application):
    DESCRIPTION = "Create a new project from a template."
    DESCRIPTION_MORE = colors.yellow | """
    WARNING! Use only trusted project templates, as they might
    execute code with the same level of access as your user.
    """
    USAGE = """
    copier [SWITCHES] [copy] template_src destination_path
    copier [SWITCHES] [update] [destination_path]
    """
    VERSION = __version__
    CALL_MAIN_IF_NESTED_COMMAND = False
    data: AnyByStrDict = {}

    extra_paths = cli.SwitchAttr(
        ["-p", "--extra-paths"], str, list=True,
        help="Additional directories to find parent templates in")
    exclude = cli.SwitchAttr(
        ["-x", "--exclude"], str, list=True,
        help=(
            "A name or shell-style pattern matching files or folders "
            "that must not be copied"
        ),
    )
    include = cli.SwitchAttr(
        ["-i", "--include"], str, list=True,
        help=(
            "A name or shell-style pattern matching files or folders "
            "that must be included, even if their names are in the `exclude` list"
        ),
    )

    pretend = cli.Flag(
        ["-n", "--pretend"],
        help="Run but do not make any changes",
    )
    force = cli.Flag(
        ["-f", "--force"],
        help="Overwrite files that already exist, without asking",
    )
    skip = cli.Flag(
        ["-s", "--skip"],
        help="Skip files that already exist, without asking",
    )
    quiet = cli.Flag(
        ["-q", "--quiet"],
        help="Suppress status output",
    )

    @cli.switch(
        ["-d", "--data"], str, "VARIABLE=VALUE", list=True,
        help="Make VARIABLE available as VALUE when rendering the template")
    def data_switch(self, values):
        self.data.update(value.split("=", 1) for value in values)

    def _copy(self, src_path: OptStr = None, dst_path: str = ".") -> None:
        """Run Copier's internal API using CLI switches."""
        return copy(
            data=self.data,
            dst_path=dst_path,
            exclude=self.exclude,
            extra_paths=self.extra_paths,
            force=self.force,
            include=self.include,
            pretend=self.pretend,
            quiet=self.quiet,
            skip=self.skip,
            src_path=src_path,
        )

    def main(self, *args) -> int:
        """Copier shortcuts."""
        # If using 0 or 1 args, you want to update
        if len(args) in {0, 1}:
            self.nested_command = (
                self._subcommands["update"].subapplication,
                ["copier update"] + list(args))
        # If using 2 args, you want to copy
        elif len(args) == 2:
            self.nested_command = (
                self._subcommands["copy"].subapplication,
                ["copier copy"] + list(args))
        # If using more args, you're wrong
        else:
            self.help()
            print(colors.red | "Unsupported arguments", file=sys.stderr)
            return 1
        return 0


@CopierApp.subcommand("copy")
class CopierCopySubApp(cli.Application):
    DESCRIPTION = "Copy form a template source to a destination"

    def main(self, template_src: str, destination_path: str) -> int:
        self.parent._copy(template_src, destination_path)
        return 0


@CopierApp.subcommand("update")
class CopierUpdateSubApp(cli.Application):
    DESCRIPTION = "Update a copy from its original template"
    DESCRIPTION_MORE = """
    The copy must have a file called `.copier-answers.yml` which contains info
    from the last Copier execution, including the source template
    (it must be a key called `_src_path`).
    """

    def main(self, destination_path: cli.ExistingDirectory = ".") -> int:
        self.parent._copy(dst_path=destination_path)
        return 0


if __name__ == "__main__":
    CopierApp.run()
