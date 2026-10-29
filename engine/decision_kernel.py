"""Generic evidence-to-decision kernel used by Medad's reusable operating method.

The kernel validates traceability and decision gates. It does not invent evidence,
promote hypotheses automatically to established facts, or approve investments.
"""
from __future__ import annotations

from datetime import date, datetime
from typing import Any

CLAIM_LABELS = {
    "ESTABLISHED", "EXPERIMENTALLY_SUPPORTED", "USER_REPORTED", "INFERENCE",
    "HYPOTHESIS", "CONTRADICTED", "UNKNOWN", "OPEN",
}
EVIDENCE_LABELS = {"observed", "quoted", "estimated", "assumed"}
POLARITIES = {"supports", "contradicts", "context"}
SOURCE_KINDS = {"url", "document", "experiment", "dataset", "run", "user_report"}
GATE_STATES = {"PASS", "FAIL", "UNKNOWN", "NOT_APPLICABLE"}


def _text(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _date(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    try:
        parsed = date.fromisoformat(value)
    except ValueError:
        return False
    return parsed <= date.today()


def validate_evidence_record(record: dict[str, Any]) -> list[str]:
    """Return contract violations; an empty list means structurally valid, not proven true."""
    if not isinstance(record, dict):
        return ["evidence record must be an object"]
    errors: list[str] = []
    for field in ("evidence_id", "source_kind", "evidence_label", "polarity", "observed_on"):
        if not _text(record.get(field)):
            errors.append(f"{field} is required")
    if not isinstance(record.get("source_kind"), str) or record["source_kind"] not in SOURCE_KINDS:
        errors.append(f"source_kind must be one of {sorted(SOURCE_KINDS)}")
    if not isinstance(record.get("evidence_label"), str) or record["evidence_label"] not in EVIDENCE_LABELS:
        errors.append(f"evidence_label must be one of {sorted(EVIDENCE_LABELS)}")
    if not isinstance(record.get("polarity"), str) or record["polarity"] not in POLARITIES:
        errors.append(f"polarity must be one of {sorted(POLARITIES)}")
    if not _date(record.get("observed_on")):
        errors.append("observed_on must be a valid non-future YYYY-MM-DD date")

    if record.get("source_kind") == "url":
        if not isinstance(record.get("source_ref"), str) or not record["source_ref"].startswith("https://"):
            errors.append("URL evidence requires an HTTPS source_ref")
    else:
        if not _text(record.get("artifact_ref")):
            errors.append("non-URL evidence requires an artifact_ref")
    if not _text(record.get("independence_key")):
        errors.append("independence_key is required to avoid counting duplicate evidence as independent")
    sample_size = record.get("sample_size")
    if sample_size is not None and (
        not isinstance(sample_size, int) or isinstance(sample_size, bool) or sample_size < 0
    ):
        errors.append("sample_size must be a non-negative integer when supplied")
    if record.get("evidence_label") == "observed" and record.get("sample_size") is None:
        errors.append("observed evidence must declare sample_size (zero is permitted but weak)")
    if record.get("source_kind") == "experiment":
        if not _text(record.get("method_ref")):
            errors.append("experiment evidence requires method_ref")
        if record.get("sample_size", 0) <= 0:
            errors.append("experiment evidence requires a positive sample_size")
    if record.get("artifact_sha256") is not None:
        digest = record["artifact_sha256"]
        if not isinstance(digest, str) or len(digest) != 64 or any(c not in "0123456789abcdef" for c in digest.lower()):
            errors.append("artifact_sha256 must be a 64-character hexadecimal digest")
    return errors


def validate_claim(claim: dict[str, Any], evidence_records: list[dict[str, Any]]) -> list[str]:
    """Validate claim shape and all referenced evidence without changing the declared label."""
    if not isinstance(claim, dict):
        return ["claim must be an object"]
    errors: list[str] = []
    for field in ("claim_id", "statement", "declared_status"):
        if not _text(claim.get(field)):
            errors.append(f"{field} is required")
    if not isinstance(claim.get("declared_status"), str) or claim["declared_status"] not in CLAIM_LABELS:
        errors.append(f"declared_status must be one of {sorted(CLAIM_LABELS)}")
    if not isinstance(evidence_records, list):
        errors.append("evidence_records must be an array")
        evidence_records = []
    refs = claim.get("evidence_refs", [])
    if not isinstance(refs, list):
        errors.append("evidence_refs must be an array")
        refs = []
    elif any(not _text(ref) for ref in refs):
        errors.append("every evidence reference must be a non-empty string")
    else:
        if len(refs) != len(set(refs)):
            errors.append("evidence_refs must not contain duplicates")
    ids_list = [item.get("evidence_id") for item in evidence_records if isinstance(item, dict)]
    if len(ids_list) != len(set(item for item in ids_list if _text(item))):
        errors.append("evidence_records contains duplicate evidence_id values")
    ids = {item for item in ids_list if _text(item)}
    for ref in refs:
        if isinstance(ref, str) and ref not in ids:
            errors.append(f"unknown evidence reference: {ref!r}")
    return errors


def assess_claim(claim: dict[str, Any], evidence_records: list[dict[str, Any]]) -> dict[str, Any]:
    """Derive a cautious decision-facing state from declared status plus linked evidence.

    ESTABLISHED is never inferred automatically. Contradictions remain OPEN when
    both supporting and contradicting evidence exist and require explicit resolution.
    """
    contract_errors = validate_claim(claim, evidence_records)
    if contract_errors:
        return {
            "claim_id": claim.get("claim_id"),
            "declared_status": claim.get("declared_status"),
            "effective_status": "OPEN",
            "decision_usable": False,
            "contract_errors": contract_errors,
            "warnings": ["Claim metadata is incomplete or references missing evidence."],
        }

    by_id = {item["evidence_id"]: item for item in evidence_records if isinstance(item, dict)}
    linked = [by_id[ref] for ref in claim.get("evidence_refs", [])]
    evidence_errors = {
        item.get("evidence_id"): validate_evidence_record(item)
        for item in linked
        if validate_evidence_record(item)
    }
    if evidence_errors:
        return {
            "claim_id": claim["claim_id"],
            "declared_status": claim["declared_status"],
            "effective_status": "OPEN",
            "decision_usable": False,
            "evidence_errors": evidence_errors,
            "warnings": ["At least one linked evidence record fails its traceability contract."],
        }

    supporters = [item for item in linked if item["polarity"] == "supports" and item["evidence_label"] != "assumed"]
    contradictors = [item for item in linked if item["polarity"] == "contradicts" and item["evidence_label"] != "assumed"]
    declared = claim["declared_status"]
    warnings: list[str] = []

    if supporters and contradictors:
        effective = "OPEN"
        warnings.append("Supporting and contradicting evidence coexist; resolve the conflict before relying on this claim.")
    elif contradictors:
        effective = "CONTRADICTED"
    elif declared == "ESTABLISHED":
        strong_supporters = [item for item in supporters if item["evidence_label"] in {"observed", "quoted"}]
        independent = {item["independence_key"] for item in strong_supporters}
        if len(independent) >= 2:
            effective = "ESTABLISHED"
        else:
            effective = "OPEN"
            warnings.append("ESTABLISHED requires at least two independent non-assumption supporting records.")
    elif declared == "EXPERIMENTALLY_SUPPORTED":
        experiments = [
            item for item in supporters
            if item["source_kind"] == "experiment"
            and item.get("sample_size", 0) > 0
            and _text(item.get("method_ref"))
        ]
        if experiments:
            effective = "EXPERIMENTALLY_SUPPORTED"
        else:
            effective = "OPEN"
            warnings.append("No valid linked experiment supports this status.")
    elif declared == "USER_REPORTED":
        effective = "USER_REPORTED"
        warnings.append("This remains user-reported unless independent evidence supports it.")
    elif declared == "INFERENCE":
        effective = "INFERENCE" if supporters else "OPEN"
        if not supporters:
            warnings.append("No non-assumption supporting evidence is linked to this inference.")
    elif declared == "CONTRADICTED":
        effective = "OPEN"
        warnings.append("The declared contradiction has no linked non-assumption contradicting evidence.")
    elif declared == "HYPOTHESIS":
        effective = "HYPOTHESIS"
        warnings.append("Evidence has not automatically promoted this hypothesis to a stronger claim.")
    elif declared == "UNKNOWN":
        effective = "UNKNOWN"
        warnings.append("The claim remains unknown until a discriminating observation is recorded.")
    else:  # OPEN
        effective = "OPEN"
        warnings.append("The claim requires resolution or a discriminating test.")

    usable = effective in {"ESTABLISHED", "EXPERIMENTALLY_SUPPORTED", "INFERENCE"} and not warnings
    if not linked and declared not in {"USER_REPORTED", "HYPOTHESIS", "UNKNOWN", "OPEN"}:
        usable = False
        warnings.append("No evidence is linked.")
    return {
        "claim_id": claim["claim_id"],
        "declared_status": declared,
        "effective_status": effective,
        "supporting_evidence_count": len(supporters),
        "contradicting_evidence_count": len(contradictors),
        "independent_support_count": len({item["independence_key"] for item in supporters}),
        "decision_usable": usable,
        "evidence_refs": list(claim.get("evidence_refs", [])),
        "warnings": warnings,
    }


def assess_gates(
    gates: list[dict[str, Any]],
    evidence_records: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Only explicit, reviewed PASS values with valid evidence references satisfy a gate.

    If the caller does not provide the evidence records, no gate can be confirmed as
    passed from references alone. This fails closed instead of trusting arbitrary IDs.
    """
    errors: list[str] = []
    seen: set[str] = set()
    normalized: list[dict[str, Any]] = []
    record_index: dict[str, dict[str, Any]] = {}

    if evidence_records is not None and not isinstance(evidence_records, list):
        errors.append("evidence_records must be an array")
        evidence_records = []
    for index, record in enumerate(evidence_records or []):
        if not isinstance(record, dict):
            errors.append(f"Evidence record at index {index} must be an object")
            continue
        record_id = record.get("evidence_id")
        if not _text(record_id) or record_id in record_index:
            errors.append(f"Evidence record ID is missing or duplicated: {record_id!r}")
            continue
        record_errors = validate_evidence_record(record)
        if record_errors:
            errors.append(f"Evidence record {record_id!r} invalid: {record_errors}")
            continue
        record_index[record_id] = record

    if not isinstance(gates, list):
        errors.append("gates must be an array")
        gates = []
    for gate in gates:
        if not isinstance(gate, dict):
            errors.append("Every gate must be an object")
            continue
        gate_id = gate.get("gate_id")
        state = gate.get("state", "UNKNOWN")
        if not _text(gate_id):
            errors.append(f"Gate ID is missing or invalid: {gate_id!r}")
        elif gate_id in seen:
            errors.append(f"Gate ID is duplicated: {gate_id!r}")
        else:
            seen.add(gate_id)
        if not isinstance(state, str) or state not in GATE_STATES:
            errors.append(f"Invalid gate state for {gate_id!r}: {state!r}")
            state = "UNKNOWN"

        refs = gate.get("evidence_refs", [])
        if not isinstance(refs, list) or any(not _text(ref) for ref in refs):
            errors.append(f"evidence_refs for {gate_id!r} must be an array of non-empty strings")
            refs = []
        elif len(refs) != len(set(refs)):
            errors.append(f"evidence_refs for {gate_id!r} must not contain duplicates")
            refs = []

        if state == "PASS":
            if not refs:
                errors.append(f"PASS gate {gate_id!r} requires at least one evidence reference")
                state = "UNKNOWN"
            elif evidence_records is None:
                errors.append(f"PASS gate {gate_id!r} cannot be verified without the evidence records")
                state = "UNKNOWN"
            elif any(ref not in record_index for ref in refs):
                unknown_refs = [ref for ref in refs if ref not in record_index]
                errors.append(f"PASS gate {gate_id!r} references invalid or unknown evidence: {unknown_refs}")
                state = "UNKNOWN"
            if not _text(gate.get("reviewed_by")) or not _date(gate.get("reviewed_at")) or not _text(gate.get("reason")):
                errors.append(f"PASS gate {gate_id!r} requires reviewed_by, reviewed_at and reason")
                state = "UNKNOWN"
        elif state == "NOT_APPLICABLE":
            if not _text(gate.get("reviewed_by")) or not _date(gate.get("reviewed_at")) or not _text(gate.get("reason")):
                errors.append(f"NOT_APPLICABLE gate {gate_id!r} requires reviewer, date and rationale")
                state = "UNKNOWN"
        elif state == "FAIL" and not _text(gate.get("reason")):
            errors.append(f"FAIL gate {gate_id!r} requires a reason")

        normalized.append({
            "gate_id": gate_id,
            "state": state,
            "evidence_refs": refs,
            "reviewed_by": gate.get("reviewed_by"),
            "reviewed_at": gate.get("reviewed_at"),
            "reason": gate.get("reason"),
        })

    blockers = [item["gate_id"] for item in normalized if item["state"] not in {"PASS", "NOT_APPLICABLE"}]
    eligible = not errors and not blockers and bool(normalized)
    return {
        "eligible_for_next_stage": eligible,
        "gate_count": len(normalized),
        "passed_count": sum(item["state"] == "PASS" for item in normalized),
        "not_applicable_count": sum(item["state"] == "NOT_APPLICABLE" for item in normalized),
        "blocking_gate_ids": blockers,
        "contract_errors": errors,
        "meaning": "Eligibility only; a separate authorized decision is still required." if eligible else "Do not advance; resolve every blocking gate and contract error.",
    }


def validate_continuation_contract(contract: dict[str, Any]) -> list[str]:
    """Validate a compact handoff so work can resume from evidence, not recollection."""
    if not isinstance(contract, dict):
        return ["continuation contract must be an object"]
    errors: list[str] = []
    required = ("task_id", "goal", "current_state_ref", "last_verified_ref", "next_discriminating_test", "owner")
    for field in required:
        if not _text(contract.get(field)):
            errors.append(f"{field} is required")
    for field in ("open_gates", "known_failures", "assumptions", "next_actions"):
        value = contract.get(field)
        if not isinstance(value, list):
            errors.append(f"{field} must be an array")
        elif any(not _text(item) for item in value):
            errors.append(f"every item in {field} must be a non-empty string")
    verified_at = contract.get("last_verified_at")
    if not _date(verified_at):
        errors.append("last_verified_at must be a valid non-future YYYY-MM-DD date")
    return errors
