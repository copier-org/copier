from pathlib import Path
from stat import S_IREAD
from tempfile import TemporaryDirectory

import pytest
from poethepoet.app import PoeThePoet

from copier._tools import cast_to_bool, split_nul

from .helpers import git


def test_types() -> None:
    """Ensure source code static typing."""
    result = PoeThePoet(Path())(["types"])
    assert result == 0


@pytest.mark.parametrize(
    "value",
    [
        "",
        " ",
        "\t",
        "\n",
        "  \n\t  ",
    ],
)
def test_cast_to_bool_treats_blank_strings_as_false(value: str) -> None:
    assert cast_to_bool(value) is False


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (" true ", True),
        ("\nfalse\n", False),
    ],
)
def test_cast_to_bool_ignores_surrounding_whitespace(
    value: str, expected: bool
) -> None:
    assert cast_to_bool(value) is expected


def test_temporary_directory_with_readonly_files_deletion() -> None:
    """Ensure temporary directories containing read-only files are properly deleted,
    whatever the OS.
    """
    with TemporaryDirectory() as tmp_dir:
        ro_file = Path(tmp_dir) / "readonly.txt"
        with ro_file.open("w") as fp:
            fp.write("don't touch me!")
        ro_file.chmod(S_IREAD)
    assert not Path(tmp_dir).exists()


def test_temporary_directory_with_git_repo_deletion() -> None:
    """Ensure temporary directories containing git repositories are properly deleted,
    whatever the OS.
    """
    with TemporaryDirectory() as tmp_dir:
        git("init")
    assert not Path(tmp_dir).exists()


@pytest.mark.parametrize(
    ("output", "entries"),
    [
        ("", []),
        ("readme.md\0", ["readme.md"]),
        ("\0readme.md", ["", "readme.md"]),
        ("a\0b\0", ["a", "b"]),
        ("a\0b", ["a", "b"]),
        ("\0a\0\0b\0", ["", "a", "", "b"]),
        ("\0", [""]),
        ('quo"tes\0', ['quo"tes']),
        ('"surrounded"\0', ['"surrounded"']),
        ("m4â4ñ4a\0", ["m4â4ñ4a"]),
        ("tab\t\0", ["tab\t"]),
        ("lf\n\0", ["lf\n"]),
        ("crlf\r\n\0", ["crlf\r\n"]),
        ("back\\slash\0", ["back\\slash"]),
        ('qu"o\\tes\0', ['qu"o\\tes']),
        (
            "\a\b\f\n\t\vcontrol\a\b\f\n\t\vcharacters\a\b\f\n\t\v\0",
            ["\a\b\f\n\t\vcontrol\a\b\f\n\t\vcharacters\a\b\f\n\t\v"],
        ),
        ('lf\n\0qu"o\\tes\0', ["lf\n", 'qu"o\\tes']),
    ],
)
def test_split_nul(output: str, entries: list[str]) -> None:
    assert split_nul(output) == entries
