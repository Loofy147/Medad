import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from cli import parse_inputs

ENGINE_DIR = Path(__file__).resolve().parent
REPO_ROOT = ENGINE_DIR.parent
SYNTHETIC_INPUTS = {
    "product_name": "synthetic-cli-fixture",
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


class CliTests(unittest.TestCase):
    def test_input_parser_rejects_unknown_fields(self):
        with self.assertRaises(ValueError):
            parse_inputs({"inputs": {"selling_price": 1000, "unknown_cost": 20}})

    def test_cli_requires_explicit_core_inputs_instead_of_silent_defaults(self):
        with tempfile.TemporaryDirectory() as directory:
            input_path = Path(directory) / "partial.json"
            input_path.write_text(json.dumps({"inputs": {"product_name": "partial"}}, ensure_ascii=False), encoding="utf-8")
            result = subprocess.run(
                [sys.executable, str(ENGINE_DIR / "cli.py"), "economics", "--input", str(input_path)],
                cwd=ENGINE_DIR, capture_output=True, text=True, check=False,
            )
            self.assertEqual(result.returncode, 2)
            self.assertIn("defaults are not silently applied", result.stderr)

    def test_economics_command_emits_json_and_keeps_unverified_decision(self):
        with tempfile.TemporaryDirectory() as directory:
            input_path = Path(directory) / "inputs.json"
            input_path.write_text(json.dumps({"inputs": dict(SYNTHETIC_INPUTS, product_name="generic-demo")}, ensure_ascii=False), encoding="utf-8")
            result = subprocess.run(
                [sys.executable, str(ENGINE_DIR / "cli.py"), "economics", "--input", str(input_path)],
                cwd=ENGINE_DIR, capture_output=True, text=True, check=False,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            payload = json.loads(result.stdout)
            self.assertEqual(payload["decision"]["status"], "UNVERIFIED_ECONOMICS")
            self.assertEqual(payload["data_quality"]["grade"], "UNKNOWN")

    def test_instant_command_replays_same_snapshot_without_duplicate_journal_rows(self):
        with tempfile.TemporaryDirectory() as directory:
            input_path = Path(directory) / "inputs.json"
            journal_path = Path(directory) / "events.jsonl"
            input_path.write_text(json.dumps({"inputs": SYNTHETIC_INPUTS, "subject_id": "cli-test"}, ensure_ascii=False), encoding="utf-8")
            command = [
                sys.executable, str(ENGINE_DIR / "cli.py"), "instant",
                "--input", str(input_path), "--journal", str(journal_path),
            ]
            first = subprocess.run(command, cwd=ENGINE_DIR, capture_output=True, text=True, check=False)
            self.assertEqual(first.returncode, 0, first.stderr)
            first_payload = json.loads(first.stdout)
            self.assertGreater(first_payload["inserted_count"], 0)
            second = subprocess.run(command, cwd=ENGINE_DIR, capture_output=True, text=True, check=False)
            self.assertEqual(second.returncode, 0, second.stderr)
            second_payload = json.loads(second.stdout)
            self.assertEqual(second_payload["inserted_count"], 0)
            self.assertEqual(second_payload["replayed_count"], first_payload["generated_count"])
            rows = [line for line in journal_path.read_text(encoding="utf-8").splitlines() if line.strip()]
            self.assertEqual(len(rows), first_payload["generated_count"])

    def test_sensitivity_command_returns_limitation_and_factors(self):
        with tempfile.TemporaryDirectory() as directory:
            input_path = Path(directory) / "inputs.json"
            input_path.write_text(json.dumps({"inputs": SYNTHETIC_INPUTS}, ensure_ascii=False), encoding="utf-8")
            result = subprocess.run(
                [sys.executable, str(ENGINE_DIR / "cli.py"), "sensitivity", "--input", str(input_path)],
                cwd=ENGINE_DIR, capture_output=True, text=True, check=False,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            payload = json.loads(result.stdout)
            self.assertGreaterEqual(len(payload["factors"]), 5)
            self.assertTrue(any("probabilities" in item for item in payload["limitations"]))


if __name__ == "__main__":
    unittest.main()
