import platform
from pathlib import Path
from shutil import rmtree
from textwrap import dedent
from typing import Optional

import pytest
import yaml
from plumbum import local
from plumbum.cmd import git

from copier import Worker, copy
from copier.cli import CopierApp
from copier.main import run_copy, run_update
from copier.types import RelativePath

from .helpers import BRACKET_ENVOPS_JSON, SUFFIX_TMPL, build_file_tree


def test_updatediff(tmp_path_factory):
    src, dst = map(tmp_path_factory.mktemp, ("src", "dst"))
    # Prepare repo bundle
    repo = src / "repo"
    bundle = src / "demo_updatediff_repo.bundle"
    last_commit = ""
    build_file_tree(
        {
            repo
            / ".copier-answers.yml.jinja": """\
                # Changes here will be overwritten by Copier
                {{ _copier_answers|to_nice_yaml }}
            """,
            repo
            / "copier.yml": """\
                _envops:
                    "keep_trailing_newline": True
                project_name: to become a pirate
                author_name: Guybrush
            """,
            repo
            / "README.txt.jinja": """
                Let me introduce myself.

                My name is {{author_name}}, and my project is {{project_name}}.

                Thanks for your attention.
            """,
        }
    )
    with local.cwd(repo):
        git("init")
        git("add", ".")
        git("commit", "-m", "Guybrush wants to be a pirate")
        git("tag", "v0.0.1")
    build_file_tree(
        {
            repo
            / "copier.yml": """\
                _envops:
                    "keep_trailing_newline": True
                project_name: to become a pirate
                author_name: Guybrush
                _migrations:
                    -   version: v0.0.1
                        before:
                            - touch before-v0.0.1
                        after:
                            - touch after-v0.0.1
                    -   version: v0.0.2
                        before:
                            - touch before-v0.0.2
                        after:
                            - touch after-v0.0.2
                    -   version: v1.0.0
                        before:
                            - touch before-v1.0.0
                        after:
                            - touch after-v1.0.0
            """,
        }
    )
    with local.cwd(repo):
        git("init")
        git("add", ".")
        git("commit", "-m", "Add migrations")
        git("tag", "v0.0.2")
    build_file_tree(
        {
            repo
            / "copier.yml": """\
                _envops:
                    "keep_trailing_newline": True
                project_name: to rule
                author_name: Elaine
                _migrations:
                    -   version: v0.0.1
                        before:
                            - touch before-v0.0.1
                        after:
                            - touch after-v0.0.1
                    -   version: v0.0.2
                        before:
                            - touch before-v0.0.2
                        after:
                            - touch after-v0.0.2
                    -   version: v1.0.0
                        before:
                            - touch before-v1.0.0
                        after:
                            - touch after-v1.0.0
            """,
            repo
            / "README.txt.jinja": """
                Let me introduce myself.

                My name is {{author_name}}.

                My project is {{project_name}}.

                Thanks for your attention.
            """,
        }
    )
    with local.cwd(repo):
        git("init")
        git("add", ".")
        git("commit", "-m", "Elaine wants to rule")
        git("bundle", "create", bundle, "--all")
        last_commit = git("describe", "--tags").strip()
    # Generate repo bundle
    target = dst / "target"
    readme = target / "README.txt"
    answers = target / ".copier-answers.yml"
    commit = git["commit", "--all"]
    # Run copier 1st time, with specific tag
    CopierApp.invoke(
        "copy",
        str(bundle),
        str(target),
        defaults=True,
        overwrite=True,
        vcs_ref="v0.0.1",
    )
    # Check it's copied OK
    assert answers.read_text() == dedent(
        f"""\
            # Changes here will be overwritten by Copier
            _commit: v0.0.1
            _src_path: {bundle}
            author_name: Guybrush
            project_name: to become a pirate\n
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
        CopierApp.invoke(defaults=True, overwrite=True)
        assert answers.read_text() == dedent(
            f"""\
                # Changes here will be overwritten by Copier
                _commit: v0.0.2
                _src_path: {bundle}
                author_name: Guybrush
                project_name: to become a pirate\n
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
        CopierApp.invoke(defaults=True, overwrite=True, vcs_ref="HEAD")
        # Check no new migrations were executed
        assert not (target / "before-v0.0.1").is_file()
        assert not (target / "after-v0.0.1").is_file()
        assert not (target / "before-v0.0.2").is_file()
        assert not (target / "after-v0.0.2").is_file()
        assert not (target / "before-v1.0.0").is_file()
        assert not (target / "after-v1.0.0").is_file()
        # Check it's updated OK
        assert answers.read_text() == dedent(
            f"""\
                # Changes here will be overwritten by Copier
                _commit: {last_commit}
                _src_path: {bundle}
                author_name: Guybrush
                project_name: to become a pirate\n
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
        commit("-m", f"Update template to {last_commit}")
        assert not git("status", "--porcelain")
        # No more updates exist, so updating again should change nothing
        CopierApp.invoke(defaults=True, overwrite=True, vcs_ref="HEAD")
        assert not git("status", "--porcelain")
        # If I change an option, it updates properly
        copy(
            data={"author_name": "Largo LaGrande", "project_name": "to steal a lot"},
            defaults=True,
            overwrite=True,
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
        Worker(
            data={"author_name": "Largo LaGrande", "project_name": "to steal a lot"},
            defaults=True,
            overwrite=True,
            vcs_ref="HEAD",
        ).run_copy()
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
                "copier.yml": f"""
                _envops: {BRACKET_ENVOPS_JSON}
                _templates_suffix: {SUFFIX_TMPL}
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
                - repo: https://github.com/pre-commit/mirrors-prettier
                  rev: v2.0.4
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
    copy(src_path=str(src), dst_path=dst1, defaults=True, overwrite=True)
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
    copy(dst_path=dst1, defaults=True, overwrite=True)
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
        copy(data={"what": "study"}, defaults=True, overwrite=True)
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


def test_update_from_tagged_to_head(src_repo, tmp_path):
    # Build a template
    with local.cwd(src_repo):
        build_file_tree(
            {
                "{{ _copier_conf.answers_file }}.jinja": "{{ _copier_answers|to_nice_yaml }}",
                "example": "1",
            }
        )
        git("add", "-A")
        git("commit", "-m1")
        # Publish v1 release
        git("tag", "v1")
        # New commit, no release
        build_file_tree({"example": "2"})
        git("commit", "-am2")
        sha = git("rev-parse", "--short", "HEAD").strip()
    # Copy it without specifying version
    run_copy(src_path=str(src_repo), dst_path=tmp_path)
    example = tmp_path / "example"
    answers_file = tmp_path / ".copier-answers.yml"
    assert example.read_text() == "1"
    assert yaml.safe_load(answers_file.read_text())["_commit"] == "v1"
    # Build repo on copy
    with local.cwd(tmp_path):
        git("init")
        git("add", "-A")
        git("commit", "-m3")
    # Update project, it must let us do it
    run_update(tmp_path, vcs_ref="HEAD", defaults=True, overwrite=True)
    assert example.read_text() == "2"
    assert yaml.safe_load(answers_file.read_text())["_commit"] == f"v1-1-g{sha}"


def test_skip_update(tmp_path_factory):
    src, dst = map(tmp_path_factory.mktemp, ("src", "dst"))
    with local.cwd(src):
        build_file_tree(
            {
                "copier.yaml": "_skip_if_exists: [skip_me]",
                "{{ _copier_conf.answers_file }}.jinja": "{{ _copier_answers|to_yaml }}",
                "skip_me": "1",
            }
        )
        git("init")
        git("add", ".")
        git("commit", "-m1")
        git("tag", "1.0.0")
    run_copy(str(src), dst, defaults=True, overwrite=True)
    skip_me: Path = dst / "skip_me"
    answers_file = dst / ".copier-answers.yml"
    answers = yaml.safe_load(answers_file.read_text())
    assert skip_me.read_text() == "1"
    assert answers["_commit"] == "1.0.0"
    skip_me.write_text("2")
    with local.cwd(dst):
        git("init")
        git("add", ".")
        git("commit", "-m1")
    with local.cwd(src):
        build_file_tree({"skip_me": "3"})
        git("commit", "-am2")
        git("tag", "2.0.0")
    run_update(dst, defaults=True, overwrite=True)
    answers = yaml.safe_load(answers_file.read_text())
    assert skip_me.read_text() == "2"
    assert answers["_commit"] == "2.0.0"
    assert not (dst / "skip_me.rej").exists()


@pytest.mark.timeout(20)
@pytest.mark.parametrize(
    "answers_file", (None, ".copier-answers.yml", ".custom.copier-answers.yaml")
)
def test_overwrite_answers_file_always(
    tmp_path_factory, answers_file: Optional[RelativePath]
):
    src, dst = map(tmp_path_factory.mktemp, ("src", "dst"))
    with local.cwd(src):
        build_file_tree(
            {
                "copier.yaml": "question_1: true",
                "{{ _copier_conf.answers_file }}.jinja": "{{ _copier_answers|to_yaml }}",
                "answer_1.jinja": "{{ question_1 }}",
            }
        )
        git("init")
        git("add", ".")
        git("commit", "-m1")
        git("tag", "1")
        build_file_tree({"copier.yaml": "question_1: false"})
        git("commit", "-am2")
        git("tag", "2")
    # When copying, there's nothing to overwrite, overwrite=False shouldn't hang
    run_copy(str(src), str(dst), vcs_ref="1", defaults=True, answers_file=answers_file)
    with local.cwd(dst):
        git("init")
        git("add", ".")
        git("commit", "-m1")
        # When updating, the only thing to overwrite is the copier answers file,
        # which shouldn't ask, so also this shouldn't hang with overwrite=False
        run_update(defaults=True, answers_file=answers_file)
    answers = yaml.safe_load(
        Path(dst, answers_file or ".copier-answers.yml").read_bytes()
    )
    assert answers["question_1"] is True
    assert answers["_commit"] == "2"
    assert (dst / "answer_1").read_text() == "True"


def test_file_removed(src_repo, tmp_path):
    # Add a file in the template repo
    with local.cwd(src_repo):
        build_file_tree(
            {
                "{{ _copier_conf.answers_file }}.jinja": "{{ _copier_answers|to_yaml }}",
                "1.txt": "content 1",
                Path("dir 2", "2.txt"): "content 2",
                Path("dir 3", "subdir 3", "3.txt"): "content 3",
                Path("dir 4", "subdir 4", "4.txt"): "content 4",
                Path("dir 5", "subdir 5", "5.txt"): "content 5",
            }
        )
        git("add", "-A")
        git("commit", "-m1")
        git("tag", "1")
    # Copy in subproject
    with local.cwd(tmp_path):
        git("init")
        run_copy(str(src_repo))
        # Subproject has an extra file
        build_file_tree(
            {
                "I.txt": "content I",
                Path("dir II", "II.txt"): "content II",
                Path("dir 3", "subdir III", "III.txt"): "content III",
                Path("dir 4", "subdir 4", "IV.txt"): "content IV",
            }
        )
        git("add", "-A")
        git("commit", "-m2")
    # All files exist
    assert tmp_path.joinpath(".copier-answers.yml").is_file()
    assert tmp_path.joinpath("1.txt").is_file()
    assert tmp_path.joinpath("dir 2", "2.txt").is_file()
    assert tmp_path.joinpath("dir 3", "subdir 3", "3.txt").is_file()
    assert tmp_path.joinpath("dir 4", "subdir 4", "4.txt").is_file()
    assert tmp_path.joinpath("dir 5", "subdir 5", "5.txt").is_file()
    assert tmp_path.joinpath("I.txt").is_file()
    assert tmp_path.joinpath("dir II", "II.txt").is_file()
    assert tmp_path.joinpath("dir 3", "subdir III", "III.txt").is_file()
    assert tmp_path.joinpath("dir 4", "subdir 4", "IV.txt").is_file()
    # Template removes file 1
    with local.cwd(src_repo):
        Path("1.txt").unlink()
        rmtree("dir 2")
        rmtree("dir 3")
        rmtree("dir 4")
        rmtree("dir 5")
        build_file_tree({"6.txt": "content 6"})
        git("add", "-A")
        git("commit", "-m3")
        git("tag", "2")
    # Subproject updates
    with local.cwd(tmp_path):
        run_update()
    # Check what must still exist
    assert tmp_path.joinpath(".copier-answers.yml").is_file()
    assert tmp_path.joinpath("I.txt").is_file()
    assert tmp_path.joinpath("dir II", "II.txt").is_file()
    assert tmp_path.joinpath("dir 3", "subdir III", "III.txt").is_file()
    assert tmp_path.joinpath("dir 4", "subdir 4", "IV.txt").is_file()
    assert tmp_path.joinpath("6.txt").is_file()
    # Check what must not exist
    assert not tmp_path.joinpath("1.txt").exists()
    assert not tmp_path.joinpath("dir 2").exists()
    assert not tmp_path.joinpath("dir 3", "subdir 3").exists()
    assert not tmp_path.joinpath("dir 4", "subdir 4", "4.txt").exists()
    assert not tmp_path.joinpath("dir 5").exists()
