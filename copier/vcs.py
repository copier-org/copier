import re
import shutil
import tempfile
from pathlib import Path

from plumbum import TF, local
from plumbum.cmd import git

from .types import OptStr

__all__ = ("get_repo", "clone")

GIT_PREFIX = ("git@", "git://", "git+")
GIT_POSTFIX = (".git",)

RE_GITHUB = re.compile(r"^gh:/?")
RE_GITLAB = re.compile(r"^gl:/?")


def is_git_repo_root(path: Path) -> bool:
    """Indicate if a given path is a git repo root directory."""
    try:
        with local.cwd(path / ".git"):
            return bool(git("rev-parse", "--is-inside-git-dir") == "true\n")
    except (FileNotFoundError, NotADirectoryError):
        return False


def is_git_bundle(path: Path) -> bool:
    """Indicate if a path is a valid git bundle."""
    with tempfile.TemporaryDirectory() as dirname:
        with local.cwd(dirname):
            git("init")
            return bool(git["bundle", "verify", path] & TF)


def get_repo(url: str) -> OptStr:
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

    url = re.sub(RE_GITHUB, "https://github.com/", url)
    url = re.sub(RE_GITLAB, "https://gitlab.com/", url)
    return url


def clone(url: str, ref: str = "HEAD") -> str:
    location = tempfile.mkdtemp()
    shutil.rmtree(location)  # Path must not exist
    git("clone", "--no-checkout", url, location)
    with local.cwd(location):
        git("checkout", ref)
        git("submodule", "update", "--checkout", "--init", "--recursive", "--force")
    return location
