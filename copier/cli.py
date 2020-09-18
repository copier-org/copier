#!/usr/bin/env python
"""
Command line entrypoint. This module declares the Copier CLI applications.

Basically, there are 3 different commands you can run:

-   [`copier`][copier.cli.CopierApp], the main app, which includes shortcuts
    for the `copy` and `update` subapps.
-   [`copier copy`][copier.cli.CopierApp], used to bootstrap a new project
    from a template.
-   [`copier update`][copier.cli.CopierUpdateSubApp] to update a preexisting
    project to a newer version of its template.

Below are the docs of each one of those.
"""

import sys
from functools import wraps
from io import StringIO
from textwrap import dedent
from unittest.mock import patch

from plumbum import cli, colors

from . import __version__
from .config.objects import UserMessageError
from .main import copy
from .types import AnyByStrDict, List, OptStr


def handle_exceptions(method):
    """Handle keyboard interruption while running a method."""

    @wraps(method)
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
    """The Copier CLI application.

    Attributes:
        answers_file: Set [answers_file][] option.
        extra_paths: Set [extra_paths][] option.
        exclude: Set [exclude][] option.
        vcs_ref: Set [vcs_ref][] option.
        subdirectory: Set [subdirectory][] option.
        pretend: Set [pretend][] option.
        force: Set [force][] option.
        skip: Set [skip_if_exists][] option.
        prereleases: Set [use_prereleases][] option.
        quiet: Set [quiet][] option.
    """

    DESCRIPTION = "Create a new project from a template."
    DESCRIPTION_MORE = (
        dedent(
            """\
            Docs in https://copier.readthedocs.io/

            """
        )
        + (
            colors.yellow
            | dedent(
                """\
                WARNING! Use only trusted project templates, as they might
                execute code with the same level of access as your user.\n
                """
            )
        )
    )
    USAGE = dedent(
        """\
        copier [MAIN_SWITCHES] [copy] [SUB_SWITCHES] template_src destination_path
        copier [MAIN_SWITCHES] [update] [SUB_SWITCHES] [destination_path]
        """
    )
    VERSION = __version__
    CALL_MAIN_IF_NESTED_COMMAND = False
    data: AnyByStrDict = {}

    answers_file: cli.SwitchAttr = cli.SwitchAttr(
        ["-a", "--answers-file"],
        default=None,
        help=(
            "Update using this path (relative to `destination_path`) "
            "to find the answers file"
        ),
    )
    extra_paths: cli.SwitchAttr = cli.SwitchAttr(
        ["-p", "--extra-paths"],
        str,
        list=True,
        help="Additional directories to find parent templates in",
    )
    exclude: cli.SwitchAttr = cli.SwitchAttr(
        ["-x", "--exclude"],
        str,
        list=True,
        help=(
            "A name or shell-style pattern matching files or folders "
            "that must not be copied"
        ),
    )
    vcs_ref: cli.SwitchAttr = cli.SwitchAttr(
        ["-r", "--vcs-ref"],
        str,
        help=(
            "Git reference to checkout in `template_src`. "
            "If you do not specify it, it will try to checkout the latest git tag, "
            "as sorted using the PEP 440 algorithm. If you want to checkout always "
            "the latest version, use `--vcs-ref=HEAD`."
        ),
    )
    subdirectory: cli.SwitchAttr = cli.SwitchAttr(
        ["-b", "--subdirectory"],
        str,
        help=(
            "Subdirectory to use when generating the project. "
            "If you do not specify it, the root of the template is used."
        ),
    )

    pretend: cli.Flag = cli.Flag(
        ["-n", "--pretend"], help="Run but do not make any changes"
    )
    force: cli.Flag = cli.Flag(
        ["-f", "--force"], help="Overwrite files that already exist, without asking"
    )
    skip: cli.Flag = cli.Flag(
        ["-s", "--skip"], help="Skip files that already exist, without asking"
    )
    quiet: cli.Flag = cli.Flag(["-q", "--quiet"], help="Suppress status output")
    prereleases: cli.Flag = cli.Flag(
        ["-g", "--prereleases"], help="Use prereleases to compare template VCS tags.",
    )

    @cli.switch(
        ["-d", "--data"],
        str,
        "VARIABLE=VALUE",
        list=True,
        help="Make VARIABLE available as VALUE when rendering the template",
    )
    def data_switch(self, values: List[str]) -> None:
        """Update [data][] with provided values.

        Arguments:
            values: The list of values to apply.
                Each value in the list is of the following form: `NAME=VALUE`.
        """
        self.data.update(value.split("=", 1) for value in values)  # type: ignore

    def _copy(self, src_path: OptStr = None, dst_path: str = ".", **kwargs) -> None:
        """
        Run Copier's internal API using CLI switches.

        Arguments:
            src_path: The source path of the template to generate the project from.
            dst_path: The path to generate the project to.
            **kwargs: Arguments passed to [`copy`][copier.main.copy].
        """
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
            use_prereleases=self.prereleases,
            **kwargs,
        )

    @handle_exceptions
    def main(self, *args: str) -> int:
        """Copier CLI app shortcuts.

        This method redirects abstract CLI calls
        (those that don't specify `copy` or `update`)
        to [CopierCopySubApp.main][copier.cli.CopierCopySubApp.main]
        or [CopierUpdateSubApp.main][copier.cli.CopierUpdateSubApp.main]
        automatically.

        Examples:
            - `copier from to` → `copier copy from to`
            - `copier from` → `copier update from`
            - `copier` → `copier update .`
        """
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
    """The `copier copy` subcommand.

    Use this subcommand to bootstrap a new subproject from a template, or to override
    a preexisting subproject ignoring its history diff.

    Attributes:
        cleanup_on_error: Set [cleanup_on_error][] option.
    """

    DESCRIPTION = "Copy form a template source to a destination."

    cleanup_on_error: cli.Flag = cli.Flag(
        ["-C", "--no-cleanup"],
        default=True,
        help="On error, do not delete destination if it was created by Copier.",
    )

    @handle_exceptions
    def main(self, template_src: str, destination_path: str) -> int:
        """Call [`copy`][copier.main.copy] in copy mode.

        Params:
            template_src:
                Indicate where to get the template from.

                This can be a git URL or a local path.

            destination_path:
                Where to generate the new subproject. It must not exist or be empty.
        """
        self.parent._copy(
            template_src,
            destination_path,
            cleanup_on_error=self.cleanup_on_error,
            only_diff=False,
        )
        return 0


@CopierApp.subcommand("update")
class CopierUpdateSubApp(cli.Application):
    """The `copier update` subcommand.

    Use this subcommand to update an existing subproject from a template
    that supports updates.
    """

    DESCRIPTION = "Update a copy from its original template"
    DESCRIPTION_MORE = dedent(
        """\
        The copy must have a valid answers file which contains info
        from the last Copier execution, including the source template
        (it must be a key called `_src_path`).

        If that file contains also `_commit` and `destination_path` is a git
        repository, this command will do its best to respect the diff that you have
        generated since the last `copier` execution. To avoid that, use `copier copy`
        instead.
        """
    )

    @handle_exceptions
    def main(self, destination_path: cli.ExistingDirectory = ".") -> int:
        """Call [`copy`][copier.main.copy] in update mode.

        Parameters:
            destination_path:
                Only the destination path is needed to update, because the
                `src_path` comes from [the answers file][the-copier-answersyml-file].

                The subproject must exist. If not specified, the currently
                working directory is used.
        """
        self.parent._copy(
            dst_path=destination_path, only_diff=True,
        )
        return 0


# Add --help-all results to docs
if __doc__:
    help_io = StringIO()
    with patch("sys.stdout", help_io):
        CopierApp.run(["copier", "--help-all"], exit=False)
    help_io.seek(0)
    __doc__ += f"\n\nCLI help generated from `copier --help-all`:\n\n```\n{help_io.read()}\n```"

if __name__ == "__main__":
    CopierApp.run()
