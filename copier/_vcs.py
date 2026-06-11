"""Utilities related to VCS."""

from __future__ import annotations

import os
import re
import sys
from contextlib import suppress
from hashlib import sha256
from pathlib import Path
from shutil import rmtree
from tempfile import TemporaryDirectory, mkdtemp
from warnings import warn

from packaging import version
from packaging.version import InvalidVersion, Version
from platformdirs import user_cache_dir
from plumbum import TF, CommandNotFound, ProcessExecutionError, colors, local
from plumbum.commands.base import BaseCommand

from ._tools import handle_remove_readonly
from ._types import OptBool, OptStrOrPath, StrOrPath
from .errors import DirtyLocalWarning, ShallowCloneWarning

GIT_USER_NAME = "Copier"
GIT_USER_EMAIL = "copier@copier"

CLONE_PREFIX = f"{__name__}.clone."

# Environment variable to override the on-disk location of the git mirror cache.
CACHE_DIR_ENV_VAR = "COPIER_CACHE_DIR"


class _PathStr(str):
    """A string that represents a path."""


def get_git(context_dir: OptStrOrPath = None) -> BaseCommand:
    """Gets `git` command, or fails if it's not available."""
    command = local["git"].with_env(
        GIT_AUTHOR_NAME=GIT_USER_NAME,
        GIT_AUTHOR_EMAIL=GIT_USER_EMAIL,
        GIT_COMMITTER_NAME=GIT_USER_NAME,
        GIT_COMMITTER_EMAIL=GIT_USER_EMAIL,
    )
    if context_dir:
        command = command["-C", context_dir]
    return command


def get_git_version() -> Version:
    """Get the installed git version."""
    git = get_git()

    return Version(re.findall(r"\d+\.\d+(?:\.\d+)?", git("version"))[0])


def is_git_available() -> bool:
    """Indicate if `git` is available in the system."""
    git_path: str | None = None
    for exe in ("git", "git.exe"):
        try:
            git_path = local.which(exe)
        except CommandNotFound:  # noqa: PERF203
            continue
        else:
            break
    return git_path is not None


GIT_PREFIX = ("git@", "git://", "git+", "https://github.com/", "https://gitlab.com/")
GIT_POSTFIX = ".git"
REPLACEMENTS = (
    (re.compile(r"^gh:/?(.*\.git)$"), r"https://github.com/\1"),
    (re.compile(r"^gh:/?(.*)$"), r"https://github.com/\1.git"),
    (re.compile(r"^gl:/?(.*\.git)$"), r"https://gitlab.com/\1"),
    (re.compile(r"^gl:/?(.*)$"), r"https://gitlab.com/\1.git"),
)


def is_git_repo_root(path: StrOrPath) -> bool:
    """Indicate if a given path is a git repo root directory."""
    try:
        return (
            Path(
                get_git()("-C", path, "rev-parse", "--show-toplevel").strip()
            ).resolve()
            == Path(path).resolve()
        )
    except (OSError, ProcessExecutionError):
        return False


def is_in_git_repo(path: StrOrPath) -> bool:
    """Indicate if a given path is in a git repo directory."""
    try:
        get_git()("-C", path, "rev-parse", "--show-toplevel")
        return True
    except (OSError, ProcessExecutionError):
        return False


def is_git_shallow_repo(path: StrOrPath) -> bool:
    """Indicate if a given path is a git shallow repo directory."""
    try:
        return (
            get_git()("-C", path, "rev-parse", "--is-shallow-repository").strip()
            == "true"
        )
    except (OSError, ProcessExecutionError):
        return False


def is_git_bundle(path: Path) -> bool:
    """Indicate if a path is a valid git bundle."""
    with suppress(OSError):
        path = path.resolve()
    with TemporaryDirectory(prefix=f"{__name__}.is_git_bundle.") as dirname:
        with local.cwd(dirname):
            get_git()("init")
            return bool(get_git()["bundle", "verify", path] & TF)


def get_repo(url: str) -> str | None:
    """Transform `url` into a git-parseable origin URL.

    Args:
        url:
            Valid examples:

            - gh:copier-org/copier
            - gl:copier-org/copier
            - git@github.com:copier-org/copier.git
            - git+https://mywebsiteisagitrepo.example.com/
            - /local/path/to/git/repo
            - /local/path/to/git/bundle/file.bundle
            - ~/path/to/git/repo
            - ~/path/to/git/repo.bundle
    """
    for pattern, replacement in REPLACEMENTS:
        url = re.sub(pattern, replacement, url)

    if url.endswith(GIT_POSTFIX) or url.startswith(GIT_PREFIX):
        if url.startswith("git+"):
            return url[4:]
        if url.startswith("https://") and not url.endswith(GIT_POSTFIX):
            return "".join((url, GIT_POSTFIX))
        return url

    url_path = Path(url)
    if url.startswith("~"):
        url_path = url_path.expanduser()

    if is_git_repo_root(url_path) or is_git_bundle(url_path):
        return _PathStr(url_path.as_posix())

    return None


def get_latest_tag(url: str, use_prereleases: OptBool = False) -> str:
    """Get latest git tag, sorted by PEP 440.

    Args:
        url:
            Git-parseable URL of the repo. As returned by
            [get_repo][copier.vcs.get_repo].
        use_prereleases:
            If `False`, skip prerelease git tags.

    Returns:
        The latest git tag, or `HEAD` if no valid tags are found.
    """
    # For local Git repos, `git ls-remote` requires an absolute path to work correctly,
    # it behaves unexpectedly with some relative paths, especially with parent path
    # traversal.
    #
    # See:
    # - https://github.com/copier-org/copier/issues/2589
    # - https://stackoverflow.com/q/59981939
    if isinstance(url, _PathStr):
        url = Path(url).resolve().as_posix()
    git = get_git()
    all_tags = (
        tag.split("\t", 1)[1].removeprefix("refs/tags/")
        for tag in git("ls-remote", "--tags", "--refs", url).splitlines()
    )
    all_tags = (tag for tag in all_tags if valid_version(tag))
    if not use_prereleases:
        all_tags = (tag for tag in all_tags if not version.parse(tag).is_prerelease)
    sorted_tags = sorted(all_tags, key=version.parse, reverse=True)
    try:
        return str(sorted_tags[0])
    except IndexError:
        print(
            colors.warn | "No git tags found in template; using HEAD as ref",
            file=sys.stderr,
        )
        return "HEAD"


def get_cache_dir() -> Path:
    """Get the directory where cached git mirrors are stored.

    Defaults to a per-user cache directory (via `platformdirs`), but can be
    overridden with the `COPIER_CACHE_DIR` environment variable.
    """
    override = os.environ.get(CACHE_DIR_ENV_VAR)
    if override:
        return Path(override)
    return Path(user_cache_dir("copier")) / "git"


def _mirror_path(url: str) -> Path:
    """Compute the deterministic on-disk location of the mirror for `url`."""
    digest = sha256(url.encode("utf-8")).hexdigest()
    return get_cache_dir() / f"{digest}.git"


def _is_remote(url: str) -> bool:
    """Tell whether `url` points to a remote repository worth caching.

    Local repositories (existing directories or bundle files, as well as
    paths marked with [_PathStr][]) keep their original clone behavior, which
    preserves features like including dirty changes.
    """
    if isinstance(url, _PathStr):
        return False
    try:
        if Path(url).exists():
            return False
    except OSError:
        pass
    return True


def _force_rmtree(path: Path) -> None:
    """Remove `path`, coping with git's read-only files (e.g. on Windows)."""
    if sys.version_info >= (3, 12):
        rmtree(path, onexc=handle_remove_readonly)
    else:
        rmtree(path, onerror=handle_remove_readonly)


def _is_valid_mirror(mirror: Path) -> bool:
    """Tell whether `mirror` is a usable bare git repository.

    Guards against partial or corrupt cache entries (e.g. left behind by an
    interrupted clone or a failed deletion) that would otherwise be mistaken
    for a healthy mirror.
    """
    if not (mirror / "objects").is_dir():
        return False
    try:
        out = get_git()(
            "--git-dir", str(mirror), "rev-parse", "--is-bare-repository"
        ).strip()
    except (OSError, ProcessExecutionError):
        return False
    return out == "true"


def get_or_create_mirror(url: str) -> Path:
    """Get a cached `--mirror` clone of `url`, creating or refreshing it.

    On first use the remote is mirror-cloned into the cache. On subsequent
    uses the existing mirror is refreshed via `git remote update` and stale
    worktree registrations are pruned, so no full re-download is needed. A
    corrupt or partial cache entry is discarded and re-created.
    """
    git = get_git()
    mirror = _mirror_path(url)
    if _is_valid_mirror(mirror):
        # Refreshing the existing mirror. Use `--git-dir` explicitly when
        # operating on the bare repository so this works even when Git is
        # configured with `safe.bareRepository=explicit`.
        git("--git-dir", str(mirror), "remote", "update", "--prune")
        # Dropping registrations for worktrees whose directories were already
        # removed by the cleanup step (from `Template._cleanup`).
        git("--git-dir", str(mirror), "worktree", "prune")
    else:
        # Discarding any corrupt/partial remnant before recreating.
        if mirror.exists():
            _force_rmtree(mirror)

        '''Creating the mirror atomically: clone into a staging directory, then
        move it into place. If a concurrent Copier process created the
        mirror first, discard ours and reuse theirs. This avoids colliding
        on a half-written mirror without requiring full inter-process locks.
        A fresh `--mirror` clone already has every ref, so no fetch is needed.'''

        mirror.parent.mkdir(parents=True, exist_ok=True)
        staging = Path(mkdtemp(prefix=CLONE_PREFIX, dir=mirror.parent))
        try:
            staging_repo = staging / "repo.git"
            git("clone", "--mirror", url, str(staging_repo))
            try:
                staging_repo.rename(mirror)
            except OSError:
                if not _is_valid_mirror(mirror):
                    raise
        finally:
            rmtree(staging, ignore_errors=True)
    return mirror


def _clone_via_cache(ref: str, location: str, mirror: Path) -> str:
    """Create a temporary worktree of `mirror` at `ref` in `location`.
    
    `git worktree add` refuses a path that already exists, so remove the
    pre-allocated (empty) placeholder directory and let git recreate it."""
    git = get_git()
    placeholder = Path(location)
    if placeholder.exists():
        placeholder.rmdir()
    git(
        "--git-dir", str(mirror),
        "worktree", "add", "--detach", "--force", location, ref,
    )
    with local.cwd(location):
        git("submodule", "update", "--checkout", "--init", "--recursive", "--force")
    return location


def clone(url: str, ref: str = "HEAD", location: str | None = None) -> str:
    """Clone repo into some temporary destination.

    Remote repositories are cached as a local git mirror and checked out into
    a temporary worktree, so repeated use of the same template avoids a full
    re-download.

    Includes dirty changes for local templates by copying into a temp
    directory and applying a wip commit there.

    Args:
        url:
            Git-parseable URL of the repo. As returned by
            [get_repo][copier.vcs.get_repo].
        ref:
            Reference to checkout. For Git repos, defaults to `HEAD`.
        location:
            Pre-allocated empty directory to clone into. When `None`, a new
            temporary directory is created.
    """
    git = get_git()
    git_version = get_git_version()
    if location is None:
        location = mkdtemp(prefix=CLONE_PREFIX)
    # Remote templates: use a cached mirror + temporary worktree.
    if _is_remote(url):
        mirror = get_or_create_mirror(url)
        return _clone_via_cache(ref, location, mirror)
    # Local templates: keep the original clone behavior.
    _clone = git["clone", "--no-checkout", url, location]
    # Faster clones if possible
    if git_version >= Version("2.27"):
        if url_match := re.match("(file://)?(.*)", url):
            file_url = url_match.groups()[-1]
        else:
            file_url = url
        if is_git_shallow_repo(file_url):
            warn(
                f"The repository '{url}' is a shallow clone, this might lead to unexpected "
                "failure or unusually high resource consumption.",
                ShallowCloneWarning,
            )
        else:
            _clone = _clone["--filter=blob:none"]
    _clone()
    # Include dirty changes if checking out a local HEAD
    url_abspath = Path(url).absolute()
    if ref == "HEAD" and url_abspath.is_dir():
        is_dirty = False
        with local.cwd(url):
            is_dirty = bool(git("status", "--porcelain").strip())
        if is_dirty:
            with local.cwd(location):
                git("--git-dir=.git", f"--work-tree={url_abspath}", "add", "-A")
                git(
                    "--git-dir=.git",
                    f"--work-tree={url_abspath}",
                    "commit",
                    "-m",
                    "Copier automated commit for draft changes",
                    "--no-verify",
                    "--no-gpg-sign",
                )
                warn(
                    "Dirty template changes included automatically.",
                    DirtyLocalWarning,
                )

    with local.cwd(location):
        ## The `git checkout -f <ref>` command doesn't works when repo is local, dirty
        ## and core.fsmonitor is enabled
        ## ref: https://github.com/copier-org/copier/issues/1887
        git("-c", "core.fsmonitor=false", "checkout", "-f", ref)
        git("submodule", "update", "--checkout", "--init", "--recursive", "--force")

    return location


def valid_version(version_: str) -> bool:
    """Tell if a string is a valid [PEP 440][] version specifier.

    [PEP 440]: https://peps.python.org/pep-0440/
    """
    try:
        version.parse(version_)
    except InvalidVersion:
        return False
    return True
