"""Scoring configuration validation."""


def validate_weights(weights: dict[str, float], *, tolerance: float = 1e-9) -> None:
    if any(value < 0 for value in weights.values()):
        raise ValueError("weights cannot be negative")
    if abs(sum(weights.values()) - 1.0) > tolerance:
        raise ValueError("weights must sum to 1")
