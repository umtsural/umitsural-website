from pathlib import Path

from usural_prospect_finder.utils.config_hash import configuration_hash


def test_configuration_hash_is_order_independent_and_ignores_secrets_paths() -> None:
    first = {"weights": {"seo": 0.4, "quality": 0.6}, "api_key": "one", "cache_dir": Path("/a")}
    second = {"cache_dir": Path("/b"), "api_key": "two", "weights": {"quality": 0.6, "seo": 0.4}}
    assert configuration_hash(first) == configuration_hash(second)


def test_configuration_hash_changes_for_behavior() -> None:
    assert configuration_hash({"weight": 1}) != configuration_hash({"weight": 2})
