import sqlite3
import tempfile
import unittest
from pathlib import Path

from store import (
    AccessPolicy,
    Actor,
    AuthorizationError,
    SQLiteStore,
    StoreConflict,
)


def actor(subject: str, *roles: str) -> Actor:
    return Actor(
        subject_id=subject,
        issuer="test-identity-provider",
        roles=tuple(roles),
        authenticated_at="2026-10-29T12:00:00+00:00",
        authn_method="test-fixture",
    )


class SQLiteStoreTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.db_path = Path(self.directory.name) / "medad.sqlite3"
        self.store = SQLiteStore(self.db_path)
        self.analyst = actor("analyst-1", "analyst")
        self.auditor = actor("auditor-1", "auditor")
        self.reviewer = actor("reviewer-1", "reviewer")
        self.approver = actor("approver-1", "approver")

    def tearDown(self):
        self.store.close()
        self.directory.cleanup()

    def test_records_persist_and_updates_require_expected_revision(self):
        created = self.store.put_record(
            self.analyst,
            "evidence",
            "evidence-1",
            {"label": "USER_REPORTED", "source_ref": "artifact:sample-1"},
            expected_revision=0,
            reason="Capture evidence candidate",
        )
        self.assertEqual(created["revision"], 1)

        loaded = self.store.get_record(self.analyst, "evidence", "evidence-1")
        self.assertEqual(loaded["payload"]["label"], "USER_REPORTED")

        updated = self.store.put_record(
            self.analyst,
            "evidence",
            "evidence-1",
            {"label": "EXPERIMENTALLY_SUPPORTED", "source_ref": "artifact:sample-1"},
            expected_revision=1,
            reason="Record reviewed evidence status",
        )
        self.assertEqual(updated["revision"], 2)

        with self.assertRaises(StoreConflict):
            self.store.put_record(
                self.analyst,
                "evidence",
                "evidence-1",
                {"label": "CONTRADICTED"},
                expected_revision=1,
                reason="Stale update must not win",
            )

        with self.assertRaises(StoreConflict):
            self.store.put_record(
                self.analyst,
                "evidence",
                "evidence-1",
                {"label": "CONTRADICTED"},
                reason="Blind updates are forbidden",
            )

    def test_unknown_collections_and_non_json_payloads_are_rejected(self):
        with self.assertRaises(ValueError):
            self.store.put_record(
                self.analyst, "users", "user-1", {"name": "X"}, reason="Not a supported record type"
            )
        with self.assertRaises(ValueError):
            self.store.put_record(
                self.analyst, "evidence", "evidence-bad", {"number": float("nan")}, reason="Reject NaN"
            )

    def test_write_denial_is_audited_and_does_not_mutate_records(self):
        with self.assertRaises(AuthorizationError):
            self.store.put_record(
                self.reviewer,
                "evidence",
                "evidence-denied",
                {"label": "USER_REPORTED"},
                reason="Reviewer should not mutate source evidence",
            )

        self.assertIsNone(self.store.get_record(self.analyst, "evidence", "evidence-denied"))
        events = self.store.audit_events(self.auditor)
        self.assertTrue(any(
            event["outcome"] == "DENIED"
            and event["resource_id"] == "evidence-denied"
            for event in events
        ))

    def test_review_and_stage_decisions_require_separate_roles_and_are_immutable(self):
        review = {
            "decision_type": "EVIDENCE_REVIEW",
            "outcome": "PASS",
            "subject_id": "claim:delivery-rate",
            "rationale": "Reviewed against the cited source artifact",
            "evidence_refs": ["evidence-1"],
            "reviewed_at": "2026-10-29T12:10:00+00:00",
        }
        with self.assertRaises(AuthorizationError):
            self.store.record_decision(self.approver, "review-1", review)

        self.store.put_record(
            self.analyst, "evidence", "evidence-1",
            {"label": "OBSERVED", "source_ref": "artifact:delivery-rate"},
            reason="Add referenced source record",
        )
        stored_review = self.store.record_decision(self.reviewer, "review-1", review)
        self.assertEqual(stored_review["payload"]["outcome"], "PASS")

        stage_decision = {
            "decision_type": "STAGE_DECISION",
            "outcome": "ADVANCE",
            "subject_id": "case:sample-1",
            "rationale": "Required evidence and gates were reviewed",
            "evidence_refs": ["evidence-1"],
            "reviewed_at": "2026-10-29T12:20:00+00:00",
            "stop_condition": "Stop if retained-order margin falls below zero",
            "rollback_plan": "Return to HOLD and invalidate the stage decision",
        }
        with self.assertRaises(AuthorizationError):
            self.store.record_decision(self.reviewer, "stage-1", stage_decision)

        approved = self.store.record_decision(self.approver, "stage-1", stage_decision)
        self.assertEqual(approved["payload"]["outcome"], "ADVANCE")
        self.assertFalse(approved["payload"].get("authorization_granted", False))

        with self.assertRaises(StoreConflict):
            self.store.record_decision(self.approver, "stage-1", stage_decision)

    def test_unsafe_or_underspecified_advance_is_rejected(self):
        payload = {
            "decision_type": "STAGE_DECISION",
            "outcome": "ADVANCE",
            "subject_id": "case:sample-1",
            "rationale": "Advance",
            "evidence_refs": [],
            "reviewed_at": "2026-10-29T12:20:00+00:00",
        }
        with self.assertRaisesRegex(ValueError, "evidence_refs"):
            self.store.record_decision(self.approver, "stage-unsafe", payload)

        payload["evidence_refs"] = ["evidence-1"]
        with self.assertRaisesRegex(ValueError, "stop_condition"):
            self.store.record_decision(self.approver, "stage-no-stop", payload)

        payload["stop_condition"] = "Stop on negative margin"
        payload["rollback_plan"] = "Revert to HOLD"
        payload["authorization_granted"] = True
        with self.assertRaisesRegex(ValueError, "unknown decision fields"):
            self.store.record_decision(self.approver, "stage-auth-flag", payload)

    def test_schema_migration_is_recorded_and_data_survives_reopen(self):
        self.store.put_record(
            self.analyst, "tasks", "task-1", {"status": "OPEN"}, reason="Create task"
        )
        self.store.close()
        second = SQLiteStore(self.db_path)
        try:
            loaded = second.get_record(self.analyst, "tasks", "task-1")
            self.assertEqual(loaded["payload"]["status"], "OPEN")
            with sqlite3.connect(self.db_path) as connection:
                version = connection.execute(
                    "SELECT MAX(version) FROM schema_migrations"
                ).fetchone()[0]
            self.assertEqual(version, 1)
        finally:
            second.close()

    def test_audit_chain_verifies_and_database_triggers_block_mutation(self):
        self.store.put_record(
            self.analyst, "artifacts", "artifact-1",
            {"sha256": "abc123"}, reason="Register artifact",
        )
        self.assertTrue(self.store.verify_audit_chain(self.auditor)["valid"])

        with self.assertRaises(sqlite3.IntegrityError):
            self.store._connection.execute(
                "UPDATE audit_events SET reason = 'changed' WHERE sequence = 1"
            )
        with self.assertRaises(sqlite3.IntegrityError):
            self.store._connection.execute(
                "DELETE FROM audit_events WHERE sequence = 1"
            )

    def test_policy_defaults_to_deny_for_unmapped_roles(self):
        restricted = SQLiteStore(
            self.db_path.parent / "restricted.sqlite3",
            policy=AccessPolicy(),
        )
        try:
            with self.assertRaises(ValueError):
                actor("unknown-role", "root")
            with self.assertRaises(AuthorizationError):
                restricted.put_record(
                    actor("read-only", "reader"), "tasks", "task-2",
                    {"status": "OPEN"}, reason="Reader cannot write",
                )
        finally:
            restricted.close()


if __name__ == "__main__":
    unittest.main()
