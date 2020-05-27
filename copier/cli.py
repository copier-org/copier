#!/usr/bin/env python
import sys
from textwrap import dedent

from plumbum import cli, colors

from . import __version__
from .config.objects import UserMessageError
from .main import copy
from .types import AnyByStrDict, OptStr


def handle_exceptions(method):
    def _wrapper(*args, **kwargs):
        try:
            try:
                return method(*args, **kwargs)
            except KeyboardInterrupt:
                raise UserMessageError("Execution stopped by user")
        except UserMessageError as error:
            print(colors.red | "\n".join(error.args), file=sys.stderr)
            return 1

    return _wrapper


class CopierApp(cli.Application):
    DESCRIPTION = "Create a new project from a template."
    DESCRIPTION_MORE = colors.yellow | dedent(
        """
        WARNING! Use only trusted project templates, as they might
        execute code with the same level of access as your user.\n
        """
    )
    USAGE = dedent(
        """
        copier [SWITCHES] [copy] template_src destination_path
        copier [SWITCHES] [update] [destination_path]
        """
    )
    VERSION = __version__
    CALL_MAIN_IF_NESTED_COMMAND = False
    data: AnyByStrDict = {}

    answers_file = cli.SwitchAttr(
        ["-a", "--answers-file"],
        default=None,
        help=(
            "Update using this path (relative to `destination_path`) "
            "to find the answers file"
        ),
    )
    extra_paths = cli.SwitchAttr(
        ["-p", "--extra-paths"],
        str,
        list=True,
        help="Additional directories to find parent templates in",
    )
    exclude = cli.SwitchAttr(
        ["-x", "--exclude"],
        str,
        list=True,
        help=(
            "A name or shell-style pattern matching files or folders "
            "that must not be copied"
        ),
    )
    vcs_ref = cli.SwitchAttr(
        ["-r", "--vcs-ref"],
        str,
        help=(
            "Git reference to checkout in `template_src`. "
            "If you do not specify it, it will try to checkout the latest git tag, "
            "as sorted using the PEP 440 algorithm. If you want to checkout always "
            "the latest version, use `--vcs-ref=HEAD`."
        ),
    )
    subdirectory = cli.SwitchAttr(
        ["-b", "--subdirectory"],
        str,
        help=(
            "Subdirectory to use when generating the project. "
            "If you do not specify it, the root of the template is used."
        ),
    )

    pretend = cli.Flag(["-n", "--pretend"], help="Run but do not make any changes")
    force = cli.Flag(
        ["-f", "--force"], help="Overwrite files that already exist, without asking"
    )
    skip = cli.Flag(
        ["-s", "--skip"], help="Skip files that already exist, without asking"
    )
    quiet = cli.Flag(["-q", "--quiet"], help="Suppress status output")

    @cli.switch(
        ["-d", "--data"],
        str,
        "VARIABLE=VALUE",
        list=True,
        help="Make VARIABLE available as VALUE when rendering the template",
    )
    def data_switch(self, values):
        self.data.update(value.split("=", 1) for value in values)

    def _copy(self, src_path: OptStr = None, dst_path: str = ".", **kwargs) -> None:
        """Run Copier's internal API using CLI switches."""
        return copy(
            data=self.data,
            dst_path=dst_path,
            answers_file=self.answers_file,
            exclude=self.exclude,
            extra_paths=self.extra_paths,
            force=self.force,
            pretend=self.pretend,
            quiet=self.quiet,
            skip=self.skip,
            src_path=src_path,
            vcs_ref=self.vcs_ref,
            subdirectory=self.subdirectory,
            **kwargs,
        )

    @handle_exceptions
    def main(self, *args: str) -> int:
        """Copier shortcuts."""
        # Redirect to subcommand if supplied
        if args and args[0] in self._subcommands:
            self.nested_command = (
                self._subcommands[args[0]].subapplication,
                ["copier %s" % args[0]] + list(args[1:]),
            )
        # If using 0 or 1 args, you want to update
        elif len(args) in {0, 1}:
            self.nested_command = (
                self._subcommands["update"].subapplication,
                ["copier update"] + list(args),
            )
        # If using 2 args, you want to copy
        elif len(args) == 2:
            self.nested_command = (
                self._subcommands["copy"].subapplication,
                ["copier copy"] + list(args),
            )
        # If using more args, you're wrong
        else:
            self.help()
            raise UserMessageError("Unsupported arguments")
        return 0


@CopierApp.subcommand("copy")
class CopierCopySubApp(cli.Application):
    DESCRIPTION = "Copy form a template source to a destination"

    @handle_exceptions
    def main(self, template_src: str, destination_path: str) -> int:
        self.parent._copy(template_src, destination_path)
        return 0


@CopierApp.subcommand("update")
class CopierUpdateSubApp(cli.Application):
    DESCRIPTION = "Update a copy from its original template"
    DESCRIPTION_MORE = """
    The copy must have a valid answers file which contains info
    from the last Copier execution, including the source template
    (it must be a key called `_src_path`).

    If that file contains also `_commit` and `destination_path` is a git
    repository, this command will do its best to respect the diff that you have
    generated since the last `copier` execution. To disable that, use `--no-diff`.
    """

    only_diff = cli.Flag(
        ["-D", "--no-diff"], default=True, help="Disable smart diff detection."
    )

    @handle_exceptions
    def main(self, destination_path: cli.ExistingDirectory = ".") -> int:
        self.parent._copy(
            dst_path=destination_path, only_diff=self.only_diff,
        )
        return 0


if __name__ == "__main__":
    CopierApp.run()
