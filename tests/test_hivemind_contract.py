import json
import unittest

from hivemind import HiveMindGateway, run_demo, seed_demo_store


RESERVED_SCOPE = "scope:juniper:reserved-pool"
SHARED_SCOPE = "scope:juniper:shared-pool"
QUERY = "overnight refresh"
CORRECTION_TEXT = (
    "The supplied evidence does not establish overnight refresh on Juniper's "
    "shared pool; request a shared-pool rehearsal before promising readiness."
)
OLD_CHAT_SENTINEL = "OLD_CHAT_ONLY_SENTINEL_9F4D"


class HiveMindContractTests(unittest.TestCase):
    def setUp(self):
        self.gateway = HiveMindGateway(seed_demo_store())

    @staticmethod
    def _text(result):
        return json.dumps(result, sort_keys=True).lower()

    @staticmethod
    def _first_memory(result):
        memories = result["memory_versions"]
        if not memories:
            raise AssertionError("expected at least one recalled memory")
        return memories[0]

    @staticmethod
    def _memory_by_id(result, memory_id):
        for memory in result["memory_versions"]:
            if memory.get("id") == memory_id:
                return memory
        raise AssertionError(f"memory {memory_id!r} was not recalled")

    def assert_safe_error(self, result, *codes):
        self.assertIsInstance(result, dict)
        self.assertFalse(result.get("ok"), result)
        error = result.get("error")
        self.assertIsInstance(error, dict, result)
        self.assertIn(str(error.get("code", "")).lower(), {code.lower() for code in codes}, result)
        self.assertTrue(error.get("message"), result)
        self.assertNotIn("traceback", self._text(result))

    def test_seeded_scopes_retain_the_qualified_observation(self):
        reserved = self.gateway.recall_context(RESERVED_SCOPE)
        shared = self.gateway.recall_context(SHARED_SCOPE)

        self.assertTrue(reserved["ok"])
        self.assertEqual(reserved["scope_id"], RESERVED_SCOPE)
        reserved_memory = self._first_memory(reserved)
        self.assertEqual(reserved_memory["scope_id"], RESERVED_SCOPE)
        self.assertIsInstance(reserved_memory["version"], int)
        self.assertTrue(reserved_memory["scope_match"])
        self.assertIn("reserved worker pool", self._text(reserved))
        self.assertIn("shared-pool", self._text(reserved))

        self.assertTrue(shared["ok"])
        self.assertTrue(shared["memory_versions"])
        self.assertIn("reserved worker pool", self._text(shared))
        self.assertTrue(any(not item["scope_match"] for item in shared["memory_versions"]))

    def test_shared_pool_recall_preserves_limitation_and_unknown(self):
        shared = self.gateway.recall_context(SHARED_SCOPE)

        self.assertEqual(shared["status"], "needs-clarification")
        self.assertTrue(shared["needs_clarification"])
        visible = self._text(shared)
        self.assertIn("reserved worker pool", visible)
        self.assertTrue("not exercised" in visible or "unknown" in visible)
        self.assertNotIn("shared-pool is ready", visible)

    def test_evidence_inspection_is_bounded_and_reaches_exact_source(self):
        reserved = self.gateway.recall_context(RESERVED_SCOPE)
        memory = self._first_memory(reserved)

        evidence = self.gateway.inspect_evidence(memory["id"], max_hops=4)

        self.assertTrue(evidence["ok"])
        self.assertTrue(evidence["bounded"])
        self.assertLessEqual(len(evidence["path"]), 8)
        self.assertEqual(evidence["memory_id"], memory["id"])
        source_nodes = [node for node in evidence["path"] if node.get("kind") == "SourcePassage"]
        self.assertEqual(len(source_nodes), 1, evidence)
        self.assertIn("reserved worker pool", source_nodes[0]["text"].lower())
        self.assertIn("shared-pool", source_nodes[0]["text"].lower())

    def test_read_exposure_does_not_become_support(self):
        reserved = self.gateway.recall_context(RESERVED_SCOPE)
        memory = self._first_memory(reserved)

        receipt = self.gateway.record_exposure("run:read-only", memory["id"])
        self.assertTrue(receipt["ok"])
        self.assertEqual(receipt["relation"], "READ_MEMORY")

        evidence = self.gateway.inspect_evidence(memory["id"], max_hops=4)
        self.assertTrue(evidence["ok"])
        self.assertIn("run:read-only", self._text(evidence["exposure"]))
        self.assertNotIn("run:read-only", self._text(evidence["support"]))
        self.assertNotIn("READ_MEMORY", self._text(evidence["support"]))

    def test_correction_creates_an_immutable_version_and_is_duplicate_safe(self):
        reserved_before = self.gateway.recall_context(RESERVED_SCOPE)
        old_memory = dict(self._first_memory(reserved_before))

        applied = self.gateway.apply_correction(
            old_memory["id"], SHARED_SCOPE, correction_text=CORRECTION_TEXT
        )

        self.assertTrue(applied["ok"])
        self.assertNotEqual(applied["new_memory_id"], old_memory["id"])
        self.assertGreater(applied["version"], old_memory["version"])
        self.assertEqual(applied["scope"], SHARED_SCOPE)
        self.assertEqual(applied["supersedes"], old_memory["id"])

        reserved_after = self.gateway.recall_context(RESERVED_SCOPE)
        old_after = self._memory_by_id(reserved_after, old_memory["id"])
        self.assertEqual(old_after["version"], old_memory["version"])
        self.assertEqual(old_after["qualified_text"], old_memory["qualified_text"])

        duplicate = self.gateway.apply_correction(
            old_memory["id"], SHARED_SCOPE, correction_text=CORRECTION_TEXT
        )
        self.assertTrue(duplicate.get("ok"))
        self.assertTrue(duplicate.get("idempotent"))
        self.assertEqual(duplicate["new_memory_id"], applied["new_memory_id"])

        changed = self.gateway.apply_correction(
            old_memory["id"], SHARED_SCOPE, correction_text="A different scoped correction."
        )
        self.assert_safe_error(changed, "correction_conflict")

        target = self.gateway.recall_context(SHARED_SCOPE)
        target_ids = [item["id"] for item in target["memory_versions"]]
        self.assertEqual(target_ids.count(applied["new_memory_id"]), 1)

    def test_correction_is_limited_to_juniper_shared_pool(self):
        reserved = self.gateway.recall_context(RESERVED_SCOPE)
        old_memory = self._first_memory(reserved)
        applied = self.gateway.apply_correction(
            old_memory["id"], SHARED_SCOPE, correction_text=CORRECTION_TEXT
        )
        self.assertTrue(applied["ok"])

        shared_after = self.gateway.recall_context(SHARED_SCOPE)
        reserved_after = self.gateway.recall_context(RESERVED_SCOPE)
        self.assertIn(CORRECTION_TEXT.lower(), self._text(shared_after))
        self.assertIn(applied["new_memory_id"], self._text(shared_after))
        self.assertNotIn(CORRECTION_TEXT.lower(), self._text(reserved_after))
        self.assertNotIn(applied["new_memory_id"], self._text(reserved_after))

    def test_cold_demo_starts_a_new_session_and_changes_a_cited_local_draft(self):
        first_demo = run_demo()
        second_demo = run_demo()

        self.assertTrue(first_demo["consumer_run"]["cold"])
        self.assertNotEqual(first_demo["writer_run"]["session_id"], first_demo["consumer_run"]["session_id"])
        self.assertNotEqual(first_demo["consumer_run"]["session_id"], second_demo["consumer_run"]["session_id"])
        self.assertFalse(first_demo["old_chat_sentinel_present"])
        self.assertNotIn(OLD_CHAT_SENTINEL, self._text(first_demo))
        self.assertTrue(first_demo["consumer_recall"]["ok"])

        before = first_demo["draft_before"]
        after = first_demo["draft_after"]
        self.assertNotEqual(before["text"], after["text"])
        self.assertIn("rehearsal", after["text"].lower())
        self.assertTrue(after["citations"])
        for citation in after["citations"]:
            self.assertTrue(citation.get("memory_id"), citation)
            self.assertTrue(citation.get("source_id"), citation)
        selected_id = first_demo["cold_selected_memory_id"]
        self.assertIn(selected_id, first_demo["consumer_recall"]["exposure"]["returned_version_ids"])
        self.assertEqual(after["citations"][0]["memory_id"], selected_id)

    def test_invalid_inputs_and_unreviewed_memory_are_safe(self):
        self.assert_safe_error(self.gateway.recall_context("not-a-real-scope"), "SCOPE_NOT_FOUND")
        self.assert_safe_error(self.gateway.inspect_evidence("memory:does-not-exist", max_hops=4), "memory_not_found")
        self.assert_safe_error(self.gateway.record_exposure("run:invalid", "memory:does-not-exist"), "memory_not_found")

        reserved = self.gateway.recall_context(RESERVED_SCOPE)
        memory = self._first_memory(reserved)
        self.assert_safe_error(
            self.gateway.apply_correction(memory["id"], "not-a-real-scope", correction_text=CORRECTION_TEXT),
            "scope_not_found",
        )


if __name__ == "__main__":
    unittest.main()
