"""The main functions, used to generate or update projects."""

from pathlib import Path
from typing import Callable, List, Tuple

from .models import Worker
from .types import AnyByStrDict, OptStr, StrOrPath, StrSeq

__all__ = ("copy",)


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
    if data is None:
        del data
    worker = Worker(**locals(), **kwargs)
    worker.run_auto()


# FIXME Refactor and delete
def get_source_paths(
    conf: "ConfigData",
    folder: Path,
    rel_folder: Path,
    files: StrSeq,
    render: "Renderer",
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
