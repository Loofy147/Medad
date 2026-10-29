import unittest
from datetime import date, datetime, timezone
from copy import deepcopy

from workflow import build_decision_run


def high_quality_inputs() -> dict:
    groups = ["unit_cost", "selling_price", "delivery_rate", "return_rate", "ad_cost"]
    today = date.today().isoformat()
    return {
        "product_name": "generic-engine-fixture",
        "selling_price": 2900.0,
        "purchase_cost": 1200.0,
        "packaging_cost": 80.0,
        "outbound_delivery_cost": 450.0,
        "delivery_fee_collected": 300.0,
        "failed_delivery_return_cost": 250.0,
        "return_shipping_cost": 200.0,
        "return_handling_cost": 150.0,
        "ad_spend": 35000.0,
        "placed_orders": 100,
        "delivery_rate": 0.70,
        "customer_return_rate": 0.05,
        "inventory_recovery_rate": 0.90,
        "other_variable_cost_per_retained_order": 0.0,
        "other_fixed_costs": 3000.0,
        "confidence": {key: 0.95 for key in groups},
        "evidence": {key: "observed" for key in groups},
        "evidence_sources": {
            key: {"url": f"https://evidence.example/{key}", "observed_on": today, "label": "observed"}
            for key in groups
        },
        "sample_size": 100,
        "data_age_days": 0,
    }


def valid_experiment_evidence(evidence_id: str = "e-pilot") -> dict:
    return {
        "evidence_id": evidence_id,
        "source_kind": "experiment",
        "evidence_label": "observed",
        "polarity": "supports",
        "observed_on": date.today().isoformat(),
        "artifact_ref": "run://pilot-01",
        "independence_key": "pilot-run-01",
        "sample_size": 50,
        "method_ref": "method://controlled-pilot-v1",
    }


def base_payload() -> dict:
    return {
        "schema_version": "medad.decision-run.v1",
        "run_id": "run-001",
        "case_id": "generic-case-001",
        "observed_at": datetime.now(timezone.utc).isoformat(),
        "code_revision": "test-revision",
        "inputs": high_quality_inputs(),
        "evidence_records": [valid_experiment_evidence()],
        "gates": [{
            "gate_id": "baseline-evidence-reviewed",
            "state": "PASS",
            "evidence_refs": ["e-pilot"],
            "reviewed_by": "reviewer-a",
            "reviewed_at": date.today().isoformat(),
            "reason": "Reviewed evidence contract fixture",
        }],
    }


class DecisionWorkflowTests(unittest.TestCase):
    def test_complete_run_packet_is_hashable_and_never_authorizes_spend(self):
        result = build_decision_run(base_payload())
        self.assertEqual(result["schema_version"], "medad.decision-run.v1")
        self.assertEqual(result["economics"]["decision"]["status"], "TEST_CANDIDATE")
        self.assertEqual(result["gates"]["eligible_for_next_stage"], True)
        self.assertEqual(result["decision"]["stage"], "ELIGIBLE_FOR_BOUNDED_TEST")
        self.assertFalse(result["decision"]["authorization_granted"])
        self.assertEqual(len(result["run_manifest"]["input_hash"]), 64)
        self.assertEqual(len(result["run_manifest"]["report_hash"]), 64)
        self.assertEqual(result["run_manifest"]["mode"], "ANALYSIS_ONLY_NO_EXTERNAL_SIDE_EFFECTS")

    def test_report_hash_covers_calculated_outputs_and_is_stable_for_same_run(self):
        payload = base_payload()
        first = build_decision_run(payload)
        second = build_decision_run(payload)
        self.assertEqual(first["run_manifest"]["input_hash"], second["run_manifest"]["input_hash"])
        self.assertEqual(first["run_manifest"]["report_hash"], second["run_manifest"]["report_hash"])

        changed = deepcopy(payload)
        changed["inputs"]["purchase_cost"] += 25
        third = build_decision_run(changed)
        self.assertNotEqual(first["run_manifest"]["report_hash"], third["run_manifest"]["report_hash"])

    def test_workflow_rejects_unknown_fields_and_missing_revision(self):
        payload = base_payload()
        payload["unrecognized_flag"] = True
        with self.assertRaises(ValueError):
            build_decision_run(payload)
        payload = base_payload()
        payload.pop("code_revision")
        with self.assertRaises(ValueError):
            build_decision_run(payload)

    def test_missing_gates_block_even_high_quality_positive_economics(self):
        payload = base_payload()
        payload["gates"] = []
        result = build_decision_run(payload)
        self.assertEqual(result["economics"]["decision"]["status"], "TEST_CANDIDATE")
        self.assertEqual(result["decision"]["stage"], "BLOCKED_GATES")
        self.assertFalse(result["decision"]["authorization_granted"])

    def test_critical_claim_with_only_assumed_support_blocks_run(self):
        payload = base_payload()
        payload["evidence_records"].append({
            "evidence_id": "e-assumption",
            "source_kind": "url",
            "source_ref": "https://example.org/claim",
            "evidence_label": "assumed",
            "polarity": "supports",
            "observed_on": date.today().isoformat(),
            "independence_key": "unverified-claim-source",
        })
        payload["claims"] = [{
            "claim_id": "c-demand",
            "statement": "Demand is sufficient to scale",
            "declared_status": "INFERENCE",
            "evidence_refs": ["e-assumption"],
            "decision_critical": True,
        }]
        result = build_decision_run(payload)
        self.assertEqual(result["claims"][0]["effective_status"], "OPEN")
        self.assertEqual(result["decision"]["stage"], "BLOCKED_CRITICAL_CLAIMS")
        self.assertEqual(result["decision"]["critical_claim_blockers"], ["c-demand"])

    def test_unknown_cost_data_blocks_run_even_when_gate_passes(self):
        payload = base_payload()
        payload["inputs"] = {
            "product_name": "assumption-only",
            "selling_price": 2900.0,
            "purchase_cost": 1200.0,
            "packaging_cost": 80.0,
            "outbound_delivery_cost": 450.0,
            "delivery_fee_collected": 300.0,
            "failed_delivery_return_cost": 250.0,
            "return_shipping_cost": 200.0,
            "return_handling_cost": 150.0,
            "ad_spend": 35000.0,
            "placed_orders": 100,
            "delivery_rate": 0.70,
            "customer_return_rate": 0.05,
            "inventory_recovery_rate": 0.90,
            "other_variable_cost_per_retained_order": 0.0,
            "other_fixed_costs": 3000.0,
        }
        result = build_decision_run(payload)
        self.assertEqual(result["decision"]["stage"], "BLOCKED_UNVERIFIED_ECONOMICS")

    def test_invalid_or_duplicate_evidence_records_fail_closed(self):
        payload = base_payload()
        payload["evidence_records"][0]["evidence_label"] = "guaranteed"
        with self.assertRaises(ValueError):
            build_decision_run(payload)
        payload = base_payload()
        payload["evidence_records"].append(deepcopy(payload["evidence_records"][0]))
        with self.assertRaises(ValueError):
            build_decision_run(payload)

    def test_run_rejects_naive_timestamps_and_implicit_defaults(self):
        payload = base_payload()
        payload["observed_at"] = "2026-10-29T12:00:00"
        with self.assertRaises(ValueError):
            build_decision_run(payload)
        payload = base_payload()
        payload["inputs"].pop("purchase_cost")
        with self.assertRaises(ValueError):
            build_decision_run(payload)

    def test_candidate_without_product_gates_does_not_become_scale_ready(self):
        payload = base_payload()
        payload["candidate"] = {"id": "candidate-with-no-artifacts"}
        result = build_decision_run(payload)
        self.assertEqual(result["opportunity"]["stage"], "RESEARCH_ONLY")
        self.assertEqual(result["decision"]["stage"], "BLOCKED_OPPORTUNITY_RESEARCH_ONLY")

    def test_sensitivity_is_opt_in_and_does_not_change_base_decision(self):
        payload = base_payload()
        baseline = build_decision_run(payload)
        payload["options"] = {"sensitivity": True}
        enhanced = build_decision_run(payload)
        self.assertIsNone(baseline["sensitivity"])
        self.assertGreater(len(enhanced["sensitivity"]["factors"]), 5)
        self.assertEqual(baseline["decision"]["stage"], enhanced["decision"]["stage"])
        self.assertEqual(baseline["economics"]["data_quality"], enhanced["economics"]["data_quality"])


if __name__ == "__main__":
    unittest.main()
