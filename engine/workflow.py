"""Orchestrate Medad's decision engines into one reproducible analysis packet."""
from __future__ import annotations

from dataclasses import asdict, fields
from datetime import datetime, timezone
from hashlib import sha256
from typing import Any
import json

from decision_kernel import assess_claim, assess_gates, validate_evidence_record
from engine import Inputs, evaluate
from instant import generate_instant_events
from opportunity import assess_candidate
from sensitivity import sensitivity_report

SCHEMA_VERSION = "medad.decision-run.v1"
REQUIRED_INPUT_FIELDS = {
    "product_name", "selling_price", "purchase_cost", "packaging_cost",
    "outbound_delivery_cost", "delivery_fee_collected", "failed_delivery_return_cost",
    "return_shipping_cost", "return_handling_cost", "ad_spend", "placed_orders",
    "delivery_rate", "customer_return_rate", "inventory_recovery_rate",
    "other_variable_cost_per_retained_order", "other_fixed_costs",
}


def _canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")


def _aware_timestamp(value: Any, name: str) -> datetime:
    if not isinstance(value, str):
        raise ValueError(f"{name} must be an ISO-8601 timestamp")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError(f"{name} must be an ISO-8601 timestamp") from exc
    if parsed.tzinfo is None:
        raise ValueError(f"{name} must include a timezone")
    return parsed


def _parse_inputs(value: Any) -> Inputs:
    if not isinstance(value, dict):
        raise ValueError("inputs must be an object")
    allowed = {field.name for field in fields(Inputs)}
    unknown = sorted(set(value) - allowed)
    if unknown:
        raise ValueError(f"unknown input fields: {unknown}")
    missing = sorted(REQUIRED_INPUT_FIELDS - set(value))
    if missing:
        raise ValueError(f"missing explicit economics inputs: {missing}")
    return Inputs(**value)


def _validate_records(records: Any, name: str) -> list[dict[str, Any]]:
    if not isinstance(records, list):
        raise ValueError(f"{name} must be an array")
    if any(not isinstance(record, dict) for record in records):
        raise ValueError(f"every record in {name} must be an object")
    return records


def build_decision_run(payload: dict[str, Any]) -> dict[str, Any]:
    """Return an analysis packet. It makes no external changes and never authorizes spend."""
    if not isinstance(payload, dict):
        raise ValueError("run payload must be an object")
    allowed_top_level = {"schema_version", "run_id", "case_id", "observed_at", "code_revision", "inputs", "evidence_records", "claims", "gates", "candidate", "options", "subject_id"}
    unknown_top_level = sorted(set(payload) - allowed_top_level)
    if unknown_top_level:
        raise ValueError(f"unknown run payload fields: {unknown_top_level}")
    run_id = payload.get("run_id")
    case_id = payload.get("case_id")
    if not isinstance(run_id, str) or not run_id.strip():
        raise ValueError("run_id is required")
    if not isinstance(case_id, str) or not case_id.strip():
        raise ValueError("case_id is required")
    if payload.get("schema_version") != SCHEMA_VERSION:
        raise ValueError(f"schema_version must be explicitly set to {SCHEMA_VERSION}")

    now = datetime.now(timezone.utc)
    observed_at = payload.get("observed_at")
    observed_dt = _aware_timestamp(observed_at, "observed_at")
    if observed_dt > now:
        raise ValueError("observed_at cannot be in the future")
    created_at = now.isoformat(timespec="seconds")

    inputs = _parse_inputs(payload.get("inputs"))
    evidence_records = _validate_records(payload.get("evidence_records", []), "evidence_records")
    evidence_ids: set[str] = set()
    for index, record in enumerate(evidence_records):
        record_id = record.get("evidence_id")
        if not isinstance(record_id, str) or not record_id.strip() or record_id in evidence_ids:
            raise ValueError(f"evidence_records[{index}] has a missing or duplicate evidence_id")
        errors = validate_evidence_record(record)
        if errors:
            raise ValueError(f"evidence_records[{index}] violates the evidence contract: {errors}")
        evidence_ids.add(record_id)
    claims = _validate_records(payload.get("claims", []), "claims")
    gates = _validate_records(payload.get("gates", []), "gates")
    candidate = payload.get("candidate")
    if candidate is not None and not isinstance(candidate, dict):
        raise ValueError("candidate must be an object when supplied")

    options = payload.get("options", {})
    if not isinstance(options, dict):
        raise ValueError("options must be an object")
    sensitivity_enabled = options.get("sensitivity", False)
    if not isinstance(sensitivity_enabled, bool):
        raise ValueError("options.sensitivity must be a boolean")
    subject_id = payload.get("subject_id", case_id)
    if not isinstance(subject_id, str) or not subject_id.strip():
        raise ValueError("subject_id must be a non-empty string")
    code_revision = payload.get("code_revision")
    if not isinstance(code_revision, str) or not code_revision.strip():
        raise ValueError("code_revision is required for a reproducible decision run")
    unknown_options = sorted(set(options) - {"sensitivity"})
    if unknown_options:
        raise ValueError(f"unknown run options: {unknown_options}")

    inputs_data = asdict(inputs)
    run_basis = {
        "schema_version": SCHEMA_VERSION,
        "run_id": run_id,
        "case_id": case_id,
        "observed_at": observed_dt.isoformat(),
        "inputs": inputs_data,
        "evidence_records": evidence_records,
        "claims": claims,
        "gates": gates,
        "candidate": candidate,
        "options": options,
        "code_revision": code_revision,
    }
    input_hash = sha256(_canonical(run_basis)).hexdigest()

    economics = evaluate(inputs)
    claim_results = [assess_claim(claim, evidence_records) for claim in claims]
    gate_result = assess_gates(gates, evidence_records=evidence_records)
    opportunity_result = assess_candidate(candidate) if candidate is not None else None
    sensitivity = sensitivity_report(inputs) if sensitivity_enabled else None
    instant_events = generate_instant_events(economics, subject_id=subject_id, observed_at=observed_dt.isoformat())

    critical_claim_blockers = [
        result["claim_id"]
        for claim, result in zip(claims, claim_results)
        if claim.get("decision_critical") is True and not result.get("decision_usable", False)
    ]
    economics_status = economics["decision"]["status"]
    if economics_status == "NO_VOLUME":
        stage = "BLOCKED_NO_VOLUME"
    elif economics_status == "LOSS_UNDER_CURRENT_INPUTS":
        stage = "BLOCKED_NEGATIVE_ECONOMICS"
    elif economics_status in {"UNVERIFIED_ECONOMICS", "UNKNOWN"}:
        stage = "BLOCKED_UNVERIFIED_ECONOMICS"
    elif economics_status == "HIGH_OPERATIONAL_RISK":
        stage = "BLOCKED_OPERATIONAL_RISK"
    elif critical_claim_blockers:
        stage = "BLOCKED_CRITICAL_CLAIMS"
    elif not gate_result["eligible_for_next_stage"]:
        stage = "BLOCKED_GATES"
    elif opportunity_result is not None and opportunity_result["stage"] != "SCALE_REVIEW_CANDIDATE":
        stage = f"BLOCKED_OPPORTUNITY_{opportunity_result['stage']}"
    elif opportunity_result is not None:
        stage = "ELIGIBLE_FOR_HUMAN_SCALE_REVIEW"
    else:
        # TEST_CANDIDATE is a permission for a bounded experiment only.
        stage = "ELIGIBLE_FOR_BOUNDED_TEST"

    output_core = {
        "run_id": run_id,
        "case_id": case_id,
        "input_hash": input_hash,
        "stage": stage,
        "economics_decision": economics_status,
        "gate_eligible": gate_result["eligible_for_next_stage"],
        "critical_claim_blockers": critical_claim_blockers,
        "candidate_stage": opportunity_result["stage"] if opportunity_result else None,
    }
    stable_events = [
        {key: value for key, value in event.items() if key not in {"created_at", "observed_at"}}
        for event in instant_events
    ]
    report_basis = {
        "decision_core": output_core,
        "economics": economics,
        "claims": claim_results,
        "gates": gate_result,
        "opportunity": opportunity_result,
        "sensitivity": sensitivity,
        "instant_events": stable_events,
    }
    report_hash = sha256(_canonical(report_basis)).hexdigest()

    return {
        "schema_version": SCHEMA_VERSION,
        "run_manifest": {
            "run_id": run_id,
            "case_id": case_id,
            "created_at": created_at,
            "observed_at": observed_dt.isoformat(),
            "code_revision": code_revision,
            "runtime": "python-stdlib-local",
            "mode": "ANALYSIS_ONLY_NO_EXTERNAL_SIDE_EFFECTS",
            "input_hash": input_hash,
            "report_hash": report_hash,
        },
        "decision": {
            "stage": stage,
            "economics_status": economics_status,
            "gate_eligible": gate_result["eligible_for_next_stage"],
            "critical_claim_blockers": critical_claim_blockers,
            "next_action": (
                "Resolve the listed blocking condition and rerun from a new, source-backed snapshot."
                if stage.startswith("BLOCKED_")
                else "A bounded test may be proposed; a separate authorized decision is still required."
            ),
            "authorization_granted": False,
        },
        "economics": economics,
        "claims": claim_results,
        "gates": gate_result,
        "opportunity": opportunity_result,
        "sensitivity": sensitivity,
        "instant_events": instant_events,
        "provenance_summary": {
            "evidence_record_count": len(evidence_records),
            "claim_count": len(claims),
            "gate_count": gate_result["gate_count"],
            "source_urls": sorted({
                record["source_ref"]
                for record in evidence_records
                if record.get("source_kind") == "url" and isinstance(record.get("source_ref"), str)
            }),
        },
        "limitations": [
            "The run is a local analysis packet, not a transaction or authorization.",
            "A report hash establishes packet identity, not truth or tamper-proof storage.",
            "Evidence artifacts must be retained separately; an artifact reference is not independent authenticity verification.",
            "Instant events are generated from this one evaluated snapshot; no live source updates are subscribed.",
            "Sensitivity outputs are conditional stress cases, not probabilities or calibrated forecasts.",
        ],
    }
