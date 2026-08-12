from datetime import UTC, date, datetime

import pytest

from usural_prospect_finder.utils.serialization import dumps_json, loads_json


def test_signal_values_round_trip_with_types() -> None:
    value = {
        "boolean": True,
        "integer": 1,
        "nothing": None,
        "date": date(2026, 8, 9),
        "datetime": datetime(2026, 8, 9, 10, 30, tzinfo=UTC),
        "nested": [False, 2.5, "Ümit"],
    }
    restored = loads_json(dumps_json(value))
    assert restored == value
    assert type(restored["boolean"]) is bool
    assert type(restored["integer"]) is int


def test_serialization_is_deterministic() -> None:
    assert dumps_json({"b": 2, "a": 1}) == dumps_json({"a": 1, "b": 2})


def test_unsupported_value_fails_clearly() -> None:
    with pytest.raises(TypeError, match="unsupported JSON value type"):
        dumps_json({"bad": object()})  # type: ignore[dict-item]
