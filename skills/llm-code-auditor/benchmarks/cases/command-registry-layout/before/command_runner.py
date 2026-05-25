def execute_request(request, records):
    action = request.get("action", "")
    record_id = request.get("id", "")

    if not isinstance(records, dict):
        return {"ok": False, "message": "records must be a mapping"}
    if not isinstance(request, dict):
        return {"ok": False, "message": "request must be a mapping"}
    if not record_id:
        return {"ok": False, "message": "missing id"}

    if action == "create":
        if record_id in records:
            return {"ok": False, "message": f"record exists: {record_id}"}
        title = request.get("title", "")
        if not title:
            return {"ok": False, "message": "missing title"}
        records[record_id] = {
            "id": record_id,
            "title": title,
            "status": "open",
            "owner": "",
            "priority": "normal",
            "tags": [],
            "notes": [],
        }
        return {"ok": True, "record": dict(records[record_id])}

    if action == "assign":
        if record_id not in records:
            return {"ok": False, "message": f"missing record: {record_id}"}
        owner = request.get("owner", "")
        if not owner:
            return {"ok": False, "message": "missing owner"}
        records[record_id]["owner"] = owner
        return {"ok": True, "record": dict(records[record_id])}

    if action == "prioritize":
        if record_id not in records:
            return {"ok": False, "message": f"missing record: {record_id}"}
        priority = request.get("priority", "")
        if priority not in {"low", "normal", "high"}:
            return {"ok": False, "message": "invalid priority"}
        records[record_id]["priority"] = priority
        return {"ok": True, "record": dict(records[record_id])}

    if action == "close":
        if record_id not in records:
            return {"ok": False, "message": f"missing record: {record_id}"}
        records[record_id]["status"] = "closed"
        return {"ok": True, "record": dict(records[record_id])}

    if action == "reopen":
        if record_id not in records:
            return {"ok": False, "message": f"missing record: {record_id}"}
        records[record_id]["status"] = "open"
        return {"ok": True, "record": dict(records[record_id])}

    if action == "rename":
        if record_id not in records:
            return {"ok": False, "message": f"missing record: {record_id}"}
        title = request.get("title", "")
        if not title:
            return {"ok": False, "message": "missing title"}
        records[record_id]["title"] = title
        return {"ok": True, "record": dict(records[record_id])}

    if action == "tag":
        if record_id not in records:
            return {"ok": False, "message": f"missing record: {record_id}"}
        tag = request.get("tag", "")
        if not tag:
            return {"ok": False, "message": "missing tag"}
        if tag not in records[record_id]["tags"]:
            records[record_id]["tags"].append(tag)
        return {"ok": True, "record": dict(records[record_id])}

    if action == "note":
        if record_id not in records:
            return {"ok": False, "message": f"missing record: {record_id}"}
        note = request.get("note", "")
        if not note:
            return {"ok": False, "message": "missing note"}
        records[record_id]["notes"].append(note)
        return {"ok": True, "record": dict(records[record_id])}

    return {"ok": False, "message": f"unknown action: {action}"}
