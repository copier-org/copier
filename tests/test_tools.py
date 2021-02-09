from pathlib import Path

from poethepoet.app import PoeThePoet


def test_lint():
    """Ensure source code formatting"""
    PoeThePoet(Path("."))(["lint", "--show-diff-on-failure", "--color=always"])


def test_types():
    """Ensure source code static typing."""
    PoeThePoet(Path("."))(["types"])
