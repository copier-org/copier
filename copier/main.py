"""The main functions, used to generate or update projects."""

import filecmp
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Callable, Dict, List, Optional, Sequence, Tuple

from packaging.version import InvalidVersion, Version
from plumbum import ProcessExecutionError, colors, local
from plumbum.cli.terminal import ask
from plumbum.cmd import git

from copier.models import Copier

from . import vcs
from .config.objects import ConfigData, UserMessageError
from .config.user_data import load_answersfile_data
from .tools import (
    Renderer,
    Style,
    copy_file,
    create_path_filter,
    get_migration_tasks,
    make_folder,
    printf,
)
from .types import AnyByStrDict, CheckPathFunc, OptStr, StrOrPath, StrSeq

__all__ = ("copy", "copy_local")


def copy(
    src_path: OptStr = None,
    dst_path: StrOrPath = ".",
    data: AnyByStrDict = None,
    **kwargs,
) -> None:
    """Uses the template in `src_path` to generate a new project at `dst_path`.

    This is usually the main entrypoint for API usage.

    Arguments:
        src_path:
            Absolute path to the project skeleton. May be a version control system URL.
            If `None`, it will be taken from `dst_path/answers_file` or fail.

        dst_path:
            Absolute path to where to render the skeleton

        data:
            Optional. Data to be passed to the templates in addtion to the user data
            from a `copier.json`.

        answers_file:
            Path where to obtain the answers recorded from the last update.
            The path must be relative to `dst_path`.

        exclude:
            A list of names or gitignore-style patterns matching files or folders that
            must not be copied.

        skip_if_exists:
            A list of names or gitignore-style patterns matching files or folders,
            that are skipped if another with the same name already exists in the
            destination folder. (It only makes sense if you are copying to a folder
            that already exists).

        tasks:
            Optional lists of commands to run in order after finishing the copy.
            Like in the templates files, you can use variables on the commands that
            will be replaced by the real values before running the command.
            If one of the commands fail, the rest of them will not run.

        envops:
            Extra options for the Jinja template environment.

        extra_paths:
            Optional. Additional paths, outside the `src_path`, from where to search
            for templates. This is intended to be used with shared parent templates,
            files with macros, etc. outside the copied project skeleton.

        pretend:
            Run but do not make any changes.

        force:
            Overwrite files that already exist, without asking.

        skip:
            Skip files that already exist, without asking.

        quiet:
            Suppress the status output.

        cleanup_on_error:
            Remove the destination folder if Copier created it and the copy process
            or one of the tasks fail.

        vcs_ref:
            VCS reference to checkout in the template.

        only_diff:
            Try to update only the template diff.

        subdirectory:
            Specify a subdirectory to use when generating the project.

        use_prereleases: See [use_prereleases][].
    """
    conf = ConfigData(
        src_path=src_path, dst_path=dst_path, data_from_init=data or {}, **kwargs
    )
    copier = Copier(conf=conf)
    copier.run_auto()


def copy_local(conf: ConfigData) -> None:
    """Use the given configuration to generate a project.

    Arguments:
        conf: Configuration obtained with [`make_config`][copier.config.factory.make_config].
    """
    must_filter = create_path_filter(conf.exclude)

    render = Renderer(conf)
    skip_patterns = [render.string(pattern) for pattern in conf.skip_if_exists]
    must_skip = create_path_filter(skip_patterns)

    if not conf.quiet:
        print("")  # padding space

    folder: StrOrPath
    rel_folder: StrOrPath

    src_path = conf.src_path
    if conf.subdirectory is not None:
        src_path /= conf.subdirectory

    for folder, sub_dirs, files in os.walk(src_path):
        rel_folder = str(folder).replace(str(src_path), "", 1).lstrip(os.path.sep)
        rel_folder = render.string(rel_folder)
        rel_folder = str(rel_folder).replace("." + os.path.sep, ".", 1)

        if must_filter(rel_folder):
            # Folder is excluded, so stop walking it
            sub_dirs[:] = []
            continue

        folder = Path(folder)
        rel_folder = Path(rel_folder)

        render_folder(rel_folder, conf)

        source_paths = get_source_paths(
            conf, folder, rel_folder, files, render, must_filter
        )
        for source_path, rel_path in source_paths:
            render_file(conf, rel_path, source_path, render, must_skip)

    if not conf.quiet:
        print("")  # padding space

    run_tasks(
        conf, render, [{"task": t, "extra_env": {"STAGE": "task"}} for t in conf.tasks]
    )
    if not conf.quiet:
        print("")  # padding space


def update_diff(conf: ConfigData) -> None:
    """Use the given configuration to update a project.

    Arguments:
        conf: Configuration obtained with [`make_config`][copier.config.factory.make_config].
    """
    # Ensure local repo is clean
    if vcs.is_git_repo_root(conf.dst_path):
        with local.cwd(conf.dst_path):
            if git("status", "--porcelain"):
                raise UserMessageError(
                    "Destination repository is dirty; cannot continue. "
                    "Please commit or stash your local changes and retry."
                )
    last_answers = load_answersfile_data(conf.dst_path, conf.answers_file)
    downgrading = False
    if conf.old_commit and conf.commit:
        try:
            downgrading = Version(conf.old_commit) > Version(conf.commit)
        except InvalidVersion:
            print(
                colors.warn
                | f"Either {conf.old_commit} or {conf.vcs_ref} is not a PEP 440 valid version.",
                file=sys.stderr,
            )
        else:
            if downgrading:
                raise UserMessageError(
                    f"Your are downgrading from {conf.old_commit} to {conf.commit}. "
                    "Downgrades are not supported."
                )
    # Copy old template into a temporary destination
    with tempfile.TemporaryDirectory(prefix=f"{__name__}.update_diff.") as dst_temp:
        copy(
            dst_path=dst_temp,
            data=last_answers,
            force=True,
            quiet=True,
            skip=False,
            src_path=conf.original_src_path,
            vcs_ref=conf.old_commit,
        )
        # Extract diff between temporary destination and real destination
        with local.cwd(dst_temp):
            git("init", retcode=None)
            git("add", ".")
            git("config", "user.name", "Copier")
            git("config", "user.email", "copier@copier")
            # 1st commit could fail if any pre-commit hook reformats code
            git("commit", "--allow-empty", "-am", "dumb commit 1", retcode=None)
            git("commit", "--allow-empty", "-am", "dumb commit 2")
            git("config", "--unset", "user.name")
            git("config", "--unset", "user.email")
            git("remote", "add", "real_dst", conf.dst_path)
            git("fetch", "--depth=1", "real_dst", "HEAD")
            diff_cmd = git["diff-tree", "--unified=1", "HEAD...FETCH_HEAD"]
            try:
                diff = diff_cmd("--inter-hunk-context=-1")
            except ProcessExecutionError:
                print(
                    colors.warn
                    | "Make sure Git >= 2.24 is installed to improve updates.",
                    file=sys.stderr,
                )
                diff = diff_cmd("--inter-hunk-context=0")
    # Run pre-migration tasks
    renderer = Renderer(conf)
    run_tasks(conf, renderer, get_migration_tasks(conf, "before"))
    # Import possible answers migration
    conf = conf.copy(
        update={
            "data_from_answers_file": load_answersfile_data(
                conf.dst_path, conf.answers_file
            )
        }
    )
    # Do a normal update in final destination
    copy_local(conf)
    # Try to apply cached diff into final destination
    with local.cwd(conf.dst_path):
        apply_cmd = git["apply", "--reject", "--exclude", conf.answers_file]
        for skip_pattern in conf.skip_if_exists:
            apply_cmd = apply_cmd["--exclude", skip_pattern]
        (apply_cmd << diff)(retcode=None)
    # Run post-migration tasks
    run_tasks(conf, renderer, get_migration_tasks(conf, "after"))


def get_source_paths(
    conf: ConfigData,
    folder: Path,
    rel_folder: Path,
    files: StrSeq,
    render: Renderer,
    must_filter: Callable[[StrOrPath], bool],
) -> List[Tuple[Path, Path]]:
    """Get the paths to all the files to render.

    Arguments:
        conf: Configuration obtained with [`make_config`][copier.config.factory.make_config].
        folder:
        rel_folder: Relative path to the folder.
        files:
        render: The [template renderer][copier.tools.Renderer] instance.
        must_filter: A callable telling whether to skip rendering a file.

    Returns:
        The list of files to render.
    """
    source_paths = []
    files_set = set(files)
    for src_name in files:
        src_name = str(src_name)
        if f"{src_name}{conf.templates_suffix}" in files_set:
            continue
        dst_name = (
            src_name[: -len(conf.templates_suffix)]
            if src_name.endswith(conf.templates_suffix)
            else src_name
        )
        dst_name = render.string(dst_name)
        rel_path = rel_folder / dst_name

        if rel_folder == rel_path or must_filter(rel_path):
            continue
        source_paths.append((folder / src_name, rel_path))
    return source_paths


def render_folder(rel_folder: Path, conf: ConfigData) -> None:
    """Render a complete folder.

    This function renders the folder's name as well as its contents.

    Arguments:
        rel_folder: The relative path to the folder.
        conf: Configuration obtained with [`make_config`][copier.config.factory.make_config].
    """
    dst_path = conf.dst_path / rel_folder
    rel_path = f"{rel_folder}{os.path.sep}"

    if rel_folder == Path("."):
        if not conf.pretend:
            make_folder(dst_path)
        return

    if dst_path.exists():
        printf(
            "identical",
            rel_path,
            style=Style.IGNORE,
            quiet=conf.quiet,
            file_=sys.stderr,
        )
        return

    if not conf.pretend:
        make_folder(dst_path)

    printf("create", rel_path, style=Style.OK, quiet=conf.quiet, file_=sys.stderr)


def render_file(
    conf: ConfigData,
    rel_path: Path,
    src_path: Path,
    render: Renderer,
    must_skip: CheckPathFunc,
) -> None:
    """Process or copy a file of the skeleton.

    Arguments:
        conf: Configuration obtained with [`make_config`][copier.config.factory.make_config].
        rel_path: The relative path to the file.
        src_path:
        render: The [template renderer][copier.tools.Renderer] instance.
        must_skip: A callable telling whether to skip a file.
    """
    content: Optional[str] = None
    if str(src_path).endswith(conf.templates_suffix):
        content = render(src_path)

    dst_path = conf.dst_path / rel_path

    if not dst_path.exists():
        printf("create", rel_path, style=Style.OK, quiet=conf.quiet, file_=sys.stderr)
    elif files_are_identical(src_path, dst_path, content):
        printf(
            "identical",
            rel_path,
            style=Style.IGNORE,
            quiet=conf.quiet,
            file_=sys.stderr,
        )
        return
    elif must_skip(rel_path) or not overwrite_file(conf, dst_path, rel_path):
        printf(
            "skip", rel_path, style=Style.WARNING, quiet=conf.quiet, file_=sys.stderr
        )
        return
    else:
        printf(
            "force", rel_path, style=Style.WARNING, quiet=conf.quiet, file_=sys.stderr
        )

    if conf.pretend:
        pass
    elif content is None:
        copy_file(src_path, dst_path)
    else:
        dst_path.write_text(content)


def files_are_identical(src_path: Path, dst_path: Path, content: Optional[str]) -> bool:
    """Tell whether two files are identical.

    Arguments:
        src_path: Source file.
        dst_path: Destination file.
        content: File contents.

    Returns:
        True if the files are identical, False otherwise.
    """
    if content is None:
        return filecmp.cmp(str(src_path), str(dst_path), shallow=False)
    return dst_path.read_text() == content


def overwrite_file(conf: ConfigData, dst_path: Path, rel_path: Path) -> bool:
    """Handle the case when there's an update conflict.

    Arguments:
        conf: Configuration obtained with [`make_config`][copier.config.factory.make_config].
        dst_path: The destination file.
        rel_path: The new file.

    Returns:
        True if the overwrite was forced or the user answered yes,
        False if skipped by configuration or if the user answered no.
    """
    printf("conflict", rel_path, style=Style.DANGER, quiet=conf.quiet, file_=sys.stderr)
    if conf.force:
        return True
    if conf.skip:
        return False
    return bool(ask(f" Overwrite {dst_path}?", default=True))


def run_tasks(conf: ConfigData, render: Renderer, tasks: Sequence[Dict]) -> None:
    """Run the given tasks.

    Arguments:
        conf: Configuration obtained with [`make_config`][copier.config.factory.make_config].
        render: The [template renderer][copier.tools.Renderer] instance.
        tasks: The list of tasks to run.
    """
    for i, task in enumerate(tasks):
        task_cmd = task["task"]
        use_shell = isinstance(task_cmd, str)
        if use_shell:
            task_cmd = render.string(task_cmd)
        else:
            task_cmd = [render.string(part) for part in task_cmd]
        if not conf.quiet:
            print(
                colors.info | f" > Running task {i + 1} of {len(tasks)}: {task_cmd}",
                file=sys.stderr,
            )
        with local.cwd(conf.dst_path), local.env(**task.get("extra_env", {})):
            subprocess.run(task_cmd, shell=use_shell, check=True, env=local.env)
