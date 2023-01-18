import os
import shutil
from os.path import exists, join
from pathlib import Path

import pytest
from plumbum import local
from plumbum.cmd import git

from copier import Worker, run_copy, run_update, vcs


def test_get_repo():
    get = vcs.get_repo

    assert get("git@git.myproject.org:MyProject") == "git@git.myproject.org:MyProject"
    assert (
        get("git://git.myproject.org/MyProject") == "git://git.myproject.org/MyProject"
    )
    assert (
        get("https://github.com/jpscaletti/copier.git")
        == "https://github.com/jpscaletti/copier.git"
    )

    assert (
        get("https://github.com/jpscaletti/copier")
        == "https://github.com/jpscaletti/copier.git"
    )
    assert (
        get("https://gitlab.com/gitlab-org/gitlab")
        == "https://gitlab.com/gitlab-org/gitlab.git"
    )

    assert (
        get("gh:/jpscaletti/copier.git") == "https://github.com/jpscaletti/copier.git"
    )
    assert get("gh:jpscaletti/copier.git") == "https://github.com/jpscaletti/copier.git"
    assert get("gl:jpscaletti/copier.git") == "https://gitlab.com/jpscaletti/copier.git"
    assert get("gh:jpscaletti/copier") == "https://github.com/jpscaletti/copier.git"
    assert get("gl:jpscaletti/copier") == "https://gitlab.com/jpscaletti/copier.git"

    assert (
        get("git+https://git.myproject.org/MyProject")
        == "https://git.myproject.org/MyProject"
    )
    assert (
        get("git+ssh://git.myproject.org/MyProject")
        == "ssh://git.myproject.org/MyProject"
    )

    assert get("git://git.myproject.org/MyProject.git@master")
    assert get("git://git.myproject.org/MyProject.git@v1.0")
    assert get("git://git.myproject.org/MyProject.git@da39a3ee5e6b4b0d3255bfef956018")

    assert get("http://google.com") is None
    assert get("git.myproject.org/MyProject") is None
    assert get("https://google.com") is None

    assert (
        get("tests/demo_updatediff_repo.bundle") == "tests/demo_updatediff_repo.bundle"
    )


@pytest.mark.impure
def test_clone():
    tmp = vcs.clone("https://github.com/copier-org/copier.git")
    assert tmp
    assert exists(join(tmp, "README.md"))
    shutil.rmtree(tmp, ignore_errors=True)


@pytest.mark.impure
def test_removes_temporary_clone(tmp_path):
    src_path = "https://github.com/copier-org/autopretty.git"
    with Worker(src_path=src_path, dst_path=tmp_path, defaults=True) as worker:
        worker.run_copy()
        temp_clone = worker.template.local_abspath
    assert not temp_clone.exists()


@pytest.mark.impure
def test_dont_remove_local_clone(tmp_path):
    src_path = vcs.clone("https://github.com/copier-org/autopretty.git")
    with Worker(src_path=src_path, dst_path=tmp_path, defaults=True) as worker:
        worker.run_copy()
    assert exists(src_path)


@pytest.mark.impure
def test_update_using_local_source_path_with_tilde(tmp_path):
    # first, get a local repository clone
    src_path = vcs.clone("https://github.com/copier-org/autopretty.git")

    # then prepare the user path to this clone (starting with ~)
    if os.name == "nt":
        src_path = Path(src_path)
        # in GitHub CI, the user in the temporary path is not the same as the current user:
        # ["C:\\", "Users", "RUNNER~X"] vs. runneradmin
        user = src_path.parts[2]
        user_src_path = str(Path("~", "..", user, *src_path.parts[3:]))
    else:
        # temporary path is in /tmp, so climb back up from ~ using ../
        user_src_path = f"~/{'/'.join(['..'] * len(Path.home().parts))}{src_path}"

    # generate project and assert correct path in answers
    worker = run_copy(src_path=user_src_path, dst_path=tmp_path, defaults=True)
    assert worker.answers.combined["_src_path"] == user_src_path

    # assert project update works and correct path again
    with local.cwd(tmp_path):
        git("init")
        git("add", "-A")
        git("commit", "-m", "init")
    worker = run_update(
        dst_path=tmp_path,
        defaults=True,
        overwrite=True,
        answers_file=".copier-answers.autopretty.yml",
    )
    assert worker.answers.combined["_src_path"] == user_src_path
