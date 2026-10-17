"""Deterministic synthetic Juniper graph fixture.

The fixture is intentionally small: one source passage, two exact scopes, one
qualified base memory, two summaries derived from that same source, and no
pre-seeded correction.  The operator correction is created by the gateway so
its immutable write path is exercised by the demo.
"""

from __future__ import annotations

from typing import Any

from .domain import (
    AgentRun,
    Claim,
    CompanyEntity,
    MemoryUse,
    MemoryVersion,
    Review,
    Scope,
    SourcePassage,
    SupportProposal,
    content_hash,
)
from .store import InMemoryGraphStore


TENANT_ID = "tenant:demo"
PROJECT_ID = "project:hivemind"
JUNIPER_COMPANY_ID = "company:juniper"
OVERNIGHT_REFRESH_ID = "capability:overnight-refresh"
RESERVED_SCOPE_ID = "scope:juniper:reserved-pool"
SHARED_SCOPE_ID = "scope:juniper:shared-pool"
SOURCE_PASSAGE_ID = "source:juniper:overnight-refresh:v1"
BASE_MEMORY_ID = "memory:juniper:overnight-refresh:reserved:v1"
SUMMARY_A_MEMORY_ID = "memory:juniper:overnight-refresh:summary-a:v1"
SUMMARY_B_MEMORY_ID = "memory:juniper:overnight-refresh:summary-b:v1"

SOURCE_TEXT = (
    "Juniper's overnight refresh completed successfully during the 2026-10-14 pilot "
    "on a reserved worker pool. The shared-pool behavior was not exercised, so "
    "applicability to a shared pool is unknown."
)
UNKNOWN_SHARED_POOL = "Whether overnight refresh applies to Juniper's shared worker pool is unknown; it was not exercised."


def _review(
    review_id: str,
    target_id: str,
    proposal_id: str,
    memory_id: str,
    scope_id: str,
    source_ids: tuple[str, ...],
    binding: Any,
) -> Review:
    return Review(
        id=review_id,
        tenant_id=TENANT_ID,
        project_id=PROJECT_ID,
        reviewed_target_id=target_id,
        proposal_id=proposal_id,
        memory_version_id=memory_id,
        scope_id=scope_id,
        reviewer="validation-reviewer",
        state="accepted",
        binding_hash=content_hash(binding),
        cited_source_ids=source_ids,
        accepted_at="2026-10-15T09:00:00Z",
    )


def seed_demo_store(
    store: InMemoryGraphStore | Any | None = None,
    *,
    clear: bool = True,
) -> Any:
    """Return a fresh deterministic in-memory store for the Juniper scenario.

    Passing a store is supported for API reset code.  The default clears it
    before seeding; ``clear=False`` performs an idempotent replay for the live
    FalkorDB profile and preserves corrections/drafts already stored there.
    """

    graph = store if store is not None else InMemoryGraphStore(tenant_id=TENANT_ID, project_id=PROJECT_ID)
    if graph.tenant_id != TENANT_ID or graph.project_id != PROJECT_ID:
        raise ValueError("The Juniper fixture requires the demo tenant/project binding")
    if clear:
        graph.clear()

    company = CompanyEntity(
        id=JUNIPER_COMPANY_ID,
        canonical_id="juniper",
        kind="account",
        name="Juniper",
        tenant_id=TENANT_ID,
        project_id=PROJECT_ID,
        aliases=("Juniper", "Juniper pilot"),
    )
    capability = CompanyEntity(
        id=OVERNIGHT_REFRESH_ID,
        canonical_id="overnight-refresh",
        kind="capability",
        name="Overnight refresh",
        tenant_id=TENANT_ID,
        project_id=PROJECT_ID,
        aliases=("overnight refresh", "refresh window"),
    )
    reserved_scope = Scope(
        id=RESERVED_SCOPE_ID,
        tenant_id=TENANT_ID,
        project_id=PROJECT_ID,
        company_id=JUNIPER_COMPANY_ID,
        stage="technical-walkthrough",
        environment="reserved-worker-pool",
        qualifiers={"pool_type": "reserved", "customer": "Juniper"},
        unknowns=(UNKNOWN_SHARED_POOL,),
        valid_from="2026-10-14T00:00:00Z",
    )
    shared_scope = Scope(
        id=SHARED_SCOPE_ID,
        tenant_id=TENANT_ID,
        project_id=PROJECT_ID,
        company_id=JUNIPER_COMPANY_ID,
        stage="technical-walkthrough",
        environment="shared-worker-pool",
        qualifiers={"pool_type": "shared", "customer": "Juniper"},
        unknowns=(UNKNOWN_SHARED_POOL,),
        valid_from="2026-10-14T00:00:00Z",
    )
    source = SourcePassage(
        id=SOURCE_PASSAGE_ID,
        tenant_id=TENANT_ID,
        project_id=PROJECT_ID,
        artifact_id="artifact:juniper-pilot-notes",
        version="v1",
        content_hash=content_hash(SOURCE_TEXT),
        span_start=0,
        span_end=len(SOURCE_TEXT),
        text=SOURCE_TEXT,
        source_uri="synthetic://juniper/pilot-notes#overnight-refresh",
        observed_at="2026-10-14T22:00:00Z",
        source_stated_at="2026-10-14T21:45:00Z",
        scope_id=RESERVED_SCOPE_ID,
    )

    writer_run = AgentRun(
        id="run:fixture:validation-writer",
        tenant_id=TENANT_ID,
        project_id=PROJECT_ID,
        role="validation-writer",
        session_id="session:fixture:validation",
        input_manifest_hash=content_hash([SOURCE_PASSAGE_ID]),
        started_at="2026-10-14T22:05:00Z",
        context_coverage="source-read",
    )
    summary_a_run = AgentRun(
        id="run:fixture:summary-a",
        tenant_id=TENANT_ID,
        project_id=PROJECT_ID,
        role="engineering-summary",
        session_id="session:fixture:summary-a",
        input_manifest_hash=content_hash([BASE_MEMORY_ID, SOURCE_PASSAGE_ID]),
        started_at="2026-10-14T22:30:00Z",
        context_coverage="partial",
    )
    summary_b_run = AgentRun(
        id="run:fixture:summary-b",
        tenant_id=TENANT_ID,
        project_id=PROJECT_ID,
        role="support-summary",
        session_id="session:fixture:summary-b",
        input_manifest_hash=content_hash([BASE_MEMORY_ID, SOURCE_PASSAGE_ID]),
        started_at="2026-10-14T23:00:00Z",
        context_coverage="partial",
    )
    exposure_a_run = AgentRun(
        id="run:fixture:exposure-a",
        tenant_id=TENANT_ID,
        project_id=PROJECT_ID,
        role="engineering-summary",
        session_id="session:fixture:summary-a",
        input_manifest_hash=content_hash([BASE_MEMORY_ID]),
        started_at="2026-10-14T22:25:00Z",
        context_coverage="memory-exposure-only",
    )
    exposure_b_run = AgentRun(
        id="run:fixture:exposure-b",
        tenant_id=TENANT_ID,
        project_id=PROJECT_ID,
        role="support-summary",
        session_id="session:fixture:summary-b",
        input_manifest_hash=content_hash([BASE_MEMORY_ID]),
        started_at="2026-10-14T22:55:00Z",
        context_coverage="memory-exposure-only",
    )

    base_claim_id = "claim:juniper:overnight-refresh:reserved:v1"
    summary_a_claim_id = "claim:juniper:overnight-refresh:summary-a:v1"
    summary_b_claim_id = "claim:juniper:overnight-refresh:summary-b:v1"
    base_proposal_id = "proposal:juniper:overnight-refresh:reserved:v1"
    summary_a_proposal_id = "proposal:juniper:overnight-refresh:summary-a:v1"
    summary_b_proposal_id = "proposal:juniper:overnight-refresh:summary-b:v1"

    base_claim = Claim(
        id=base_claim_id,
        tenant_id=TENANT_ID,
        project_id=PROJECT_ID,
        qualified_proposition="Overnight refresh completed on Juniper's reserved worker pool; shared-pool applicability is unknown.",
        entity_id=OVERNIGHT_REFRESH_ID,
        scope_id=RESERVED_SCOPE_ID,
        status="reviewed_assertion",
        exact_quote_refs=(SOURCE_PASSAGE_ID,),
    )
    summary_a_claim = Claim(
        id=summary_a_claim_id,
        tenant_id=TENANT_ID,
        project_id=PROJECT_ID,
        qualified_proposition="Engineering reported overnight refresh as ready for the Juniper walkthrough, qualified to the reserved pool and not to a shared pool.",
        entity_id=OVERNIGHT_REFRESH_ID,
        scope_id=RESERVED_SCOPE_ID,
        status="reviewed_assertion",
        exact_quote_refs=(SOURCE_PASSAGE_ID,),
    )
    summary_b_claim = Claim(
        id=summary_b_claim_id,
        tenant_id=TENANT_ID,
        project_id=PROJECT_ID,
        qualified_proposition="Support summarized overnight refresh as ready after the pilot, while retaining the reserved-pool condition and shared-pool unknown.",
        entity_id=OVERNIGHT_REFRESH_ID,
        scope_id=RESERVED_SCOPE_ID,
        status="reviewed_assertion",
        exact_quote_refs=(SOURCE_PASSAGE_ID,),
    )
    base_proposal = SupportProposal(
        id=base_proposal_id,
        tenant_id=TENANT_ID,
        project_id=PROJECT_ID,
        claim_id=base_claim_id,
        relation_kind="supports",
        cited_memory_ids=(),
        cited_passage_ids=(SOURCE_PASSAGE_ID,),
        proposing_run_id=writer_run.id,
        rationale="The exact source passage records the reserved-pool observation and explicitly names the untested shared-pool condition.",
        created_at="2026-10-14T22:06:00Z",
        status="accepted_proposal",
    )
    summary_a_proposal = SupportProposal(
        id=summary_a_proposal_id,
        tenant_id=TENANT_ID,
        project_id=PROJECT_ID,
        claim_id=summary_a_claim_id,
        relation_kind="supports",
        cited_memory_ids=(BASE_MEMORY_ID,),
        cited_passage_ids=(),
        proposing_run_id=summary_a_run.id,
        rationale="This summary derives from the qualified base memory; it is not an independent source observation.",
        created_at="2026-10-14T22:31:00Z",
        status="accepted_proposal",
    )
    summary_b_proposal = SupportProposal(
        id=summary_b_proposal_id,
        tenant_id=TENANT_ID,
        project_id=PROJECT_ID,
        claim_id=summary_b_claim_id,
        relation_kind="supports",
        cited_memory_ids=(BASE_MEMORY_ID,),
        cited_passage_ids=(),
        proposing_run_id=summary_b_run.id,
        rationale="This summary derives from the same qualified base memory; repeated wording is not independent confirmation.",
        created_at="2026-10-14T23:01:00Z",
        status="accepted_proposal",
    )

    base_review = _review(
        "review:juniper:overnight-refresh:reserved:v1",
        base_proposal_id,
        base_proposal_id,
        BASE_MEMORY_ID,
        RESERVED_SCOPE_ID,
        (SOURCE_PASSAGE_ID,),
        {"memory_id": BASE_MEMORY_ID, "proposal_id": base_proposal_id, "scope_id": RESERVED_SCOPE_ID, "source_ids": [SOURCE_PASSAGE_ID]},
    )
    summary_a_review = _review(
        "review:juniper:overnight-refresh:summary-a:v1",
        summary_a_proposal_id,
        summary_a_proposal_id,
        SUMMARY_A_MEMORY_ID,
        RESERVED_SCOPE_ID,
        (SOURCE_PASSAGE_ID,),
        {"memory_id": SUMMARY_A_MEMORY_ID, "proposal_id": summary_a_proposal_id, "scope_id": RESERVED_SCOPE_ID, "source_ids": [SOURCE_PASSAGE_ID]},
    )
    summary_b_review = _review(
        "review:juniper:overnight-refresh:summary-b:v1",
        summary_b_proposal_id,
        summary_b_proposal_id,
        SUMMARY_B_MEMORY_ID,
        RESERVED_SCOPE_ID,
        (SOURCE_PASSAGE_ID,),
        {"memory_id": SUMMARY_B_MEMORY_ID, "proposal_id": summary_b_proposal_id, "scope_id": RESERVED_SCOPE_ID, "source_ids": [SOURCE_PASSAGE_ID]},
    )

    base_memory = MemoryVersion(
        id=BASE_MEMORY_ID,
        tenant_id=TENANT_ID,
        project_id=PROJECT_ID,
        qualified_text="Overnight refresh was observed on Juniper's reserved worker pool; applicability to a shared pool is unknown.",
        created_at="2026-10-14T22:07:00Z",
        writer_run_id=writer_run.id,
        version=1,
        scope_id=RESERVED_SCOPE_ID,
        source_ids=(SOURCE_PASSAGE_ID,),
        claim_ids=(base_claim_id,),
        unknowns=(UNKNOWN_SHARED_POOL,),
        status="reviewed",
        content_hash=content_hash("Overnight refresh was observed on Juniper's reserved worker pool; applicability to a shared pool is unknown."),
        review_id=base_review.id,
    )
    summary_a_memory = MemoryVersion(
        id=SUMMARY_A_MEMORY_ID,
        tenant_id=TENANT_ID,
        project_id=PROJECT_ID,
        qualified_text="Overnight refresh is ready for the Juniper walkthrough on the reserved pool; shared-pool applicability remains unknown.",
        created_at="2026-10-14T22:32:00Z",
        writer_run_id=summary_a_run.id,
        version=1,
        scope_id=RESERVED_SCOPE_ID,
        source_ids=(SOURCE_PASSAGE_ID,),
        claim_ids=(summary_a_claim_id,),
        unknowns=(UNKNOWN_SHARED_POOL,),
        status="reviewed",
        content_hash=content_hash("Overnight refresh is ready for the Juniper walkthrough on the reserved pool; shared-pool applicability remains unknown."),
        review_id=summary_a_review.id,
    )
    summary_b_memory = MemoryVersion(
        id=SUMMARY_B_MEMORY_ID,
        tenant_id=TENANT_ID,
        project_id=PROJECT_ID,
        qualified_text="Overnight refresh was reported as ready after validation, but the evidence covers the reserved pool only and shared-pool behavior is unknown.",
        created_at="2026-10-14T23:02:00Z",
        writer_run_id=summary_b_run.id,
        version=1,
        scope_id=RESERVED_SCOPE_ID,
        source_ids=(SOURCE_PASSAGE_ID,),
        claim_ids=(summary_b_claim_id,),
        unknowns=(UNKNOWN_SHARED_POOL,),
        status="reviewed",
        content_hash=content_hash("Overnight refresh was reported as ready after validation, but the evidence covers the reserved pool only and shared-pool behavior is unknown."),
        review_id=summary_b_review.id,
    )

    exposure_a_use = MemoryUse(
        id="memory-use:fixture:summary-a",
        tenant_id=TENANT_ID,
        project_id=PROJECT_ID,
        requesting_run_id=exposure_a_run.id,
        returned_version_ids=(BASE_MEMORY_ID,),
        source_manifest_hash=content_hash([SOURCE_PASSAGE_ID]),
        scope_id=RESERVED_SCOPE_ID,
        created_at="2026-10-14T22:26:00Z",
        tool_coverage="memory-exposure-only",
    )
    exposure_b_use = MemoryUse(
        id="memory-use:fixture:summary-b",
        tenant_id=TENANT_ID,
        project_id=PROJECT_ID,
        requesting_run_id=exposure_b_run.id,
        returned_version_ids=(BASE_MEMORY_ID,),
        source_manifest_hash=content_hash([SOURCE_PASSAGE_ID]),
        scope_id=RESERVED_SCOPE_ID,
        created_at="2026-10-14T22:56:00Z",
        tool_coverage="memory-exposure-only",
    )

    graph.add_nodes(
        [
            company,
            capability,
            reserved_scope,
            shared_scope,
            source,
            writer_run,
            summary_a_run,
            summary_b_run,
            exposure_a_run,
            exposure_b_run,
            base_claim,
            summary_a_claim,
            summary_b_claim,
            base_proposal,
            summary_a_proposal,
            summary_b_proposal,
            base_review,
            summary_a_review,
            summary_b_review,
            base_memory,
            summary_a_memory,
            summary_b_memory,
            exposure_a_use,
            exposure_b_use,
        ]
    )

    graph.add_edge("ABOUT", base_claim.id, capability.id)
    graph.add_edge("ABOUT", summary_a_claim.id, capability.id)
    graph.add_edge("ABOUT", summary_b_claim.id, capability.id)
    for claim in (base_claim, summary_a_claim, summary_b_claim):
        graph.add_edge("IN_SCOPE", claim.id, RESERVED_SCOPE_ID)
    graph.add_edge("WROTE", writer_run.id, base_memory.id)
    graph.add_edge("WROTE", summary_a_run.id, summary_a_memory.id)
    graph.add_edge("WROTE", summary_b_run.id, summary_b_memory.id)
    graph.add_edge("ASSERTS", base_memory.id, base_claim.id)
    graph.add_edge("ASSERTS", summary_a_memory.id, summary_a_claim.id)
    graph.add_edge("ASSERTS", summary_b_memory.id, summary_b_claim.id)
    graph.add_edge("HAS_PROPOSAL", base_claim.id, base_proposal.id)
    graph.add_edge("HAS_PROPOSAL", summary_a_claim.id, summary_a_proposal.id)
    graph.add_edge("HAS_PROPOSAL", summary_b_claim.id, summary_b_proposal.id)
    graph.add_edge("CITES_PASSAGE", base_proposal.id, source.id)
    graph.add_edge("CITES_MEMORY", summary_a_proposal.id, base_memory.id)
    graph.add_edge("CITES_MEMORY", summary_b_proposal.id, base_memory.id)
    for review, proposal in (
        (base_review, base_proposal),
        (summary_a_review, summary_a_proposal),
        (summary_b_review, summary_b_proposal),
    ):
        graph.add_edge("REVIEWS", review.id, proposal.id, {"state": review.state, "scope_id": review.scope_id})
        graph.add_edge("APPLIES_IN", review.id, review.scope_id, {"scope_id": review.scope_id})
    for run, source_id in ((writer_run, SOURCE_PASSAGE_ID), (summary_a_run, SOURCE_PASSAGE_ID), (summary_b_run, SOURCE_PASSAGE_ID)):
        graph.add_edge("READ_PASSAGE", run.id, source_id, {"coverage": run.context_coverage})
    for run, use in ((exposure_a_run, exposure_a_use), (exposure_b_run, exposure_b_use)):
        graph.add_edge("HAS_MEMORY_USE", run.id, use.id, {"coverage": "exposure-only"})
        graph.add_edge("RETURNED", use.id, BASE_MEMORY_ID, {"scope_id": RESERVED_SCOPE_ID})
        graph.add_edge("READ_MEMORY", run.id, BASE_MEMORY_ID, {"coverage": "exposure-only"})
        graph.add_edge("READ_PASSAGE", run.id, SOURCE_PASSAGE_ID, {"coverage": "exposure-only"})

    return graph


def reset_demo_store() -> InMemoryGraphStore:
    """Convenience alias returning a newly seeded demo store."""

    return seed_demo_store()
