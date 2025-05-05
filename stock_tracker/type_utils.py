from typing import Any, Union, get_origin, get_args
from pathlib import Path
import types


def convert_type(value: Any, expected_type: type | types.UnionType) -> Any:
    """Convert a value to the expected type with fallback handling and clear errors."""

    if value is None:
        return None

    origin = get_origin(expected_type)

    # Handle Union or `|` (e.g., int | None)
    if origin is Union or origin is types.UnionType:
        for subtype in get_args(expected_type):
            try:
                return convert_type(value, subtype)
            except Exception:
                continue
        raise ValueError(
            f"Cannot convert {value!r} to any of {get_args(expected_type)}"
        )

    # Handle Path conversion
    if expected_type is Path:
        return Path(value)

    # Handle bool conversion
    if expected_type is bool:
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            lowered: str = value.strip().lower()
            if lowered in ("true", "1", "yes"):
                return True
            if lowered in ("false", "0", "no"):
                return False
        raise ValueError(f"Cannot convert {value!r} to bool")

    # Default fallback: attempt direct type cast
    if isinstance(expected_type, type):
        try:
            return expected_type(value)
        except (TypeError, ValueError) as e:
            raise ValueError(
                f"Invalid value for config field: expected {expected_type.__name__}, ",
                f"got {value!r} ({type(value).__name__})",
            ) from e

    raise TypeError(f"Expected a callable type, got {expected_type!r}")
