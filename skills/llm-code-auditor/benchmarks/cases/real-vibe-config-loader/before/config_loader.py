import json


class ConfigManager:
    def processData(self, data):
        return ConfigProcessor().processData(data)


class ConfigProcessor:
    def processData(self, data):
        try:
            config = json.loads(data)
        except Exception:
            return {}

        if "debug" not in config:
            config["debug"] = False
        if config["debug"] == "true":
            config["debug"] = True
        if config["debug"] == "false":
            config["debug"] = False
        if "retries" not in config:
            config["retries"] = 3
        if config["retries"] == "":
            config["retries"] = 3
        if isinstance(config["retries"], str):
            config["retries"] = int(config["retries"])
        if "timeout_seconds" not in config:
            config["timeout_seconds"] = 30
        if config["timeout_seconds"] == "":
            config["timeout_seconds"] = 30
        if isinstance(config["timeout_seconds"], str):
            config["timeout_seconds"] = int(config["timeout_seconds"])
        if "region" not in config:
            config["region"] = "us-east-1"
        if config["region"] == "":
            config["region"] = "us-east-1"
        if "features" not in config:
            config["features"] = []
        if config["features"] is None:
            config["features"] = []
        if isinstance(config["features"], str):
            config["features"] = [config["features"]]
        return config


def load_config(data):
    return ConfigManager().processData(data)
