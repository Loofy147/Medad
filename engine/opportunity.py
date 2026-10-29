"""Evidence-gated candidate readiness. No synthetic profitability rank."""
from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Any
import json

REQUIRED_RESEARCH_GATES = {
    "product_spec_verified": "Exact SKU/specification is verified",
    "sample_inspection": "An inspected sample has a traceable record",
    "supplier_quotes": "Two current comparable supplier quotes for the same SKU are verified",
    "landed_cost": "Landed cost is reconciled from documented components",
    "courier_quote": "Seller-specific courier terms are documented by route scope",
}
REQUIRED_TEST_GATES = {
    "pilot_campaign": "A capped, measured campaign has a traceable evidence record",
    "order_cohorts": "At least one reconciled delivered/failed/returned order cohort is recorded",
}


def _nonblank(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _valid_date(value: Any, *, allow_future: bool = False) -> bool:
    if not isinstance(value, str):
        return False
    try:
        parsed = date.fromisoformat(value)
    except ValueError:
        return False
    return allow_future or parsed <= date.today()


def _has_artifact(item: Any, date_field: str) -> bool:
    return (
        isinstance(item, dict)
        and _nonblank(item.get("artifact_ref"))
        and _valid_date(item.get(date_field))
    )


def _valid_supplier_quotes(candidate: dict[str, Any]) -> list[dict[str, Any]]:
    sku = candidate.get("sku")
    quotes = candidate.get("supplier_quotes")
    if not _nonblank(sku) or not isinstance(quotes, list):
        return []
    valid: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    seen_sellers: set[str] = set()
    for quote in quotes:
        if not isinstance(quote, dict):
            continue
        quote_id = quote.get("quote_id")
        supplier_id = quote.get("supplier_id")
        min_qty = quote.get("minimum_quantity")
        unit_price = quote.get("unit_price_dzd")
        current_quote = (
            _nonblank(quote_id)
            and quote_id not in seen_ids
            and _nonblank(quote.get("artifact_ref"))
            and _nonblank(supplier_id)
            and supplier_id not in seen_sellers
            and quote.get("seller_verified") is True
            and quote.get("sku") == sku
            and _valid_date(quote.get("quoted_on"))
            and (date.today() - date.fromisoformat(quote["quoted_on"])).days <= 90
            and _valid_date(quote.get("valid_until"), allow_future=True)
            and quote.get("valid_until") >= date.today().isoformat()
            and isinstance(min_qty, int)
            and not isinstance(min_qty, bool)
            and min_qty > 0
            and isinstance(unit_price, (int, float))
            and not isinstance(unit_price, bool)
            and unit_price > 0
            and quote.get("currency") == "DZD"
        )
        if current_quote:
            valid.append(quote)
            seen_ids.add(quote_id)
            seen_sellers.add(supplier_id)
    return valid


def _valid_product_spec(candidate: dict[str, Any]) -> bool:
    spec = candidate.get("product_spec")
    if not isinstance(spec, dict) or not _has_artifact(spec, "verified_on"):
        return False
    age = (date.today() - date.fromisoformat(spec["verified_on"])).days
    source_ref = spec.get("source_ref")
    attributes = spec.get("fields")
    return (
        age <= 180
        and spec.get("verified") is True
        and _nonblank(spec.get("verified_by"))
        and spec.get("sku") == candidate.get("sku")
        and _nonblank(spec.get("artifact_ref"))
        and isinstance(source_ref, str)
        and source_ref.startswith("https://")
        and isinstance(attributes, dict)
        and bool(attributes)
        and all(_nonblank(key) and value is not None for key, value in attributes.items())
    )


def _valid_sample(candidate: dict[str, Any]) -> bool:
    sample = candidate.get("sample_inspection")
    spec = candidate.get("product_spec")
    if not isinstance(sample, dict) or not isinstance(spec, dict) or not _has_artifact(sample, "inspected_on"):
        return False
    inspected_on = date.fromisoformat(sample["inspected_on"])
    return (
        (date.today() - inspected_on).days <= 180
        and _nonblank(sample.get("inspector_id"))
        and sample.get("outcome") == "PASS"
        and sample.get("sku") == candidate.get("sku")
        and sample.get("spec_match") is True
        and sample.get("compared_to_spec_artifact_ref") == spec.get("artifact_ref")
    )


def _valid_landed_cost(candidate: dict[str, Any], quote_ids: set[str]) -> bool:
    item = candidate.get("landed_cost")
    if not isinstance(item, dict) or not _has_artifact(item, "calculated_on"):
        return False
    if item.get("verified") is not True or not _nonblank(item.get("reviewed_by")):
        return False
    components = item.get("component_costs_dzd")
    if not isinstance(components, dict):
        return False
    required = {"purchase", "packaging", "inbound_transport"}
    if not required.issubset(components):
        return False
    if any(not isinstance(v, (int, float)) or isinstance(v, bool) or v < 0 for v in components.values()):
        return False
    if components["purchase"] <= 0:
        return False
    total = item.get("unit_cost_dzd")
    if not isinstance(total, (int, float)) or isinstance(total, bool) or total <= 0:
        return False
    if abs(sum(components.values()) - total) > 0.02:
        return False
    quote_refs = item.get("source_quote_ids")
    return (
        isinstance(quote_refs, list)
        and len(set(quote_refs)) >= 1
        and set(quote_refs).issubset(quote_ids)
    )


def _valid_courier_quote(candidate: dict[str, Any]) -> bool:
    quote = candidate.get("courier_quote")
    if not isinstance(quote, dict) or not _has_artifact(quote, "quoted_on"):
        return False
    quoted_on = date.fromisoformat(quote["quoted_on"])
    if (date.today() - quoted_on).days > 90:
        return False
    if not _valid_date(quote.get("valid_until"), allow_future=True) or quote["valid_until"] < date.today().isoformat():
        return False
    if quote.get("seller_account_verified") is not True or not _nonblank(quote.get("origin_wilaya")):
        return False
    destinations = quote.get("coverage_wilayas")
    if not isinstance(destinations, list) or not destinations or any(not _nonblank(x) for x in destinations):
        return False
    for field in ("outbound_dzd", "failed_delivery_dzd", "return_dzd"):
        value = quote.get(field)
        if not isinstance(value, (int, float)) or isinstance(value, bool) or value < 0:
            return False
    remittance_days = quote.get("cod_remittance_days")
    return (
        isinstance(remittance_days, int)
        and not isinstance(remittance_days, bool)
        and remittance_days >= 0
        and _nonblank(quote.get("contract_or_quote_id"))
    )


def _valid_campaign(candidate: dict[str, Any]) -> bool:
    campaign = candidate.get("pilot_campaign")
    if not isinstance(campaign, dict) or not _has_artifact(campaign, "ended_on"):
        return False
    if (date.today() - date.fromisoformat(campaign["ended_on"])).days > 90:
        return False
    if not _valid_date(campaign.get("started_on")) or campaign["started_on"] > campaign["ended_on"]:
        return False
    if not all(_nonblank(campaign.get(field)) for field in ("platform", "creative_id", "attribution_method")):
        return False
    for field in ("spend_dzd", "placed_orders", "attributed_orders"):
        value = campaign.get(field)
        if not isinstance(value, (int, float)) or isinstance(value, bool) or value < 0:
            return False
    if campaign["spend_dzd"] <= 0 or not isinstance(campaign["placed_orders"], int) or not isinstance(campaign["attributed_orders"], int):
        return False
    return campaign["attributed_orders"] <= campaign["placed_orders"]


def _valid_order_cohort(cohort: Any, candidate_sku: Any) -> bool:
    if not isinstance(cohort, dict) or not _has_artifact(cohort, "ended_on"):
        return False
    if (date.today() - date.fromisoformat(cohort["ended_on"])).days > 90:
        return False
    if not _valid_date(cohort.get("started_on")) or cohort["started_on"] > cohort["ended_on"]:
        return False
    if not _nonblank(cohort.get("cohort_id")) or cohort.get("sku") != candidate_sku:
        return False
    if cohort.get("reconciled") is not True or not _nonblank(cohort.get("reconciled_by")):
        return False
    counts = ("placed_orders", "delivered_orders", "failed_orders", "returned_orders", "retained_orders")
    for field in counts:
        value = cohort.get(field)
        if not isinstance(value, int) or isinstance(value, bool) or value < 0:
            return False
    return (
        cohort["placed_orders"] > 0
        and cohort["delivered_orders"] + cohort["failed_orders"] == cohort["placed_orders"]
        and cohort["returned_orders"] <= cohort["delivered_orders"]
        and cohort["retained_orders"] == cohort["delivered_orders"] - cohort["returned_orders"]
    )


def assess_candidate(candidate: dict[str, Any]) -> dict[str, Any]:
    """Return a gate status, not a success probability or automatic investment approval."""
    missing_research: list[str] = []
    if not _nonblank(candidate.get("sku")) or not _valid_product_spec(candidate):
        missing_research.append(REQUIRED_RESEARCH_GATES["product_spec_verified"])
    if not _valid_sample(candidate):
        missing_research.append(REQUIRED_RESEARCH_GATES["sample_inspection"])

    valid_quotes = _valid_supplier_quotes(candidate)
    if len(valid_quotes) < 2:
        missing_research.append(REQUIRED_RESEARCH_GATES["supplier_quotes"])

    quote_ids = {q["quote_id"] for q in valid_quotes}
    if not _valid_landed_cost(candidate, quote_ids):
        missing_research.append(REQUIRED_RESEARCH_GATES["landed_cost"])
    if not _valid_courier_quote(candidate):
        missing_research.append(REQUIRED_RESEARCH_GATES["courier_quote"])

    missing_test: list[str] = []
    if not _valid_campaign(candidate):
        missing_test.append(REQUIRED_TEST_GATES["pilot_campaign"])

    cohorts = candidate.get("order_cohorts", [])
    if not isinstance(cohorts, list):
        cohorts = []
    valid_cohorts = [c for c in cohorts if _valid_order_cohort(c, candidate.get("sku"))]
    # Independent cohorts must have unique IDs and artifacts and non-overlapping date windows.
    accepted_cohorts: list[dict[str, Any]] = []
    seen_cohort_ids: set[str] = set()
    seen_cohort_artifacts: set[str] = set()
    for cohort in sorted(valid_cohorts, key=lambda item: (item["started_on"], item["ended_on"], item["cohort_id"])):
        cohort_id = cohort["cohort_id"]
        artifact_ref = cohort["artifact_ref"]
        if cohort_id in seen_cohort_ids or artifact_ref in seen_cohort_artifacts:
            continue
        start_day = date.fromisoformat(cohort["started_on"])
        end_day = date.fromisoformat(cohort["ended_on"])
        if any(start_day <= date.fromisoformat(prior["ended_on"]) for prior in accepted_cohorts):
            continue
        accepted_cohorts.append(cohort)
        seen_cohort_ids.add(cohort_id)
        seen_cohort_artifacts.add(artifact_ref)
    valid_cohorts = accepted_cohorts
    if not valid_cohorts:
        missing_test.append(REQUIRED_TEST_GATES["order_cohorts"])

    if missing_research:
        stage = "RESEARCH_ONLY"
        next_action = "Obtain exact-SKU sample inspection, two current comparable verified supplier quotes, reconciled landed cost, and seller-specific courier terms before committing inventory."
    elif missing_test:
        stage = "PRETEST_READY"
        next_action = "Run a capped campaign with pre-declared stop conditions; record spend and creative attribution, then reconcile every order outcome."
    elif len(valid_cohorts) < 2:
        stage = "TESTED_SINGLE_COHORT"
        next_action = "Reconcile a second independent comparable cohort and check cash recovery before human scale review."
    else:
        stage = "SCALE_REVIEW_CANDIDATE"
        next_action = "Eligible only for human scale review. This is not automatic approval or a profit guarantee."

    total_gates = len(REQUIRED_RESEARCH_GATES) + len(REQUIRED_TEST_GATES) + 1
    satisfied = len(REQUIRED_RESEARCH_GATES) - len(missing_research) + len(REQUIRED_TEST_GATES) - len(missing_test) + int(len(valid_cohorts) >= 2)
    return {
        "candidate_id": candidate.get("id"),
        "stage": stage,
        "gates_satisfied": satisfied,
        "gates_total": total_gates,
        "gate_coverage": round(satisfied / total_gates, 3),
        "missing_research_gates": missing_research,
        "missing_test_gates": missing_test,
        "valid_supplier_quote_count": len(valid_quotes),
        "valid_reconciled_cohort_count": len(valid_cohorts),
        "next_action": next_action,
        "is_profitability_score": False,
        "is_investment_approval": False,
    }


def load_snapshot(path: str | Path) -> dict[str, Any]:
    with Path(path).open("r", encoding="utf-8") as file:
        snapshot = json.load(file)
    if not isinstance(snapshot, dict):
        raise ValueError("Snapshot root must be a JSON object")
    if not _nonblank(snapshot.get("snapshot_id")):
        raise ValueError("snapshot_id is required")
    if not _valid_date(snapshot.get("captured_at")):
        raise ValueError("captured_at must be a valid non-future YYYY-MM-DD date")

    source_records = snapshot.get("sources", [])
    if not isinstance(source_records, list):
        raise ValueError("sources must be an array")
    source_ids: set[str] = set()
    for source in source_records:
        if not isinstance(source, dict):
            raise ValueError("Every source record must be a JSON object")
        source_id = source.get("id")
        if not _nonblank(source_id) or source_id in source_ids:
            raise ValueError(f"Missing or duplicate source id: {source_id!r}")
        source_ids.add(source_id)
        url = source.get("url", "")
        if not isinstance(url, str) or not url.startswith("https://"):
            raise ValueError(f"Source {source_id!r} must use an HTTPS URL")

    candidate_records = snapshot.get("candidates", [])
    if not isinstance(candidate_records, list):
        raise ValueError("candidates must be an array")
    candidate_ids: set[str] = set()
    for item in candidate_records:
        if not isinstance(item, dict):
            raise ValueError("Every candidate record must be a JSON object")
        candidate_id = item.get("id")
        if not _nonblank(candidate_id) or candidate_id in candidate_ids:
            raise ValueError(f"Missing or duplicate candidate id: {candidate_id!r}")
        candidate_ids.add(candidate_id)
        refs = item.get("source_ids", [])
        if not isinstance(refs, list) or not refs or any(not _nonblank(source_id) for source_id in refs):
            raise ValueError(f"Candidate {candidate_id!r} must cite an array of source IDs")
        for source_id in refs:
            if source_id not in source_ids:
                raise ValueError(f"Candidate {candidate_id!r} references unknown source {source_id!r}")

    leads = snapshot.get("sourcing_leads", [])
    if not isinstance(leads, list):
        raise ValueError("sourcing_leads must be an array")
    lead_ids: set[str] = set()
    for lead in leads:
        if not isinstance(lead, dict):
            raise ValueError("Every sourcing lead must be a JSON object")
        lead_id = lead.get("id")
        if not _nonblank(lead_id) or lead_id in lead_ids:
            raise ValueError(f"Missing or duplicate sourcing lead id: {lead_id!r}")
        lead_ids.add(lead_id)
        due_refs = lead.get("due_diligence_source_ids", [])
        if not isinstance(due_refs, list):
            raise ValueError(f"Sourcing lead {lead_id!r} due_diligence_source_ids must be an array")
        linked_ids = [lead.get("platform_source_id"), *due_refs]
        if any(not _nonblank(source_id) or source_id not in source_ids for source_id in linked_ids):
            raise ValueError(f"Sourcing lead {lead_id!r} references unknown source ids")
        # A discovery record must never masquerade as a received/verified supplier quote.
        if lead.get("quote_verified") is not False:
            raise ValueError(f"Sourcing lead {lead_id!r} must set quote_verified=false; store actual quote artifacts against a candidate")

    snapshot["readiness"] = [assess_candidate(item) for item in candidate_records]
    snapshot["sourcing_lead_count"] = len(leads)
    snapshot["verified_supplier_quote_count"] = sum(len(_valid_supplier_quotes(item)) for item in candidate_records)
    return snapshot

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Audit the Medad evidence snapshot.")
    parser.add_argument("snapshot", nargs="?", default=str(Path(__file__).resolve().parent.parent / "data" / "research_snapshot_2026-10-29.json"))
    args = parser.parse_args()
    report = load_snapshot(args.snapshot)
    print(json.dumps({
        "snapshot_id": report.get("snapshot_id"),
        "candidate_count": len(report.get("candidates", [])),
        "sourcing_lead_count": report.get("sourcing_lead_count"),
        "verified_supplier_quote_count": report.get("verified_supplier_quote_count"),
        "readiness": report.get("readiness"),
    }, ensure_ascii=False, indent=2))
