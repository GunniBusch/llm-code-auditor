import json


DEFAULT_REGION = "us-east-1"


def load_config(raw_config):
    try:
        config = json.loads(raw_config)
    except json.JSONDecodeError as error:
        raise ValueError("config must be valid JSON") from error

    if not isinstance(config, dict):
        raise ValueError("config must be a JSON object")

    return {
        "debug": parse_bool(config.get("debug", False), "debug"),
        "retries": parse_non_negative_int(config.get("retries", 3), "retries"),
        "timeout_seconds": parse_non_negative_int(
            config.get("timeout_seconds", 30),
            "timeout_seconds",
        ),
        "region": parse_region(config.get("region", DEFAULT_REGION)),
        "features": parse_features(config.get("features", [])),
    }


def parse_bool(value, field):
    if isinstance(value, bool):
        return value
    if value in {"true", "false"}:
        return value == "true"
    raise ValueError(f"{field} must be a boolean")


def parse_non_negative_int(value, field):
    try:
        parsed = int(value)
    except (TypeError, ValueError) as error:
        raise ValueError(f"{field} must be an integer") from error
    if parsed < 0:
        raise ValueError(f"{field} must be non-negative")
    return parsed


def parse_region(value):
    if isinstance(value, str) and value:
        return value
    raise ValueError("region must be a non-empty string")


def parse_features(value):
    if value is None:
        return []
    if isinstance(value, str):
        return [value]
    if isinstance(value, list) and all(isinstance(feature, str) for feature in value):
        return value
    raise ValueError("features must be a string or list of strings")
