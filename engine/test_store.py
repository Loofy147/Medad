import sqlite3
import tempfile
import unittest
from datetime import date
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


def evidence_payload(
    evidence_id: str,
    *,
    evidence_label: str = "quoted",
    polarity: str = "supports",
    sample_size: int | None = None,
) -> dict:
    payload = {
        "evidence_id": evidence_id,
        "source_kind": "document",
        "evidence_label": evidence_label,
        "polarity": polarity,
        "observed_on": date.today().isoformat(),
        "scope": {"subject": "delivery-rate", "metric": "delivery_rate", "geography": "Algeria"},
        "artifact_ref": f"artifact:{evidence_id}",
        "independence_key": f"source:{evidence_id}",
    }
    if evidence_label == "observed":
        payload["sample_size"] = 10 if sample_size is None else sample_size
    elif sample_size is not None:
        payload["sample_size"] = sample_size
    return payload


def valid_run_payload(run_id: str) -> dict:
    return {
        "schema_version": "medad.decision-run.v1",
        "run_manifest": {
            "run_id": run_id,
            "case_id": "case:store-fixture",
            "code_revision": "test-revision",
            "mode": "ANALYSIS_ONLY_NO_EXTERNAL_SIDE_EFFECTS",
            "input_hash": "a" * 64,
            "report_hash": "b" * 64,
        },
        "decision": {"authorization_granted": False},
    }


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
            evidence_payload("evidence-1"),
            expected_revision=0,
            reason="Capture evidence candidate",
        )
        self.assertEqual(created["revision"], 1)

        loaded = self.store.get_record(self.analyst, "evidence", "evidence-1")
        self.assertEqual(loaded["payload"]["evidence_label"], "quoted")

        updated = self.store.put_record(
            self.analyst,
            "evidence",
            "evidence-1",
            evidence_payload("evidence-1", evidence_label="observed", sample_size=12),
            expected_revision=1,
            reason="Record reviewed evidence status",
        )
        self.assertEqual(updated["revision"], 2)

        with self.assertRaises(StoreConflict):
            self.store.put_record(
                self.analyst,
                "evidence",
                "evidence-1",
                evidence_payload("evidence-1", polarity="contradicts"),
                expected_revision=1,
                reason="Stale update must not win",
            )

        with self.assertRaises(StoreConflict):
            self.store.put_record(
                self.analyst,
                "evidence",
                "evidence-1",
                evidence_payload("evidence-1", polarity="contradicts"),
                reason="Blind updates are forbidden",
            )

    def test_evidence_contract_is_enforced_at_storage_boundary(self):
        invalid = evidence_payload("evidence-invalid")
        invalid["scope"] = {"subject": "delivery-rate"}
        with self.assertRaisesRegex(ValueError, "evidence contract"):
            self.store.put_record(
                self.analyst, "evidence", "evidence-invalid", invalid,
                reason="Reject incomplete evidence scope",
            )

        mismatched = evidence_payload("payload-id")
        with self.assertRaisesRegex(ValueError, "evidence_id must match"):
            self.store.put_record(
                self.analyst, "evidence", "different-id", mismatched,
                reason="Reject identity mismatch",
            )

    def test_run_records_must_be_analysis_only_and_hash_identified(self):
        report = valid_run_payload("run-1")
        saved = self.store.put_record(
            self.analyst, "runs", "run-1", report, reason="Persist a decision-run report"
        )
        self.assertEqual(saved["payload"]["run_manifest"]["run_id"], "run-1")

        unsafe = valid_run_payload("run-unsafe")
        unsafe["decision"]["authorization_granted"] = True
        with self.assertRaisesRegex(ValueError, "authorization_granted"):
            self.store.put_record(
                self.analyst, "runs", "run-unsafe", unsafe,
                reason="Reject a run that claims authorization",
            )

        malformed = valid_run_payload("run-bad-hash")
        malformed["run_manifest"]["input_hash"] = "not-a-digest"
        with self.assertRaisesRegex(ValueError, "input_hash"):
            self.store.put_record(
                self.analyst, "runs", "run-bad-hash", malformed,
                reason="Reject malformed run identity",
            )

    def test_artifact_records_require_a_reference_or_digest(self):
        with self.assertRaisesRegex(ValueError, "artifact_ref or sha256"):
            self.store.put_record(
                self.analyst, "artifacts", "artifact-empty", {"label": "empty"},
                reason="Reject artifact without an identity",
            )

        with self.assertRaisesRegex(ValueError, "64-character"):
            self.store.put_record(
                self.analyst, "artifacts", "artifact-bad-digest", {"sha256": "bad"},
                reason="Reject malformed artifact digest",
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
                evidence_payload("evidence-denied"),
                reason="Reviewer should not mutate source evidence",
            )

        self.assertIsNone(self.store.get_record(self.analyst, "evidence", "evidence-denied"))
        events = self.store.audit_events(self.auditor)
        denied_event = next(
            event for event in events
            if event["outcome"] == "DENIED" and event["resource_id"] == "evidence-denied"
        )
        self.assertEqual(denied_event["actor_roles"], ["reviewer"])
        self.assertEqual(denied_event["authn_method"], "test-fixture")

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
            evidence_payload("evidence-1"),
            reason="Add referenced source record",
        )
        stored_review = self.store.record_decision(self.reviewer, "review-1", review)
        self.assertEqual(stored_review["payload"]["outcome"], "PASS")
        self.assertEqual(stored_review["payload"]["evidence_snapshots"][0]["revision"], 1)

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

        with self.assertRaises(sqlite3.IntegrityError):
            self.store._connection.execute(
                "UPDATE records SET payload_json = '{}' WHERE collection = 'decisions' AND record_id = 'stage-1'"
            )
        with self.assertRaises(sqlite3.IntegrityError):
            self.store._connection.execute(
                "DELETE FROM records WHERE collection = 'decisions' AND record_id = 'stage-1'"
            )

    def test_stage_advance_rejects_evidence_changed_after_pass_review(self):
        self.store.put_record(
            self.analyst, "evidence", "mutable-evidence", evidence_payload("mutable-evidence"),
            reason="Capture baseline evidence",
        )
        review = {
            "decision_type": "EVIDENCE_REVIEW",
            "outcome": "PASS",
            "subject_id": "claim:delivery-rate",
            "rationale": "Baseline evidence reviewed",
            "evidence_refs": ["mutable-evidence"],
            "reviewed_at": "2026-10-29T12:10:00+00:00",
        }
        self.store.record_decision(self.reviewer, "review-old", review)
        self.store.put_record(
            self.analyst, "evidence", "mutable-evidence",
            evidence_payload("mutable-evidence", evidence_label="observed", sample_size=11),
            expected_revision=1,
            reason="Correct source snapshot after review",
        )
        stage = {
            "decision_type": "STAGE_DECISION",
            "outcome": "ADVANCE",
            "subject_id": "case:stale-review",
            "rationale": "Try to advance on a stale review",
            "evidence_refs": ["mutable-evidence"],
            "reviewed_at": "2026-10-29T12:20:00+00:00",
            "stop_condition": "Stop on negative contribution",
            "rollback_plan": "Return stage to HOLD",
        }
        with self.assertRaisesRegex(ValueError, "current PASS review"):
            self.store.record_decision(self.approver, "stage-stale", stage)

        refreshed_review = dict(review)
        refreshed_review["rationale"] = "Corrected evidence revision reviewed"
        refreshed_review["reviewed_at"] = "2026-10-29T12:25:00+00:00"
        self.store.record_decision(self.reviewer, "review-new", refreshed_review)
        approved = self.store.record_decision(self.approver, "stage-fresh", stage)
        self.assertEqual(approved["payload"]["outcome"], "ADVANCE")

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
            {"sha256": "a" * 64}, reason="Register artifact",
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
