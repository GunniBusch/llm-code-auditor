def build_receipt(customer_id, line_items):
    total_cents = sum(
        line_item["unit_cents"] * line_item["quantity"]
        for line_item in line_items
    )
    return {"customer_id": customer_id, "total_cents": total_cents}
