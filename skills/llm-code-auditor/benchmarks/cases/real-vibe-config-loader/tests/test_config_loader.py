import unittest

from config_loader import load_config


class ConfigLoaderTests(unittest.TestCase):
    def test_loads_defaults_and_normalizes_fields(self):
        self.assertEqual(
            load_config('{"debug": "true", "retries": "2", "features": "audit"}'),
            {
                "debug": True,
                "retries": 2,
                "timeout_seconds": 30,
                "region": "us-east-1",
                "features": ["audit"],
            },
        )

    def test_rejects_invalid_json(self):
        with self.assertRaises(ValueError):
            load_config("{not json")

    def test_rejects_negative_retries(self):
        with self.assertRaises(ValueError):
            load_config('{"retries": -1}')

    def test_rejects_bad_feature_shape(self):
        with self.assertRaises(ValueError):
            load_config('{"features": [1, "audit"]}')


if __name__ == "__main__":
    unittest.main()
