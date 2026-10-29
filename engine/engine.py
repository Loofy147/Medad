"""Medad high-leverage product engine. Standard library only; values are DZD."""
from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import date
from math import isfinite
from typing import Any
import json


@dataclass
class Inputs:
    product_name: str = "Example product"
    selling_price: float = 2900.0
    purchase_cost: float = 1200.0
    packaging_cost: float = 80.0
    outbound_delivery_cost: float = 450.0
    delivery_fee_collected: float = 300.0
    failed_delivery_return_cost: float = 250.0
    return_shipping_cost: float = 200.0
    return_handling_cost: float = 150.0
    ad_spend: float = 35000.0
    placed_orders: int = 100
    delivery_rate: float = 0.70
    customer_return_rate: float = 0.05
    inventory_recovery_rate: float = 0.90
    other_variable_cost_per_retained_order: float = 0.0
    other_fixed_costs: float = 3000.0
    confidence: dict[str, float] | None = None
    evidence: dict[str, str] | None = None
    evidence_sources: dict[str, dict[str, Any]] | None = None  # URL, observed_on, label
    sample_size: int | None = None
    data_age_days: int | None = None


NONNEGATIVE_FIELDS = (
    "selling_price", "purchase_cost", "packaging_cost",
    "outbound_delivery_cost", "delivery_fee_collected",
    "failed_delivery_return_cost", "return_shipping_cost",
    "return_handling_cost", "ad_spend",
    "other_variable_cost_per_retained_order", "other_fixed_costs",
)
RATE_FIELDS = ("delivery_rate", "customer_return_rate", "inventory_recovery_rate")
VALID_EVIDENCE = {"observed", "quoted", "estimated", "assumed"}


def _validate(x: Inputs) -> None:
    if not isinstance(x.product_name, str) or not x.product_name.strip():
        raise ValueError("product_name must be a non-empty string")
    for name in NONNEGATIVE_FIELDS:
        value = getattr(x, name)
        if not isinstance(value, (int, float)) or isinstance(value, bool) or not isfinite(value) or value < 0:
            raise ValueError(f"{name} must be a finite non-negative number")
    if not isinstance(x.placed_orders, int) or isinstance(x.placed_orders, bool) or x.placed_orders < 0:
        raise ValueError("placed_orders must be a non-negative integer")
    for name in RATE_FIELDS:
        value = getattr(x, name)
        if not isinstance(value, (int, float)) or isinstance(value, bool) or not isfinite(value) or not 0 <= value <= 1:
            raise ValueError(f"{name} must be finite and between 0 and 1")
    if x.sample_size is not None and (not isinstance(x.sample_size, int) or isinstance(x.sample_size, bool) or x.sample_size < 0):
        raise ValueError("sample_size must be a non-negative integer")
    if x.data_age_days is not None and (not isinstance(x.data_age_days, int) or isinstance(x.data_age_days, bool) or x.data_age_days < 0):
        raise ValueError("data_age_days must be a non-negative integer")
    for source, label in (x.evidence or {}).items():
        if not isinstance(label, str) or label not in VALID_EVIDENCE:
            raise ValueError(f"evidence[{source!r}] must be one of {sorted(VALID_EVIDENCE)}")
    for source, score in (x.confidence or {}).items():
        if not isinstance(score, (int, float)) or isinstance(score, bool) or not isfinite(score) or not 0 <= score <= 1:
            raise ValueError(f"confidence[{source!r}] must be between 0 and 1")
    for source, details in (x.evidence_sources or {}).items():
        if not isinstance(details, dict):
            raise ValueError(f"evidence_sources[{source!r}] must be an object")
        url = details.get("url")
        observed_on = details.get("observed_on")
        if not isinstance(url, str) or not url.startswith("https://"):
            raise ValueError(f"evidence_sources[{source!r}].url must be an HTTPS URL")
        if not isinstance(observed_on, str):
            raise ValueError(f"evidence_sources[{source!r}].observed_on must be YYYY-MM-DD")
        try:
            parsed_date = date.fromisoformat(observed_on)
        except ValueError as exc:
            raise ValueError(f"evidence_sources[{source!r}].observed_on must be YYYY-MM-DD") from exc
        if parsed_date > date.today():
            raise ValueError(f"evidence_sources[{source!r}].observed_on cannot be in the future")
        if not isinstance(details.get("label"), str) or details.get("label") not in VALID_EVIDENCE:
            raise ValueError(f"evidence_sources[{source!r}].label must be one of {sorted(VALID_EVIDENCE)}")
        declared_label = (x.evidence or {}).get(source)
        if declared_label is not None and declared_label != details.get("label"):
            raise ValueError(f"evidence label mismatch for {source!r}: declared input label and source label must match")


def assess_data_quality(x: Inputs) -> dict[str, Any]:
    _validate(x)
    scores = x.confidence or {}
    evidence = x.evidence or {}
    provenance = x.evidence_sources or {}
    if not scores and not evidence and not provenance and x.sample_size is None and x.data_age_days is None:
        return {
            "score": None, "grade": "UNKNOWN", "coverage": 0.0,
            "note": "No evidence metadata supplied; forecasts are unverified.",
        }

    evidence_weights = {"observed": 1.0, "quoted": 0.8, "estimated": 0.45, "assumed": 0.15}
    expected_groups = ("unit_cost", "selling_price", "delivery_rate", "return_rate", "ad_cost")

    # Provenance can supply the label for a group, but a source label is not counted
    # twice when an operator also entered the same label manually.
    effective_labels = dict(evidence)
    for key, detail in provenance.items():
        if key not in effective_labels and isinstance(detail, dict):
            label = detail.get("label")
            if isinstance(label, str) and label in VALID_EVIDENCE:
                effective_labels[key] = label

    group_scores: dict[str, float] = {}
    for key in expected_groups:
        candidates: list[float] = []
        if key in scores:
            candidates.append(float(scores[key]))
        if key in effective_labels:
            candidates.append(evidence_weights[effective_labels[key]])
        if candidates:
            group_scores[key] = round(sum(candidates) / len(candidates), 6)

    # Missing groups reduce coverage instead of silently receiving a zero value.
    coverage = len(group_scores) / len(expected_groups)
    confidence_score = sum(group_scores.values()) / len(group_scores) if group_scores else 0.0

    # Derive freshness from the oldest source and supplied age so a stale source
    # cannot be made fresh by a more optimistic manual age.
    source_ages = [
        (date.today() - date.fromisoformat(item["observed_on"])).days
        for item in provenance.values()
        if isinstance(item, dict) and isinstance(item.get("observed_on"), str)
    ]
    ages = source_ages + ([x.data_age_days] if x.data_age_days is not None else [])
    effective_age = max(ages) if ages else None
    freshness = 0.4 if effective_age is None else max(0.0, 1.0 - effective_age / 180.0)
    sample_factor = 0.25 if x.sample_size is None else min(1.0, x.sample_size / 100.0)
    score = confidence_score * (0.75 + 0.25 * freshness) * (0.75 + 0.25 * sample_factor)

    provenance_groups = {
        key for key, detail in provenance.items()
        if key in expected_groups
        and isinstance(detail, dict)
        and isinstance(detail.get("url"), str)
        and detail["url"].startswith("https://")
        and isinstance(detail.get("observed_on"), str)
        and isinstance(detail.get("label"), str)
        and detail["label"] in VALID_EVIDENCE
    }
    provenance_coverage = len(provenance_groups) / len(expected_groups)
    has_assumptions = any(effective_labels.get(key) == "assumed" for key in expected_groups)
    has_usable_sample = x.sample_size is not None and x.sample_size >= 30
    has_freshness = effective_age is not None and effective_age <= 90

    grade = (
        "HIGH"
        if score >= 0.8 and coverage >= 0.8 and provenance_coverage >= 0.8
        and has_usable_sample and has_freshness and not has_assumptions
        else "MEDIUM"
        if score >= 0.55 and coverage >= 0.4 and provenance_coverage >= 0.4
        and has_usable_sample and has_freshness
        else "LOW"
    )
    if not group_scores or provenance_coverage == 0:
        grade = "LOW"

    warnings: list[str] = []
    if coverage < 0.8:
        warnings.append("Important evidence groups are missing.")
    if provenance_coverage < 0.8:
        warnings.append("Source URL, observation date, and evidence label are missing for some or all input groups.")
    if x.sample_size is None or x.sample_size < 30:
        warnings.append("Observed sample size is absent or small.")
    if effective_age is None or effective_age > 90:
        warnings.append("Source freshness is unknown or at least one evidence source is older than 90 days.")
    if has_assumptions:
        warnings.append("One or more important evidence groups are assumptions, not verified evidence.")
    return {
        "score": round(score, 4),
        "grade": grade,
        "coverage": round(coverage, 4),
        "provenance_coverage": round(provenance_coverage, 4),
        "components": group_scores,
        "confidence_inputs": scores,
        "evidence_labels": effective_labels,
        "evidence_sources": provenance,
        "sample_size": x.sample_size,
        "data_age_days": effective_age,
        "warnings": warnings,
        "note": "Heuristic completeness/freshness indicator, not a statistical probability of truth, demand, or profit.",
    }


def evaluate(x: Inputs) -> dict[str, Any]:
    _validate(x)
    placed = x.placed_orders
    delivered = placed * x.delivery_rate
    undelivered = placed - delivered
    returned = delivered * x.customer_return_rate
    retained = delivered - returned
    revenue = retained * x.selling_price
    customer_delivery_revenue = retained * x.delivery_fee_collected
    product_cogs = retained * x.purchase_cost
    unrecoverable_return_inventory = returned * x.purchase_cost * (1 - x.inventory_recovery_rate)
    packaging = placed * x.packaging_cost
    outbound_shipping = placed * x.outbound_delivery_cost
    failed_delivery_logistics = undelivered * x.failed_delivery_return_cost
    return_logistics = returned * x.return_shipping_cost
    return_handling = returned * x.return_handling_cost
    other_variable = retained * x.other_variable_cost_per_retained_order
    contribution_before_ads = (
        revenue + customer_delivery_revenue - product_cogs - unrecoverable_return_inventory
        - packaging - outbound_shipping - failed_delivery_logistics - return_logistics
        - return_handling - other_variable
    )
    profit = contribution_before_ads - x.ad_spend - x.other_fixed_costs
    break_even_surplus = contribution_before_ads - x.other_fixed_costs
    # Zero is a valid break-even budget only when contribution exactly covers fixed costs.
    break_even_ad_spend = break_even_surplus if break_even_surplus >= 0 else None
    cac_per_placed = x.ad_spend / placed if placed else None
    cac_per_retained = x.ad_spend / retained if retained else None
    break_even_cac_per_placed = break_even_ad_spend / placed if placed and break_even_ad_spend is not None else None
    break_even_cac_per_retained = break_even_ad_spend / retained if retained and break_even_ad_spend is not None else None
    margin = profit / (revenue + customer_delivery_revenue) if (revenue + customer_delivery_revenue) else None
    data_quality = assess_data_quality(x)
    return {
        "product_name": x.product_name,
        "funnel": {
            "placed_orders": placed, "delivered_orders_expected": round(delivered, 2),
            "undelivered_orders_expected": round(undelivered, 2), "returned_orders_expected": round(returned, 2),
            "retained_orders_expected": round(retained, 2), "delivery_rate": x.delivery_rate,
            "customer_return_rate": x.customer_return_rate,
        },
        "economics_dzd": {
            "product_revenue": round(revenue, 2), "customer_delivery_revenue": round(customer_delivery_revenue, 2),
            "total_revenue": round(revenue + customer_delivery_revenue, 2), "product_cogs": round(product_cogs, 2),
            "unrecoverable_return_inventory": round(unrecoverable_return_inventory, 2),
            "packaging": round(packaging, 2), "outbound_shipping": round(outbound_shipping, 2),
            "failed_delivery_logistics": round(failed_delivery_logistics, 2), "return_logistics": round(return_logistics, 2),
            "return_handling": round(return_handling, 2), "other_variable_costs": round(other_variable, 2),
            "ad_spend": round(x.ad_spend, 2), "other_fixed_costs": round(x.other_fixed_costs, 2),
            "contribution_before_ads": round(contribution_before_ads, 2), "estimated_profit": round(profit, 2),
            "profit_margin": round(margin, 4) if margin is not None else None,
            "profit_per_placed_order": round(profit / placed, 2) if placed else None,
            "profit_per_retained_order": round(profit / retained, 2) if retained else None,
            "ad_cost_per_placed_order": round(cac_per_placed, 2) if cac_per_placed is not None else None,
            "ad_cost_per_retained_order": round(cac_per_retained, 2) if cac_per_retained is not None else None,
            "break_even_ad_spend": round(break_even_ad_spend, 2) if break_even_ad_spend is not None else None,
            "break_even_possible_before_ads": break_even_ad_spend is not None,
            "break_even_ad_cost_per_placed_order": round(break_even_cac_per_placed, 2) if break_even_cac_per_placed is not None else None,
            "break_even_ad_cost_per_retained_order": round(break_even_cac_per_retained, 2) if break_even_cac_per_retained is not None else None,
        },
        "decision": classify(profit, placed, x, data_quality), "data_quality": data_quality,
        "assumptions": [
            "Expected counts may be fractional and should be rounded only for operational forecasts.",
            "All placed orders incur packaging and outbound-shipping costs; adjust if pre-shipment cancellations are material.",
            "Product cost is expensed for retained units; returned units are expensed only to the extent their inventory value cannot be recovered.",
            "Customer delivery fees are modeled as revenue on retained orders only.",
            "Supplier minimums, working-capital timing, taxes, payment fees, warehouse costs, and salaries must be entered or modeled separately.",
        ],
    }


def classify(profit: float, placed: int, x: Inputs, quality: dict[str, Any] | None = None) -> dict[str, str]:
    if placed <= 0:
        return {"status": "NO_VOLUME", "meaning": "No order volume supplied; cannot assess viability."}
    if profit < 0:
        return {"status": "LOSS_UNDER_CURRENT_INPUTS", "meaning": "Negative modeled profit under current inputs; validate costs and operational assumptions before concluding."}

    quality = quality if quality is not None else assess_data_quality(x)
    if quality["grade"] in {"UNKNOWN", "LOW"}:
        return {
            "status": "UNVERIFIED_ECONOMICS",
            "meaning": "The model is positive, but source coverage, sample size or freshness is insufficient; do not treat this as a profitable-product signal.",
        }
    if (
        x.delivery_rate < 0.55
        or x.customer_return_rate > 0.15
        or quality["grade"] != "HIGH"
    ):
        return {
            "status": "HIGH_OPERATIONAL_RISK",
            "meaning": "The modeled result is positive, but delivery/return performance or evidence quality needs controlled testing before any scale decision.",
        }
    return {
        "status": "TEST_CANDIDATE",
        "meaning": "A positive modeled result with recent, traceable evidence and adequate sample; this permits a bounded test, not inventory scale-up.",
    }


def scenarios(base: Inputs) -> dict[str, dict[str, Any]]:
    cases = {
        "downside": {
            "delivery_rate": max(0, base.delivery_rate - .15),
            "customer_return_rate": min(1, base.customer_return_rate + .08),
            "ad_spend": base.ad_spend * 1.25,
            "outbound_delivery_cost": base.outbound_delivery_cost * 1.10,
            "failed_delivery_return_cost": base.failed_delivery_return_cost * 1.20,
        },
        "base": {},
        "upside": {
            "delivery_rate": min(1, base.delivery_rate + .10),
            "customer_return_rate": max(0, base.customer_return_rate - .03),
            "ad_spend": base.ad_spend * .90,
        },
    }
    result = {}
    for name, changes in cases.items():
        data = asdict(base)
        data.update(changes)
        result[name] = evaluate(Inputs(**data))
    return result


def _demo() -> None:
    inp = Inputs(
        confidence={"unit_cost": .9, "selling_price": .8, "delivery_rate": .3, "return_rate": .45, "ad_cost": .6},
        evidence={"unit_cost": "quoted", "selling_price": "estimated", "delivery_rate": "assumed", "return_rate": "assumed", "ad_cost": "estimated"},
        sample_size=20, data_age_days=14,
    )
    print(json.dumps({"base": evaluate(inp), "scenarios": scenarios(inp)}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    _demo()
