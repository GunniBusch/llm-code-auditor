import json


def load_invoice(raw):
    try:
        invoice = json.loads(raw)
    except json.JSONDecodeError as error:
        raise ValueError("invalid invoice JSON") from error

    if not isinstance(invoice, dict):
        raise ValueError("invoice must be an object")

    invoice_id = invoice.get("id")
    total_cents = invoice.get("total_cents")
    if not isinstance(invoice_id, str) or not invoice_id:
        raise ValueError("invoice id is required")
    if not isinstance(total_cents, int) or total_cents < 0:
        raise ValueError("invoice total must be a non-negative integer")

    return {"id": invoice_id, "total_cents": total_cents}
