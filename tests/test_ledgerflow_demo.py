from pathlib import Path
import tempfile
import unittest

from hivemind.ledgerflow_demo import IMPLEMENTATION_PATH, POLICY_PATH, run_demo


class LedgerFlowDemoTests(unittest.TestCase):
    def test_writer_consumer_challenge_stale_and_provenance_flow(self):
        with tempfile.TemporaryDirectory() as directory:
            result = run_demo(Path(directory) / "ledgerflow")

        self.assertTrue(result["ok"], result)
        self.assertEqual(result["consumer"]["applicability"], "applicable")
        self.assertEqual(result["stale"]["applicability"], "historical_source_changed")
        paths = {item["path"] for item in result["provenance"]["source_bindings"]}
        self.assertEqual(paths, {POLICY_PATH, IMPLEMENTATION_PATH})
        self.assertTrue(result["assertions"]["provenance_keeps_branch_binding"])


if __name__ == "__main__":
    unittest.main()
