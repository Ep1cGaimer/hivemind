"""Opt-in live FalkorDB contract tests.

The default test command never requires a server.  Run this module with
``HIVEMIND_LIVE_TESTS=1`` and explicit FALKORDB_* settings to exercise the
isolated project graph.
"""

from __future__ import annotations

import os
import unittest

from hivemind.api import HiveMindRuntime
from hivemind.auth import Identity
from hivemind.backend import create_store
from hivemind.fixture import BASE_MEMORY_ID, RESERVED_SCOPE_ID, SHARED_SCOPE_ID
from hivemind.gateway import HiveMindGateway
from hivemind.workspace import MemoryWorkspace


LIVE_ENABLED = os.environ.get("HIVEMIND_LIVE_TESTS", "").strip() == "1"
REQUIRED_ENV = ("FALKORDB_HOST", "FALKORDB_PORT", "FALKORDB_GRAPH")


@unittest.skipUnless(
    LIVE_ENABLED,
    "live FalkorDB tests skipped; set HIVEMIND_LIVE_TESTS=1 with FALKORDB_HOST, FALKORDB_PORT, and FALKORDB_GRAPH",
)
class FalkorDBLiveTests(unittest.TestCase):
    """Exercise the same gateway contract against a configured live graph."""

    @classmethod
    def setUpClass(cls):
        missing = [key for key in REQUIRED_ENV if not os.environ.get(key, "").strip()]
        if missing:
            raise unittest.SkipTest(f"live tests require explicit environment variables: {', '.join(missing)}")
        cls.environ = {
            "HIVEMIND_BACKEND": "falkordb",
            **{key: os.environ[key] for key in REQUIRED_ENV},
            "FALKORDB_USERNAME": os.environ.get("FALKORDB_USERNAME", ""),
            "FALKORDB_PASSWORD": os.environ.get("FALKORDB_PASSWORD", ""),
        }

    def setUp(self):
        self.store = create_store(self.environ, reset=True)
        self.gateway = HiveMindGateway(self.store, session_nonce="live-test")

    @staticmethod
    def _memory_ids(result):
        return [item["id"] for item in result.get("memory_versions", [])]

    def test_reset_seed_and_recall_use_the_live_graph(self):
        self.assertEqual(self.store.backend_name, "falkordb")
        self.assertEqual(self.store.snapshot()["counts"], {"nodes": 24, "edges": 35, "memories": 3, "drafts": 0})
        result = self.gateway.recall_context(RESERVED_SCOPE_ID)
        self.assertTrue(result["ok"], result)
        self.assertIn(BASE_MEMORY_ID, self._memory_ids(result))
        self.assertTrue(self.store.check_server())

    def test_evidence_and_exposure_remain_separate(self):
        evidence = self.gateway.inspect_evidence(BASE_MEMORY_ID, max_depth=4)
        self.assertTrue(evidence["ok"], evidence)
        self.assertTrue(evidence["source_passages"])

        exposure = self.gateway.record_exposure("run:live-exposure", BASE_MEMORY_ID)
        self.assertTrue(exposure["ok"], exposure)
        after = self.gateway.inspect_evidence(BASE_MEMORY_ID, max_depth=4)
        self.assertTrue(after["ok"], after)
        self.assertTrue(any("run:live-exposure" in str(item) for item in after["exposure"]))
        self.assertNotIn("run:live-exposure", str(after["support"]))
        self.assertNotIn("READ_MEMORY", str(after["support"]))

    def test_fixed_registry_queries_read_the_persisted_graph(self):
        state = self.store.run_fixed("state", {"node_limit": 64})
        recall = self.store.run_fixed(
            "recall_context",
            {"scope_id": RESERVED_SCOPE_ID, "memory_limit": 8},
        )
        evidence = self.store.run_fixed(
            "inspect_evidence",
            {"memory_id": BASE_MEMORY_ID, "max_depth": 4, "path_limit": 8},
        )

        self.assertTrue(state.result_set)
        self.assertTrue(recall.result_set)
        self.assertTrue(evidence.result_set)

    def test_scoped_correction_is_immutable_and_duplicate_safe(self):
        first = self.gateway.apply_correction(
            BASE_MEMORY_ID,
            SHARED_SCOPE_ID,
            correction_text="The supplied evidence does not establish shared-pool readiness; request a rehearsal before promising readiness.",
        )
        self.assertTrue(first["ok"], first)
        duplicate = self.gateway.apply_correction(
            BASE_MEMORY_ID,
            SHARED_SCOPE_ID,
            correction_text="The supplied evidence does not establish shared-pool readiness; request a rehearsal before promising readiness.",
        )
        self.assertTrue(duplicate["ok"], duplicate)
        self.assertTrue(duplicate["idempotent"])
        self.assertEqual(duplicate["new_memory_id"], first["new_memory_id"])
        conflict = self.gateway.apply_correction(
            BASE_MEMORY_ID,
            SHARED_SCOPE_ID,
            correction_text="A different scoped correction.",
        )
        self.assertFalse(conflict["ok"])
        self.assertEqual(conflict["error"]["code"], "CORRECTION_CONFLICT")
        reserved = self.gateway.recall_context(RESERVED_SCOPE_ID)
        self.assertNotIn(first["new_memory_id"], self._memory_ids(reserved))
        self.assertEqual(self.store.require_node(BASE_MEMORY_ID).version, 1)

    def test_draft_citation_and_persistence_survive_a_new_store_gateway(self):
        correction = self.gateway.apply_correction(BASE_MEMORY_ID, SHARED_SCOPE_ID, reviewer="operator")
        self.assertTrue(correction["ok"], correction)
        correction_id = correction["new_memory_id"]
        draft = self.gateway.save_draft(
            SHARED_SCOPE_ID,
            "Live shared-pool plan",
            "Request and review a shared-pool rehearsal before promising readiness.",
            [correction_id],
        )
        self.assertTrue(draft["ok"], draft)
        self.assertEqual(draft["citations"][0]["memory_id"], correction_id)

        fresh_store = create_store(self.environ)
        fresh_gateway = HiveMindGateway(fresh_store, session_nonce="live-fresh")
        recalled = fresh_gateway.recall_context(SHARED_SCOPE_ID)
        self.assertIn(correction_id, self._memory_ids(recalled))
        self.assertIsNotNone(fresh_store.get_node(draft["draft"]["id"]))

    def test_runtime_health_state_and_reset_are_live_and_latched(self):
        runtime = HiveMindRuntime(environ=self.environ)
        health = runtime.health()
        self.assertTrue(health["ok"], health)
        self.assertEqual(health["backend"], "falkordb")
        self.assertTrue(health["falkordb_adapter"]["server_checked"])
        state = runtime.get_gateway().state()
        self.assertTrue(state["ok"], state)
        self.assertEqual(state["state"]["backend"], "falkordb")
        runtime.get_gateway().apply_correction(BASE_MEMORY_ID, SHARED_SCOPE_ID)
        reset_state = runtime.reset()
        self.assertTrue(reset_state["ok"], reset_state)
        self.assertEqual(reset_state["state"]["counts"], {"nodes": 24, "edges": 35, "memories": 3, "drafts": 0})

    def test_human_workspace_memory_persists_across_live_store_instances(self):
        workspace = MemoryWorkspace(self.store)
        identity = Identity("operator", "Operator", "operator")
        created = workspace.create(identity, "Live team note", "This memory is stored in FalkorDB.", ["live"])
        self.assertTrue(created["ok"], created)
        edited = workspace.edit(identity, created["memory"]["id"], None, "This edited memory is stored in FalkorDB.")
        self.assertTrue(edited["ok"], edited)

        fresh_store = create_store(self.environ)
        fresh_workspace = MemoryWorkspace(fresh_store)
        listed = fresh_workspace.list_memories()
        self.assertEqual(listed["count"], 1)
        self.assertEqual(listed["memories"][0]["version"], 2)
        self.assertEqual(listed["memories"][0]["body"], "This edited memory is stored in FalkorDB.")


if __name__ == "__main__":
    unittest.main()
