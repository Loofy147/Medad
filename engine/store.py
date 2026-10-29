"""Transactional local storage contract and reviewed-decision audit trail.

Authentication is intentionally outside this module. Only a trusted adapter that has
verified an identity provider's result should construct/pass an Actor. SQLiteStore
enforces the supplied role claims, optimistic revisions, and audit recording; it does
not establish that those claims are authentic.
"""
from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
from threading import RLock
from typing import Any, Iterator, Protocol
import json
import sqlite3
import uuid

try:
    from decision_kernel import validate_evidence_record
    from workflow import validate_decision_run_report
except ModuleNotFoundError:  # support both engine-directory CLI and package imports
    from .decision_kernel import validate_evidence_record
    from .workflow import validate_decision_run_report


STORE_SCHEMA_VERSION = 1
RECORD_COLLECTIONS = frozenset({"evidence", "runs", "tasks", "artifacts"})
DECISION_TYPES = frozenset({"EVIDENCE_REVIEW", "STAGE_DECISION", "RISK_ACCEPTANCE"})
DECISION_FIELDS = frozenset({
    "decision_type", "outcome", "subject_id", "rationale", "evidence_refs",
    "reviewed_at", "stop_condition", "rollback_plan", "accepted_risks",
})
ROLE_NAMES = frozenset({"reader", "analyst", "reviewer", "approver", "auditor", "admin"})


class StoreError(RuntimeError):
    """Base class for store operations that cannot be completed."""


class AuthorizationError(StoreError):
    """Raised when the policy denies an operation."""


class StoreConflict(StoreError):
    """Raised for stale revisions, duplicate IDs, or identity conflicts."""


@dataclass(frozen=True)
class Actor:
    """Identity and role claims supplied by a trusted authentication adapter."""

    subject_id: str
    issuer: str
    roles: tuple[str, ...]
    authenticated_at: str
    authn_method: str

    def __post_init__(self) -> None:
        for name in ("subject_id", "issuer", "authenticated_at", "authn_method"):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"actor.{name} must be a non-empty string")
        if not isinstance(self.roles, tuple) or any(not isinstance(role, str) for role in self.roles):
            raise ValueError("actor.roles must be a tuple of role strings")
        unknown = sorted(set(self.roles) - ROLE_NAMES)
        if unknown:
            raise ValueError(f"unknown actor roles: {unknown}")
        try:
            auth_time = datetime.fromisoformat(self.authenticated_at.replace("Z", "+00:00"))
        except ValueError as exc:
            raise ValueError("actor.authenticated_at must be an ISO-8601 timestamp") from exc
        if auth_time.tzinfo is None:
            raise ValueError("actor.authenticated_at must include a timezone")
        if auth_time > datetime.now(timezone.utc):
            raise ValueError("actor.authenticated_at cannot be in the future")


class AccessPolicy:
    """Default-deny role policy. Roles must come from an external trusted identity boundary."""

    _ROLE_ACTIONS = {
        "reader": frozenset({"read"}),
        "analyst": frozenset({
            "read", "write:evidence", "write:runs", "write:tasks", "write:artifacts",
            "commit:run_packet",
        }),
        "reviewer": frozenset({"read", "record:evidence_review"}),
        "approver": frozenset({"read", "record:stage_decision", "record:risk_acceptance"}),
        "auditor": frozenset({"read", "audit:read", "audit:verify"}),
        "admin": frozenset({"*"}),
    }

    def allows(self, actor: Actor, action: str) -> bool:
        return any(
            action in self._ROLE_ACTIONS[role] or "*" in self._ROLE_ACTIONS[role]
            for role in actor.roles
        )


class TransactionalStore(Protocol):
    """Backend-neutral contract for atomic writes with revisions and an audit trail."""

    def put_record(
        self, actor: Actor, collection: str, record_id: str, payload: dict[str, Any],
        *, expected_revision: int | None = None, reason: str,
    ) -> dict[str, Any]: ...

    def commit_run_packet(
        self, actor: Actor, report: dict[str, Any], evidence_records: list[dict[str, Any]],
        *, reason: str,
    ) -> dict[str, Any]: ...

    def commit_run_packet(
        self, actor: Actor, report: dict[str, Any], evidence_records: list[dict[str, Any]],
        *, reason: str,
    ) -> dict[str, Any]:
        """Atomically persist a validated analysis report and exactly the evidence it used."""
        if not isinstance(reason, str) or not reason.strip():
            raise ValueError("reason must be a non-empty string for the audit record")
        errors = validate_decision_run_report(report)
        if errors:
            raise ValueError(f"decision-run contract violations: {errors}")
        manifest = report["run_manifest"]
        run_id = self._validate_record_id(manifest["run_id"], "run_id")
        if not isinstance(evidence_records, list):
            raise ValueError("evidence_records must be an array")
        if any(not isinstance(item, dict) for item in evidence_records):
            raise ValueError("every evidence record must be an object")

        normalized: dict[str, tuple[dict[str, Any], str, str]] = {}
        for item in evidence_records:
            evidence_id = self._validate_record_id(item.get("evidence_id"), "evidence_id")
            if evidence_id in normalized:
                raise ValueError(f"duplicate evidence_id in run packet: {evidence_id!r}")
            _validate_collection_payload("evidence", evidence_id, item)
            payload_json = _canonical(item).decode("utf-8")
            content_hash = sha256(payload_json.encode("utf-8")).hexdigest()
            normalized[evidence_id] = (item, payload_json, content_hash)

        expected_manifest = [
            {"evidence_id": evidence_id, "content_hash": normalized[evidence_id][2]}
            for evidence_id in sorted(normalized)
        ]
        actual_manifest = report["provenance_summary"]["evidence_manifest"]
        if actual_manifest != expected_manifest:
            raise ValueError("supplied evidence records do not match the report evidence_manifest")
        if report["provenance_summary"]["evidence_record_count"] != len(normalized):
            raise ValueError("evidence record count does not match the supplied evidence records")

        run_payload_json = _canonical(report).decode("utf-8")
        run_content_hash = sha256(run_payload_json.encode("utf-8")).hexdigest()
        self._require_permission(
            actor, "commit:run_packet", "runs", run_id,
            reason=f"Commit decision run packet: {reason}",
        )

        with self._transaction() as connection:
            existing_run = connection.execute(
                "SELECT * FROM records WHERE collection = 'runs' AND record_id = ?",
                (run_id,),
            ).fetchone()
            if existing_run is not None:
                existing_report = json.loads(existing_run["payload_json"])
                existing_manifest = existing_report.get("run_manifest", {})
                same_identity = all(
                    existing_manifest.get(field) == manifest.get(field)
                    for field in ("run_id", "case_id", "input_hash", "report_hash", "code_revision")
                )
                if not same_identity:
                    raise StoreConflict(
                        f"run_id {run_id!r} already exists with different input/report identity"
                    )
                # created_at can differ on a replay; stable run identity is the validated input/report hash.
                # A prior run is idempotent only if all of its referenced evidence still exists unchanged.
                for evidence_id, (_, _, content_hash) in normalized.items():
                    current_evidence = connection.execute(
                        "SELECT content_hash FROM records WHERE collection = 'evidence' AND record_id = ?",
                        (evidence_id,),
                    ).fetchone()
                    if current_evidence is None or current_evidence["content_hash"] != content_hash:
                        raise StoreConflict(
                            f"existing run {run_id!r} has missing or changed evidence {evidence_id!r}"
                        )
                evidence_rows = [
                    self._record_from_row(connection.execute(
                        "SELECT * FROM records WHERE collection = 'evidence' AND record_id = ?",
                        (evidence_id,),
                    ).fetchone())
                    for evidence_id in sorted(normalized)
                ]
                return {
                    "run": self._record_from_row(existing_run),
                    "evidence": evidence_rows,
                    "inserted": False,
                    "reason": "IDEMPOTENT_REPLAY",
                }

            evidence_rows: list[dict[str, Any]] = []
            now = _utc_now()
            for evidence_id in sorted(normalized):
                payload, payload_json, content_hash = normalized[evidence_id]
                existing = connection.execute(
                    "SELECT * FROM records WHERE collection = 'evidence' AND record_id = ?",
                    (evidence_id,),
                ).fetchone()
                if existing is not None:
                    if existing["content_hash"] != content_hash:
                        raise StoreConflict(
                            f"evidence_id {evidence_id!r} already exists with different content; "
                            "a run packet cannot silently replace evidence"
                        )
                    evidence_rows.append(self._record_from_row(existing))
                    continue

                connection.execute(
                    "INSERT INTO records(collection, record_id, revision, payload_json, content_hash, "
                    "created_at, updated_at, updated_by) VALUES ('evidence', ?, 1, ?, ?, ?, ?, ?)",
                    (evidence_id, payload_json, content_hash, now, now, actor.subject_id),
                )
                self._append_audit(
                    connection, actor, "write:evidence", "evidence", evidence_id,
                    "CREATED", reason, {"revision": 1, "content_hash": content_hash, "via_run_id": run_id},
                )
                row = connection.execute(
                    "SELECT * FROM records WHERE collection = 'evidence' AND record_id = ?",
                    (evidence_id,),
                ).fetchone()
                evidence_rows.append(self._record_from_row(row))

            connection.execute(
                "INSERT INTO records(collection, record_id, revision, payload_json, content_hash, "
                "created_at, updated_at, updated_by) VALUES ('runs', ?, 1, ?, ?, ?, ?, ?)",
                (run_id, run_payload_json, run_content_hash, now, now, actor.subject_id),
            )
            self._append_audit(
                connection, actor, "commit:run_packet", "runs", run_id, "COMMITTED", reason,
                {
                    "case_id": manifest["case_id"],
                    "input_hash": manifest["input_hash"],
                    "report_hash": manifest["report_hash"],
                    "evidence_manifest": expected_manifest,
                    "evidence_count": len(expected_manifest),
                },
            )
            stored_run = connection.execute(
                "SELECT * FROM records WHERE collection = 'runs' AND record_id = ?",
                (run_id,),
            ).fetchone()
            return {
                "run": self._record_from_row(stored_run),
                "evidence": evidence_rows,
                "inserted": True,
                "reason": "COMMITTED",
            }

    def get_record(self, actor: Actor, collection: str, record_id: str) -> dict[str, Any] | None: ...

    def list_records(
        self, actor: Actor, collection: str, *, after_id: str | None = None, limit: int = 100,
    ) -> list[dict[str, Any]]: ...

    def record_decision(
        self, actor: Actor, decision_id: str, payload: dict[str, Any],
    ) -> dict[str, Any]: ...

    def audit_events(
        self, actor: Actor, *, after_sequence: int = 0, limit: int = 100,
    ) -> list[dict[str, Any]]: ...

    def verify_audit_chain(self, actor: Actor) -> dict[str, Any]: ...

    def close(self) -> None: ...


def _canonical(value: Any) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode("utf-8")


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="microseconds")


def _parse_aware_time(value: Any, field_name: str) -> datetime:
    if not isinstance(value, str):
        raise ValueError(f"{field_name} must be an ISO-8601 timestamp")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError(f"{field_name} must be an ISO-8601 timestamp") from exc
    if parsed.tzinfo is None:
        raise ValueError(f"{field_name} must include a timezone")
    return parsed.astimezone(timezone.utc)


def _validate_collection_payload(collection: str, record_id: str, payload: dict[str, Any]) -> None:
    """Validate established domain contracts before accepting durable records."""
    if collection == "evidence":
        if payload.get("evidence_id") != record_id:
            raise ValueError("evidence_id must match the storage record_id")
        errors = validate_evidence_record(payload)
        if errors:
            raise ValueError(f"evidence contract violations: {errors}")
        return

    if collection == "runs":
        manifest = payload.get("run_manifest")
        if not isinstance(manifest, dict) or manifest.get("run_id") != record_id:
            raise ValueError("run_manifest.run_id must match the storage record_id")
        errors = validate_decision_run_report(payload)
        if errors:
            raise ValueError(f"decision-run contract violations: {errors}")
        return

    if collection == "artifacts":
        artifact_ref = payload.get("artifact_ref")
        digest = payload.get("sha256", payload.get("artifact_sha256"))
        has_ref = isinstance(artifact_ref, str) and bool(artifact_ref.strip())
        if not has_ref and digest is None:
            raise ValueError("artifact_ref or sha256 is required to identify an artifact")
        if digest is not None and (
            not isinstance(digest, str) or len(digest) != 64
            or any(char not in "0123456789abcdef" for char in digest.lower())
        ):
            raise ValueError("artifact SHA-256 digest must be a 64-character hexadecimal string")


def _audit_body(row: sqlite3.Row | dict[str, Any]) -> dict[str, Any]:
    fields = (
        "event_id", "occurred_at", "actor_id", "actor_issuer", "actor_roles_json",
        "authenticated_at", "authn_method", "action", "resource_type", "resource_id",
        "outcome", "reason", "details_json", "previous_hash",
    )
    return {key: row[key] for key in fields}


def _audit_hash(body: dict[str, Any]) -> str:
    return sha256(_canonical(body)).hexdigest()


class SQLiteStore:
    """SQLite-backed transactional store for local/single-host use.

    Writes use BEGIN IMMEDIATE, optimistic revisions, and an audit event committed in
    the same transaction. The audit chain detects content modification and the local
    schema blocks normal UPDATE/DELETE statements, but a database owner can still
    disable triggers or replace the entire file. This is not a remote trust anchor.
    """

    def __init__(self, path: str | Path, *, policy: AccessPolicy | None = None):
        self.path = str(path)
        if self.path != ":memory:":
            Path(self.path).expanduser().resolve().parent.mkdir(parents=True, exist_ok=True)
        self.policy = policy or AccessPolicy()
        self._lock = RLock()
        self._closed = False
        self._connection = sqlite3.connect(
            self.path, timeout=10, isolation_level=None, check_same_thread=False
        )
        self._connection.row_factory = sqlite3.Row
        self._connection.execute("PRAGMA foreign_keys = ON")
        self._connection.execute("PRAGMA busy_timeout = 10000")
        if self.path != ":memory:":
            self._connection.execute("PRAGMA journal_mode = WAL")
            self._connection.execute("PRAGMA synchronous = FULL")
        self._migrate()

    @contextmanager
    def _transaction(self) -> Iterator[sqlite3.Connection]:
        with self._lock:
            if self._closed:
                raise StoreError("store is closed")
            self._connection.execute("BEGIN IMMEDIATE")
            try:
                yield self._connection
                self._connection.commit()
            except BaseException:
                self._connection.rollback()
                raise

    def _migrate(self) -> None:
        with self._transaction() as connection:
            connection.execute(
                "CREATE TABLE IF NOT EXISTS schema_migrations "
                "(version INTEGER PRIMARY KEY, applied_at TEXT NOT NULL)"
            )
            row = connection.execute("SELECT MAX(version) AS version FROM schema_migrations").fetchone()
            version = row["version"] or 0
            if version > STORE_SCHEMA_VERSION:
                raise StoreError(
                    f"database schema version {version} is newer than supported version {STORE_SCHEMA_VERSION}"
                )
            if version == 0:
                connection.execute(
                    "CREATE TABLE records ("
                    "collection TEXT NOT NULL CHECK(collection IN "
                    "('evidence','runs','tasks','artifacts','decisions')), "
                    "record_id TEXT NOT NULL, revision INTEGER NOT NULL CHECK(revision > 0), "
                    "payload_json TEXT NOT NULL, content_hash TEXT NOT NULL, "
                    "created_at TEXT NOT NULL, updated_at TEXT NOT NULL, updated_by TEXT NOT NULL, "
                    "PRIMARY KEY(collection, record_id))"
                )
                connection.execute(
                    "CREATE TABLE audit_events ("
                    "sequence INTEGER PRIMARY KEY AUTOINCREMENT, event_id TEXT NOT NULL UNIQUE, "
                    "occurred_at TEXT NOT NULL, actor_id TEXT NOT NULL, actor_issuer TEXT NOT NULL, "
                    "actor_roles_json TEXT NOT NULL, authenticated_at TEXT NOT NULL, authn_method TEXT NOT NULL, "
                    "action TEXT NOT NULL, resource_type TEXT NOT NULL, resource_id TEXT NOT NULL, "
                    "outcome TEXT NOT NULL, reason TEXT NOT NULL, details_json TEXT NOT NULL, "
                    "previous_hash TEXT NOT NULL, event_hash TEXT NOT NULL)"
                )
                connection.execute(
                    "CREATE TRIGGER audit_events_no_update BEFORE UPDATE ON audit_events "
                    "BEGIN SELECT RAISE(ABORT, 'audit events are append-only'); END"
                )
                connection.execute(
                    "CREATE TRIGGER audit_events_no_delete BEFORE DELETE ON audit_events "
                    "BEGIN SELECT RAISE(ABORT, 'audit events are append-only'); END"
                )
                connection.execute(
                    "CREATE TRIGGER decisions_records_no_update BEFORE UPDATE ON records "
                    "WHEN OLD.collection = 'decisions' "
                    "BEGIN SELECT RAISE(ABORT, 'decision records are append-only'); END"
                )
                connection.execute(
                    "CREATE TRIGGER decisions_records_no_delete BEFORE DELETE ON records "
                    "WHEN OLD.collection = 'decisions' "
                    "BEGIN SELECT RAISE(ABORT, 'decision records are append-only'); END"
                )
                connection.execute(
                    "INSERT INTO schema_migrations(version, applied_at) VALUES (?, ?)",
                    (1, _utc_now()),
                )

    def _require_permission(
        self, actor: Actor, action: str, resource_type: str, resource_id: str, *, reason: str
    ) -> None:
        if not isinstance(actor, Actor):
            raise AuthorizationError("operation requires an Actor produced by the trusted identity adapter")
        if self.policy.allows(actor, action):
            return
        # Persist the denial separately because the operation itself must roll back.
        with self._transaction() as connection:
            self._append_audit(
                connection, actor, action, resource_type, resource_id, "DENIED", reason,
                {"required_action": action},
            )
        raise AuthorizationError(f"actor {actor.subject_id!r} is not permitted to {action}")

    def _append_audit(
        self, connection: sqlite3.Connection, actor: Actor, action: str,
        resource_type: str, resource_id: str, outcome: str, reason: str,
        details: dict[str, Any],
    ) -> dict[str, Any]:
        previous = connection.execute(
            "SELECT event_hash FROM audit_events ORDER BY sequence DESC LIMIT 1"
        ).fetchone()
        body = {
            "event_id": uuid.uuid4().hex,
            "occurred_at": _utc_now(),
            "actor_id": actor.subject_id,
            "actor_issuer": actor.issuer,
            "actor_roles_json": _canonical(sorted(set(actor.roles))).decode("utf-8"),
            "authenticated_at": actor.authenticated_at,
            "authn_method": actor.authn_method,
            "action": action,
            "resource_type": resource_type,
            "resource_id": resource_id,
            "outcome": outcome,
            "reason": reason,
            "details_json": _canonical(details).decode("utf-8"),
            "previous_hash": previous["event_hash"] if previous else "",
        }
        event_hash = _audit_hash(body)
        connection.execute(
            "INSERT INTO audit_events(event_id, occurred_at, actor_id, actor_issuer, actor_roles_json, "
            "authenticated_at, authn_method, action, resource_type, resource_id, outcome, reason, "
            "details_json, previous_hash, event_hash) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                body["event_id"], body["occurred_at"], body["actor_id"], body["actor_issuer"],
                body["actor_roles_json"], body["authenticated_at"], body["authn_method"],
                body["action"], body["resource_type"], body["resource_id"], body["outcome"],
                body["reason"], body["details_json"], body["previous_hash"], event_hash,
            ),
        )
        return {**body, "details": details, "event_hash": event_hash}

    @staticmethod
    def _validate_record_id(record_id: Any, label: str = "record_id") -> str:
        if not isinstance(record_id, str) or not record_id.strip() or len(record_id) > 256:
            raise ValueError(f"{label} must be a non-empty string of at most 256 characters")
        return record_id

    @staticmethod
    def _record_from_row(row: sqlite3.Row) -> dict[str, Any]:
        return {
            "collection": row["collection"],
            "record_id": row["record_id"],
            "revision": row["revision"],
            "payload": json.loads(row["payload_json"]),
            "content_hash": row["content_hash"],
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
            "updated_by": row["updated_by"],
        }

    def put_record(
        self, actor: Actor, collection: str, record_id: str, payload: dict[str, Any],
        *, expected_revision: int | None = None, reason: str,
    ) -> dict[str, Any]:
        if collection not in RECORD_COLLECTIONS:
            raise ValueError(f"unsupported mutable collection: {collection!r}")
        record_id = self._validate_record_id(record_id)
        if not isinstance(reason, str) or not reason.strip():
            raise ValueError("reason must be a non-empty string for the audit record")
        if expected_revision is not None and (
            isinstance(expected_revision, bool) or not isinstance(expected_revision, int) or expected_revision < 0
        ):
            raise ValueError("expected_revision must be a non-negative integer when supplied")
        if not isinstance(payload, dict):
            raise ValueError("payload must be an object")
        try:
            payload_json = _canonical(payload).decode("utf-8")
        except (TypeError, ValueError) as exc:
            raise ValueError("payload must be JSON-serializable without NaN/Infinity") from exc
        payload_hash = sha256(payload_json.encode("utf-8")).hexdigest()
        _validate_collection_payload(collection, record_id, payload)
        self._require_permission(actor, f"write:{collection}", collection, record_id, reason=reason)

        with self._transaction() as connection:
            current = connection.execute(
                "SELECT * FROM records WHERE collection = ? AND record_id = ?",
                (collection, record_id),
            ).fetchone()
            if collection == "runs":
                for item in payload["provenance_summary"]["evidence_manifest"]:
                    referenced = connection.execute(
                        "SELECT content_hash FROM records WHERE collection = 'evidence' AND record_id = ?",
                        (item["evidence_id"],),
                    ).fetchone()
                    if referenced is None or referenced["content_hash"] != item["content_hash"]:
                        raise ValueError(
                            "run packet evidence is missing or changed; use commit_run_packet for atomic persistence"
                        )
            now = _utc_now()
            if current is None:
                if expected_revision not in (None, 0):
                    raise StoreConflict("cannot update a record that does not exist")
                connection.execute(
                    "INSERT INTO records(collection, record_id, revision, payload_json, content_hash, "
                    "created_at, updated_at, updated_by) VALUES (?, ?, 1, ?, ?, ?, ?, ?)",
                    (collection, record_id, payload_json, payload_hash, now, now, actor.subject_id),
                )
                outcome, revision, created_at = "CREATED", 1, now
            else:
                if expected_revision is None:
                    raise StoreConflict("expected_revision is required to update an existing record")
                if expected_revision != current["revision"]:
                    raise StoreConflict(
                        f"stale revision: expected {expected_revision}, current {current['revision']}"
                    )
                if current["content_hash"] == payload_hash:
                    return self._record_from_row(current)
                revision = current["revision"] + 1
                created_at = current["created_at"]
                connection.execute(
                    "UPDATE records SET revision = ?, payload_json = ?, content_hash = ?, "
                    "updated_at = ?, updated_by = ? WHERE collection = ? AND record_id = ?",
                    (revision, payload_json, payload_hash, now, actor.subject_id, collection, record_id),
                )
                outcome = "UPDATED"
            self._append_audit(
                connection, actor, f"write:{collection}", collection, record_id,
                outcome, reason, {"revision": revision, "content_hash": payload_hash},
            )
            row = connection.execute(
                "SELECT * FROM records WHERE collection = ? AND record_id = ?",
                (collection, record_id),
            ).fetchone()
            return self._record_from_row(row)

    def get_record(self, actor: Actor, collection: str, record_id: str) -> dict[str, Any] | None:
        if collection not in RECORD_COLLECTIONS | {"decisions"}:
            raise ValueError(f"unsupported collection: {collection!r}")
        record_id = self._validate_record_id(record_id)
        self._require_permission(actor, "read", collection, record_id, reason="read record")
        with self._lock:
            if self._closed:
                raise StoreError("store is closed")
            row = self._connection.execute(
                "SELECT * FROM records WHERE collection = ? AND record_id = ?",
                (collection, record_id),
            ).fetchone()
        return self._record_from_row(row) if row else None

    def list_records(
        self, actor: Actor, collection: str, *, after_id: str | None = None, limit: int = 100,
    ) -> list[dict[str, Any]]:
        if collection not in RECORD_COLLECTIONS | {"decisions"}:
            raise ValueError(f"unsupported collection: {collection!r}")
        if isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= 1000:
            raise ValueError("limit must be an integer between 1 and 1000")
        if after_id is not None:
            after_id = self._validate_record_id(after_id, "after_id")
        self._require_permission(actor, "read", collection, collection, reason="list records")
        with self._lock:
            if self._closed:
                raise StoreError("store is closed")
            if after_id is None:
                rows = self._connection.execute(
                    "SELECT * FROM records WHERE collection = ? ORDER BY record_id LIMIT ?",
                    (collection, limit),
                ).fetchall()
            else:
                rows = self._connection.execute(
                    "SELECT * FROM records WHERE collection = ? AND record_id > ? "
                    "ORDER BY record_id LIMIT ?",
                    (collection, after_id, limit),
                ).fetchall()
        return [self._record_from_row(row) for row in rows]

    def record_decision(
        self, actor: Actor, decision_id: str, payload: dict[str, Any],
    ) -> dict[str, Any]:
        decision_id = self._validate_record_id(decision_id, "decision_id")
        if not isinstance(payload, dict):
            raise ValueError("decision payload must be an object")
        unknown = sorted(set(payload) - DECISION_FIELDS)
        if unknown:
            raise ValueError(f"unknown decision fields: {unknown}")
        decision_type = payload.get("decision_type")
        if decision_type not in DECISION_TYPES:
            raise ValueError(f"decision_type must be one of {sorted(DECISION_TYPES)}")
        action = {
            "EVIDENCE_REVIEW": "record:evidence_review",
            "STAGE_DECISION": "record:stage_decision",
            "RISK_ACCEPTANCE": "record:risk_acceptance",
        }[decision_type]
        rationale = payload.get("rationale")
        if not isinstance(rationale, str) or not rationale.strip():
            raise ValueError("rationale is required")
        subject_id = payload.get("subject_id")
        if not isinstance(subject_id, str) or not subject_id.strip():
            raise ValueError("subject_id is required")
        evidence_refs = payload.get("evidence_refs")
        if (
            not isinstance(evidence_refs, list) or not evidence_refs
            or any(not isinstance(item, str) or not item.strip() for item in evidence_refs)
            or len(set(evidence_refs)) != len(evidence_refs)
        ):
            raise ValueError("evidence_refs must be a non-empty array of unique evidence record IDs")
        reviewed_at = _parse_aware_time(payload.get("reviewed_at"), "reviewed_at")
        if reviewed_at > datetime.now(timezone.utc):
            raise ValueError("reviewed_at cannot be in the future")
        outcome = payload.get("outcome")
        allowed_outcomes = {
            "EVIDENCE_REVIEW": {"PASS", "FAIL", "UNKNOWN"},
            "STAGE_DECISION": {"ADVANCE", "HOLD", "REJECT"},
            "RISK_ACCEPTANCE": {"ACCEPT", "DECLINE"},
        }[decision_type]
        if outcome not in allowed_outcomes:
            raise ValueError(f"outcome for {decision_type} must be one of {sorted(allowed_outcomes)}")
        if decision_type == "STAGE_DECISION" and outcome == "ADVANCE":
            for field_name in ("stop_condition", "rollback_plan"):
                if not isinstance(payload.get(field_name), str) or not payload[field_name].strip():
                    raise ValueError(f"{field_name} is required for ADVANCE")
        if decision_type == "RISK_ACCEPTANCE" and outcome == "ACCEPT":
            risks = payload.get("accepted_risks")
            if not isinstance(risks, list) or not risks or any(
                not isinstance(item, str) or not item.strip() for item in risks
            ):
                raise ValueError("accepted_risks must be a non-empty array for ACCEPT")
            for field_name in ("stop_condition", "rollback_plan"):
                if not isinstance(payload.get(field_name), str) or not payload[field_name].strip():
                    raise ValueError(f"{field_name} is required for RISK_ACCEPTANCE ACCEPT")
        try:
            _canonical(payload)
        except (TypeError, ValueError) as exc:
            raise ValueError("decision must be JSON-serializable without NaN/Infinity") from exc
        self._require_permission(
            actor, action, "decisions", decision_id, reason=f"{decision_type}: {rationale}"
        )

        with self._transaction() as connection:
            existing = connection.execute(
                "SELECT 1 FROM records WHERE collection = 'decisions' AND record_id = ?",
                (decision_id,),
            ).fetchone()
            if existing:
                raise StoreConflict(f"decision_id {decision_id!r} already exists; decisions are append-only")

            evidence_rows: dict[str, sqlite3.Row] = {}
            for evidence_id in evidence_refs:
                row = connection.execute(
                    "SELECT revision, content_hash FROM records "
                    "WHERE collection = 'evidence' AND record_id = ?",
                    (evidence_id,),
                ).fetchone()
                if row is not None:
                    evidence_rows[evidence_id] = row
            missing_refs = [evidence_id for evidence_id in evidence_refs if evidence_id not in evidence_rows]
            if missing_refs:
                raise ValueError(f"decision references missing evidence records: {missing_refs}")
            evidence_snapshots = [
                {
                    "evidence_id": evidence_id,
                    "revision": evidence_rows[evidence_id]["revision"],
                    "content_hash": evidence_rows[evidence_id]["content_hash"],
                }
                for evidence_id in evidence_refs
            ]

            if decision_type == "STAGE_DECISION" and outcome == "ADVANCE":
                existing_decisions = connection.execute(
                    "SELECT payload_json FROM records WHERE collection = 'decisions'"
                ).fetchall()
                reviewed_at_matches = []
                for snapshot in evidence_snapshots:
                    current_pass_review = None
                    for decision_row in existing_decisions:
                        try:
                            previous_decision = json.loads(decision_row["payload_json"])
                        except json.JSONDecodeError:
                            continue
                        if (
                            previous_decision.get("decision_type") != "EVIDENCE_REVIEW"
                            or previous_decision.get("outcome") != "PASS"
                        ):
                            continue
                        if snapshot in previous_decision.get("evidence_snapshots", []):
                            previous_reviewed_at = _parse_aware_time(
                                previous_decision.get("reviewed_at"), "reviewed_at"
                            )
                            if current_pass_review is None or previous_reviewed_at > current_pass_review:
                                current_pass_review = previous_reviewed_at
                    if current_pass_review is None:
                        raise ValueError(
                            "ADVANCE requires a current PASS review for each evidence record; "
                            "the review is missing or refers to an older evidence revision"
                        )
                    if reviewed_at < current_pass_review:
                        raise ValueError("stage decision reviewed_at must not precede the current PASS review")
                    reviewed_at_matches.append(current_pass_review.isoformat())

            stored_payload = {**payload, "evidence_snapshots": evidence_snapshots}
            payload_json = _canonical(stored_payload).decode("utf-8")
            content_hash = sha256(payload_json.encode("utf-8")).hexdigest()
            now = _utc_now()
            connection.execute(
                "INSERT INTO records(collection, record_id, revision, payload_json, content_hash, "
                "created_at, updated_at, updated_by) VALUES ('decisions', ?, 1, ?, ?, ?, ?, ?)",
                (decision_id, payload_json, content_hash, now, now, actor.subject_id),
            )
            self._append_audit(
                connection, actor, action, "decisions", decision_id, "RECORDED",
                rationale, {
                    "decision_type": decision_type,
                    "outcome": outcome,
                    "evidence_refs": evidence_refs,
                    "evidence_snapshots": evidence_snapshots,
                    "content_hash": content_hash,
                },
            )
            row = connection.execute(
                "SELECT * FROM records WHERE collection = 'decisions' AND record_id = ?",
                (decision_id,),
            ).fetchone()
            return self._record_from_row(row)

    def audit_events(
        self, actor: Actor, *, after_sequence: int = 0, limit: int = 100,
    ) -> list[dict[str, Any]]:
        if isinstance(after_sequence, bool) or not isinstance(after_sequence, int) or after_sequence < 0:
            raise ValueError("after_sequence must be a non-negative integer")
        if isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= 1000:
            raise ValueError("limit must be an integer between 1 and 1000")
        self._require_permission(actor, "audit:read", "audit_events", str(after_sequence), reason="read audit")
        with self._lock:
            if self._closed:
                raise StoreError("store is closed")
            rows = self._connection.execute(
                "SELECT * FROM audit_events WHERE sequence > ? ORDER BY sequence LIMIT ?",
                (after_sequence, limit),
            ).fetchall()
        events = []
        for row in rows:
            body = _audit_body(row)
            actor_roles = json.loads(body.pop("actor_roles_json"))
            events.append({
                **body,
                "actor_roles": actor_roles,
                "sequence": row["sequence"],
                "details": json.loads(row["details_json"]),
                "event_hash": row["event_hash"],
            })
        return events

    def verify_audit_chain(self, actor: Actor) -> dict[str, Any]:
        self._require_permission(actor, "audit:verify", "audit_events", "chain", reason="verify audit chain")
        with self._lock:
            if self._closed:
                raise StoreError("store is closed")
            rows = self._connection.execute(
                "SELECT * FROM audit_events ORDER BY sequence"
            ).fetchall()
        previous_hash = ""
        for row in rows:
            if row["previous_hash"] != previous_hash:
                return {
                    "valid": False, "checked_events": row["sequence"] - 1,
                    "failing_sequence": row["sequence"], "reason": "PREVIOUS_HASH_MISMATCH",
                }
            if _audit_hash(_audit_body(row)) != row["event_hash"]:
                return {
                    "valid": False, "checked_events": row["sequence"] - 1,
                    "failing_sequence": row["sequence"], "reason": "EVENT_HASH_MISMATCH",
                }
            try:
                json.loads(row["details_json"])
            except json.JSONDecodeError:
                return {
                    "valid": False, "checked_events": row["sequence"] - 1,
                    "failing_sequence": row["sequence"], "reason": "INVALID_DETAILS_JSON",
                }
            previous_hash = row["event_hash"]
        return {"valid": True, "checked_events": len(rows), "final_hash": previous_hash}

    def close(self) -> None:
        with self._lock:
            if not self._closed:
                self._connection.close()
                self._closed = True
