import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from cli import parse_inputs

ENGINE_DIR = Path(__file__).resolve().parent
REPO_ROOT = ENGINE_DIR.parent


class CliTests(unittest.TestCase):
    def test_input_parser_rejects_unknown_fields(self):
        with self.assertRaises(ValueError):
            parse_inputs({"inputs": {"selling_price": 1000, "unknown_cost": 20}})

    def test_economics_command_emits_json_and_keeps_unverified_decision(self):
        with tempfile.TemporaryDirectory() as directory:
            input_path = Path(directory) / "inputs.json"
            input_path.write_text(json.dumps({"inputs": {"product_name": "generic-demo"}}, ensure_ascii=False), encoding="utf-8")
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
            input_path.write_text(json.dumps({"inputs": {}, "subject_id": "cli-test"}, ensure_ascii=False), encoding="utf-8")
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
            input_path.write_text(json.dumps({"inputs": {}}, ensure_ascii=False), encoding="utf-8")
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
