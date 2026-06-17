import os
import shutil
from collections.abc import Callable, Iterator, Sequence
from contextlib import ExitStack
from pathlib import Path
from unittest import mock

import pytest
from packaging.version import Version
from plumbum import local
from pytest_gitconfig.plugin import GitConfig

from copier import run_copy, run_update
from copier._main import Worker
from copier._user_data import load_answersfile_data
from copier._vcs import (
    _get_mirror_path,
    _is_remote,
    clone,
    get_git,
    get_git_version,
    get_latest_tag,
    get_repo,
    is_git_repo_root,
)
from copier.errors import DirtyLocalWarning, ShallowCloneWarning

from .helpers import build_file_tree, git, git_save


def test_get_repo() -> None:
    get = get_repo

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
def test_clone() -> None:
    tmp = clone("https://github.com/copier-org/copier.git")
    assert tmp
    assert Path(tmp, "README.md").exists()
    shutil.rmtree(tmp, ignore_errors=True)


@pytest.mark.impure
def test_local_clone() -> None:
    tmp = clone("https://github.com/copier-org/copier.git")
    assert tmp
    assert Path(tmp, "README.md").exists()

    local_tmp = clone(tmp)
    assert local_tmp
    assert Path(local_tmp, "README.md").exists()
    shutil.rmtree(local_tmp, ignore_errors=True)


@pytest.fixture
def remote_repo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> str:
    """A small local git repo exposed via a ``file://`` URL (treated as remote).

    A ``file://`` URL is treated as remote by ``clone()``, so this exercises
    the mirror-cache code path without requiring network access. The mirror
    cache is redirected to a temp dir to keep the test isolated.
    """
    monkeypatch.setenv("COPIER_CACHE_DIR", str(tmp_path / "cache"))
    path = tmp_path / "remote"
    path.mkdir(parents=True, exist_ok=True)
    with local.cwd(path):
        git("init")
        Path("README.md").write_text("hello world")
        git("add", "-A")
        git("commit", "-m", "init")
        git("tag", "v1.0.0")
    return path.as_uri()


@pytest.fixture
def clone_cleanup() -> Iterator[Callable[[str], str]]:
    """Register clone destinations to remove on teardown, even on failure.

    Returns a function that records and returns its argument, so test
    assertions can't leak temporary worktrees when they fail.
    """
    with ExitStack() as stack:

        def register(dst: str) -> str:
            stack.callback(shutil.rmtree, dst, ignore_errors=True)
            return dst

        yield register


def test_is_remote() -> None:
    assert _is_remote("https://github.com/copier-org/copier.git")
    assert _is_remote("git@github.com:copier-org/copier.git")
    assert _is_remote("file:///some/where/repo.git")
    # Local, on-disk paths are not remote.
    assert not _is_remote(str(Path.cwd()))
    # `get_repo` marks resolved local repos so they keep the old behavior.
    assert not _is_remote(get_repo(str(Path.cwd())) or "")


def test_mirror_path_ignores_credentials() -> None:
    # Embedded credentials must not affect the cache key, so the same repo
    # accessed with or without a token maps to a single mirror.
    base = "https://github.com/org/repo.git"
    with_token = "https://x-access-token:github_pat_secret@github.com/org/repo.git"
    assert _get_mirror_path(with_token) == _get_mirror_path(base)


def test_remote_clone_creates_and_reuses_mirror(
    remote_repo: str, clone_cleanup: Callable[[str], str]
) -> None:
    # First use creates the mirror and checks out a worktree.
    dst1 = clone_cleanup(clone(remote_repo))
    mirror = _get_mirror_path(remote_repo)
    assert (mirror / "objects").is_dir()
    assert Path(dst1, "README.md").read_text() == "hello world"

    # Drop a sentinel inside the mirror; if the second use re-clones from
    # scratch the mirror directory (and the sentinel) would be recreated.
    sentinel = mirror / "copier-cache-sentinel"
    sentinel.write_text("kept")

    dst2 = clone_cleanup(clone(remote_repo))
    assert sentinel.exists(), "mirror was re-created instead of reused"
    assert Path(dst2, "README.md").exists()
    assert dst2 != dst1  # a fresh worktree per use


def test_remote_clone_checks_out_ref(
    remote_repo: str, clone_cleanup: Callable[[str], str]
) -> None:
    dst = clone_cleanup(clone(remote_repo, "v1.0.0"))
    assert Path(dst, "README.md").read_text() == "hello world"


def test_remote_clone_prunes_stale_worktree(
    remote_repo: str, clone_cleanup: Callable[[str], str]
) -> None:
    mirror = _get_mirror_path(remote_repo)

    # Simulate Copier's cleanup: the worktree directory is removed, leaving a
    # stale registration behind in the mirror.
    dst1 = clone(remote_repo)
    shutil.rmtree(dst1, ignore_errors=True)
    assert not Path(dst1).exists()

    # The next use must prune the stale registration and succeed.
    dst2 = clone_cleanup(clone(remote_repo))
    assert Path(dst2, "README.md").exists()
    worktrees = get_git()("-C", str(mirror), "worktree", "list", "--porcelain")
    assert Path(dst1).as_posix() not in worktrees.replace("\\", "/")


def test_remote_clone_recovers_from_corrupt_mirror(
    remote_repo: str, clone_cleanup: Callable[[str], str]
) -> None:
    dst1 = clone(remote_repo)
    shutil.rmtree(dst1, ignore_errors=True)
    mirror = _get_mirror_path(remote_repo)

    # Simulate a partial/corrupt cache entry: the `objects` directory survives
    # but the rest of the repository is gone (e.g. an interrupted deletion).
    for child in mirror.iterdir():
        if child.name != "objects":
            if child.is_dir():
                shutil.rmtree(child, ignore_errors=True)
            else:
                child.unlink()
    assert (mirror / "objects").is_dir()

    # The next use must discard the corrupt mirror and rebuild it.
    dst2 = clone_cleanup(clone(remote_repo))
    assert Path(dst2, "README.md").read_text() == "hello world"


def test_local_dirty_clone(
    tmp_path_factory: pytest.TempPathFactory, gitconfig: GitConfig
) -> None:
    """
    When core.fsmonitor is enabled, normal `git checkout` command won't works.
    """

    gitconfig.set({"core.fsmonitor": "true"})
    src = tmp_path_factory.mktemp("src")
    print(src)

    build_file_tree({src / "version.txt": "0.1.0"})
    git_save(src)

    build_file_tree({src / "version.txt": "0.2.0", src / "README.md": "hello world"})

    with pytest.warns(DirtyLocalWarning):
        local_tmp = clone(str(src))

    assert local_tmp
    assert Path(local_tmp, "version.txt").exists()
    assert Path(local_tmp, "version.txt").read_text() == "0.2.0"
    assert Path(local_tmp, "README.md").exists()
    assert Path(local_tmp, "README.md").read_text() == "hello world"
    shutil.rmtree(local_tmp, ignore_errors=True)


@pytest.mark.impure
def test_shallow_clone(tmp_path: Path, recwarn: pytest.WarningsRecorder) -> None:
    # This test should always work but should be much slower if `is_git_shallow_repo()`
    # is not checked in `clone()`.
    src_path = str(tmp_path / "autopretty")
    git("clone", "--depth=2", "https://github.com/copier-org/autopretty.git", src_path)
    assert Path(src_path, "README.md").exists()

    if get_git_version() >= Version("2.27"):
        with pytest.warns(ShallowCloneWarning):
            local_tmp = clone(str(src_path))
    else:
        assert len(recwarn) == 0
        local_tmp = clone(str(src_path))
        assert len(recwarn) == 0
    assert local_tmp
    assert Path(local_tmp, "README.md").exists()
    shutil.rmtree(local_tmp, ignore_errors=True)


@pytest.mark.impure
def test_removes_temporary_clone(tmp_path: Path) -> None:
    src_path = "https://github.com/copier-org/autopretty.git"
    with Worker(
        src_path=src_path, dst_path=tmp_path, defaults=True, unsafe=True
    ) as worker:
        worker.run_copy()
        temp_clone = worker.template.local_abspath
    assert not temp_clone.exists()


@pytest.mark.impure
def test_dont_remove_local_clone(tmp_path: Path) -> None:
    src_path = str(tmp_path / "autopretty")
    git("clone", "https://github.com/copier-org/autopretty.git", src_path)
    with Worker(
        src_path=src_path, dst_path=tmp_path, defaults=True, unsafe=True
    ) as worker:
        worker.run_copy()
    assert Path(src_path).exists()


@pytest.mark.impure
def test_update_using_local_source_path_with_tilde(tmp_path: Path) -> None:
    # first, get a local repository clone
    src_path = str(tmp_path / "autopretty")
    git("clone", "https://github.com/copier-org/autopretty.git", src_path)

    # then prepare the user path to this clone (starting with ~)
    if os.name == "nt":
        # in GitHub CI, the user in the temporary path is not the same as the current
        # user:
        # ["C:\\", "Users", "RUNNER~X"] vs. runneradmin
        user = Path(src_path).parts[2]
        user_src_path = str(Path("~", "..", user, *Path(src_path).parts[3:]))
    else:
        # temporary path is in /tmp, so climb back up from ~ using ../
        user_src_path = f"~/{'/'.join(['..'] * len(Path.home().parts))}{src_path}"

    # generate project and assert correct path in answers
    worker = run_copy(
        src_path=user_src_path, dst_path=tmp_path, defaults=True, unsafe=True
    )
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
        unsafe=True,
    )
    assert worker.answers.combined["_src_path"] == user_src_path


def test_invalid_version(tmp_path: Path) -> None:
    sample = tmp_path / "sample.txt"
    with local.cwd(tmp_path):
        git("init")
        sample.write_text("1")
        git("add", sample)
        git("commit", "-m1")
        git("tag", "not-a-version")
        sample.write_text("2")
        git("commit", "-am2")
        git("tag", "v2")
        sample.write_text("3")
        git("commit", "-am3")
        assert git("describe", "--tags").strip() != "v2"
        assert get_latest_tag(str(tmp_path)) == "v2"


@pytest.mark.parametrize("sorter", [iter, reversed])
def test_select_latest_version_tag(
    tmp_path_factory: pytest.TempPathFactory,
    sorter: Callable[[Sequence[str]], Iterator[str]],
) -> None:
    src, dst = map(tmp_path_factory.mktemp, ("src", "dst"))
    filename = "version.txt"

    with local.cwd(src):
        git("init")
        Path("{{ _copier_conf.answers_file }}.jinja").write_text(
            "{{ _copier_answers|to_nice_yaml }}"
        )
        for version in sorter(["v1", "v1.0", "v1.0.0", "v1.0.1"]):
            Path(filename).write_text(version)
            git("add", ".")
            git("commit", "-m", version)
            git("tag", version)

    run_copy(str(src), dst)

    assert (dst / filename).is_file()
    assert (dst / filename).read_text() == "v1.0.1"
    answers = load_answersfile_data(dst)
    assert answers["_commit"] == "v1.0.1"


def test_is_git_repo_root_worktree(tmp_path: Path) -> None:
    """is_git_repo_root should return True for git worktrees where .git is a file."""
    main_repo = tmp_path / "main"
    main_repo.mkdir()
    with local.cwd(main_repo):
        git("init")
        git("commit", "--allow-empty", "-m", "init")
        git("branch", "wt-branch")
    worktree = tmp_path / "worktree"
    with local.cwd(main_repo):
        git("worktree", "add", str(worktree), "wt-branch")

    # Sanity: .git in worktree is a file, not a directory
    assert (worktree / ".git").is_file()
    assert not (worktree / ".git").is_dir()

    assert is_git_repo_root(worktree)


def test_get_repo_worktree(tmp_path: Path) -> None:
    """get_repo should recognise a git worktree as a valid local repo."""
    main_repo = tmp_path / "main"
    main_repo.mkdir()
    with local.cwd(main_repo):
        git("init")
        git("commit", "--allow-empty", "-m", "init")
        git("branch", "wt-branch")
    worktree = tmp_path / "worktree"
    with local.cwd(main_repo):
        git("worktree", "add", str(worktree), "wt-branch")

    assert get_repo(str(worktree)) == worktree.as_posix()


@pytest.mark.parametrize(
    ("git_version_output", "expected_version"),
    [
        ("git version 2.53.0\n", Version("2.53.0")),
        ("git version 2.53.GIT\n", Version("2.53.0")),
    ],
)
def test_get_git_version(git_version_output: str, expected_version: Version) -> None:
    def _mock_git(*args: str) -> str:
        assert args == ("version",)
        return git_version_output

    with mock.patch(
        "copier._vcs.get_git", return_value=mock.MagicMock(side_effect=_mock_git)
    ):
        assert get_git_version() == expected_version
