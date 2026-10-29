import json
import tempfile
import unittest
from datetime import date, timedelta
from pathlib import Path

from decision_kernel import (
    assess_claim,
    assess_gates,
    validate_continuation_contract,
    validate_evidence_record,
)
from engine import Inputs, evaluate
from instant import IdempotencyConflict, JsonlEventJournal, generate_instant_events
from sensitivity import find_profit_threshold, sensitivity_report


def observed_experiment(evidence_id: str, independence_key: str, *, polarity: str = "supports") -> dict:
    return {
        "evidence_id": evidence_id,
        "source_kind": "experiment",
        "evidence_label": "observed",
        "polarity": polarity,
        "observed_on": date.today().isoformat(),
        "artifact_ref": f"run://{evidence_id}",
        "independence_key": independence_key,
        "sample_size": 50,
        "method_ref": "method://pilot-v1",
    }


class DecisionKernelTests(unittest.TestCase):
    def test_established_claim_requires_two_independent_supports(self):
        claim = {"claim_id": "c1", "statement": "Observed outcome repeats", "declared_status": "ESTABLISHED", "evidence_refs": ["e1"]}
        one = assess_claim(claim, [observed_experiment("e1", "campaign-a")])
        self.assertEqual(one["effective_status"], "OPEN")
        self.assertFalse(one["decision_usable"])

        claim["evidence_refs"] = ["e1", "e2"]
        two = assess_claim(claim, [
            observed_experiment("e1", "campaign-a"),
            observed_experiment("e2", "campaign-b"),
        ])
        self.assertEqual(two["effective_status"], "ESTABLISHED")
        self.assertTrue(two["decision_usable"])

    def test_mixed_support_and_contradiction_stays_open(self):
        claim = {"claim_id": "c2", "statement": "Campaign succeeds", "declared_status": "INFERENCE", "evidence_refs": ["e1", "e2"]}
        result = assess_claim(claim, [
            observed_experiment("e1", "campaign-a"),
            observed_experiment("e2", "campaign-b", polarity="contradicts"),
        ])
        self.assertEqual(result["effective_status"], "OPEN")
        self.assertFalse(result["decision_usable"])
        self.assertTrue(any("coexist" in warning for warning in result["warnings"]))

    def test_assumed_evidence_does_not_prove_inference(self):
        evidence = {
            "evidence_id": "e1", "source_kind": "url", "source_ref": "https://example.org/listing",
            "evidence_label": "assumed", "polarity": "supports",
            "observed_on": date.today().isoformat(), "independence_key": "source-a",
        }
        claim = {"claim_id": "c3", "statement": "Demand is strong", "declared_status": "INFERENCE", "evidence_refs": ["e1"]}
        result = assess_claim(claim, [evidence])
        self.assertEqual(result["effective_status"], "OPEN")
        self.assertFalse(result["decision_usable"])

    def test_experiment_contract_requires_method_and_sample(self):
        evidence = observed_experiment("e1", "campaign-a")
        evidence["method_ref"] = ""
        self.assertTrue(any("method_ref" in error for error in validate_evidence_record(evidence)))

    def test_unknown_gate_blocks_even_if_another_gate_passes(self):
        result = assess_gates([
            {"gate_id": "sample", "state": "PASS", "evidence_refs": ["artifact://sample"]},
            {"gate_id": "courier", "state": "UNKNOWN", "evidence_refs": []},
        ])
        self.assertFalse(result["eligible_for_next_stage"])
        self.assertEqual(result["blocking_gate_ids"], ["courier"])

    def test_pass_without_evidence_is_not_pass(self):
        result = assess_gates([{"gate_id": "cost", "state": "PASS", "evidence_refs": []}])
        self.assertFalse(result["eligible_for_next_stage"])
        self.assertIn("cost", result["blocking_gate_ids"])
        self.assertTrue(result["contract_errors"])

    def test_continuation_contract_requires_resume_evidence_and_test(self):
        contract = {
            "task_id": "medad-001", "goal": "Stabilize unit economics", "current_state_ref": "branch://feature",
            "last_verified_ref": "commit://abc", "last_verified_at": date.today().isoformat(),
            "next_discriminating_test": "Run delivery-rate edge mutation", "owner": "engineering",
            "open_gates": [], "known_failures": [], "assumptions": [], "next_actions": [],
        }
        self.assertEqual(validate_continuation_contract(contract), [])
        del contract["next_discriminating_test"]
        self.assertTrue(validate_continuation_contract(contract))


class SensitivityEngineTests(unittest.TestCase):
    def test_sensitivity_is_deterministic_and_does_not_upgrade_quality(self):
        base = Inputs()
        first = sensitivity_report(base)
        second = sensitivity_report(base)
        self.assertEqual(first, second)
        self.assertGreaterEqual(len(first["factors"]), 5)
        self.assertTrue(all(item["evidence_quality_unchanged"] for item in first["factors"]))
        self.assertEqual(first["baseline_data_quality"]["grade"], "UNKNOWN")

    def test_sensitivity_custom_empty_grid_is_empty_not_defaulted(self):
        report = sensitivity_report(Inputs(), {})
        self.assertEqual(report["factors"], [])

    def test_sensitivity_requires_neutral_central_shock(self):
        with self.assertRaises(ValueError):
            sensitivity_report(Inputs(), {"selling_price": (0.8, 1.1, 1.2, "multiply")})

    def test_threshold_rejects_non_monotonic_field(self):
        with self.assertRaises(ValueError):
            find_profit_threshold(Inputs(), "delivery_rate", 0.4, 0.8)

    def test_sensitivity_rejects_unknown_field(self):
        with self.assertRaises(ValueError):
            sensitivity_report(Inputs(), {"made_up": (0.8, 1.0, 1.2, "multiply")})

    def test_purchase_cost_threshold_is_bracketed_when_profit_crosses_zero(self):
        result = find_profit_threshold(Inputs(), "purchase_cost", 1000, 2000)
        self.assertTrue(result["bracketed"])
        self.assertGreaterEqual(result["threshold"], 1000)
        self.assertLessEqual(result["threshold"], 2000)
        self.assertLessEqual(abs(result["modeled_profit_at_threshold_dzd"]), 0.01)

    def test_threshold_does_not_extrapolate_when_not_bracketed(self):
        result = find_profit_threshold(Inputs(), "selling_price", 2500, 3000)
        self.assertFalse(result["bracketed"])
        self.assertIsNone(result["threshold"])


class InstantEventTests(unittest.TestCase):
    def test_generate_alert_for_unverified_positive_model(self):
        result = evaluate(Inputs())
        events = generate_instant_events(result, subject_id="candidate-demo")
        self.assertIn("EVIDENCE_GAP", {event["event_type"] for event in events})
        self.assertTrue(all(event["state"] == "OPEN" for event in events))
        self.assertTrue(all(event["idempotency_key"] for event in events))

    def test_instant_event_contains_auditable_trigger_observation_and_recovery_fields(self):
        events = generate_instant_events(evaluate(Inputs()), subject_id="auditable-candidate")
        event = next(x for x in events if x["event_type"] == "EVIDENCE_GAP")
        self.assertEqual(event["context"]["mode"], "LOCAL_ECONOMICS_SNAPSHOT")
        self.assertIn("data_quality_grade", event["observations"])
        self.assertIn("LOW", event["trigger_rule"])
        self.assertEqual(event["state_delta"], {"from": None, "to": "OPEN"})
        self.assertIn("append-only-history", event["invariants"])
        self.assertIn("RESOLVED", event["recovery_actions"])
        self.assertEqual(event["propagation"]["mode"], "LOCAL_ONLY")
        self.assertEqual(event["action_kind"], "RECOMMENDATION_ONLY")

    def test_event_replay_is_idempotent(self):
        events = generate_instant_events(evaluate(Inputs()), subject_id="candidate-demo")
        with tempfile.TemporaryDirectory() as directory:
            journal = JsonlEventJournal(Path(directory) / "events.jsonl")
            first = journal.append(events[0])
            replay = journal.append(dict(events[0], created_at=(date.today().isoformat() + "T12:00:00+00:00")))
            self.assertTrue(first["inserted"])
            self.assertFalse(replay["inserted"])
            self.assertEqual(replay["reason"], "IDEMPOTENT_REPLAY")
            self.assertEqual(len(journal.list_events()), 1)

    def test_idempotency_key_reuse_with_different_content_fails_closed(self):
        event = generate_instant_events(evaluate(Inputs()), subject_id="candidate-demo")[0]
        with tempfile.TemporaryDirectory() as directory:
            journal = JsonlEventJournal(Path(directory) / "events.jsonl")
            journal.append(event)
            changed = dict(event, summary="Different semantic event")
            with self.assertRaises(IdempotencyConflict):
                journal.append(changed)

    def test_state_transitions_are_append_only_and_project_current_state(self):
        events = generate_instant_events(evaluate(Inputs()), subject_id="candidate-demo")
        with tempfile.TemporaryDirectory() as directory:
            journal = JsonlEventJournal(Path(directory) / "events.jsonl")
            event = journal.append(events[0])["event"]
            transitioned = journal.transition(event["event_id"], "ACKNOWLEDGED", actor="reviewer", reason="Seen and assigned")
            self.assertTrue(transitioned["inserted"])
            self.assertEqual(journal.list_events()[0]["state"], "ACKNOWLEDGED")
            self.assertEqual(len(journal.list_events(include_history=True)), 2)
            resolved = journal.transition(event["event_id"], "RESOLVED", actor="reviewer", reason="Evidence attached")
            self.assertTrue(resolved["inserted"])
            self.assertEqual(journal.list_events()[0]["state"], "RESOLVED")
            self.assertEqual(len(journal.list_events(include_history=True)), 3)

    def test_noop_state_transition_adds_no_history(self):
        event = generate_instant_events(evaluate(Inputs()), subject_id="candidate-demo")[0]
        with tempfile.TemporaryDirectory() as directory:
            journal = JsonlEventJournal(Path(directory) / "events.jsonl")
            stored = journal.append(event)["event"]
            journal.transition(stored["event_id"], "ACKNOWLEDGED", actor="reviewer", reason="Seen")
            no_op = journal.transition(stored["event_id"], "ACKNOWLEDGED", actor="reviewer", reason="Seen again")
            self.assertFalse(no_op["inserted"])
            self.assertEqual(no_op["reason"], "ALREADY_IN_STATE")
            self.assertEqual(len(journal.list_events(include_history=True)), 2)

    def test_reopen_cycle_does_not_conflict_with_prior_transition_keys(self):
        event = generate_instant_events(evaluate(Inputs()), subject_id="cycle-test")[0]
        with tempfile.TemporaryDirectory() as directory:
            journal = JsonlEventJournal(Path(directory) / "events.jsonl")
            stored = journal.append(event)["event"]
            journal.transition(stored["event_id"], "ACKNOWLEDGED", actor="reviewer", reason="Seen")
            journal.transition(stored["event_id"], "RESOLVED", actor="reviewer", reason="Evidence attached")
            journal.transition(stored["event_id"], "OPEN", actor="reviewer", reason="New evidence contradicts resolution")
            journal.transition(stored["event_id"], "ACKNOWLEDGED", actor="reviewer", reason="Rechecked")
            self.assertEqual(journal.list_events()[0]["state"], "ACKNOWLEDGED")
            self.assertEqual(len(journal.list_events(include_history=True)), 5)

    def test_invalid_event_rejects_missing_timezone(self):
        event = generate_instant_events(evaluate(Inputs()), subject_id="candidate-demo")[0]
        event["observed_at"] = "2026-10-29T12:00:00"
        with tempfile.TemporaryDirectory() as directory:
            journal = JsonlEventJournal(Path(directory) / "events.jsonl")
            with self.assertRaises(ValueError):
                journal.append(event)


if __name__ == "__main__":
    unittest.main()
