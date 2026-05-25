import unittest

from command_runner import execute_request


class CommandRunnerTests(unittest.TestCase):
    def test_create_assign_and_close_record(self):
        records = {}

        created = execute_request(
            {"action": "create", "id": "R-7", "title": "Prepare invoice"},
            records,
        )
        assigned = execute_request(
            {"action": "assign", "id": "R-7", "owner": "Mira"},
            records,
        )
        closed = execute_request({"action": "close", "id": "R-7"}, records)

        self.assertTrue(created["ok"])
        self.assertEqual(assigned["record"]["owner"], "Mira")
        self.assertEqual(closed["record"]["status"], "closed")

    def test_priority_tag_note_and_rename_preserve_existing_fields(self):
        records = {}
        execute_request(
            {"action": "create", "id": "R-9", "title": "Draft summary"},
            records,
        )

        execute_request({"action": "prioritize", "id": "R-9", "priority": "high"}, records)
        execute_request({"action": "tag", "id": "R-9", "tag": "billing"}, records)
        execute_request({"action": "note", "id": "R-9", "note": "Call vendor"}, records)
        result = execute_request(
            {"action": "rename", "id": "R-9", "title": "Draft final summary"},
            records,
        )

        self.assertEqual(result["record"]["priority"], "high")
        self.assertEqual(result["record"]["tags"], ["billing"])
        self.assertEqual(result["record"]["notes"], ["Call vendor"])
        self.assertEqual(result["record"]["title"], "Draft final summary")

    def test_reports_unknown_action_and_missing_fields(self):
        records = {}

        missing_title = execute_request({"action": "create", "id": "R-1"}, records)
        unknown = execute_request({"action": "archive", "id": "R-1"}, records)

        self.assertEqual(missing_title, {"ok": False, "message": "missing title"})
        self.assertEqual(unknown, {"ok": False, "message": "unknown action: archive"})


if __name__ == "__main__":
    unittest.main()
