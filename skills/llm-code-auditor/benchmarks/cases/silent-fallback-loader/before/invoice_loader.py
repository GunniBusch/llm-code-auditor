import json


def load_invoice(raw):
    try:
        invoice = json.loads(raw)
    except Exception:
        return {}

    if not isinstance(invoice, dict):
        return {}
    if "id" not in invoice:
        return {}
    if "total_cents" not in invoice:
        return {}

    return {
        "id": str(invoice["id"]),
        "total_cents": int(invoice.get("total_cents", 0)),
    }
