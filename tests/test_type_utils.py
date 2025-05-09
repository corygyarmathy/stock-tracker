from pathlib import Path

import pytest

from stock_tracker.utils.type_utils import convert_type


@pytest.mark.parametrize(
    "input_value, expected_type, expected_result",
    [
        ("123", int, 123),
        ("3.14", float, 3.14),
        ("hello", str, "hello"),
        ("some/path", Path, Path("some/path")),
        (True, bool, True),
        ("true", bool, True),
        ("False", bool, False),
        (None, int | None, None),
        ("456", int | None, 456),
        ("another/path", Path | str, Path("another/path")),
    ],
)
def test_convert_type_valid_cases(input_value, expected_type, expected_result):
    assert convert_type(input_value, expected_type) == expected_result


def test_convert_type_union_fallback_order():
    # Should try str first (will succeed), not int
    assert convert_type("abc", str | int) == "abc"

    # Should raise because neither str nor Path are convertible from bool
    with pytest.raises(ValueError):
        convert_type(True, dict | Path)


def test_convert_type_invalid_bool():
    with pytest.raises(ValueError):
        convert_type("maybe", bool)


def test_convert_type_invalid_type_cast():
    with pytest.raises(ValueError):
        convert_type("not-a-float", float)


def test_convert_type_unknown_type_object():
    class Dummy:
        pass

    with pytest.raises(ValueError):
        convert_type("value", Dummy | None)
