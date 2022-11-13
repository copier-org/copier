import os
import platform

import pytest
import yaml
from plumbum import local
from plumbum.cmd import git

import copier

from .helpers import BRACKET_ENVOPS_JSON, SUFFIX_TMPL, build_file_tree


def git_init(message="hello world"):
    git("init")
    git("config", "user.name", "Copier Test")
    git("config", "user.email", "test@copier")
    git("add", ".")
    git("commit", "-m", message)


@pytest.fixture(scope="module")
def demo_template(tmp_path_factory):
    root = tmp_path_factory.mktemp("demo_subdirectory")
    build_file_tree(
        {
            root / "api_project" / "api_readme.md": "",
            root
            / "api_project"
            / "[[ _copier_conf.answers_file ]].tmpl": "[[ _copier_answers|to_nice_yaml ]]",
            root
            / "conf_project"
            / "conf_readme.md": """\
                # Demo subdirectory

                Generated using previous answers `_subdirectory` value.
                """,
            root
            / "conf_project"
            / "[[ _copier_conf.answers_file ]].tmpl": "[[ _copier_answers|to_nice_yaml ]]",
            root
            / "copier.yml": f"""\
                _templates_suffix: {SUFFIX_TMPL}
                _envops: {BRACKET_ENVOPS_JSON}
                choose_subdir:
                    type: str
                    default: conf_project
                    choices:
                        - api_project
                        - conf_project
                _subdirectory: "[[ choose_subdir ]]"
            """,
        }
    )
    with local.cwd(root):
        git_init()
    return str(root)


def test_copy_subdirectory_api_option(demo_template, tmp_path):
    copier.copy(
        demo_template,
        tmp_path,
        defaults=True,
        overwrite=True,
        data={"choose_subdir": "api_project"},
    )
    assert (tmp_path / "api_readme.md").exists()
    assert not (tmp_path / "conf_readme.md").exists()


def test_copy_subdirectory_config(demo_template, tmp_path):
    copier.copy(demo_template, tmp_path, defaults=True, overwrite=True)
    assert (tmp_path / "conf_readme.md").exists()
    assert not (tmp_path / "api_readme.md").exists()


def test_update_subdirectory(demo_template, tmp_path):
    copier.copy(demo_template, tmp_path, defaults=True, overwrite=True)

    with local.cwd(tmp_path):
        git_init()

    copier.copy(dst_path=tmp_path, defaults=True, overwrite=True)
    assert not (tmp_path / "conf_project").exists()
    assert not (tmp_path / "api_project").exists()
    assert not (tmp_path / "api_readme.md").exists()
    assert (tmp_path / "conf_readme.md").exists()


def test_update_subdirectory_from_root_path(tmp_path_factory):
    src, dst = map(tmp_path_factory.mktemp, ("src", "dst"))
    with local.cwd(src):
        build_file_tree(
            {
                "copier.yaml": """\
                    q1:
                        type: str
                        default: a1
                """,
                "file1.jinja": """\
                    version 1
                    hello
                    {{ q1 }}
                    bye
                """,
                "{{ _copier_conf.answers_file }}.jinja": "{{ _copier_answers|to_nice_yaml }}",
            }
        )
        git("init")
        git("add", ".")
        git("commit", "-m1")
        git("tag", "1")
        build_file_tree(
            {
                "file1.jinja": """\
                    version 2
                    hello
                    {{ q1 }}
                    bye
                """,
            }
        )
        git("commit", "-am2")
        git("tag", "2")
    with local.cwd(dst):
        build_file_tree({"dst_top_file": "one"})
        git("init")
        git("add", ".")
        git("commit", "-m0")
    copier.run_copy(
        str(src),
        str(dst / "subfolder"),
        vcs_ref="1",
        defaults=True,
        overwrite=True,
        answers_file=".custom.copier-answers.yaml",
    )
    assert (dst / "subfolder" / "file1").read_text() == "version 1\nhello\na1\nbye\n"
    with local.cwd(dst):
        git("add", ".")
        git("commit", "-m1")
        copier.run_update(
            "subfolder",
            defaults=True,
            overwrite=True,
            answers_file=".custom.copier-answers.yaml",
        )
    answers = yaml.safe_load(
        (dst / "subfolder" / ".custom.copier-answers.yaml").read_bytes()
    )
    assert answers["_commit"] == "2"
    assert (dst / "subfolder" / "file1").read_text() == "version 2\nhello\na1\nbye\n"


@pytest.mark.parametrize(
    "conflict, readme, expect_reject",
    [
        pytest.param(
            "rej",
            "upstream version 2\n",
            True,
        ),
        pytest.param(
            "inline",
            "<<<<<<< modified\ndownstream version 1\n"
            "=======\nupstream version 2\n>>>>>>> new upstream\n",
            False,
        ),
    ],
)
def test_new_version_uses_subdirectory(
    conflict, tmp_path_factory, readme, expect_reject
):
    # Template in v1 doesn't have a _subdirectory;
    # in v2 it moves all things into a subdir and adds that key to copier.yml.
    # Some files change. Downstream project has evolved too. Does that work as expected?
    template_path = tmp_path_factory.mktemp("subdirectory_template")
    project_path = tmp_path_factory.mktemp("subdirectory_project")

    # First, create the template with an initial README
    with local.cwd(template_path):
        with open("README.md", "wb") as fd:
            fd.write(b"upstream version 1\n")

        with open("{{_copier_conf.answers_file}}.jinja", "w") as fd:
            fd.write("{{_copier_answers|to_nice_yaml}}\n")

        if conflict == "inline" and platform.system() == "Windows":
            # Workaround for odd behavior in Windows git. Without this, inline
            # conflict markers result in doubled CR and/or LF characters.
            with open(".gitattributes", "w") as fd:
                fd.write("*.md binary\n")

        git_init("hello template")
        git("tag", "v1")

    # Generate the project a first time, assert the README exists
    copier.copy(str(template_path), project_path, defaults=True, overwrite=True)
    assert (project_path / "README.md").exists()
    assert "_commit: v1" in (project_path / ".copier-answers.yml").read_text()

    # Start versioning the generated project
    with local.cwd(project_path):
        git_init("hello project")

        # After first commit, change the README, commit again
        with open("README.md", "wb") as fd:
            fd.write(b"downstream version 1\n")
        git("commit", "-am", "updated readme")

    # Now change the template
    with local.cwd(template_path):

        # Update the README
        with open("README.md", "wb") as fd:
            fd.write(b"upstream version 2\n")

        # Create a subdirectory, move files into it
        os.mkdir("subdir")
        os.rename("README.md", "subdir/README.md")
        os.rename(
            "{{_copier_conf.answers_file}}.jinja",
            "subdir/{{_copier_conf.answers_file}}.jinja",
        )

        # Add the subdirectory option to copier.yml
        with open("copier.yml", "w") as fd:
            fd.write("_subdirectory: subdir\n")

        # Commit the changes
        git("add", ".", "-A")
        git("commit", "-m", "use a subdirectory now")
        git("tag", "v2")

    # Finally, update the generated project
    copier.copy(dst_path=project_path, defaults=True, overwrite=True, conflict=conflict)
    assert "_commit: v2" in (project_path / ".copier-answers.yml").read_text()

    # Assert that the README still exists, and the conflicts were handled
    # correctly.
    assert (project_path / "README.md").exists()

    with (project_path / "README.md").open("rb") as fd:
        file_content = fd.read()
        assert [
            s.decode("utf-8") for s in file_content.splitlines()
        ] == readme.splitlines()
    reject_path = project_path / "README.md.rej"
    assert reject_path.exists() == expect_reject

    # Also assert the subdirectory itself was not rendered
    assert not (project_path / "subdir").exists()


def test_new_version_changes_subdirectory(tmp_path_factory):
    # Template in v3 changes from one subdirectory to another.
    # Some file evolves also. Sub-project evolves separately.
    # Sub-project is updated. Does that work as expected?
    template_path = tmp_path_factory.mktemp("subdirectory_template")
    project_path = tmp_path_factory.mktemp("subdirectory_project")

    # First, create the template with an initial subdirectory and README inside it
    with local.cwd(template_path):
        os.mkdir("subdir1")

        with open("subdir1/README.md", "w") as fd:
            fd.write("upstream version 1\n")

        with open("subdir1/[[_copier_conf.answers_file]].tmpl", "w") as fd:
            fd.write("[[_copier_answers|to_nice_yaml]]\n")

        # Add the subdirectory option to copier.yml
        with open("copier.yml", "w") as fd:
            fd.write("_subdirectory: subdir1\n")

        git_init("hello template")

    # Generate the project a first time, assert the README exists
    copier.copy(str(template_path), project_path, defaults=True, overwrite=True)
    assert (project_path / "README.md").exists()

    # Start versioning the generated project
    with local.cwd(project_path):
        git_init("hello project")

        # After first commit, change the README, commit again
        with open("README.md", "w") as fd:
            fd.write("downstream version 1\n")
        git("commit", "-am", "updated readme")

    # Now change the template
    with local.cwd(template_path):

        # Update the README
        with open("subdir1/README.md", "w") as fd:
            fd.write("upstream version 2\n")

        # Rename the subdirectory
        os.rename("subdir1", "subdir2")

        # Update copier.yml to reflect this change
        with open("copier.yml", "w") as fd:
            fd.write("_subdirectory: subdir2\n")

        # Commit the changes
        git("add", ".", "-A")
        git("commit", "-m", "changed from subdir1 to subdir2")

    # Finally, update the generated project
    copier.copy(
        str(template_path),
        project_path,
        defaults=True,
        overwrite=True,
        skip_if_exists=["README.md"],
    )

    # Assert that the README still exists, and was NOT force updated
    assert (project_path / "README.md").exists()
    with (project_path / "README.md").open() as fd:
        assert fd.read() == "downstream version 1\n"

    # Also assert the subdirectories themselves were not rendered
    assert not (project_path / "subdir1").exists()
    assert not (project_path / "subdir2").exists()
