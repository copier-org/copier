import datetime
import filecmp
import os
import re
import shutil
import subprocess

from . import tools, vcs
from .user_data import get_user_data, prompt_bool


__all__ = (
    'copy',
    'copy_local',
)

# Files of the template to exclude from the final project
DEFAULT_EXCLUDE = (
    'copier.yml',
    '~*', '*.py[co]', '__pycache__', '__pycache__/*', '.git', '.git/*',
    '.DS_Store', '.svn'
)

DEFAULT_INCLUDE = ()

DEFAULT_DATA = {
    'now': datetime.datetime.utcnow,
}


def copy(
    src_path,
    dst_path,
    data=None,
    *,
    exclude=None,
    include=None,
    tasks=None,
    envops=None,

    pretend=False,
    force=False,
    skip=False,
    quiet=False
):
    """
    Uses the template in src_path to generate a new project at dst_path.

    Arguments:

    - src_path (str):
        Absolute path to the project skeleton. May be a version control system URL

    - dst_path (str):
        Absolute path to where to render the skeleton

    - data (dict):
        Optional. Data to be passed to the templates in addtion to the user data from
        a `copier.json`.

    - exclude (list):
        A list of names or shell-style patterns matching files or folders
        that must not be copied.

    - include (list):
        A list of names or shell-style patterns matching files or folders that
        must be included, even if its name are in the `exclude` list.
        Eg: `['.gitignore']`. The default is an empty list.

    - tasks (list):
        Optional lists of commands to run in order after finishing the copy.
        Like in the templates files, you can use variables on the commands that will
        be replaced by the real values before running the command.
        If one of the commands fail, the rest of them will not run.

    - envops (dict):
        Extra options for the Jinja template environment.

    - pretend (bool):
        Run but do not make any changes

    - force (bool):
        Overwrite files that already exist, without asking

    - skip (bool):
        Skip files that already exist, without asking

    - quiet (bool):
        Suppress the status output

    """
    repo = vcs.get_repo(src_path)
    if repo:
        src_path = vcs.clone(repo)

    _data = DEFAULT_DATA.copy()
    _data.update(data or {})

    try:
        copy_local(
            src_path,
            dst_path,
            data=_data,
            exclude=exclude,
            include=include,
            tasks=tasks,
            envops=envops,

            pretend=pretend,
            force=force,
            skip=skip,
            quiet=quiet,
        )
    finally:
        if repo:
            shutil.rmtree(src_path)


RE_TMPL = re.compile(r'\.tmpl$', re.IGNORECASE)


def copy_local(
    src_path,
    dst_path,
    data,
    *,
    exclude,
    include,
    tasks,
    envops,
    **flags
):
    if not os.path.exists(src_path):
        raise ValueError('Project template not found')
    if not os.path.isdir(src_path):
        raise ValueError('The project template must be a folder')

    user_data = get_user_data(src_path, **flags)

    if exclude is None:
        exclude = user_data.pop('_exclude', None) or DEFAULT_EXCLUDE
    if include is None:
        include = user_data.pop('_include', None) or DEFAULT_INCLUDE
    must_filter = tools.get_name_filter(exclude, include)

    if tasks is None:
        tasks = user_data.pop('_tasks', None) or []

    data.update(user_data)
    data.setdefault('folder_name', os.path.basename(dst_path))

    render = tools.get_jinja_renderer(src_path, data, envops)

    if not flags['quiet']:
        print('')  # padding space
    for folder, _, files in os.walk(src_path):
        rel_folder = folder.replace(src_path, '').lstrip(os.path.sep)
        rel_folder = render.string(rel_folder)
        if must_filter(rel_folder):
            continue

        for src_name in files:
            dst_name = re.sub(RE_TMPL, '', src_name)
            dst_name = render.string(dst_name)
            rel_path = os.path.join(rel_folder, dst_name)
            if must_filter(rel_path):
                continue

            render_file(
                dst_path,
                rel_folder,
                folder,
                src_name,
                dst_name,
                render,
                **flags,
            )
    if not flags['quiet']:
        print('')  # padding space

    if tasks:
        run_tasks(dst_path, render, tasks)


def render_file(
    dst_path,
    rel_folder,
    folder,
    src_name,
    dst_name,
    render,
    **flags
):
    """Process or copy a file of the skeleton.
    """
    source_path = os.path.join(folder, src_name)
    display_path = os.path.join(rel_folder, dst_name).lstrip('.').lstrip(os.path.sep)
    final_path = tools.make_folder(
        dst_path, rel_folder, dst_name,
        pretend=flags['pretend']
    )

    if src_name.endswith('.tmpl'):
        content = render(source_path)
    else:
        content = None

    if not os.path.exists(final_path):
        if not flags['quiet']:
            tools.print_format('create', display_path, color=tools.COLOR_OK)
    else:
        if file_is_identical(source_path, final_path, content):
            if not flags['quiet']:
                tools.print_format(
                    'identical', display_path,
                    color=tools.COLOR_IGNORE, bright=None
                )
            return

        if not overwrite_file(display_path, source_path, final_path, content, **flags):
            return

    if flags['pretend']:
        return

    if content is None:
        tools.copy_file(source_path, final_path)
    else:
        tools.write_file(final_path, content)


def file_is_identical(source_path, final_path, content):
    if content is None:
        return files_are_identical(source_path, final_path)

    return file_has_this_content(final_path, content)


def files_are_identical(path1, path2):
    return filecmp.cmp(path1, path2, shallow=False)


def file_has_this_content(path, content):
    return content == tools.read_file(path)


def overwrite_file(display_path, source_path, final_path, content, **flags):
    if not flags['quiet']:
        tools.print_format('conflict', display_path, color=tools.COLOR_DANGER)
    if flags['force']:
        overwrite = True
    elif flags['skip']:
        overwrite = False
    else:  # pragma:no cover
        msg = '  Overwrite {}? (y/n)'.format(final_path)
        overwrite = prompt_bool(msg, default=True)

    if not flags['quiet']:
        tools.print_format(
            'force' if overwrite else 'skip',
            display_path, color=tools.COLOR_WARNING,
        )

    return overwrite


def run_tasks(dst_path, render, tasks):
    cwd = os.getcwd()
    os.chdir(dst_path)
    try:
        for task in tasks:
            task = render.string(task)
            subprocess.run(task, shell=True, check=True)
    finally:
        os.chdir(cwd)
