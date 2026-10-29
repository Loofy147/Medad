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
    allowed_top_level = {"schema_version", "run_id", "case_id", "observed_at", "code_revision", "run_note", "inputs", "evidence_records", "claims", "gates", "candidate", "options", "subject_id"}
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
    run_note = payload.get("run_note", "")
    if not isinstance(run_note, str):
        raise ValueError("run_note must be a string")
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
        "run_note": run_note,
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
    evidence_manifest = sorted(
        [
            {
                "evidence_id": record["evidence_id"],
                "content_hash": sha256(_canonical(record)).hexdigest(),
            }
            for record in evidence_records
        ],
        key=lambda item: item["evidence_id"],
    )
    decision_output = {
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
    }
    provenance_summary = {
        "evidence_record_count": len(evidence_records),
        "evidence_manifest": evidence_manifest,
        "claim_count": len(claims),
        "gate_count": gate_result["gate_count"],
        "source_urls": sorted({
            record["source_ref"]
            for record in evidence_records
            if record.get("source_kind") == "url" and isinstance(record.get("source_ref"), str)
        }),
    }
    limitations = [
        "The run is a local analysis packet, not a transaction or authorization.",
        "A report hash establishes packet identity, not truth or tamper-proof storage.",
        "Evidence artifacts must be retained separately; an artifact reference is not independent authenticity verification.",
        "Instant events are generated from this one evaluated snapshot; no live source updates are subscribed.",
        "Sensitivity outputs are conditional stress cases, not probabilities or calibrated forecasts.",
    ]
    manifest_identity = {
        "run_id": run_id,
        "case_id": case_id,
        "observed_at": observed_dt.isoformat(),
        "code_revision": code_revision,
        "run_note": run_note,
        "runtime": "python-stdlib-local",
        "mode": "ANALYSIS_ONLY_NO_EXTERNAL_SIDE_EFFECTS",
        "input_hash": input_hash,
    }
    report_basis = {
        "decision_core": output_core,
        "manifest_identity": manifest_identity,
        "decision_details": decision_output,
        "economics": economics,
        "claims": claim_results,
        "gates": gate_result,
        "opportunity": opportunity_result,
        "sensitivity": sensitivity,
        "instant_events": stable_events,
        "evidence_manifest": evidence_manifest,
        "provenance_summary": provenance_summary,
        "limitations": limitations,
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
            "run_note": run_note,
            "runtime": "python-stdlib-local",
            "mode": "ANALYSIS_ONLY_NO_EXTERNAL_SIDE_EFFECTS",
            "input_hash": input_hash,
            "report_hash": report_hash,
        },
        "decision": decision_output,
        "economics": economics,
        "claims": claim_results,
        "gates": gate_result,
        "opportunity": opportunity_result,
        "sensitivity": sensitivity,
        "instant_events": instant_events,
        "provenance_summary": provenance_summary,
        "limitations": limitations,
    }


def validate_decision_run_report(report: Any) -> list[str]:
    """Validate packet structure and recompute its output hash before persistence/replay.

    A valid hash proves packet consistency, not that its source evidence is true.
    """
    if not isinstance(report, dict):
        return ["report must be an object"]
    errors: list[str] = []
    if report.get("schema_version") != SCHEMA_VERSION:
        errors.append(f"schema_version must be {SCHEMA_VERSION}")
    manifest = report.get("run_manifest")
    decision = report.get("decision")
    provenance = report.get("provenance_summary")
    if not isinstance(manifest, dict):
        return errors + ["run_manifest must be an object"]
    if not isinstance(decision, dict):
        return errors + ["decision must be an object"]
    if not isinstance(provenance, dict):
        return errors + ["provenance_summary must be an object"]

    for field in ("run_id", "case_id", "observed_at", "code_revision", "runtime", "input_hash", "report_hash", "mode"):
        if not isinstance(manifest.get(field), str) or not manifest[field].strip():
            errors.append(f"run_manifest.{field} is required")
    if not isinstance(manifest.get("run_note", ""), str):
        errors.append("run_manifest.run_note must be a string")
    if isinstance(manifest.get("observed_at"), str):
        try:
            observed_dt = _aware_timestamp(manifest["observed_at"], "run_manifest.observed_at")
            if observed_dt > datetime.now(timezone.utc):
                errors.append("run_manifest.observed_at cannot be in the future")
        except ValueError as exc:
            errors.append(str(exc))
    if manifest.get("mode") != "ANALYSIS_ONLY_NO_EXTERNAL_SIDE_EFFECTS":
        errors.append("run_manifest.mode must be analysis-only")
    for field in ("input_hash", "report_hash"):
        digest = manifest.get(field)
        if isinstance(digest, str) and (
            len(digest) != 64
            or any(char not in "0123456789abcdef" for char in digest.lower())
        ):
            errors.append(f"run_manifest.{field} must be a 64-character hexadecimal digest")
    if decision.get("authorization_granted") is not False:
        errors.append("decision.authorization_granted must be false")
    if not isinstance(decision.get("stage"), str) or not decision["stage"]:
        errors.append("decision.stage is required")
    if not isinstance(decision.get("economics_status"), str) or not decision["economics_status"]:
        errors.append("decision.economics_status is required")
    if not isinstance(decision.get("gate_eligible"), bool):
        errors.append("decision.gate_eligible must be boolean")
    if not isinstance(decision.get("critical_claim_blockers"), list):
        errors.append("decision.critical_claim_blockers must be an array")

    evidence_manifest = provenance.get("evidence_manifest")
    if not isinstance(evidence_manifest, list):
        errors.append("provenance_summary.evidence_manifest must be an array")
        evidence_manifest = []
    seen_ids: set[str] = set()
    for index, item in enumerate(evidence_manifest):
        if not isinstance(item, dict):
            errors.append(f"evidence_manifest[{index}] must be an object")
            continue
        evidence_id = item.get("evidence_id")
        digest = item.get("content_hash")
        if not isinstance(evidence_id, str) or not evidence_id.strip():
            errors.append(f"evidence_manifest[{index}].evidence_id is required")
        elif evidence_id in seen_ids:
            errors.append(f"evidence_manifest contains duplicate evidence_id {evidence_id!r}")
        else:
            seen_ids.add(evidence_id)
        if not isinstance(digest, str) or len(digest) != 64 or any(
            char not in "0123456789abcdef" for char in digest.lower()
        ):
            errors.append(f"evidence_manifest[{index}].content_hash must be a SHA-256 digest")

    count = provenance.get("evidence_record_count")
    if isinstance(count, bool) or not isinstance(count, int) or count != len(evidence_manifest):
        errors.append("provenance_summary.evidence_record_count must match evidence_manifest length")

    required_outputs = ("economics", "claims", "gates", "instant_events")
    for field in required_outputs:
        if field not in report:
            errors.append(f"{field} is required")
    if not isinstance(report.get("claims"), list):
        errors.append("claims must be an array")
    if not isinstance(report.get("instant_events"), list):
        errors.append("instant_events must be an array")
    gates = report.get("gates")
    if not isinstance(gates, dict) or not isinstance(gates.get("eligible_for_next_stage"), bool):
        errors.append("gates.eligible_for_next_stage must be boolean")
    opportunity = report.get("opportunity")
    if opportunity is not None and not isinstance(opportunity, dict):
        errors.append("opportunity must be an object or null")

    if errors:
        return errors

    for field in ("run_id", "case_id"):
        if not isinstance(manifest.get(field), str) or not manifest[field].strip():
            return errors
    opportunity = report.get("opportunity")
    output_core = {
        "run_id": manifest["run_id"],
        "case_id": manifest["case_id"],
        "input_hash": manifest["input_hash"],
        "stage": decision["stage"],
        "economics_decision": decision["economics_status"],
        "gate_eligible": gates["eligible_for_next_stage"],
        "critical_claim_blockers": decision["critical_claim_blockers"],
        "candidate_stage": opportunity["stage"] if opportunity else None,
    }
    stable_events = [
        {key: value for key, value in event.items() if key not in {"created_at", "observed_at"}}
        for event in report["instant_events"]
        if isinstance(event, dict)
    ]
    if len(stable_events) != len(report["instant_events"]):
        return ["every instant event must be an object"]
    manifest_identity = {
        "run_id": manifest["run_id"],
        "case_id": manifest["case_id"],
        "observed_at": manifest.get("observed_at"),
        "code_revision": manifest.get("code_revision"),
        "run_note": manifest.get("run_note", ""),
        "runtime": manifest.get("runtime"),
        "mode": manifest.get("mode"),
        "input_hash": manifest["input_hash"],
    }
    report_basis = {
        "decision_core": output_core,
        "manifest_identity": manifest_identity,
        "decision_details": decision,
        "economics": report["economics"],
        "claims": report["claims"],
        "gates": report["gates"],
        "opportunity": report.get("opportunity"),
        "sensitivity": report.get("sensitivity"),
        "instant_events": stable_events,
        "evidence_manifest": evidence_manifest,
        "provenance_summary": provenance,
        "limitations": report.get("limitations"),
    }
    try:
        computed = sha256(_canonical(report_basis)).hexdigest()
    except (TypeError, ValueError) as exc:
        return [f"report contains non-canonical JSON values: {exc}"]
    if computed != manifest["report_hash"]:
        errors.append("run_manifest.report_hash does not match report content")
    return errors
