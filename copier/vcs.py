import os
import re
import shutil
import subprocess
import tempfile
from typing import Optional

from .types import StrOrPath


__all__ = ("get_repo", "clone")

GIT_PREFIX = ("git@", "git://", "git+")
GIT_POSTFIX = (".git",)

RE_GITHUB = re.compile(r"^gh:/?")
RE_GITLAB = re.compile(r"^gl:/?")


def get_repo(url: StrOrPath) -> Optional[str]:
    url = str(url)  # In case we have got a `pathlib.Path`
    if not (url.endswith(GIT_POSTFIX) or url.startswith(GIT_PREFIX)):
        return None

    if url.startswith("git+"):
        url = url[4:]

    url = re.sub(RE_GITHUB, "https://github.com/", url)
    url = re.sub(RE_GITLAB, "https://gitlab.com/", url)
    return url


def clone(url: str) -> str:
    location = tempfile.mkdtemp()
    shutil.rmtree(location)  # Path must not exists
    subprocess.check_call(["git", "clone", url, location])
    git_folder = os.path.join(location, ".git")
    shutil.rmtree(git_folder)
    return location
