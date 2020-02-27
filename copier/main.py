import filecmp
import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Callable, List, Optional, Tuple

from plumbum import local
from plumbum.cli.terminal import ask
from plumbum.cmd import git

from . import vcs
from .config import make_config
from .config.objects import ConfigData, UserMessageError
from .tools import (
    Renderer,
    Style,
    copy_file,
    create_path_filter,
    get_migration_tasks,
    make_folder,
    printf,
)
from .types import (
    AnyByStrDict,
    CheckPathFunc,
    OptBool,
    OptStr,
    OptStrSeq,
    StrOrPath,
    StrSeq,
)

__all__ = ("copy", "copy_local")


def copy(
    src_path: OptStr = None,
    dst_path: StrOrPath = ".",
    data: AnyByStrDict = None,
    *,
    exclude: OptStrSeq = None,
    skip_if_exists: OptStrSeq = None,
    tasks: OptStrSeq = None,
    envops: AnyByStrDict = None,
    extra_paths: OptStrSeq = None,
    pretend: OptBool = False,
    force: OptBool = False,
    skip: OptBool = False,
    quiet: OptBool = False,
    cleanup_on_error: OptBool = True,
    vcs_ref: OptStr = None,
    only_diff: OptBool = True,
) -> None:
    """
    Uses the template in src_path to generate a new project at dst_path.

    Arguments:

    - src_path (str):
        Absolute path to the project skeleton. May be a version control system URL.
        If `None`, it will be taken from `dst_path/.copier-answers.yml` or fail.

    - dst_path (str):
        Absolute path to where to render the skeleton

    - data (dict):
        Optional. Data to be passed to the templates in addtion to the user data from
        a `copier.json`.

    - exclude (list):
        A list of names or shell-style patterns matching files or folders
        that must not be copied.

    - skip_if_exists (list):
        Skip any of these files if another with the same name already exists in the
        destination folder. (it only makes sense if you are copying to a folder that
        already exists).

    - tasks (list):
        Optional lists of commands to run in order after finishing the copy.
        Like in the templates files, you can use variables on the commands that will
        be replaced by the real values before running the command.
        If one of the commands fail, the rest of them will not run.

    - envops (dict):
        Extra options for the Jinja template environment.

    - extra_paths (list):
        Optional. Additional paths, outside the `src_path`, from where to search for
        templates. This is intended to be used with shared parent templates, files
        with macros, etc. outside the copied project skeleton.

    - pretend (bool):
        Run but do not make any changes

    - force (bool):
        Overwrite files that already exist, without asking

    - skip (bool):
        Skip files that already exist, without asking

    - quiet (bool):
        Suppress the status output

    - cleanup_on_error (bool):
        Remove the destination folder if the copy process or one of the tasks fail.

    - vcs_ref (str):
        VCS reference to checkout in the template.

    - only_diff (bool):
        Try to update only the template diff.
    """
    conf = make_config(**locals())
    is_update = conf.original_src_path != conf.src_path and vcs.is_git_repo_root(
        conf.src_path
    )
    do_diff_update = (
        conf.only_diff
        and is_update
        and conf.old_commit
        and vcs.is_git_repo_root(Path(conf.dst_path))
    )
    try:
        if do_diff_update:
            update_diff(conf=conf)
        else:
            copy_local(conf=conf)
    except Exception:
        if conf.cleanup_on_error and not do_diff_update:
            print("Something went wrong. Removing destination folder.")
            shutil.rmtree(conf.dst_path, ignore_errors=True)
        raise
    finally:
        if is_update:
            shutil.rmtree(conf.src_path)


def copy_local(conf: ConfigData) -> None:

    must_filter = create_path_filter(conf.exclude)

    render = Renderer(conf)
    skip_patterns = [render.string(pattern) for pattern in conf.skip_if_exists]
    must_skip = create_path_filter(skip_patterns)

    if not conf.quiet:
        print("")  # padding space

    folder: StrOrPath
    rel_folder: StrOrPath
    for folder, sub_dirs, files in os.walk(conf.src_path):
        rel_folder = str(folder).replace(str(conf.src_path), "", 1).lstrip(os.path.sep)
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

    run_tasks(conf, render, conf.tasks)
    if not conf.quiet:
        print("")  # padding space


def update_diff(conf: ConfigData):
    # Ensure local repo is clean
    if vcs.is_git_repo_root(conf.dst_path):
        with local.cwd(conf.dst_path):
            if git("status", "--porcelain"):
                raise UserMessageError(
                    "Destination repository is dirty; cannot continue. "
                    "Please commit or stash your local changes and retry."
                )
    # Checkout src_path into old commit
    old_commit_src_path = vcs.clone(str(conf.src_path), str(conf.old_commit))
    # Copy old template into a temporary destination
    with tempfile.TemporaryDirectory() as dst_temp:
        copy_local(
            conf.copy(
                update={
                    "force": True,
                    "skip": False,
                    "quiet": True,
                    "src_path": old_commit_src_path,
                    "dst_path": dst_temp,
                    "commit": conf.old_commit,
                },
                deep=True,
            )
        )
        # Extract diff between temporary destination and real destination
        with local.cwd(dst_temp):
            git("init", retcode=None)
            git("add", ".")
            git("config", "user.name", "Copier")
            git("config", "user.email", "copier@copier")
            git("commit", "-m", "foo")
            git("config", "--unset", "user.name")
            git("config", "--unset", "user.email")
            git("remote", "add", "real_dst", conf.dst_path)
            git("fetch", "real_dst", "HEAD")
            diff = git("diff", "--unified=0", "HEAD...FETCH_HEAD")
    # Run pre-migration tasks
    renderer = Renderer(conf)
    run_tasks(conf, renderer, get_migration_tasks(conf, "before"))
    # Do a normal update in final destination
    copy_local(conf)
    # Try to apply cached diff into final destination
    with local.cwd(conf.dst_path):
        (git["apply", "--reject"] << diff)(retcode=None)
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
    dst_path = conf.dst_path / rel_folder
    rel_path = f"{rel_folder}{os.path.sep}"

    if rel_folder == Path("."):
        if not conf.pretend:
            make_folder(dst_path)
        return

    if dst_path.exists():
        printf("identical", rel_path, style=Style.IGNORE, quiet=conf.quiet)
        return

    if not conf.pretend:
        make_folder(dst_path)

    printf("create", rel_path, style=Style.OK, quiet=conf.quiet)


def render_file(
    conf: ConfigData,
    rel_path: Path,
    src_path: Path,
    render: Renderer,
    must_skip: CheckPathFunc,
) -> None:
    """Process or copy a file of the skeleton.
    """
    content: Optional[str] = None
    if str(src_path).endswith(conf.templates_suffix):
        content = render(src_path)

    dst_path = conf.dst_path / rel_path

    if not dst_path.exists():
        printf("create", rel_path, style=Style.OK, quiet=conf.quiet)
    elif files_are_identical(src_path, dst_path, content):
        printf("identical", rel_path, style=Style.IGNORE, quiet=conf.quiet)
        return
    elif must_skip(rel_path) or not overwrite_file(conf, dst_path, rel_path):
        printf("skip", rel_path, style=Style.WARNING, quiet=conf.quiet)
        return
    else:
        printf("force", rel_path, style=Style.WARNING, quiet=conf.quiet)

    if conf.pretend:
        pass
    elif content is None:
        copy_file(src_path, dst_path)
    else:
        dst_path.write_text(content)


def files_are_identical(src_path: Path, dst_path: Path, content: Optional[str]) -> bool:
    if content is None:
        return filecmp.cmp(str(src_path), str(dst_path), shallow=False)
    return dst_path.read_text() == content


def overwrite_file(conf: ConfigData, dst_path: Path, rel_path: Path) -> bool:
    printf("conflict", rel_path, style=Style.DANGER, quiet=conf.quiet)
    if conf.force:
        return True
    if conf.skip:
        return False
    return bool(ask(f" Overwrite {dst_path}?", default=True))


def run_tasks(conf: ConfigData, render: Renderer, tasks: StrSeq) -> None:
    for i, task in enumerate(tasks):
        task = render.string(task)
        # TODO: should we respect the `quiet` flag here as well?
        printf(f" > Running task {i + 1} of {len(tasks)}", task, style=Style.OK)
        subprocess.run(task, shell=True, check=True, cwd=conf.dst_path)
