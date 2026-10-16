#!/usr/bin/env python3
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import common


class PipelineTests(unittest.TestCase):
    def test_statute_url(self):
        self.assertEqual(
            common.build_url("Minnesota Statutes", "Minn. Statutes 2025 546.07"),
            "https://www.revisor.mn.gov/statutes/cite/546.07",
        )

    def test_rule_url_without_year(self):
        self.assertEqual(
            common.build_url("Minnesota Rules", "Minn. Rules 7515.0440"),
            "https://www.revisor.mn.gov/rules/cite/7515.0440",
        )

    def test_rule_url_with_year(self):
        self.assertEqual(
            common.build_url("Minnesota Rules", "Minn. Rules 2025 7515.0440"),
            "https://www.revisor.mn.gov/rules/cite/7515.0440",
        )

    def test_alphanumeric_section(self):
        self.assertEqual(
            common.normalize_citation("Minn. Statutes 2025 336.1-201"),
            "336.1-201",
        )

    def test_whitespace(self):
        self.assertEqual(common.clean(" A \n B "), "A B")

    def test_hash(self):
        self.assertEqual(common.sha256("test"), common.sha256("test"))
        self.assertNotEqual(common.sha256("test"), common.sha256("test2"))

    def test_history_logging(self):
        with tempfile.TemporaryDirectory() as directory:
            history = Path(directory) / "change_history.jsonl"
            with patch.object(common, "HISTORY_FILE", history):
                common.log_event(
                    "local_test",
                    url="https://example.com",
                    message="isolated test",
                )
            rows = [
                json.loads(line)
                for line in history.read_text(encoding="utf-8").splitlines()
            ]
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]["event_type"], "local_test")

    def test_retry_policy(self):
        adapter = common.SESSION.get_adapter("https://")
        self.assertIn(503, adapter.max_retries.status_forcelist)
        self.assertGreater(adapter.max_retries.total, 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
