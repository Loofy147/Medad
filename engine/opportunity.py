"""Evidence-gated candidate readiness. No synthetic profitability rank."""
from __future__ import annotations
from pathlib import Path
from typing import Any
import json

REQUIRED_RESEARCH_GATES = {
    "product_spec_verified": "Product specification and sample are verified",
    "supplier_quotes_count": "At least two comparable supplier quotes are recorded",
    "landed_cost_verified": "Landed cost is verified, including procurement and packaging",
    "courier_quote_verified": "Seller-specific outbound and failed-delivery fees are quoted",
}
REQUIRED_TEST_GATES = {
    "pilot_campaign_evidence": "A bounded creative/ad pilot has measurable results",
    "delivered_order_cohort_evidence": "Delivered, refused, returned, and retained orders are reconciled",
}


def assess_candidate(candidate: dict[str, Any]) -> dict[str, Any]:
    """Return a stage gate, not a success probability or an investment recommendation."""
    missing_research = []
    for field, label in REQUIRED_RESEARCH_GATES.items():
        value = candidate.get(field)
        satisfied = (isinstance(value, int) and not isinstance(value, bool) and value >= 2) if field == "supplier_quotes_count" else value is True
        if not satisfied:
            missing_research.append(label)
    missing_test = [label for field, label in REQUIRED_TEST_GATES.items() if candidate.get(field) is not True]
    repeatable_cohorts = candidate.get("repeatable_cohorts", 0)
    if not isinstance(repeatable_cohorts, int) or isinstance(repeatable_cohorts, bool) or repeatable_cohorts < 0:
        raise ValueError("repeatable_cohorts must be a non-negative integer")

    if missing_research:
        stage = "RESEARCH_ONLY"
        next_action = "Collect supplier/sample/landed-cost and seller-specific courier evidence before any stock commitment."
    elif missing_test:
        stage = "PRETEST_READY"
        next_action = "Run a capped pilot with pre-declared stop conditions; do not scale yet."
    elif repeatable_cohorts < 2:
        stage = "TESTED_SINGLE_COHORT"
        next_action = "Reconcile a second comparable cohort and check cash recovery before a scale review."
    else:
        stage = "SCALE_REVIEW_CANDIDATE"
        next_action = "Eligible for a human scale review; this is not an automatic approval or profit guarantee."

    total_gates = len(REQUIRED_RESEARCH_GATES) + len(REQUIRED_TEST_GATES) + 1
    satisfied_gates = len(REQUIRED_RESEARCH_GATES) - len(missing_research) + len(REQUIRED_TEST_GATES) - len(missing_test) + int(repeatable_cohorts >= 2)
    return {
        "candidate_id": candidate.get("id"),
        "stage": stage,
        "gates_satisfied": satisfied_gates,
        "gates_total": total_gates,
        "gate_coverage": round(satisfied_gates / total_gates, 3),
        "missing_research_gates": missing_research,
        "missing_test_gates": missing_test,
        "repeatable_cohorts": repeatable_cohorts,
        "next_action": next_action,
        "is_profitability_score": False,
        "is_investment_approval": False,
    }


def load_snapshot(path: str | Path) -> dict[str, Any]:
    with Path(path).open("r", encoding="utf-8") as file:
        snapshot = json.load(file)
    source_ids = set()
    for source in snapshot.get("sources", []):
        source_id = source.get("id")
        if not source_id or source_id in source_ids:
            raise ValueError(f"Missing or duplicate source id: {source_id!r}")
        source_ids.add(source_id)
        url = source.get("url", "")
        if not isinstance(url, str) or not url.startswith("https://"):
            raise ValueError(f"Source {source_id!r} must use an HTTPS URL")
    candidate_ids = set()
    for item in snapshot.get("candidates", []):
        candidate_id = item.get("id")
        if not candidate_id or candidate_id in candidate_ids:
            raise ValueError(f"Missing or duplicate candidate id: {candidate_id!r}")
        candidate_ids.add(candidate_id)
        refs = item.get("source_ids", [])
        if not refs:
            raise ValueError(f"Candidate {candidate_id!r} must cite at least one source")
        for source_id in refs:
            if source_id not in source_ids:
                raise ValueError(f"Candidate {candidate_id!r} references unknown source {source_id!r}")
    lead_ids = set()
    for lead in snapshot.get("sourcing_leads", []):
        lead_id = lead.get("id")
        if not lead_id or lead_id in lead_ids:
            raise ValueError(f"Missing or duplicate sourcing lead id: {lead_id!r}")
        lead_ids.add(lead_id)
        linked_ids = [lead.get("platform_source_id"), *lead.get("due_diligence_source_ids", [])]
        if not linked_ids or any(source_id not in source_ids for source_id in linked_ids):
            raise ValueError(f"Sourcing lead {lead_id!r} references unknown source ids")
        # Discovery platforms must never masquerade as supplier quotes.
        if lead.get("quote_verified") is True and lead.get("status") == "DISCOVERY_LEAD_ONLY":
            raise ValueError(f"Sourcing lead {lead_id!r} cannot be both discovery-only and quote-verified")
    snapshot["readiness"] = [assess_candidate(item) for item in snapshot.get("candidates", [])]
    return snapshot
