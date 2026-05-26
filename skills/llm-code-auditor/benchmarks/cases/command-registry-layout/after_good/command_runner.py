from dataclasses import dataclass, field
from typing import Callable


@dataclass(frozen=True)
class CommandRequest:
    action: str
    record_id: str
    fields: dict

    def value(self, name):
        return self.fields.get(name, "")

    def first_missing(self, required_fields):
        for field_name in required_fields:
            if not self.value(field_name):
                return field_name
        return ""

    @classmethod
    def from_mapping(cls, raw_request):
        return cls(
            action=str(raw_request.get("action", "")),
            record_id=str(raw_request.get("id", "")),
            fields=dict(raw_request),
        )


@dataclass(frozen=True)
class Action:
    required_fields: tuple[str, ...]
    run: Callable[[dict, CommandRequest], dict]
    needs_record: bool = True
    validate: Callable[[dict, CommandRequest], str] = field(
        default=lambda _records, _request: "",
    )

    def validation_error(self, records, request):
        if self.needs_record and request.record_id not in records:
            return f"missing record: {request.record_id}"
        missing_field = request.first_missing(self.required_fields)
        if missing_field:
            return f"missing {missing_field}"
        return self.validate(records, request)


def execute_request(raw_request, records):
    boundary_error = command_boundary_error(raw_request, records)
    if boundary_error:
        return failure(boundary_error)

    request = CommandRequest.from_mapping(raw_request)
    action = ACTIONS.get(request.action)
    request_error = command_request_error(request, action, records)
    if request_error:
        return failure(request_error)

    return action.run(records, request)


def command_boundary_error(raw_request, records):
    if not isinstance(records, dict):
        return "records must be a mapping"
    if not isinstance(raw_request, dict):
        return "request must be a mapping"
    return ""


def command_request_error(request, action, records):
    if not request.record_id:
        return "missing id"
    if action is None:
        return f"unknown action: {request.action}"
    return action.validation_error(records, request)


def create_record(records, request):
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
    records[request.record_id]["owner"] = request.value("owner")
    return success(records[request.record_id])


def prioritize_record(records, request):
    priority = request.value("priority")
    records[request.record_id]["priority"] = priority
    return success(records[request.record_id])


def close_record(records, request):
    records[request.record_id]["status"] = "closed"
    return success(records[request.record_id])


def reopen_record(records, request):
    records[request.record_id]["status"] = "open"
    return success(records[request.record_id])


def rename_record(records, request):
    records[request.record_id]["title"] = request.value("title")
    return success(records[request.record_id])


def tag_record(records, request):
    record = records[request.record_id]
    tag = request.value("tag")
    if tag not in record["tags"]:
        record["tags"].append(tag)
    return success(record)


def note_record(records, request):
    record = records[request.record_id]
    record["notes"].append(request.value("note"))
    return success(record)


def new_record_error(records, request):
    if request.record_id in records:
        return f"record exists: {request.record_id}"
    return ""


def priority_error(_records, request):
    if request.value("priority") not in {"low", "normal", "high"}:
        return "invalid priority"
    return ""


def success(record):
    return {"ok": True, "record": dict(record)}


def failure(message):
    return {"ok": False, "message": message}


ACTIONS = {
    "create": Action(("title",), create_record, needs_record=False, validate=new_record_error),
    "assign": Action(("owner",), assign_record),
    "prioritize": Action(("priority",), prioritize_record, validate=priority_error),
    "close": Action((), close_record),
    "reopen": Action((), reopen_record),
    "rename": Action(("title",), rename_record),
    "tag": Action(("tag",), tag_record),
    "note": Action(("note",), note_record),
}
