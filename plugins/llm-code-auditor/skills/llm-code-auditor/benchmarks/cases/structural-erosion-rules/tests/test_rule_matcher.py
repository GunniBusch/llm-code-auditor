import unittest

from rule_matcher import match_rule


BASE_RULE = {
    "name": "sync",
    "kind": "job",
    "owner": "billing",
    "status": "active",
    "region": "eu",
    "source": "ledger",
    "target": "warehouse",
    "priority": "high",
    "tag": "nightly",
}


class RuleMatcherTests(unittest.TestCase):
    def test_counts_all_matching_fields(self):
        self.assertEqual(match_rule(BASE_RULE, dict(BASE_RULE)), 9)

    def test_counts_partial_match(self):
        candidate = dict(BASE_RULE)
        candidate["owner"] = "support"
        candidate["region"] = "us"
        candidate["tag"] = "manual"

        self.assertEqual(match_rule(BASE_RULE, candidate), 6)


if __name__ == "__main__":
    unittest.main()
