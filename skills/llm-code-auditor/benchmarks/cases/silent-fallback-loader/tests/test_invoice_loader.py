import unittest

from invoice_loader import load_invoice


class InvoiceLoaderTests(unittest.TestCase):
    def test_loads_valid_invoice(self):
        self.assertEqual(
            load_invoice('{"id": "inv_123", "total_cents": 2599}'),
            {"id": "inv_123", "total_cents": 2599},
        )

    def test_rejects_invalid_json(self):
        with self.assertRaises(ValueError):
            load_invoice("{not json")

    def test_rejects_missing_total(self):
        with self.assertRaises(ValueError):
            load_invoice('{"id": "inv_123"}')


if __name__ == "__main__":
    unittest.main()
