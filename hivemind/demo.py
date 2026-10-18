"""Cold-agent Juniper walkthrough used by the local API and smoke checks."""

from __future__ import annotations

from typing import Any

from .fixture import (
    BASE_MEMORY_ID,
    RESERVED_SCOPE_ID,
    SHARED_SCOPE_ID,
    SOURCE_PASSAGE_ID,
    SUMMARY_A_MEMORY_ID,
    SUMMARY_B_MEMORY_ID,
)
from .gateway import HiveMindGateway
from .fixture import seed_demo_store


def main():
    """Run the isolated historical regression without shared-service routes."""
    import json
    result = run_cold_agent_walkthrough(HiveMindGateway(seed_demo_store()))
    print(json.dumps(result, indent=2))
    return 0 if result.get('ok') else 1


def _failed(result: Any) -> bool:
    return not isinstance(result, dict) or result.get("ok") is not True


def _failure(step: str, result: Any, steps: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "ok": False,
        "scenario": "juniper-overnight-refresh",
        "synthetic": True,
        "failed_step": step,
        "steps": steps,
        "error": result.get("error", {"code": "STEP_FAILED", "message": "A demo step failed"}) if isinstance(result, dict) else {"code": "STEP_FAILED", "message": "A demo step returned a non-object"},
    }


def run_cold_agent_walkthrough(gateway: HiveMindGateway) -> dict[str, Any]:
    """Run the complete source -> correction -> cold draft path.

    The returned object keeps the intermediate tool results visible so a human
    can inspect the source/version/scope bindings and the isolation assertion.
    """

    steps: list[dict[str, Any]] = []
    reserved_before = gateway.recall_context(RESERVED_SCOPE_ID)
    if _failed(reserved_before):
        return _failure("reserved_recall", reserved_before, steps)
    steps.append(
        {
            "step": "qualified_source_recall",
            "scope_id": RESERVED_SCOPE_ID,
            "memory_ids": [item["id"] for item in reserved_before["memory_versions"]],
            "unknowns": reserved_before["unknowns"],
            "completeness": reserved_before["completeness"],
        }
    )

    evidence = gateway.inspect_evidence(SUMMARY_B_MEMORY_ID, max_depth=4)
    if _failed(evidence):
        return _failure("evidence_inspection", evidence, steps)
    source_ids = sorted({source["id"] for source in evidence["source_passages"]})
    steps.append(
        {
            "step": "bounded_evidence_inspection",
            "memory_id": SUMMARY_B_MEMORY_ID,
            "source_ids": source_ids,
            "support_paths": evidence["support_paths"],
            "completeness": evidence["completeness"],
        }
    )

    shared_before = gateway.recall_context(SHARED_SCOPE_ID)
    if _failed(shared_before):
        return _failure("shared_scope_gap", shared_before, steps)
    question = "Which worker pool will the Juniper walkthrough use?"
    steps.append(
        {
            "step": "condition_specific_question",
            "question": question,
            "scope_id": SHARED_SCOPE_ID,
            "unknowns": shared_before["unknowns"],
            "memory_ids_before_correction": [item["id"] for item in shared_before["memory_versions"]],
        }
    )

    correction_result = gateway.apply_correction(BASE_MEMORY_ID, SHARED_SCOPE_ID, reviewer="operator")
    if _failed(correction_result):
        return _failure("operator_correction", correction_result, steps)
    correction_id = correction_result["correction"]["id"]
    steps.append(
        {
            "step": "immutable_scoped_correction",
            "correction_id": correction_id,
            "base_memory_id": BASE_MEMORY_ID,
            "scope_id": SHARED_SCOPE_ID,
            "review": correction_result["review"],
            "immutable": correction_result["immutable"],
            "supersedes": correction_result["supersedes"],
        }
    )

    # A new gateway object represents a genuinely cold consumer.  Only the
    # persisted graph is reused; no result from the earlier role is injected as
    # hidden chat context.
    cold_gateway = HiveMindGateway(gateway.store)
    shared_after = cold_gateway.recall_context(SHARED_SCOPE_ID)
    if _failed(shared_after):
        return _failure("cold_recall", shared_after, steps)
    cold_correction_ids = [
        item["id"]
        for item in shared_after.get("memory_versions", [])
        if item.get("kind") == "correction" and item.get("scope_id") == SHARED_SCOPE_ID and item.get("scope_match") is True
    ]
    if not cold_correction_ids:
        return _failure(
            "cold_recall_missing_correction",
            {"ok": False, "error": {"code": "COLD_RECALL_MISSING_CORRECTION", "message": "The cold recall did not return the scoped correction"}},
            steps,
        )
    cold_correction_id = cold_correction_ids[0]
    steps.append(
        {
            "step": "cold_consumer_recall",
            "scope_id": SHARED_SCOPE_ID,
            "memory_ids": [item["id"] for item in shared_after["memory_versions"]],
            "selected_correction_id": cold_correction_id,
            "unknowns": shared_after["unknowns"],
            "exposure": shared_after["exposure"],
            "completeness": shared_after["completeness"],
        }
    )

    draft_result = cold_gateway.save_draft(
        SHARED_SCOPE_ID,
        "Juniper shared-pool walkthrough plan",
        "Do not claim overnight refresh readiness yet. Schedule and review a shared-pool rehearsal, then update the local readiness statement using the scoped correction.",
        [cold_correction_id],
    )
    if _failed(draft_result):
        return _failure("local_draft", draft_result, steps)
    steps.append(
        {
            "step": "cited_local_draft",
            "draft_id": draft_result["draft"]["id"],
            "scope_id": SHARED_SCOPE_ID,
            "citations": draft_result["citations"],
            "allowed_local_action": draft_result["draft"]["allowed_local_action"],
            "external_side_effect": draft_result["external_side_effect"],
        }
    )

    reserved_after = cold_gateway.recall_context(RESERVED_SCOPE_ID)
    if _failed(reserved_after):
        return _failure("scope_isolation_check", reserved_after, steps)
    reserved_ids = {item["id"] for item in reserved_after["memory_versions"]}
    shared_ids = {item["id"] for item in shared_after["memory_versions"]}
    all_summary_sources = set()
    for memory_id in (SUMMARY_A_MEMORY_ID, SUMMARY_B_MEMORY_ID):
        inspection = cold_gateway.inspect_evidence(memory_id, max_depth=4)
        if inspection.get("ok"):
            all_summary_sources.update(source["id"] for source in inspection["source_passages"])
    steps.append(
        {
            "step": "scope_isolation_check",
            "reserved_scope_id": RESERVED_SCOPE_ID,
            "shared_scope_id": SHARED_SCOPE_ID,
            "correction_visible_in_shared_scope": correction_id in shared_ids,
            "correction_visible_in_reserved_scope": correction_id in reserved_ids,
            "base_still_present_in_reserved_scope": BASE_MEMORY_ID in reserved_ids,
        }
    )

    read_is_support = any(
        relationship["type"] in {"READ_MEMORY", "READ_PASSAGE"}
        for path in evidence["support_paths"]
        for relationship in path["relationships"]
    )
    assertions = {
        "source_is_synthetic": True,
        "summaries_share_source_observation": all_summary_sources == {SOURCE_PASSAGE_ID},
        "repeated_summaries_are_not_independent_support": len(all_summary_sources) == 1,
        "unknown_shared_pool_preserved": any("shared" in unknown.lower() for unknown in shared_after["unknowns"]),
        "correction_recalled_after_cold_restart": cold_correction_id in shared_ids,
        "draft_cites_correction_version": any(item.get("memory_id") == cold_correction_id for item in draft_result["citations"]),
        "correction_immutable": correction_result["immutable"] is True,
        "correction_does_not_leak_to_reserved_scope": correction_id not in reserved_ids,
        "base_remains_in_reserved_scope": BASE_MEMORY_ID in reserved_ids,
        "read_edges_are_not_support": read_is_support is False and evidence["support_policy"]["read_edges_are_support"] is False,
        "cold_consumer_used_persisted_graph": True,
        "no_external_side_effect": draft_result["external_side_effect"] is False,
        "bounded_evidence": evidence["completeness"]["max_depth"] <= 4,
    }
    return {
        "ok": all(assertions.values()),
        "scenario": "juniper-overnight-refresh",
        "synthetic": True,
        "backend": getattr(gateway.store, "backend_name", "unknown"),
        "question": question,
        "steps": steps,
        "cold_consumer": {
            "fresh_gateway_instance": True,
            "old_chat_context_supplied": False,
            "scope_id": SHARED_SCOPE_ID,
            "recalled_memory_ids": sorted(shared_ids),
            "draft_id": draft_result["draft"]["id"],
        },
        "correction": correction_result,
        "draft": draft_result,
        "assertions": assertions,
        "state_counts": gateway.store.snapshot()["counts"],
    }


def run_demo() -> dict[str, Any]:
    """Return the compact cross-agent cold-handoff demo contract.

    This is intentionally a fresh process-shaped replay for each call.  The
    graph fixture is deterministic, while session IDs are unique so callers can
    prove that the consumer did not reuse the writer's conversation state.
    """

    gateway = HiveMindGateway(seed_demo_store())
    writer = gateway.store.get_node("run:fixture:validation-writer")
    writer_session = getattr(writer, "session_id", "unknown-writer-session")
    base_recall = gateway.recall_context(RESERVED_SCOPE_ID)
    if not base_recall.get("ok"):
        return base_recall
    before = {
        "title": "Juniper walkthrough plan",
        "text": "Overnight refresh is ready for the Juniper walkthrough.",
        "citations": [],
        "scope_id": SHARED_SCOPE_ID,
    }
    correction_text = (
        "The supplied evidence does not establish overnight refresh on Juniper's "
        "shared pool; request a shared-pool rehearsal before promising readiness."
    )
    correction = gateway.apply_correction(
        BASE_MEMORY_ID,
        SHARED_SCOPE_ID,
        correction_text=correction_text,
        reviewer="operator",
    )
    if not correction.get("ok"):
        return correction
    correction_id = correction["correction"]["id"]
    cold_gateway = HiveMindGateway(gateway.store)
    cold_recall = cold_gateway.recall_context(SHARED_SCOPE_ID)
    if not cold_recall.get("ok"):
        return cold_recall
    cold_correction_ids = [
        item["id"]
        for item in cold_recall.get("memory_versions", [])
        if item.get("kind") == "correction" and item.get("scope_id") == SHARED_SCOPE_ID and item.get("scope_match") is True
    ]
    if not cold_correction_ids:
        return {"ok": False, "error": {"code": "COLD_RECALL_MISSING_CORRECTION", "message": "The cold recall did not return the scoped correction"}}
    cold_correction_id = cold_correction_ids[0]
    consumer_run_id = cold_recall.get("exposure", {}).get("requesting_run_id")
    consumer_run = gateway.store.get_node(consumer_run_id) if consumer_run_id else None
    consumer_session = getattr(consumer_run, "session_id", "unknown-consumer-session")
    draft = cold_gateway.save_draft(
        SHARED_SCOPE_ID,
        "Juniper shared-pool walkthrough plan",
        "Request a shared-pool rehearsal before promising overnight refresh readiness.",
        [cold_correction_id],
    )
    if not draft.get("ok"):
        return draft
    after = {
        "title": draft["draft"]["title"],
        "text": draft["draft"]["body"],
        "citations": draft["citations"],
        "scope_id": SHARED_SCOPE_ID,
    }
    return {
        "ok": True,
        "scenario": "juniper-overnight-refresh",
        "synthetic": True,
        "writer_run": {"session_id": writer_session, "role": "engineering-writer"},
        "consumer_run": {
            "session_id": consumer_session,
            "run_id": consumer_run_id,
            "role": getattr(consumer_run, "role", "planning-consumer"),
            "cold": True,
        },
        "old_chat_sentinel_present": False,
        "draft_before": before,
        "draft_after": after,
        "consumer_recall": cold_recall,
        "cold_selected_memory_id": cold_correction_id,
        "correction": correction,
        "evidence": gateway.inspect_evidence(correction_id, max_depth=4),
        "state_counts": gateway.store.snapshot()["counts"],
    }


if __name__ == '__main__':
    raise SystemExit(main())
