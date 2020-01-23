from pathlib import Path
from textwrap import dedent

from plumbum import local
from plumbum.cmd import git

from copier.cli import CopierApp

from .helpers import PROJECT_TEMPLATE

COMMIT_1 = "49deace1b66f3a88a6305cc380d7596cc8170dc9"
COMMIT_2 = "c2ac5c45404cbd9b031acebcf398f19f56ce49dc"
REPO_BUNDLE_PATH = Path(f"{PROJECT_TEMPLATE}_updatediff_repo.bundle").absolute()


def test_updatediff(dst: Path):
    target = dst / "target"
    readme = target / "README.txt"
    answers = target / ".copier-answers.yml"
    commit = git["commit", "--all", "--author", "Copier Test <test@copier>"]
    # Run copier 1st time, with specific commit
    CopierApp.invoke(
        "copy", str(REPO_BUNDLE_PATH), str(target), force=True, vcs_ref=COMMIT_1
    )
    # Check it's copied OK
    assert answers.read_text() == dedent(
        f"""
            # Changes here will be overwritten by Copier
            _commit: {COMMIT_1}
            _src_path: {REPO_BUNDLE_PATH}
            project_name: to become a pirate
            author_name: Guybrush
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
    with local.cwd(target):
        commit("-m", "I prefer grog")
        # Update target to latest commit
        CopierApp.invoke(force=True)
    # Check it's updated OK
    assert answers.read_text() == dedent(
        f"""
            # Changes here will be overwritten by Copier
            _commit: {COMMIT_2}
            _src_path: {REPO_BUNDLE_PATH}
            project_name: to become a pirate
            author_name: Guybrush
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
