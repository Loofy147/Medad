"""Append-only local journal for reproducible decision-run packets.

This is a local development audit log, not a transactional or tamper-proof production store.
"""
from __future__ import annotations

from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
from threading import RLock
from typing import Any
import json

JOURNAL_SCHEMA_VERSION = "medad.run-journal.v1"


class RunIdConflict(ValueError):
    """Raised when a run_id is reused with different input or report identity."""


def _canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _record_hash(record: dict[str, Any]) -> str:
    unsigned = {key: value for key, value in record.items() if key != "record_hash"}
    return sha256(_canonical(unsigned)).hexdigest()


def _validate_report(report: Any) -> dict[str, Any]:
    if not isinstance(report, dict):
        raise ValueError("report must be an object")
    if report.get("schema_version") != "medad.decision-run.v1":
        raise ValueError("report schema_version must be medad.decision-run.v1")
    manifest = report.get("run_manifest")
    decision = report.get("decision")
    if not isinstance(manifest, dict) or not isinstance(decision, dict):
        raise ValueError("report requires run_manifest and decision objects")
    for field in ("run_id", "case_id", "input_hash", "report_hash"):
        value = manifest.get(field)
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"report run_manifest.{field} is required")
    if manifest.get("mode") != "ANALYSIS_ONLY_NO_EXTERNAL_SIDE_EFFECTS":
        raise ValueError("only analysis-only decision reports can be journaled")
    if decision.get("authorization_granted") is not False:
        raise ValueError("journal will not accept a report that claims authorization")
    try:
        _canonical(report)
    except (TypeError, ValueError) as exc:
        raise ValueError("report must be JSON-serializable without NaN/Infinity") from exc
    return report


class DecisionRunJournal:
    """Per-process locked append-only JSONL store with run ID conflict detection."""
    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = RLock()

    def _read_unlocked(self) -> list[dict[str, Any]]:
        if not self.path.exists():
            return []
        records: list[dict[str, Any]] = []
        with self.path.open("r", encoding="utf-8") as file:
            for line_number, line in enumerate(file, 1):
                if not line.strip():
                    continue
                try:
                    record = json.loads(line)
                except json.JSONDecodeError as exc:
                    raise ValueError(f"Corrupt run journal JSON at line {line_number}") from exc
                if not isinstance(record, dict) or record.get("journal_schema_version") != JOURNAL_SCHEMA_VERSION:
                    raise ValueError(f"Invalid run journal schema at line {line_number}")
                expected = record.get("record_hash")
                if not isinstance(expected, str) or expected != _record_hash(record):
                    raise ValueError(f"Run journal checksum mismatch at line {line_number}")
                _validate_report(record.get("report"))
                manifest = record["report"]["run_manifest"]
                if (
                    record.get("run_id") != manifest["run_id"]
                    or record.get("case_id") != manifest["case_id"]
                    or record.get("input_hash") != manifest["input_hash"]
                    or record.get("report_hash") != manifest["report_hash"]
                ):
                    raise ValueError(f"Run journal envelope mismatch at line {line_number}")
                records.append(record)
        return records

    def list_runs(self, *, case_id: str | None = None) -> list[dict[str, Any]]:
        with self._lock:
            records = self._read_unlocked()
        if case_id is not None and (not isinstance(case_id, str) or not case_id.strip()):
            raise ValueError("case_id filter must be a non-empty string")
        return [record for record in records if case_id is None or record["case_id"] == case_id]

    def get(self, run_id: str) -> dict[str, Any] | None:
        if not isinstance(run_id, str) or not run_id.strip():
            raise ValueError("run_id must be a non-empty string")
        with self._lock:
            records = self._read_unlocked()
        return next((record for record in records if record["run_id"] == run_id), None)

    def append(self, report: dict[str, Any]) -> dict[str, Any]:
        _validate_report(report)
        manifest = report["run_manifest"]
        run_id = manifest["run_id"]
        with self._lock:
            records = self._read_unlocked()
            for record in records:
                if record["run_id"] != run_id:
                    continue
                if (
                    record["input_hash"] == manifest["input_hash"]
                    and record["report_hash"] == manifest["report_hash"]
                    and record["case_id"] == manifest["case_id"]
                ):
                    return {"record": record, "inserted": False, "reason": "IDEMPOTENT_REPLAY"}
                raise RunIdConflict(
                    f"run_id {run_id!r} already exists with a different input/report identity; use a new run_id"
                )

            record = {
                "journal_schema_version": JOURNAL_SCHEMA_VERSION,
                "recorded_at": _utc_now(),
                "run_id": run_id,
                "case_id": manifest["case_id"],
                "input_hash": manifest["input_hash"],
                "report_hash": manifest["report_hash"],
                "report": report,
            }
            record["record_hash"] = _record_hash(record)
            line = json.dumps(record, ensure_ascii=False, sort_keys=True, allow_nan=False) + "\n"
            with self.path.open("a", encoding="utf-8", newline="\n") as file:
                file.write(line)
                file.flush()
                import os
                os.fsync(file.fileno())
            return {"record": record, "inserted": True, "reason": "APPENDED"}
