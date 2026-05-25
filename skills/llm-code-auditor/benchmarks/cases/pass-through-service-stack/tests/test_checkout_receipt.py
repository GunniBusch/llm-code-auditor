import unittest

from checkout_receipt import build_receipt


class CheckoutReceiptTests(unittest.TestCase):
    def test_builds_receipt_total(self):
        self.assertEqual(
            build_receipt(
                "cus_123",
                [
                    {"unit_cents": 1200, "quantity": 2},
                    {"unit_cents": 399, "quantity": 1},
                ],
            ),
            {"customer_id": "cus_123", "total_cents": 2799},
        )

    def test_empty_cart_has_zero_total(self):
        self.assertEqual(
            build_receipt("cus_123", []),
            {"customer_id": "cus_123", "total_cents": 0},
        )


if __name__ == "__main__":
    unittest.main()
