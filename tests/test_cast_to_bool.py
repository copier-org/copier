from copier._tools import cast_to_bool


def test_cast_to_bool_whitespace_only_strings_are_false() -> None:
    assert cast_to_bool("") is False
    assert cast_to_bool(" ") is False
    assert cast_to_bool("\n") is False
    assert cast_to_bool("   \n\t") is False
