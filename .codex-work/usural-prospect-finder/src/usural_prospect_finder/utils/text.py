"""Small text normalization helpers."""


def collapse_whitespace(value: str) -> str:
    return " ".join(value.split())
