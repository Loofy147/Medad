import unittest
from datetime import datetime, timedelta, timezone

from task_contract import validate_task_payload, validate_task_transition


def stamp(delta_seconds: float = 0.0) -> str:
    return (datetime.now(timezone.utc) + timedelta(seconds=delta_seconds)).isoformat()


def task_payload(task_id: str = "task-1", **overrides) -> dict:
    now = stamp(-1)
    payload = {
        "schema_version": "medad.task.v1",
        "task_id": task_id,
        "title": f"Task {task_id}",
        "description": "",
        "status": "OPEN",
        "priority": "NORMAL",
        "owner_id": None,
        "dependencies": [],
        "evidence_refs": [],
        "artifact_refs": [],
        "created_at": now,
        "updated_at": now,
        "due_at": None,
        "blocked_reason": None,
        "completion_note": None,
        "completed_at": None,
        "cancellation_reason": None,
        "transition": None,
    }
    payload.update(overrides)
    return payload


def transition(previous: dict, to_status: str, *, reason: str = "Explicit task transition") -> dict:
    occurred = stamp(-0.1)
    updated = dict(previous)
    updated["status"] = to_status
    updated["updated_at"] = occurred
    updated["transition"] = {
        "from_status": previous["status"],
        "to_status": to_status,
        "reason": reason,
        "occurred_at": occurred,
    }
    if to_status != "BLOCKED":
        updated["blocked_reason"] = None
    else:
        updated["blocked_reason"] = "Waiting on a prerequisite"
    if to_status != "CANCELLED":
        updated["cancellation_reason"] = None
    if to_status != "DONE":
        updated["completed_at"] = None
        updated["completion_note"] = None
    else:
        updated["completed_at"] = occurred
        updated["completion_note"] = "Acceptance checks passed"
        updated["owner_id"] = "operator-1"
    return updated


class TaskContractTests(unittest.TestCase):
    def test_open_task_is_valid_with_explicit_defaults(self):
        payload = task_payload()
        self.assertEqual(validate_task_payload("task-1", payload), [])

    def test_record_identity_and_unknown_fields_fail_closed(self):
        payload = task_payload()
        payload["admin_override"] = True
        self.assertTrue(any("unknown task fields" in item for item in validate_task_payload("task-1", payload)))
        self.assertTrue(any("task_id must match" in item for item in validate_task_payload("other", task_payload())))

    def test_blocked_in_progress_and_done_require_recovery_or_owner_metadata(self):
        blocked = task_payload(status="BLOCKED")
        self.assertTrue(any("blocked_reason" in item for item in validate_task_payload("task-1", blocked)))

        active = task_payload(status="IN_PROGRESS")
        self.assertTrue(any("owner_id" in item for item in validate_task_payload("task-1", active)))

        done = task_payload(status="DONE")
        self.assertTrue(any("completion_note" in item for item in validate_task_payload("task-1", done)))
        self.assertTrue(any("completed_at" in item for item in validate_task_payload("task-1", done)))

    def test_time_fields_must_be_timezone_aware_and_ordered(self):
        payload = task_payload(created_at="2026-10-29T12:00:00", updated_at="2026-10-29T12:01:00Z")
        errors = validate_task_payload("task-1", payload)
        self.assertTrue(any("created_at must include a timezone" in item for item in errors))

        old = task_payload(created_at="2026-10-29T12:02:00+00:00", updated_at="2026-10-29T12:01:00+00:00")
        self.assertTrue(any("updated_at must not precede created_at" in item for item in validate_task_payload("task-1", old)))

    def test_task_cannot_depend_on_itself_or_repeat_dependency_references(self):
        payload = task_payload(dependencies=["task-1"])
        self.assertTrue(any("cannot depend on itself" in item for item in validate_task_payload("task-1", payload)))
        other = task_payload(dependencies=["task-2", "task-2"])
        self.assertTrue(any("duplicate references" in item for item in validate_task_payload("task-1", other)))

    def test_transition_requires_explicit_source_target_reason_and_matching_timestamp(self):
        old = task_payload()
        new = dict(old)
        new["status"] = "READY"
        errors = validate_task_payload("task-1", new) + validate_task_transition(old, new)
        self.assertTrue(any("transition metadata" in item for item in errors))

        valid = transition(old, "READY")
        self.assertEqual(validate_task_payload("task-1", valid), [])
        self.assertEqual(validate_task_transition(old, valid), [])

    def test_illegal_transition_and_stale_transition_source_are_rejected(self):
        old = task_payload()
        illegal = transition(old, "DONE")
        illegal["owner_id"] = "operator-1"
        self.assertTrue(any("not allowed" in item for item in validate_task_transition(old, illegal)))

        valid = transition(old, "READY")
        valid["transition"]["from_status"] = "BLOCKED"
        self.assertTrue(any("current stored status" in item for item in validate_task_transition(old, valid)))

    def test_same_status_update_cannot_rewrite_transition_history(self):
        old = transition(task_payload(), "READY")
        new = dict(old)
        new["updated_at"] = stamp(0.02)
        new["transition"] = {
            "from_status": "READY",
            "to_status": "READY",
            "reason": "Fake re-transition",
            "occurred_at": new["updated_at"],
        }
        self.assertTrue(any(
            "may change only when task status changes" in item
            for item in validate_task_transition(old, new)
        ))

    def test_completed_at_must_be_inside_record_timeline(self):
        created = stamp(-10)
        updated = stamp()
        payload = task_payload(
            created_at=created,
            updated_at=updated,
            status="DONE",
            owner_id="operator-1",
            completed_at=stamp(1),
            completion_note="Finished",
        )
        self.assertTrue(any("completed_at cannot be in the future" in item for item in validate_task_payload("task-1", payload)))


if __name__ == "__main__":
    unittest.main()
