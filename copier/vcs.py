import re
import shutil
import tempfile
from pathlib import Path

from packaging import version
from plumbum import TF, colors, local
from plumbum.cmd import git

from .types import OptStr, StrOrPath

__all__ = ("get_repo", "clone")

GIT_PREFIX = ("git@", "git://", "git+")
GIT_POSTFIX = (".git",)
REPLACEMENTS = (
    (re.compile(r"^gh:/?(.*\.git)$"), r"https://github.com/\1"),
    (re.compile(r"^gh:/?(.*)$"), r"https://github.com/\1.git"),
    (re.compile(r"^gl:/?(.*\.git)$"), r"https://gitlab.com/\1"),
    (re.compile(r"^gl:/?(.*)$"), r"https://gitlab.com/\1.git"),
)


def is_git_repo_root(path: Path) -> bool:
    """Indicate if a given path is a git repo root directory."""
    try:
        with local.cwd(path / ".git"):
            return bool(git("rev-parse", "--is-inside-git-dir") == "true\n")
    except (FileNotFoundError, NotADirectoryError):
        return False


def is_git_bundle(path: Path) -> bool:
    """Indicate if a path is a valid git bundle."""
    with tempfile.TemporaryDirectory(prefix=f"{__name__}.is_git_bundle.") as dirname:
        with local.cwd(dirname):
            git("init")
            return bool(git["bundle", "verify", path] & TF)


def get_repo(url: str) -> OptStr:
    for pattern, replacement in REPLACEMENTS:
        url = re.sub(pattern, replacement, url)
    url_path = Path(url)
    if not (
        url.endswith(GIT_POSTFIX)
        or url.startswith(GIT_PREFIX)
        or is_git_repo_root(url_path)
        or is_git_bundle(url_path)
    ):
        return None

    if url.startswith("git+"):
        url = url[4:]
    return url


def checkout_latest_tag(local_repo: StrOrPath) -> str:
    """Checkout latest git tag and check it out, sorted by PEP 440."""
    with local.cwd(local_repo):
        all_tags = git("tag").split()
        sorted_tags = sorted(all_tags, key=version.parse, reverse=True)
        try:
            latest_tag = str(sorted_tags[0])
        except IndexError:
            print(colors.warn | "No git tags found in template; using HEAD as ref")
            latest_tag = "HEAD"
        git("checkout", "--force", latest_tag)
        git("submodule", "update", "--checkout", "--init", "--recursive", "--force")
        return latest_tag


def clone(url: str, ref: str = "HEAD") -> str:
    location = tempfile.mkdtemp(prefix=f"{__name__}.clone.")
    shutil.rmtree(location)  # Path must not exist
    git("clone", "--no-checkout", url, location)
    with local.cwd(location):
        git("checkout", ref)
        git("submodule", "update", "--checkout", "--init", "--recursive", "--force")
    return location
