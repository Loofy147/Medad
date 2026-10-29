"""Small, deterministic command line for Medad's reusable decision engines."""
from __future__ import annotations

import argparse
from dataclasses import fields
from pathlib import Path
from typing import Any
import json
import sys

from engine import Inputs, evaluate
from sensitivity import sensitivity_report
from instant import JsonlEventJournal, generate_instant_events
from decision_kernel import assess_claim, assess_gates, validate_continuation_contract
from opportunity import load_snapshot


def read_json(path: str | Path) -> dict[str, Any]:
    with Path(path).open("r", encoding="utf-8") as file:
        value = json.load(file)
    if not isinstance(value, dict):
        raise ValueError("Input JSON root must be an object")
    return value


REQUIRED_INPUT_FIELDS = {
    "product_name", "selling_price", "purchase_cost", "packaging_cost",
    "outbound_delivery_cost", "delivery_fee_collected", "failed_delivery_return_cost",
    "return_shipping_cost", "return_handling_cost", "ad_spend", "placed_orders",
    "delivery_rate", "customer_return_rate", "inventory_recovery_rate",
    "other_variable_cost_per_retained_order", "other_fixed_costs",
}


def parse_inputs(payload: dict[str, Any]) -> Inputs:
    raw = payload.get("inputs", payload)
    if not isinstance(raw, dict):
        raise ValueError("'inputs' must be an object")
    allowed = {field.name for field in fields(Inputs)}
    unknown = sorted(set(raw) - allowed)
    if unknown:
        raise ValueError(f"Unknown Inputs fields: {unknown}")
    missing = sorted(REQUIRED_INPUT_FIELDS - set(raw))
    if missing:
        raise ValueError(f"Missing explicit economics inputs; defaults are not silently applied: {missing}")
    return Inputs(**raw)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Medad local, product-agnostic decision engines")
    parser.add_argument(
        "command",
        choices=("economics", "sensitivity", "instant", "claim", "gates", "continuation", "opportunity-audit"),
    )
    parser.add_argument("--input", help="JSON input file for the selected command")
    parser.add_argument("--snapshot", help="Research snapshot JSON for opportunity-audit")
    parser.add_argument("--journal", default=".medad/instant-events.jsonl", help="Local JSONL event journal for instant")
    args = parser.parse_args(argv)

    try:
        if args.command == "opportunity-audit":
            snapshot_path = args.snapshot or args.input
            if not snapshot_path:
                raise ValueError("opportunity-audit requires --snapshot or --input")
            result = load_snapshot(snapshot_path)
            output = {
                "snapshot_id": result.get("snapshot_id"),
                "captured_at": result.get("captured_at"),
                "candidate_count": len(result.get("candidates", [])),
                "sourcing_lead_count": result.get("sourcing_lead_count"),
                "verified_supplier_quote_count": result.get("verified_supplier_quote_count"),
                "readiness": result.get("readiness"),
            }
        else:
            if not args.input:
                raise ValueError(f"{args.command} requires --input")
            payload = read_json(args.input)
            if args.command == "economics":
                output = evaluate(parse_inputs(payload))
            elif args.command == "sensitivity":
                output = sensitivity_report(parse_inputs(payload))
            elif args.command == "instant":
                inputs = parse_inputs(payload)
                subject_id = payload.get("subject_id", inputs.product_name)
                events = generate_instant_events(inputs_result := evaluate(inputs), subject_id=subject_id, observed_at=payload.get("observed_at"))
                journal = JsonlEventJournal(args.journal)
                outcomes = [journal.append(event) for event in events]
                output = {
                    "mode": "LOCAL_ONLY",
                    "subject_id": subject_id,
                    "evaluated_decision": inputs_result["decision"],
                    "generated_count": len(events),
                    "inserted_count": sum(item["inserted"] for item in outcomes),
                    "replayed_count": sum(not item["inserted"] for item in outcomes),
                    "journal_path": str(Path(args.journal)),
                    "events": [item["event"] for item in outcomes],
                }
            elif args.command == "claim":
                if not isinstance(payload.get("claim"), dict) or not isinstance(payload.get("evidence_records"), list):
                    raise ValueError("claim input requires an object 'claim' and array 'evidence_records'")
                output = assess_claim(payload["claim"], payload["evidence_records"])
            elif args.command == "gates":
                if not isinstance(payload.get("gates"), list):
                    raise ValueError("gates input requires an array 'gates'")
                records = payload.get("evidence_records", [])
                if not isinstance(records, list):
                    raise ValueError("evidence_records must be an array")
                output = assess_gates(payload["gates"], evidence_records=records)
            elif args.command == "continuation":
                output = {"contract_errors": validate_continuation_contract(payload)}
                output["valid"] = not output["contract_errors"]
            else:  # argparse choices prevent this branch in normal use
                raise ValueError(f"Unsupported command: {args.command}")

        print(json.dumps(output, ensure_ascii=False, indent=2, allow_nan=False))
        return 0
    except (OSError, json.JSONDecodeError, TypeError, ValueError, KeyError) as exc:
        print(json.dumps({"error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
