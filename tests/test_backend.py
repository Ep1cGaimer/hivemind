import os
from pathlib import Path
import subprocess
import sys
import unittest
from unittest.mock import patch

from hivemind.api import HiveMindRuntime
from hivemind.backend import BackendSelectionError, create_store, select_backend
from hivemind.fixture import seed_demo_store


class BackendFactoryTests(unittest.TestCase):
    def test_unset_backend_defaults_to_the_existing_seeded_memory_store(self):
        store = create_store({})

        self.assertEqual(store.backend_name, "memory")
        self.assertEqual(store.snapshot(), seed_demo_store().snapshot())

    def test_explicit_memory_selects_the_existing_seeded_memory_store(self):
        store = create_store({"HIVEMIND_BACKEND": "memory"})

        self.assertEqual(store.backend_name, "memory")
        self.assertTrue(store.memories())

    def test_blank_and_case_whitespace_backend_values_stay_in_memory_mode(self):
        self.assertEqual(select_backend({"HIVEMIND_BACKEND": "  MEMORY  "}), "memory")
        self.assertEqual(select_backend({"HIVEMIND_BACKEND": "   "}), "memory")

    def test_unknown_backend_has_a_stable_invalid_code(self):
        with self.assertRaises(BackendSelectionError) as context:
            create_store({"HIVEMIND_BACKEND": "redis"})

        self.assertEqual(context.exception.code, "INVALID_BACKEND")

    def test_falkordb_without_connection_settings_has_a_stable_config_code(self):
        with self.assertRaises(BackendSelectionError) as context:
            create_store({"HIVEMIND_BACKEND": "falkordb"})

        self.assertEqual(context.exception.code, "INVALID_FALKORDB_CONFIG")

    def test_explicit_falkordb_fails_without_falling_back_to_memory(self):
        with self.assertRaises(BackendSelectionError) as context:
            create_store({"HIVEMIND_BACKEND": "falkordb"})

        self.assertIn("no fallback to memory", str(context.exception).lower())

    def test_runtime_latches_backend_selection_across_environment_changes(self):
        with patch.dict(os.environ, {"HIVEMIND_BACKEND": "memory"}, clear=False):
            runtime = HiveMindRuntime()
        with patch.dict(os.environ, {"HIVEMIND_BACKEND": "falkordb"}, clear=False):
            state = runtime.reset()

        self.assertEqual(state["state"]["backend"], "memory")

    def test_entry_points_fail_before_startup_without_traceback_or_stdout(self):
        root = Path(__file__).resolve().parents[1]
        environment = os.environ.copy()
        environment["HIVEMIND_BACKEND"] = "falkordb"
        for module, extra_args in (("hivemind", ["--port", "0"]), ("hivemind.mcp_server", [])):
            with self.subTest(module=module):
                result = subprocess.run(
                    [sys.executable, "-m", module, *extra_args],
                    cwd=root,
                    env=environment,
                    input="",
                    capture_output=True,
                    text=True,
                    timeout=10,
                    check=False,
                )
                self.assertEqual(result.returncode, 2)
                self.assertEqual(result.stdout, "")
                self.assertIn("INVALID_FALKORDB_CONFIG", result.stderr)
                self.assertNotIn("Traceback", result.stderr)


if __name__ == "__main__":
    unittest.main()
