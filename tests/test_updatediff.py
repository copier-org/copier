import platform
from pathlib import Path
from textwrap import dedent

import pytest
from plumbum import local
from plumbum.cmd import git

from copier import copy
from copier.cli import CopierApp

from .helpers import PROJECT_TEMPLATE, build_file_tree

REPO_BUNDLE_PATH = Path(f"{PROJECT_TEMPLATE}_updatediff_repo.bundle").absolute()


def test_updatediff(tmpdir):
    tmp_path = Path(tmpdir)
    target = tmp_path / "target"
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
        # If I change an option, it updates properly
        copy(
            data={"author_name": "Largo LaGrande", "project_name": "to steal a lot"},
            force=True,
            vcs_ref="HEAD",
        )
        assert readme.read_text() == dedent(
            """
            Let me introduce myself.

            My name is Largo LaGrande.

            My project is to steal a lot.

            Thanks for your grog.
            """
        )
        commit("-m", "Subproject evolved")
        # Reapply template ignoring subproject evolution
        copy(
            data={"author_name": "Largo LaGrande", "project_name": "to steal a lot"},
            force=True,
            vcs_ref="HEAD",
            only_diff=False,
        )
        assert readme.read_text() == dedent(
            """
            Let me introduce myself.

            My name is Largo LaGrande.

            My project is to steal a lot.

            Thanks for your attention.
            """
        )


# This fails on Windows because there's some problem while detecting
# the diff. It seems like an older Git version were being used, while
# that's not the case...
# FIXME Some generous Windows power user please fix this test!
@pytest.mark.xfail(
    condition=platform.system() == "Windows", reason="Git broken on Windows?"
)
def test_commit_hooks_respected(tmp_path_factory):
    """Commit hooks are taken into account when producing the update diff."""
    # Prepare source template v1
    src, dst1, dst2 = map(tmp_path_factory.mktemp, ("src", "dst1", "dst2"))
    with local.cwd(src):
        build_file_tree(
            {
                "copier.yml": """
                _tasks:
                  - git init
                  - pre-commit install
                  - pre-commit run -a || true
                what: grog
                """,
                "[[ _copier_conf.answers_file ]].tmpl": """
                [[ _copier_answers|to_nice_yaml ]]
                """,
                ".pre-commit-config.yaml": r"""
                repos:
                - repo: https://github.com/prettier/prettier
                  rev: 2.0.4
                  hooks:
                    - id: prettier
                - repo: local
                  hooks:
                    - id: forbidden-files
                      name: forbidden files
                      entry: found forbidden files; remove them
                      language: fail
                      files: "\\.rej$"
                """,
                "life.yml.tmpl": """
                # Following code should be reformatted by pre-commit after copying
                Line 1:      hello
                Line 2:      [[ what ]]
                Line 3:      bye
                """,
            }
        )
        git("init")
        git("add", ".")
        git("commit", "-m", "commit 1")
        git("tag", "v1")
    # Copy source template
    copy(src_path=str(src), dst_path=dst1, force=True)
    with local.cwd(dst1):
        life = Path("life.yml")
        git("add", ".")
        # 1st commit fails because pre-commit reformats life.yml
        git("commit", "-am", "failed commit", retcode=1)
        # 2nd commit works because it's already formatted
        git("commit", "-am", "copied v1")
        assert life.read_text() == dedent(
            """\
            # Following code should be reformatted by pre-commit after copying
            Line 1: hello
            Line 2: grog
            Line 3: bye
            """
        )
    # Evolve source template to v2
    with local.cwd(src):
        build_file_tree(
            {
                "life.yml.tmpl": """
                # Following code should be reformatted by pre-commit after copying
                Line 1:     hello world
                Line 2:     grow up
                Line 3:     [[ what ]]
                Line 4:     grow old
                Line 5:     bye bye world
                """,
            }
        )
        git("init")
        git("add", ".")
        git("commit", "-m", "commit 2")
        git("tag", "v2")
    # Update subproject to v2
    copy(dst_path=dst1, force=True)
    with local.cwd(dst1):
        git("commit", "-am", "copied v2")
        assert life.read_text() == dedent(
            """\
            # Following code should be reformatted by pre-commit after copying
            Line 1: hello world
            Line 2: grow up
            Line 3: grog
            Line 4: grow old
            Line 5: bye bye world
            """
        )
        # No .rej files created (update diff was smart)
        assert not git("status", "--porcelain")
        # Subproject evolves
        life.write_text(
            dedent(
                """\
                Line 1: hello world
                Line 2: grow up
                Line 2.5: make friends
                Line 3: grog
                Line 4: grow old
                Line 4.5: no more work
                Line 5: bye bye world
                """
            )
        )
        git("commit", "-am", "subproject is evolved")
    # A new subproject appears, which is a shallow clone of the 1st one.
    # Using file:// prefix to allow local shallow clones.
    git("clone", "--depth=1", f"file://{dst1}", dst2)
    with local.cwd(dst2):
        # Subproject re-updates just to change some values
        copy(data={"what": "study"}, force=True)
        git("commit", "-am", "re-updated to change values after evolving")
        # Subproject evolution was respected up to sane possibilities.
        # In an ideal world, this file would be exactly the same as what's written
        # a few lines above, just changing "grog" for "study". However, that's nearly
        # impossible to achieve, because each change hunk needs at least 1 line of
        # context to let git apply that patch smartly, and that context couldn't be
        # found because we changed data when updating, so the sanest thing we can
        # do is to provide a .rej file to notify those
        # unresolvable diffs. OTOH, some other changes are be applied.
        # If some day you are able to produce that ideal result, you should be
        # happy to modify these asserts.
        assert life.read_text() == dedent(
            """\
            Line 1: hello world
            Line 2: grow up
            Line 3: study
            Line 4: grow old
            Line 4.5: no more work
            Line 5: bye bye world
            """
        )
        # This time a .rej file is unavoidable
        assert Path(f"{life}.rej").is_file()
