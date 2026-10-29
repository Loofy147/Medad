"""Strict task record and state-transition contract for Medad's operating store."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

TASK_SCHEMA_VERSION = "medad.task.v1"
TASK_STATES = frozenset({"OPEN", "READY", "IN_PROGRESS", "BLOCKED", "DONE", "CANCELLED"})
TASK_PRIORITIES = frozenset({"LOW", "NORMAL", "HIGH", "CRITICAL"})
TASK_TRANSITIONS = {
    "OPEN": frozenset({"READY", "BLOCKED", "CANCELLED"}),
    "READY": frozenset({"OPEN", "IN_PROGRESS", "BLOCKED", "CANCELLED"}),
    "IN_PROGRESS": frozenset({"READY", "BLOCKED", "DONE", "CANCELLED"}),
    "BLOCKED": frozenset({"OPEN", "READY", "IN_PROGRESS", "CANCELLED"}),
    "DONE": frozenset({"READY"}),
    "CANCELLED": frozenset({"OPEN"}),
}
TASK_FIELDS = frozenset({
    "schema_version", "task_id", "title", "description", "status", "priority",
    "owner_id", "dependencies", "evidence_refs", "artifact_refs", "created_at",
    "updated_at", "due_at", "blocked_reason", "completion_note", "completed_at",
    "cancellation_reason", "transition",
})
TRANSITION_FIELDS = frozenset({"from_status", "to_status", "reason", "occurred_at"})


def _text(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _datetime(value: Any, field: str, *, allow_none: bool = False) -> tuple[datetime | None, str | None]:
    if value is None and allow_none:
        return None, None
    if not isinstance(value, str):
        return None, f"{field} must be an ISO-8601 timestamp"
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None, f"{field} must be an ISO-8601 timestamp"
    if parsed.tzinfo is None:
        return None, f"{field} must include a timezone"
    return parsed.astimezone(timezone.utc), None


def validate_task_payload(record_id: str, payload: Any) -> list[str]:
    """Validate a complete task object. This checks shape/invariants, not authorization."""
    if not isinstance(payload, dict):
        return ["task payload must be an object"]
    errors: list[str] = []
    missing = sorted(TASK_FIELDS - set(payload))
    unknown = sorted(set(payload) - TASK_FIELDS)
    if missing:
        errors.append(f"missing task fields: {missing}")
    if unknown:
        errors.append(f"unknown task fields: {unknown}")
    if payload.get("schema_version") != TASK_SCHEMA_VERSION:
        errors.append(f"schema_version must be {TASK_SCHEMA_VERSION}")
    if payload.get("task_id") != record_id:
        errors.append("task_id must match the storage record_id")
    if not _text(payload.get("title")):
        errors.append("title is required")
    if not isinstance(payload.get("description"), str):
        errors.append("description must be a string")
    status = payload.get("status")
    if status not in TASK_STATES:
        errors.append(f"status must be one of {sorted(TASK_STATES)}")
    if payload.get("priority") not in TASK_PRIORITIES:
        errors.append(f"priority must be one of {sorted(TASK_PRIORITIES)}")
    owner_id = payload.get("owner_id")
    if owner_id is not None and not _text(owner_id):
        errors.append("owner_id must be a non-empty string or null")
    if status == "IN_PROGRESS" and not _text(owner_id):
        errors.append("IN_PROGRESS tasks require owner_id")

    for field in ("dependencies", "evidence_refs", "artifact_refs"):
        value = payload.get(field)
        if not isinstance(value, list) or any(not _text(item) for item in value):
            errors.append(f"{field} must be an array of non-empty strings")
            continue
        if len(value) != len(set(value)):
            errors.append(f"{field} must not contain duplicate references")
    if isinstance(payload.get("dependencies"), list) and record_id in payload["dependencies"]:
        errors.append("a task cannot depend on itself")

    parsed_times: dict[str, datetime | None] = {}
    for field in ("created_at", "updated_at"):
        parsed, error = _datetime(payload.get(field), f"{field}")
        parsed_times[field] = parsed
        if error:
            errors.append(error)
        elif parsed and parsed > datetime.now(timezone.utc):
            errors.append(f"{field} cannot be in the future")
    due, due_error = _datetime(payload.get("due_at"), "due_at", allow_none=True)
    parsed_times["due_at"] = due
    if due_error:
        errors.append(due_error)
    completed, completed_error = _datetime(payload.get("completed_at"), "completed_at", allow_none=True)
    parsed_times["completed_at"] = completed
    if completed_error:
        errors.append(completed_error)
    if parsed_times.get("created_at") and parsed_times.get("updated_at"):
        if parsed_times["updated_at"] < parsed_times["created_at"]:
            errors.append("updated_at must not precede created_at")
    if completed and completed > datetime.now(timezone.utc):
        errors.append("completed_at cannot be in the future")
    if completed and parsed_times.get("created_at") and completed < parsed_times["created_at"]:
        errors.append("completed_at must not precede created_at")
    if completed and parsed_times.get("updated_at") and completed > parsed_times["updated_at"]:
        errors.append("completed_at must not follow updated_at")

    blocked_reason = payload.get("blocked_reason")
    if status == "BLOCKED":
        if not _text(blocked_reason):
            errors.append("BLOCKED tasks require blocked_reason")
    elif blocked_reason is not None:
        errors.append("blocked_reason must be null unless status is BLOCKED")

    completion_note = payload.get("completion_note")
    if status == "DONE":
        if not _text(completion_note):
            errors.append("DONE tasks require completion_note")
        if completed is None and not completed_error:
            errors.append("DONE tasks require completed_at")
    elif completion_note is not None or completed is not None:
        errors.append("completion_note and completed_at must be null unless status is DONE")

    cancellation_reason = payload.get("cancellation_reason")
    if status == "CANCELLED":
        if not _text(cancellation_reason):
            errors.append("CANCELLED tasks require cancellation_reason")
    elif cancellation_reason is not None:
        errors.append("cancellation_reason must be null unless status is CANCELLED")

    transition = payload.get("transition")
    if transition is not None:
        if not isinstance(transition, dict):
            errors.append("transition must be an object or null")
        else:
            if set(transition) != TRANSITION_FIELDS:
                errors.append(
                    f"transition fields must match schema; missing={sorted(TRANSITION_FIELDS - set(transition))}, "
                    f"unknown={sorted(set(transition) - TRANSITION_FIELDS)}"
                )
            from_status = transition.get("from_status")
            to_status = transition.get("to_status")
            if from_status not in TASK_STATES:
                errors.append("transition.from_status is invalid")
            if to_status not in TASK_STATES:
                errors.append("transition.to_status is invalid")
            elif status != to_status:
                errors.append("transition.to_status must match task status")
            elif from_status in TASK_STATES and to_status not in TASK_TRANSITIONS[from_status]:
                errors.append(f"transition {from_status} -> {to_status} is not allowed")
            if not _text(transition.get("reason")):
                errors.append("transition.reason is required")
            transition_time, transition_error = _datetime(
                transition.get("occurred_at"), "transition.occurred_at"
            )
            if transition_error:
                errors.append(transition_error)
            elif transition_time and transition_time > datetime.now(timezone.utc):
                errors.append("transition.occurred_at cannot be in the future")
            if transition_time and parsed_times.get("updated_at") and transition_time > parsed_times["updated_at"]:
                errors.append("transition.occurred_at must not follow updated_at")
    return errors


def validate_task_transition(previous: dict[str, Any], current: dict[str, Any]) -> list[str]:
    """Validate mutation semantics when an existing task revision is replaced."""
    errors: list[str] = []
    if previous.get("task_id") != current.get("task_id"):
        errors.append("task_id is immutable")
    if previous.get("created_at") != current.get("created_at"):
        errors.append("created_at is immutable")
    old_status = previous.get("status")
    new_status = current.get("status")
    old_updated, old_error = _datetime(previous.get("updated_at"), "previous.updated_at")
    new_updated, new_error = _datetime(current.get("updated_at"), "updated_at")
    if old_error:
        errors.append(old_error)
    if new_error:
        errors.append(new_error)
    if old_updated and new_updated and new_updated <= old_updated:
        errors.append("updated_at must advance when a task record changes")
    if old_status == new_status:
        if previous.get("transition") != current.get("transition"):
            errors.append("transition metadata may change only when task status changes")
        return errors
    if old_status not in TASK_STATES or new_status not in TASK_STATES:
        errors.append("task status is invalid")
        return errors
    if new_status not in TASK_TRANSITIONS[old_status]:
        errors.append(f"task transition {old_status} -> {new_status} is not allowed")
    transition = current.get("transition")
    if not isinstance(transition, dict):
        errors.append("status changes require explicit transition metadata")
        return errors
    if transition.get("from_status") != old_status:
        errors.append("transition.from_status must match the current stored status")
    if transition.get("to_status") != new_status:
        errors.append("transition.to_status must match the new status")
    transition_time, transition_error = _datetime(transition.get("occurred_at"), "transition.occurred_at")
    if transition_error:
        errors.append(transition_error)
    elif transition_time and old_updated and transition_time <= old_updated:
        errors.append("transition.occurred_at must be after the previous task update")
    if transition_time and new_updated and transition_time != new_updated:
        errors.append("transition.occurred_at must equal updated_at for a status transition")
    return errors
