"""Deterministic, secret-safe behavioral configuration hashing."""

import hashlib
from pathlib import Path
from typing import Any

from .serialization import dumps_json

SECRET_MARKERS = ("api_key", "token", "secret", "password")
PATH_MARKERS = ("path", "dir")


def configuration_hash(config: dict[str, Any]) -> str:
    """Hash normalized behavioral config, excluding secrets and machine paths."""
    normalized = _normalize(config)
    return hashlib.sha256(dumps_json(normalized).encode()).hexdigest()


def _normalize(value: Any) -> Any:
    if isinstance(value, dict):
        result: dict[str, Any] = {}
        for key, item in value.items():
            lowered = str(key).lower()
            if any(marker in lowered for marker in SECRET_MARKERS + PATH_MARKERS):
                continue
            result[str(key)] = _normalize(item)
        return result
    if isinstance(value, list | tuple):
        return [_normalize(item) for item in value]
    if isinstance(value, Path):
        return None
    if value is None or isinstance(value, bool | int | float | str):
        return value
    raise TypeError(f"unsupported configuration value: {type(value).__name__}")
