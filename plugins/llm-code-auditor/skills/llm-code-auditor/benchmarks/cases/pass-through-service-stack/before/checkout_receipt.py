class CheckoutService:
    def processData(self, customer_id, items):
        return CheckoutProcessor().processData(customer_id, items)


class CheckoutProcessor:
    def processData(self, customer_id, items):
        return CheckoutManager().processData(customer_id, items)


class CheckoutManager:
    def processData(self, customer_id, items):
        total_cents = 0
        for item in items:
            total_cents += item["unit_cents"] * item["quantity"]
        return {"customer_id": customer_id, "total_cents": total_cents}


def build_receipt(customer_id, items):
    return CheckoutService().processData(customer_id, items)
