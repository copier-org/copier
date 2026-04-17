# from __future__ import annotations

from typing import Any

import pytest

from copier._types import LazyDict
from copier._user_data import DEFAULT_DATA, AnswersMap


def dummy() -> bool:
    return True


class TestAnswersMap:
    def test_default(self) -> None:
        _answser_map = AnswersMap()
        assert _answser_map.user == {}
        assert _answser_map.init == {}
        assert _answser_map.metadata == {}
        assert _answser_map.last == {}
        assert _answser_map.user_defaults == {}
        assert _answser_map.external == {}
        assert _answser_map.hidden == set()

    @pytest.mark.parametrize(
        "args, result",
        [
            (
                {
                    "hidden": set(),
                    "user": {},
                    "init": {},
                    "metadata": {},
                    "last": {},
                    "user_defaults": {},
                    "external": LazyDict({}),
                },
                {
                    "_external_data": {},
                    **DEFAULT_DATA,
                },
            ),
            (
                {
                    "hidden": {"dummy"},
                    "user": {"isTrue": True},
                    "init": {
                        "isTrue": False,
                    },
                    "metadata": {
                        "isTrue": False,
                    },
                    "last": {"isTrue": False, "previous": "Hello"},
                    "user_defaults": {
                        "isTrue": False,
                    },
                    "external": LazyDict({"whyNot": dummy}),
                },
                {
                    "isTrue": True,
                    "previous": "Hello",
                    "_external_data": LazyDict({"whyNot": dummy}),
                    **DEFAULT_DATA,
                },
            ),
            (
                {
                    "hidden": {"isTrue"},
                    "user": {"isTrue": True},
                    "init": {
                        "isTrue": False,
                    },
                    "metadata": {
                        "isTrue": False,
                    },
                    "last": {"isTrue": False, "previous": "Hello"},
                    "user_defaults": {
                        "isTrue": False,
                    },
                    "external": LazyDict({"whyNot": dummy}),
                },
                {
                    "isTrue": True,
                    "previous": "Hello",
                    "_external_data": LazyDict({"whyNot": dummy}),
                    **DEFAULT_DATA,
                },
            ),
        ],
    )
    def test_combined(self, args: dict[str, Any], result: dict[str, Any]) -> None:
        _answser_map = AnswersMap(**args)
        assert _answser_map.combined == result

    @pytest.mark.parametrize(
        "args, result",
        [
            (
                {
                    "hidden": set(),
                    "user": {},
                    "init": {},
                    "metadata": {},
                    "last": {},
                    "user_defaults": {},
                    "external": LazyDict({}),
                },
                None,
            ),
            (
                {
                    "hidden": set(),
                    "user": {},
                    "init": {},
                    "metadata": {},
                    "last": {"_commit": "the_commit", "dummy": None},
                    "user_defaults": {},
                    "external": LazyDict({}),
                },
                "the_commit",
            ),
        ],
    )
    def test_old_commit(self, args: dict[str, Any], result: str) -> None:
        _answser_map = AnswersMap(**args)
        assert _answser_map.old_commit() == result

    @pytest.mark.parametrize(
        "args, key, result",
        [
            (
                {
                    "hidden": set(),
                    "user": {},
                    "init": {},
                    "metadata": {},
                    "last": {},
                    "user_defaults": {},
                    "external": LazyDict({}),
                },
                "dummy",
                {"dummy"},
            ),
        ],
    )
    def test_hide(self, args: dict[str, Any], key: str, result: set[str]) -> None:
        _answser_map = AnswersMap(**args)
        assert _answser_map.hidden == set()
        _answser_map.hide(key)
        assert _answser_map.hidden == result
