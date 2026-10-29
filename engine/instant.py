"""Instant event rules and an append-only, idempotent JSONL journal."""
from __future__ import annotations

from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
from threading import RLock
from typing import Any, Iterable
import json

PRIORITIES = {"LOW", "MEDIUM", "HIGH", "CRITICAL"}
EVENT_STATES = {"OPEN", "ACKNOWLEDGED", "RESOLVED", "DISMISSED"}


class IdempotencyConflict(ValueError):
    """Raised when an idempotency key is reused for a different semantic event."""


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")


def event_fingerprint(event: dict[str, Any]) -> str:
    stable = {k: v for k, v in event.items() if k not in {"created_at", "observed_at", "event_id"}}
    return sha256(_canonical(stable)).hexdigest()


def validate_event(event: dict[str, Any]) -> list[str]:
    if not isinstance(event, dict):
        return ["event must be an object"]
    errors: list[str] = []
    for field in ("event_id", "idempotency_key", "event_type", "priority", "subject_id", "observed_at", "summary", "recommended_action", "trigger_rule", "action_kind", "state", "created_at"):
        if not isinstance(event.get(field), str) or not event[field].strip():
            errors.append(f"{field} is required")
    if not isinstance(event.get("priority"), str) or event["priority"] not in PRIORITIES:
        errors.append(f"priority must be one of {sorted(PRIORITIES)}")
    if not isinstance(event.get("state"), str) or event["state"] not in EVENT_STATES:
        errors.append(f"state must be one of {sorted(EVENT_STATES)}")
    for field in ("source_refs", "evidence_refs", "tags", "invariants", "recovery_actions"):
        value = event.get(field, [])
        if not isinstance(value, list):
            errors.append(f"{field} must be an array")
        elif any(not isinstance(item, str) or not item.strip() for item in value):
            errors.append(f"every item in {field} must be a non-empty string")
    for field in ("context", "observations", "state_delta", "propagation"):
        if not isinstance(event.get(field), dict):
            errors.append(f"{field} must be an object")
    if isinstance(event.get("state_delta"), dict) and event["state_delta"].get("to") != event.get("state"):
        errors.append("state_delta.to must match the current event state")
    if not isinstance(event.get("action_kind"), str) or event["action_kind"] not in {"RECOMMENDATION_ONLY", "STATE_TRANSITION"}:
        errors.append("action_kind must be RECOMMENDATION_ONLY or STATE_TRANSITION")
    if isinstance(event.get("context"), dict):
        if event["context"].get("subject_id") != event.get("subject_id"):
            errors.append("context.subject_id must match subject_id")
        if not isinstance(event["context"].get("snapshot_hash"), str) or not event["context"]["snapshot_hash"].strip():
            errors.append("context.snapshot_hash is required")
    if isinstance(event.get("propagation"), dict) and event["propagation"].get("mode") != "LOCAL_ONLY":
        errors.append("this prototype only supports LOCAL_ONLY propagation")
    try:
        _canonical(event)
    except (TypeError, ValueError):
        errors.append("event must be JSON serializable without NaN/Infinity")
    for field in ("observed_at", "created_at"):
        value = event.get(field)
        if isinstance(value, str):
            try:
                parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
            except ValueError:
                errors.append(f"{field} must be an ISO-8601 datetime")
                continue
            if parsed.tzinfo is None:
                errors.append(f"{field} must include a timezone")
    return errors


def _event(
    *,
    event_type: str,
    priority: str,
    subject_id: str,
    observed_at: str,
    summary: str,
    recommended_action: str,
    snapshot_hash: str,
    source_refs: list[str] | None = None,
    evidence_refs: list[str] | None = None,
    tags: list[str] | None = None,
) -> dict[str, Any]:
    semantic = {
        "idempotency_key": f"{event_type}:{subject_id}:{snapshot_hash}",
        "event_type": event_type,
        "priority": priority,
        "subject_id": subject_id,
        "observed_at": observed_at,
        "summary": summary,
        "recommended_action": recommended_action,
        "action_kind": "RECOMMENDATION_ONLY",
        "trigger_rule": event_type,
        "context": {"subject_id": subject_id, "snapshot_hash": snapshot_hash, "mode": "LOCAL_ONLY"},
        "observations": {},
        "state_delta": {"from": None, "to": "OPEN"},
        "invariants": ["idempotent-key", "append-only-history", "no-automatic-financial-commitment"],
        "recovery_actions": ["ACKNOWLEDGED", "RESOLVED", "DISMISSED", "OPEN"],
        "propagation": {"mode": "LOCAL_ONLY", "downstream_refs": []},
        "state": "OPEN",
        "source_refs": source_refs or [],
        "evidence_refs": evidence_refs or [],
        "tags": tags or [],
        "snapshot_hash": snapshot_hash,
        "created_at": utc_now(),
    }
    semantic["event_id"] = sha256(semantic["idempotency_key"].encode("utf-8")).hexdigest()[:24]
    return semantic


def generate_instant_events(economics: dict[str, Any], *, subject_id: str, observed_at: str | None = None) -> list[dict[str, Any]]:
    """Generate actionable alerts from one evaluated snapshot, never from live integrations."""
    if not isinstance(subject_id, str) or not subject_id.strip():
        raise ValueError("subject_id is required")
    timestamp = observed_at or utc_now()
    try:
        parsed = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
    except (AttributeError, ValueError) as exc:
        raise ValueError("observed_at must be ISO-8601") from exc
    if parsed.tzinfo is None:
        raise ValueError("observed_at must include a timezone")

    if not isinstance(economics, dict):
        raise ValueError("economics must be a mapping")
    for field in ("decision", "funnel", "economics_dzd", "data_quality"):
        if not isinstance(economics.get(field), dict):
            raise ValueError(f"economics[{field!r}] must be a mapping")
    stable_snapshot = {
        "decision": economics.get("decision"),
        "funnel": economics.get("funnel"),
        "economics_dzd": economics.get("economics_dzd"),
        "data_quality": economics.get("data_quality"),
    }
    snapshot_hash = sha256(_canonical(stable_snapshot)).hexdigest()
    funnel = economics.get("funnel", {})
    costs = economics.get("economics_dzd", {})
    quality = economics.get("data_quality", {})
    events: list[dict[str, Any]] = []

    if economics.get("decision", {}).get("status") in {"UNVERIFIED_ECONOMICS", "HIGH_OPERATIONAL_RISK"} or quality.get("grade") in {"UNKNOWN", "LOW"}:
        events.append(_event(
            event_type="EVIDENCE_GAP", priority="HIGH", subject_id=subject_id, observed_at=timestamp,
            summary="The current model depends on missing, stale, or low-coverage evidence.",
            recommended_action="Attach source-dated evidence for procurement, selling price, delivery, returns and advertising before treating modeled profit as actionable.",
            snapshot_hash=snapshot_hash, evidence_refs=[],
            tags=["evidence", str(quality.get("grade", "UNKNOWN"))],
        ))
    profit = costs.get("estimated_profit")
    if isinstance(profit, (int, float)) and profit < 0:
        events.append(_event(
            event_type="MODELLED_LOSS", priority="HIGH", subject_id=subject_id, observed_at=timestamp,
            summary="The current input scenario models a loss.",
            recommended_action="Check cost allocation, courier terms, returns and ad spend; do not scale based on this scenario.",
            snapshot_hash=snapshot_hash, tags=["economics", "downside"],
        ))
    if costs.get("break_even_possible_before_ads") is False:
        events.append(_event(
            event_type="NO_AD_BREAK_EVEN", priority="CRITICAL", subject_id=subject_id, observed_at=timestamp,
            summary="Contribution before ads does not cover fixed costs; reducing ad spend alone cannot reach break-even.",
            recommended_action="Rework price, procurement or fulfillment economics and rerun the model before any paid test.",
            snapshot_hash=snapshot_hash, tags=["break-even", "blocker"],
        ))
    delivery = funnel.get("delivery_rate")
    if isinstance(delivery, (int, float)) and delivery < 0.55:
        events.append(_event(
            event_type="DELIVERY_RATE_RISK", priority="HIGH", subject_id=subject_id, observed_at=timestamp,
            summary=f"Modeled delivery rate is {delivery:.1%}, below the 55% review threshold.",
            recommended_action="Validate the delivery cohort and courier fees by destination before approving more ad spend.",
            snapshot_hash=snapshot_hash, tags=["operations", "delivery"],
        ))
    returns = funnel.get("customer_return_rate")
    if isinstance(returns, (int, float)) and returns > 0.15:
        events.append(_event(
            event_type="RETURN_RATE_RISK", priority="HIGH", subject_id=subject_id, observed_at=timestamp,
            summary=f"Modeled customer return rate is {returns:.1%}, above the 15% review threshold.",
            recommended_action="Audit return reasons, product fit/quality and recovery value; rerun economics with observed cohorts.",
            snapshot_hash=snapshot_hash, tags=["operations", "returns"],
        ))
    if not events:
        events.append(_event(
            event_type="SNAPSHOT_REVIEWED", priority="LOW", subject_id=subject_id, observed_at=timestamp,
            summary="No configured threshold was breached in this input snapshot.",
            recommended_action="Keep the evidence and next review date current; this is not proof of profitability or readiness to scale.",
            snapshot_hash=snapshot_hash, tags=["review"],
        ))
    observed_values = {
        "decision_status": economics["decision"].get("status"),
        "data_quality_grade": quality.get("grade"),
        "data_quality_score": quality.get("score"),
        "provenance_coverage": quality.get("provenance_coverage"),
        "sample_size": quality.get("sample_size"),
        "data_age_days": quality.get("data_age_days"),
        "modeled_profit_dzd": costs.get("estimated_profit"),
        "contribution_before_ads_dzd": costs.get("contribution_before_ads"),
        "break_even_possible_before_ads": costs.get("break_even_possible_before_ads"),
        "delivery_rate": funnel.get("delivery_rate"),
        "customer_return_rate": funnel.get("customer_return_rate"),
    }
    trigger_rules = {
        "EVIDENCE_GAP": "decision_status in {UNVERIFIED_ECONOMICS, HIGH_OPERATIONAL_RISK} or data_quality_grade in {UNKNOWN, LOW}",
        "MODELLED_LOSS": "modeled_profit_dzd < 0",
        "NO_AD_BREAK_EVEN": "break_even_possible_before_ads is false",
        "DELIVERY_RATE_RISK": "delivery_rate < 0.55",
        "RETURN_RATE_RISK": "customer_return_rate > 0.15",
        "SNAPSHOT_REVIEWED": "no configured rule fired",
    }
    source_refs = sorted({detail.get("url") for detail in (quality.get("evidence_sources") or {}).values()
                          if isinstance(detail, dict) and isinstance(detail.get("url"), str) and detail["url"].startswith("https://")})
    evidence_refs = sorted((quality.get("evidence_sources") or {}).keys())
    for event in events:
        event["context"] = {"subject_id": subject_id, "snapshot_hash": snapshot_hash, "mode": "LOCAL_ECONOMICS_SNAPSHOT"}
        event["trigger_rule"] = trigger_rules.get(event["event_type"], event["event_type"])
        event["observations"] = {key: value for key, value in observed_values.items() if value is not None}
        event["source_refs"] = source_refs
        event["evidence_refs"] = evidence_refs
        event["state_delta"] = {"from": None, "to": event["state"]}
        errors = validate_event(event)
        if errors:
            raise ValueError(f"Generated event violates its contract: {errors}")
    return events


class JsonlEventJournal:
    """Append-only local journal with per-process locking and idempotency checks.

    This is a local prototype store. It is not a multi-host transactional database;
    production use needs a transactional store, access controls and backup/recovery.
    """
    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = RLock()

    def _read_unlocked(self) -> list[dict[str, Any]]:
        if not self.path.exists():
            return []
        events: list[dict[str, Any]] = []
        with self.path.open("r", encoding="utf-8") as file:
            for line_number, line in enumerate(file, 1):
                if not line.strip():
                    continue
                try:
                    event = json.loads(line)
                except json.JSONDecodeError as exc:
                    raise ValueError(f"Corrupt event journal at line {line_number}") from exc
                errors = validate_event(event)
                if errors:
                    raise ValueError(f"Invalid event journal record at line {line_number}: {errors}")
                events.append(event)
        return events

    def list_events(self, *, states: Iterable[str] | None = None, include_history: bool = False) -> list[dict[str, Any]]:
        with self._lock:
            records = self._read_unlocked()
        if include_history:
            events = records
        else:
            events_by_id = {event["event_id"]: dict(event) for event in records if event["event_type"] != "EVENT_STATE_TRANSITION"}
            for transition in records:
                if transition["event_type"] != "EVENT_STATE_TRANSITION":
                    continue
                current = events_by_id.get(transition.get("previous_event_id"))
                if current is not None:
                    current["state"] = transition.get("new_state", transition["state"])
                    current["updated_at"] = transition["created_at"]
                    current["last_transition_id"] = transition["event_id"]
            events = list(events_by_id.values())
        if states is None:
            requested = None
        else:
            if isinstance(states, (str, bytes)):
                raise ValueError("states must be an iterable of state names, not a single string")
            try:
                state_values = list(states)
            except TypeError as exc:
                raise ValueError("states must be an iterable of state names") from exc
            if any(not isinstance(value, str) for value in state_values):
                raise ValueError("every requested state must be a string")
            requested = set(state_values)
            if not requested.issubset(EVENT_STATES):
                raise ValueError(f"states must be drawn from {sorted(EVENT_STATES)}")
        return [event for event in events if requested is None or event["state"] in requested]

    def append(self, event: dict[str, Any]) -> dict[str, Any]:
        errors = validate_event(event)
        if errors:
            raise ValueError(f"Event contract failed: {errors}")
        with self._lock:
            current = self._read_unlocked()
            for existing in current:
                if existing["idempotency_key"] == event["idempotency_key"]:
                    if event_fingerprint(existing) == event_fingerprint(event):
                        return {"event": existing, "inserted": False, "reason": "IDEMPOTENT_REPLAY"}
                    raise IdempotencyConflict("idempotency_key already exists with a different semantic event")
                if existing["event_id"] == event["event_id"]:
                    if event_fingerprint(existing) == event_fingerprint(event):
                        return {"event": existing, "inserted": False, "reason": "EVENT_ID_REPLAY"}
                    raise IdempotencyConflict("event_id already exists with different content")
            with self.path.open("a", encoding="utf-8", newline="\n") as file:
                file.write(json.dumps(event, ensure_ascii=False, sort_keys=True, allow_nan=False) + "\n")
                file.flush()
                import os
                os.fsync(file.fileno())
            return {"event": event, "inserted": True, "reason": "APPENDED"}

    def transition(self, event_id: str, new_state: str, *, actor: str, reason: str) -> dict[str, Any]:
        """Append a state-transition event instead of rewriting history."""
        if not isinstance(new_state, str) or new_state not in EVENT_STATES:
            raise ValueError(f"new_state must be one of {sorted(EVENT_STATES)}")
        if not isinstance(actor, str) or not actor.strip() or not isinstance(reason, str) or not reason.strip():
            raise ValueError("actor and reason must be non-empty strings")
        current = next((e for e in self.list_events() if e["event_id"] == event_id), None)
        if current is None:
            raise KeyError(f"Unknown event_id: {event_id}")
        if current["state"] == new_state:
            return {"transition": None, "inserted": False, "reason": "ALREADY_IN_STATE", "prior_state": current["state"], "new_state": new_state}
        transition_key = f"transition:{event_id}:{current.get('last_transition_id', 'root')}:{current['state']}:{new_state}:{actor}:{reason}"
        transition_hash = sha256(transition_key.encode("utf-8")).hexdigest()
        transition = _event(
            event_type="EVENT_STATE_TRANSITION", priority=current["priority"],
            subject_id=current["subject_id"], observed_at=utc_now(),
            summary=f"Event {event_id} state changed {current['state']} → {new_state}.",
            recommended_action=f"Transition recorded by {actor}: {reason}",
            snapshot_hash=transition_hash, source_refs=[f"event://{event_id}"],
            evidence_refs=[], tags=["audit", current["state"], new_state],
        )
        transition["idempotency_key"] = transition_key
        transition["event_id"] = sha256(transition_key.encode("utf-8")).hexdigest()[:24]
        transition["previous_event_id"] = event_id
        transition["actor"] = actor
        transition["new_state"] = new_state
        transition["state"] = new_state
        transition["action_kind"] = "STATE_TRANSITION"
        transition["state_delta"] = {"from": current["state"], "to": new_state}
        transition["context"] = {"subject_id": current["subject_id"], "snapshot_hash": current.get("snapshot_hash"), "mode": "LOCAL_EVENT_TRANSITION", "previous_event_id": event_id}
        transition["observations"] = {"actor": actor, "reason": reason}
        transition["invariants"] = ["append-only-history", "actor-and-reason-required"]
        transition["recovery_actions"] = ["OPEN", "ACKNOWLEDGED", "RESOLVED", "DISMISSED"]
        transition["propagation"] = {"mode": "LOCAL_ONLY", "downstream_refs": [f"event://{event_id}"]}
        appended = self.append(transition)
        return {"transition": appended["event"], "inserted": appended["inserted"], "prior_state": current["state"], "new_state": new_state}
