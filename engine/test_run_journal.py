import json
import tempfile
import unittest
from pathlib import Path

from run_journal import DecisionRunJournal, RunIdConflict
from workflow import build_decision_run

REPO_ROOT = Path(__file__).resolve().parent.parent
TEMPLATE_PATH = REPO_ROOT / "docs" / "examples" / "decision-run.template.json"


def sample_report(run_id: str, *, selling_price: float = 2900.0) -> dict:
    payload = json.loads(TEMPLATE_PATH.read_text(encoding="utf-8"))
    payload["run_id"] = run_id
    payload["code_revision"] = "test-revision"
    payload["inputs"]["selling_price"] = selling_price
    return build_decision_run(payload)


class DecisionRunJournalTests(unittest.TestCase):
    def test_append_and_replay_are_idempotent_even_if_run_created_at_differs(self):
        report_a = sample_report("journal-run-1")
        report_b = sample_report("journal-run-1")
        self.assertNotEqual(report_a["run_manifest"]["created_at"], report_b["run_manifest"]["created_at"])
        self.assertEqual(report_a["run_manifest"]["report_hash"], report_b["run_manifest"]["report_hash"])

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "runs.jsonl"
            journal = DecisionRunJournal(path)
            first = journal.append(report_a)
            replay = journal.append(report_b)
            self.assertTrue(first["inserted"])
            self.assertFalse(replay["inserted"])
            self.assertEqual(replay["reason"], "IDEMPOTENT_REPLAY")
            self.assertEqual(len(journal.list_runs()), 1)
            self.assertEqual(journal.get("journal-run-1")["report_hash"], report_a["run_manifest"]["report_hash"])

    def test_run_id_reuse_with_changed_input_fails_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            journal = DecisionRunJournal(Path(directory) / "runs.jsonl")
            journal.append(sample_report("reused-run", selling_price=2900))
            with self.assertRaises(RunIdConflict):
                journal.append(sample_report("reused-run", selling_price=3100))

    def test_record_checksum_detects_accidental_mutation(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "runs.jsonl"
            journal = DecisionRunJournal(path)
            journal.append(sample_report("checksum-run"))
            record = json.loads(path.read_text(encoding="utf-8"))
            record["report"]["decision"]["stage"] = "ELIGIBLE_FOR_BOUNDED_TEST"
            path.write_text(json.dumps(record, ensure_ascii=False) + "\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "checksum mismatch"):
                journal.list_runs()

    def test_journal_rejects_report_claiming_authorization(self):
        report = sample_report("unauthorized-run")
        report["decision"]["authorization_granted"] = True
        with tempfile.TemporaryDirectory() as directory:
            journal = DecisionRunJournal(Path(directory) / "runs.jsonl")
            with self.assertRaisesRegex(ValueError, "authorization"):
                journal.append(report)

    def test_journal_rejects_corrupted_json_line(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "runs.jsonl"
            path.write_text("{not-json}\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "Corrupt run journal JSON"):
                DecisionRunJournal(path).list_runs()


if __name__ == "__main__":
    unittest.main()
