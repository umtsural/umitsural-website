"""Strict, deterministic JSON serialization for persisted evidence."""

import json
from datetime import date, datetime
from typing import Any, cast

from ..models.common import JsonValue, require_aware_utc

TYPE_KEY = "__upf_type__"
VALUE_KEY = "value"


def dumps_json(value: JsonValue) -> str:
    """Serialize supported values deterministically and reject arbitrary objects."""
    return json.dumps(
        _encode(value), ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False
    )


def loads_json(value: str) -> JsonValue:
    """Deserialize a value produced by :func:`dumps_json`."""
    return cast(JsonValue, json.loads(value, object_hook=_object_hook))


def _encode(value: JsonValue) -> Any:
    if isinstance(value, datetime):
        require_aware_utc(value, "serialized datetime")
        return {TYPE_KEY: "datetime", VALUE_KEY: value.isoformat()}
    if isinstance(value, date):
        return {TYPE_KEY: "date", VALUE_KEY: value.isoformat()}
    if value is None or isinstance(value, bool | int | float | str):
        return value
    if isinstance(value, list):
        return [_encode(item) for item in value]
    if isinstance(value, dict):
        if TYPE_KEY in value:
            raise ValueError(f"reserved metadata key is not allowed: {TYPE_KEY}")
        return {key: _encode(item) for key, item in value.items()}
    raise TypeError(f"unsupported JSON value type: {type(value).__name__}")


def _object_hook(value: dict[str, Any]) -> Any:
    marker = value.get(TYPE_KEY)
    if marker is None:
        return value
    if set(value) != {TYPE_KEY, VALUE_KEY}:
        raise ValueError("invalid typed JSON object")
    raw = value[VALUE_KEY]
    if not isinstance(raw, str):
        raise ValueError("typed JSON value must be a string")
    if marker == "datetime":
        parsed = datetime.fromisoformat(raw)
        require_aware_utc(parsed, "serialized datetime")
        return parsed
    if marker == "date":
        return date.fromisoformat(raw)
    raise ValueError(f"unknown typed JSON marker: {marker}")
