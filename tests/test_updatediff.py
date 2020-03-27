from pathlib import Path
from textwrap import dedent

from plumbum import local
from plumbum.cmd import git

from copier.cli import CopierApp

from .helpers import PROJECT_TEMPLATE

REPO_BUNDLE_PATH = Path(f"{PROJECT_TEMPLATE}_updatediff_repo.bundle").absolute()


def test_updatediff(tmpdir):
    dst = Path(tmpdir)
    target = dst / "target"
    readme = target / "README.txt"
    answers = target / ".copier-answers.yml"
    commit = git["commit", "--all"]
    # Run copier 1st time, with specific tag
    CopierApp.invoke(
        "copy", str(REPO_BUNDLE_PATH), str(target), force=True, vcs_ref="v0.0.1"
    )
    # Check it's copied OK
    assert answers.read_text() == dedent(
        f"""
            # Changes here will be overwritten by Copier
            _commit: v0.0.1
            _src_path: {REPO_BUNDLE_PATH}
            author_name: Guybrush
            project_name: to become a pirate
        """
    )
    assert readme.read_text() == dedent(
        """
        Let me introduce myself.

        My name is Guybrush, and my project is to become a pirate.

        Thanks for your attention.
        """
    )
    # Init destination as a new independent git repo
    with local.cwd(target):
        git("init")
        # Configure git in case you're running in CI
        git("config", "user.name", "Copier Test")
        git("config", "user.email", "test@copier")
        # Commit changes
        git("add", ".")
        commit("-m", "hello world")
        # Emulate the user modifying the README by hand
        with open(readme, "w") as readme_fd:
            readme_fd.write(
                dedent(
                    """
                    Let me introduce myself.

                    My name is Guybrush, and my project is to become a pirate.

                    Thanks for your grog.
                    """
                )
            )
        commit("-m", "I prefer grog")
        # Update target to latest tag and check it's updated in answers file
        CopierApp.invoke(force=True)
        assert answers.read_text() == dedent(
            f"""
                # Changes here will be overwritten by Copier
                _commit: v0.0.2
                _src_path: {REPO_BUNDLE_PATH}
                author_name: Guybrush
                project_name: to become a pirate
            """
        )
        # Check migrations were executed properly
        assert not (target / "before-v0.0.1").is_file()
        assert not (target / "after-v0.0.1").is_file()
        assert (target / "before-v0.0.2").is_file()
        assert (target / "after-v0.0.2").is_file()
        (target / "before-v0.0.2").unlink()
        (target / "after-v0.0.2").unlink()
        assert not (target / "before-v1.0.0").is_file()
        assert not (target / "after-v1.0.0").is_file()
        commit("-m", "Update template to v0.0.2")
        # Update target to latest commit, which is still untagged
        CopierApp.invoke(force=True, vcs_ref="HEAD")
        # Check no new migrations were executed
        assert not (target / "before-v0.0.1").is_file()
        assert not (target / "after-v0.0.1").is_file()
        assert not (target / "before-v0.0.2").is_file()
        assert not (target / "after-v0.0.2").is_file()
        assert not (target / "before-v1.0.0").is_file()
        assert not (target / "after-v1.0.0").is_file()
        # Check it's updated OK
        assert answers.read_text() == dedent(
            f"""
                # Changes here will be overwritten by Copier
                _commit: v0.0.2-1-g81c335d
                _src_path: {REPO_BUNDLE_PATH}
                author_name: Guybrush
                project_name: to become a pirate
            """
        )
        assert readme.read_text() == dedent(
            """
            Let me introduce myself.

            My name is Guybrush.

            My project is to become a pirate.

            Thanks for your grog.
            """
        )
        commit("-m", "Update template to v0.0.2-1-g81c335d")
        assert not git("status", "--porcelain")
        # No more updates exist, so updating again should change nothing
        CopierApp.invoke(force=True, vcs_ref="HEAD")
        assert not git("status", "--porcelain")
