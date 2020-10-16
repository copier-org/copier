from pathlib import Path

from plumbum import local
from plumbum.cmd import git

from copier import copy

from .helpers import PROJECT_TEMPLATE

REPO_BUNDLE_PATH = Path(f"{PROJECT_TEMPLATE}_update_tasks.bundle").absolute()


def test_update_tasks(tmpdir):
    """Test that updating a template runs tasks from the expected version."""
    tmp_path = tmpdir / "tmp_path"
    # Copy the 1st version
    copy(
        str(REPO_BUNDLE_PATH),
        tmp_path,
        force=True,
        vcs_ref="v1",
    )
    # Init destination as a new independent git repo
    with local.cwd(tmp_path):
        git("init")
        # Configure git in case you're running in CI
        git("config", "user.name", "Copier Test")
        git("config", "user.email", "test@copier")
        # Commit changes
        git("add", ".")
        git("commit", "-m", "hello world")
    # Update target to v2
    copy(dst_path=str(tmp_path), force=True)
