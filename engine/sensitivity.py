"""Deterministic sensitivity analysis. Results never upgrade evidence quality."""
from __future__ import annotations

from dataclasses import asdict
from typing import Any, Callable
from engine import Inputs, evaluate


DEFAULT_SHOCKS: dict[str, tuple[float, float, float, str]] = {
    # (low shock, central shock, high shock, mode)
    "selling_price": (0.80, 1.00, 1.20, "multiply"),
    "purchase_cost": (1.25, 1.00, 0.80, "multiply"),
    "ad_spend": (1.30, 1.00, 0.70, "multiply"),
    "outbound_delivery_cost": (1.20, 1.00, 0.90, "multiply"),
    "delivery_rate": (-0.15, 0.00, 0.10, "add"),
    "customer_return_rate": (0.08, 0.00, -0.05, "add"),
    "inventory_recovery_rate": (-0.20, 0.00, 0.10, "add"),
}


def _profit(inputs: Inputs) -> float:
    return float(evaluate(inputs)["economics_dzd"]["estimated_profit"])


def sensitivity_report(base: Inputs, shocks: dict[str, tuple[float, float, float, str]] | None = None) -> dict[str, Any]:
    """Run one-factor-at-a-time scenarios from the same baseline, preserving all other inputs."""
    shock_set = shocks or DEFAULT_SHOCKS
    baseline = evaluate(base)
    base_profit = baseline["economics_dzd"]["estimated_profit"]
    factors = []
    input_values = asdict(base)
    for field, spec in shock_set.items():
        if field not in input_values:
            raise ValueError(f"Unknown sensitivity field: {field}")
        if len(spec) != 4:
            raise ValueError(f"Shock for {field!r} must be (low, central, high, mode)")
        low_shock, central_shock, high_shock, mode = spec
        if mode not in {"multiply", "add"}:
            raise ValueError(f"Unsupported shock mode: {mode!r}")
        values = []
        for label, shock in (("low", low_shock), ("central", central_shock), ("high", high_shock)):
            value = float(getattr(base, field))
            changed = value * shock if mode == "multiply" else value + shock
            if field in {"delivery_rate", "customer_return_rate", "inventory_recovery_rate"}:
                changed = min(1.0, max(0.0, changed))
            elif changed < 0:
                raise ValueError(f"Shock drives {field!r} below zero")
            raw = dict(input_values)
            raw[field] = changed
            # Store the exact applied value so scenario outputs are auditable.
            result = evaluate(Inputs(**raw))
            profit = result["economics_dzd"]["estimated_profit"]
            values.append({
                "case": label,
                "applied_value": round(changed, 6),
                "modeled_profit_dzd": profit,
                "delta_vs_base_dzd": round(profit - base_profit, 2),
                "profit_sign_changed": (profit < 0) != (base_profit < 0),
            })
        spread = max(item["modeled_profit_dzd"] for item in values) - min(item["modeled_profit_dzd"] for item in values)
        factors.append({
            "field": field,
            "baseline_value": getattr(base, field),
            "mode": mode,
            "cases": values,
            "profit_spread_dzd": round(spread, 2),
            "ranking_basis": "absolute modeled-profit spread across these specified shocks only",
            "evidence_quality_unchanged": True,
        })
    factors.sort(key=lambda item: item["profit_spread_dzd"], reverse=True)
    return {
        "baseline_modeled_profit_dzd": base_profit,
        "baseline_decision": baseline["decision"],
        "baseline_data_quality": baseline["data_quality"],
        "factors": factors,
        "limitations": [
            "One-factor-at-a-time scenarios do not capture interactions between ad spend, delivery rate, returns and price.",
            "Shock sizes are explicit stress assumptions, not learned distributions or calibrated probabilities.",
            "Sensitivity measures model dependence, not certainty about the input values.",
            "Evidence quality and decision status are not upgraded by scenario calculations.",
        ],
    }


def find_profit_threshold(
    base: Inputs,
    field: str,
    low: float,
    high: float,
    *,
    target_profit_dzd: float = 0.0,
    profitable_when: str = "at_or_above",
    iterations: int = 80,
) -> dict[str, Any]:
    """Find a numeric input threshold by bisection when a monotonic bracket exists."""
    if field not in asdict(base):
        raise ValueError(f"Unknown input field: {field}")
    if not (isinstance(low, (int, float)) and isinstance(high, (int, float)) and low < high):
        raise ValueError("low and high must be numeric and low < high")
    if field in {"delivery_rate", "customer_return_rate", "inventory_recovery_rate"} and (low < 0 or high > 1):
        raise ValueError(f"{field} bounds must be within [0, 1]")
    if field in {"selling_price", "purchase_cost", "packaging_cost", "outbound_delivery_cost",
                 "delivery_fee_collected", "failed_delivery_return_cost", "return_shipping_cost",
                 "return_handling_cost", "ad_spend", "other_variable_cost_per_retained_order",
                 "other_fixed_costs"} and low < 0:
        raise ValueError(f"{field} bounds must be non-negative")
    if profitable_when not in {"at_or_above", "at_or_below"}:
        raise ValueError("profitable_when must be 'at_or_above' or 'at_or_below'")
    if iterations < 1 or iterations > 200:
        raise ValueError("iterations must be between 1 and 200")

    def score(value: float) -> float:
        raw = asdict(base)
        raw[field] = value
        return _profit(Inputs(**raw)) - target_profit_dzd

    left_score = score(float(low))
    right_score = score(float(high))
    left_pass = left_score >= 0 if profitable_when == "at_or_above" else left_score <= 0
    right_pass = right_score >= 0 if profitable_when == "at_or_above" else right_score <= 0
    if left_pass == right_pass:
        return {
            "field": field, "threshold": None, "bracketed": False,
            "low": low, "high": high, "low_profit_delta": left_score,
            "high_profit_delta": right_score,
            "meaning": "No threshold crossing was bracketed; do not extrapolate outside the tested interval.",
        }
    lo, hi = float(low), float(high)
    # The sides are kept according to the requested decision predicate; this avoids
    # assuming whether the target is crossed upward or downward as the value changes.
    for _ in range(iterations):
        mid = (lo + hi) / 2
        mid_score = score(mid)
        mid_pass = mid_score >= 0 if profitable_when == "at_or_above" else mid_score <= 0
        if mid_pass == left_pass:
            lo = mid
            left_pass = mid_pass
        else:
            hi = mid
    threshold = (lo + hi) / 2
    return {
        "field": field, "threshold": round(threshold, 9), "bracketed": True,
        "low": low, "high": high, "target_profit_dzd": target_profit_dzd,
        "modeled_profit_at_threshold_dzd": round(score(threshold) + target_profit_dzd, 4),
        "meaning": "Modeled input threshold within the requested bracket, conditional on all other inputs.",
    }
