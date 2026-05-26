from dataclasses import dataclass, field
from typing import Callable


PRIORITIES = {"low", "normal", "high"}
Apply = Callable[[dict, str, dict], dict]
Validate = Callable[[dict, str, dict], str]


@dataclass(frozen=True)
class Action:
    required: tuple[str, ...]
    apply: Apply
    needs_record: bool = True
    validate: Validate = field(default=lambda _records, _record_id, _request: "")


def execute_request(request, records):
    boundary_error = validate_boundary(request, records)
    if boundary_error:
        return {"ok": False, "message": boundary_error}

    record_id = str(request.get("id", ""))
    action = ACTIONS.get(str(request.get("action", "")))
    request_error = validate_request(action, records, record_id, request)
    if request_error:
        return {"ok": False, "message": request_error}

    return {"ok": True, "record": dict(action.apply(records, record_id, request))}


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
    return action.validate(records, record_id, request)


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


def set_record_field(record_field, request_field):
    def apply(records, record_id, request):
        records[record_id][record_field] = request[request_field]
        return records[record_id]

    return apply


def set_status(status):
    def apply(records, record_id, _request):
        records[record_id]["status"] = status
        return records[record_id]

    return apply


def tag_record(records, record_id, request):
    tag = request["tag"]
    if tag not in records[record_id]["tags"]:
        records[record_id]["tags"].append(tag)
    return records[record_id]


def note_record(records, record_id, request):
    records[record_id]["notes"].append(request["note"])
    return records[record_id]


def new_record_error(records, record_id, _request):
    return f"record exists: {record_id}" if record_id in records else ""


def priority_error(_records, _record_id, request):
    return "" if request["priority"] in PRIORITIES else "invalid priority"


ACTIONS = {
    "create": Action(("title",), create_record, needs_record=False, validate=new_record_error),
    "assign": Action(("owner",), set_record_field("owner", "owner")),
    "prioritize": Action(("priority",), set_record_field("priority", "priority"), validate=priority_error),
    "close": Action((), set_status("closed")),
    "reopen": Action((), set_status("open")),
    "rename": Action(("title",), set_record_field("title", "title")),
    "tag": Action(("tag",), tag_record),
    "note": Action(("note",), note_record),
}
