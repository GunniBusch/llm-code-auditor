from dataclasses import dataclass
from typing import Callable


@dataclass(frozen=True)
class CommandRequest:
    action: str
    record_id: str
    fields: dict

    def value(self, name):
        return self.fields.get(name, "")


@dataclass(frozen=True)
class Action:
    required_fields: tuple[str, ...]
    run: Callable[[dict, CommandRequest], dict]


def execute_request(raw_request, records):
    if not isinstance(records, dict):
        return failure("records must be a mapping")
    if not isinstance(raw_request, dict):
        return failure("request must be a mapping")

    request = parse_request(raw_request)
    if not request.record_id:
        return failure("missing id")

    action = ACTIONS.get(request.action)
    if action is None:
        return failure(f"unknown action: {request.action}")

    missing_field = first_missing_field(request, action.required_fields)
    if missing_field:
        return failure(f"missing {missing_field}")

    return action.run(records, request)


def parse_request(raw_request):
    return CommandRequest(
        action=str(raw_request.get("action", "")),
        record_id=str(raw_request.get("id", "")),
        fields=dict(raw_request),
    )


def first_missing_field(request, required_fields):
    for field in required_fields:
        if not request.value(field):
            return field
    return ""


def create_record(records, request):
    if request.record_id in records:
        return failure(f"record exists: {request.record_id}")

    record = {
        "id": request.record_id,
        "title": request.value("title"),
        "status": "open",
        "owner": "",
        "priority": "normal",
        "tags": [],
        "notes": [],
    }
    records[request.record_id] = record
    return success(record)


def assign_record(records, request):
    return update_record(
        records,
        request,
        lambda record: record.update(owner=request.value("owner")),
    )


def prioritize_record(records, request):
    priority = request.value("priority")
    if priority not in {"low", "normal", "high"}:
        return failure("invalid priority")
    return update_record(records, request, lambda record: record.update(priority=priority))


def close_record(records, request):
    return update_record(records, request, lambda record: record.update(status="closed"))


def reopen_record(records, request):
    return update_record(records, request, lambda record: record.update(status="open"))


def rename_record(records, request):
    return update_record(
        records,
        request,
        lambda record: record.update(title=request.value("title")),
    )


def tag_record(records, request):
    def add_tag(record):
        tag = request.value("tag")
        if tag not in record["tags"]:
            record["tags"].append(tag)

    return update_record(records, request, add_tag)


def note_record(records, request):
    return update_record(
        records,
        request,
        lambda record: record["notes"].append(request.value("note")),
    )


def update_record(records, request, change):
    record = records.get(request.record_id)
    if record is None:
        return failure(f"missing record: {request.record_id}")
    change(record)
    return success(record)


def success(record):
    return {"ok": True, "record": dict(record)}


def failure(message):
    return {"ok": False, "message": message}


ACTIONS = {
    "create": Action(("title",), create_record),
    "assign": Action(("owner",), assign_record),
    "prioritize": Action(("priority",), prioritize_record),
    "close": Action((), close_record),
    "reopen": Action((), reopen_record),
    "rename": Action(("title",), rename_record),
    "tag": Action(("tag",), tag_record),
    "note": Action(("note",), note_record),
}
