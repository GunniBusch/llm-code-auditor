from dataclasses import dataclass
from typing import Callable


PRIORITIES = {"low", "normal", "high"}
CommandFn = Callable[[dict, str, dict], dict]
CommandCheck = Callable[[dict, str, dict], str]


@dataclass(frozen=True)
class Action:
    required: tuple[str, ...]
    run: CommandFn
    needs_record: bool = True
    check: CommandCheck | None = None


def execute_request(request, records):
    boundary_error = validate_boundary(request, records)
    if boundary_error:
        return {"ok": False, "message": boundary_error}

    record_id = str(request.get("id", ""))
    action = ACTIONS.get(str(request.get("action", "")))
    request_error = validate_request(action, records, record_id, request)
    if request_error:
        return {"ok": False, "message": request_error}

    record = action.run(records, record_id, request)
    return {"ok": True, "record": dict(record)}


def validate_boundary(request, records):
    if not isinstance(records, dict):
        return "records must be a mapping"
    if not isinstance(request, dict):
        return "request must be a mapping"
    return ""


def validate_request(action, records, record_id, request):
    if not record_id:
        return "missing id"
    if action is None:
        return f"unknown action: {request.get('action', '')}"
    if action.needs_record and record_id not in records:
        return f"missing record: {record_id}"
    missing = next((field for field in action.required if not request.get(field, "")), "")
    if missing:
        return f"missing {missing}"
    if action.check is not None:
        return action.check(records, record_id, request)
    return ""


def create_record(records, record_id, request):
    records[record_id] = {
        "id": record_id,
        "title": request["title"],
        "status": "open",
        "owner": "",
        "priority": "normal",
        "tags": [],
        "notes": [],
    }
    return records[record_id]


def assign_record(records, record_id, request):
    records[record_id]["owner"] = request["owner"]
    return records[record_id]


def prioritize_record(records, record_id, request):
    records[record_id]["priority"] = request["priority"]
    return records[record_id]


def close_record(records, record_id, _request):
    records[record_id]["status"] = "closed"
    return records[record_id]


def reopen_record(records, record_id, _request):
    records[record_id]["status"] = "open"
    return records[record_id]


def rename_record(records, record_id, request):
    records[record_id]["title"] = request["title"]
    return records[record_id]


def tag_record(records, record_id, request):
    tag = request["tag"]
    if tag not in records[record_id]["tags"]:
        records[record_id]["tags"].append(tag)
    return records[record_id]


def note_record(records, record_id, request):
    records[record_id]["notes"].append(request["note"])
    return records[record_id]


def validate_new_record(records, record_id, _request):
    return f"record exists: {record_id}" if record_id in records else ""


def validate_priority(_records, _record_id, request):
    return "" if request["priority"] in PRIORITIES else "invalid priority"


ACTIONS = {
    "create": Action(("title",), create_record, needs_record=False, check=validate_new_record),
    "assign": Action(("owner",), assign_record),
    "prioritize": Action(("priority",), prioritize_record, check=validate_priority),
    "close": Action((), close_record),
    "reopen": Action((), reopen_record),
    "rename": Action(("title",), rename_record),
    "tag": Action(("tag",), tag_record),
    "note": Action(("note",), note_record),
}
