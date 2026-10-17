"""Deterministic, bounded gateway operations for HiveMind.

The gateway is the safety boundary used by both the HTTP and MCP adapters.  It
never accepts Cypher, never treats a READ edge as support, and requires exact
scope/version bindings for corrections and local draft citations.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any
from uuid import uuid4

from .domain import (
    AgentRun,
    Claim,
    Draft,
    MemoryUse,
    MemoryVersion,
    Review,
    Scope,
    SourcePassage,
    SupportProposal,
    canonical_json,
    content_hash,
    deterministic_id,
    record_to_dict,
)
from .store import InMemoryGraphStore, StoreError


class HiveMindGateway:
    """Expose the small stable HiveMind API over an injected graph store."""

    MAX_RECALL_ITEMS = 8
    MAX_EVIDENCE_DEPTH = 4
    MAX_EVIDENCE_NODES = 64
    MAX_CITATIONS = 8
    MAX_TITLE_LENGTH = 160
    MAX_BODY_LENGTH = 12_000
    FIXED_TIME = "2026-10-15T10:00:00Z"
    ALLOWED_REVIEWERS = {"operator", "demo-operator"}
    UNSCOPED_CORRECTION_PHRASES = (
        "universally ready",
        "every environment",
        "all environments",
        "always ready",
    )

    def __init__(self, store: InMemoryGraphStore, session_nonce: str | None = None) -> None:
        """Create a gateway bound to one deterministic tenant/project store."""

        self.store = store
        self.session_nonce = session_nonce or uuid4().hex

    @staticmethod
    def _error(code: str, message: str, details: Mapping[str, Any] | None = None) -> dict[str, Any]:
        """Build the common JSON-safe error envelope."""

        error: dict[str, Any] = {"code": code, "message": message}
        if details:
            error["details"] = dict(details)
        return {"ok": False, "error": error}

    @staticmethod
    def _ok(**payload: Any) -> dict[str, Any]:
        """Build a common JSON-safe success envelope."""

        return {"ok": True, **payload}

    def _scope(self, scope_id: Any) -> Scope | None:
        if not isinstance(scope_id, str) or not scope_id.strip():
            return None
        scope_id = {
            "reserved-pool": "scope:juniper:reserved-pool",
            "juniper/shared-pool": "scope:juniper:shared-pool",
        }.get(scope_id, scope_id)
        scope = self.store.get_node(scope_id)
        return scope if isinstance(scope, Scope) else None

    @staticmethod
    def _compat_scope_label(scope_id: str) -> str:
        """Return the short label used by the lightweight SDK compatibility API."""

        return {
            "scope:juniper:reserved-pool": "reserved-pool",
            "scope:juniper:shared-pool": "juniper/shared-pool",
        }.get(scope_id, scope_id)

    def _memory(self, memory_id: Any) -> MemoryVersion | None:
        if not isinstance(memory_id, str) or not memory_id.strip():
            return None
        memory = self.store.get_node(memory_id)
        return memory if isinstance(memory, MemoryVersion) else None

    def _source(self, source_id: str) -> SourcePassage | None:
        source = self.store.get_node(source_id)
        return source if isinstance(source, SourcePassage) else None

    @staticmethod
    def _record(record: Any) -> dict[str, Any]:
        return record_to_dict(record)

    @staticmethod
    def _unique(values: Sequence[str]) -> list[str]:
        result: list[str] = []
        seen: set[str] = set()
        for value in values:
            if value not in seen:
                seen.add(value)
                result.append(value)
        return result

    def _memory_view(self, memory: MemoryVersion) -> dict[str, Any]:
        """Add stable source/review summaries without changing the record."""

        result = self._record(memory)
        result["source_ids"] = list(memory.source_ids)
        result["source_versions"] = []
        for source_id in memory.source_ids:
            source = self._source(source_id)
            if source is not None:
                result["source_versions"].append(self._record(source))
        reviews = [self._record(review) for review in self.store.reviews_for(memory.id)]
        result["reviews"] = reviews
        result["review_state"] = reviews[0]["state"] if reviews else "unreviewed"
        result["scope_binding"] = {
            "scope_id": memory.scope_id,
            "exact": True,
            "supersedes_memory_id": memory.supersedes_memory_id,
        }
        return result

    def _ensure_recall_receipt(self, scope: Scope, memories: Sequence[MemoryVersion]) -> dict[str, Any]:
        """Record a deterministic exposure receipt separately from support."""

        memory_ids = tuple(memory.id for memory in memories)
        source_ids = tuple(self._unique([source_id for memory in memories for source_id in memory.source_ids]))
        manifest = content_hash({"scope_id": scope.id, "memory_ids": memory_ids, "source_ids": source_ids})
        run_id = deterministic_id("run-recall", self.session_nonce, scope.id, memory_ids, manifest)
        use_id = deterministic_id("memory-use", run_id, memory_ids, manifest)
        run = AgentRun(
            id=run_id,
            tenant_id=self.store.tenant_id,
            project_id=self.store.project_id,
            role="cold-consumer",
            session_id=deterministic_id("session-cold-consumer", self.session_nonce, scope.id, manifest),
            input_manifest_hash=content_hash({"manifest": manifest, "session_nonce": self.session_nonce}),
            started_at=self.FIXED_TIME,
            context_coverage="gateway-recall",
        )
        use = MemoryUse(
            id=use_id,
            tenant_id=self.store.tenant_id,
            project_id=self.store.project_id,
            requesting_run_id=run_id,
            returned_version_ids=memory_ids,
            source_manifest_hash=manifest,
            scope_id=scope.id,
            created_at=self.FIXED_TIME,
            tool_coverage="gateway-recall",
        )
        try:
            self.store.add_nodes((run, use))
            self.store.add_edge("HAS_MEMORY_USE", run.id, use.id, {"coverage": "exposure-only"})
            for memory in memories:
                self.store.add_edge("READ_MEMORY", run.id, memory.id, {"coverage": "exposure-only"})
                for source_id in memory.source_ids:
                    if self._source(source_id) is not None:
                        self.store.add_edge("READ_PASSAGE", run.id, source_id, {"coverage": "exposure-only"})
                self.store.add_edge("RETURNED", use.id, memory.id, {"scope_id": scope.id})
        except (StoreError, TypeError, ValueError) as exc:
            return {"error": {"code": "RECEIPT_WRITE_FAILED", "message": str(exc)}}
        return {
            "memory_use_id": use_id,
            "requesting_run_id": run_id,
            "returned_version_ids": list(memory_ids),
            "read_memory_ids": list(memory_ids),
            "read_source_ids": list(source_ids),
            "coverage": "exposure-only",
            "is_support": False,
        }

    def recall_context(self, scope_id: str) -> dict[str, Any]:
        """Recall current exact-scope memories with bounded provenance.

        The returned ``exposure`` receipt is deliberately separate from
        ``support_paths``.  A memory being returned or read is never promoted to
        semantic support by this method.
        """

        scope = self._scope(scope_id)
        if scope is None:
            return self._error("SCOPE_NOT_FOUND", "The requested scope does not exist", {"scope_id": scope_id})
        try:
            candidates = self.store.memory_candidates_for_scope(scope.id, limit=self.MAX_RECALL_ITEMS + 1)
            capped = len(candidates) > self.MAX_RECALL_ITEMS
            memories = candidates[: self.MAX_RECALL_ITEMS]
            exposure = self._ensure_recall_receipt(scope, memories)
            if isinstance(exposure, dict) and "error" in exposure:
                return self._error(
                    "RECEIPT_WRITE_FAILED",
                    "HiveMind could not persist the recall exposure receipt",
                    {"scope_id": scope.id, "cause": exposure["error"]},
                )
            support_inspections: list[dict[str, Any]] = []
            support_paths: list[dict[str, Any]] = []
            all_sources: dict[str, dict[str, Any]] = {}
            all_unknowns = list(scope.unknowns)
            cycle_detected = False
            evidence_capped = capped
            lineage_complete = True
            for memory in memories:
                inspection = self._inspect_evidence_internal(memory.id, self.MAX_EVIDENCE_DEPTH)
                support_inspections.append(inspection)
                support_paths.extend(inspection["support_paths"])
                cycle_detected = cycle_detected or inspection["completeness"]["cycle_detected"]
                evidence_capped = evidence_capped or inspection["completeness"]["capped"]
                lineage_complete = lineage_complete and inspection["completeness"]["lineage_complete"]
                all_unknowns.extend(inspection["unknowns"])
                for source in inspection["source_passages"]:
                    all_sources[source["id"]] = source
                for source_id in memory.source_ids:
                    source = self._source(source_id)
                    if source is not None:
                        all_sources[source.id] = self._record(source)
            dedup_paths = self._deduplicate_by_id(support_paths)
            exact_scope_memory = any(memory.scope_id == scope.id for memory in memories)
            correction_memory = any(memory.kind == "correction" and memory.scope_id == scope.id for memory in memories)
            status = "corrected" if correction_memory else ("qualified" if exact_scope_memory else "needs-clarification")
            return self._ok(
                operation="recall_context",
                backend=getattr(self.store, "backend_name", "unknown"),
                scope=self._record(scope),
                scope_id=scope.id,
                status=status,
                needs_clarification=status == "needs-clarification",
                question=(
                    "Which worker pool will the Juniper walkthrough use?"
                    if status == "needs-clarification"
                    else None
                ),
                memory_versions=[
                    {
                        **self._memory_view(memory),
                        "scope_match": memory.scope_id == scope.id,
                        "applicability": "exact" if memory.scope_id == scope.id else "nearby-evidence",
                    }
                    for memory in memories
                ],
                support_paths=dedup_paths,
                support_inspections=support_inspections,
                source_passages=sorted(all_sources.values(), key=lambda item: item["id"]),
                unknowns=self._unique(all_unknowns),
                review_state={
                    "memory_ids": [memory.id for memory in memories],
                    "accepted_memory_ids": [
                        memory.id
                        for memory in memories
                        if any(review.state == "accepted" for review in self.store.reviews_for(memory.id))
                    ],
                },
                exposure=exposure,
                support_policy={
                    "read_edges_are_support": False,
                    "support_edge_types": ["ASSERTS", "HAS_PROPOSAL", "CITES_MEMORY", "CITES_PASSAGE"],
                    "review_required_for_promoted_interpretation": True,
                },
                completeness={
                    "complete": not capped and not cycle_detected,
                    "lineage_complete": lineage_complete,
                    "capped": evidence_capped,
                    "cycle_detected": cycle_detected,
                    "max_depth": self.MAX_EVIDENCE_DEPTH,
                    "max_items": self.MAX_RECALL_ITEMS,
                },
            )
        except (StoreError, TypeError, ValueError) as exc:
            return self._error("RECALL_FAILED", str(exc), {"scope_id": scope.id})

    def _deduplicate_by_id(self, values: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
        by_id: dict[str, dict[str, Any]] = {}
        for value in values:
            item = dict(value)
            key = str(item.get("path_id") or item.get("id") or canonical_json(item))
            by_id.setdefault(key, item)
        return [by_id[key] for key in sorted(by_id)]

    def _node_view(self, node: Any) -> dict[str, Any]:
        result = self._record(node)
        result["scope_id"] = getattr(node, "scope_id", result.get("scope_id"))
        return result

    def _inspect_evidence_internal(self, memory_id: str, max_depth: int) -> dict[str, Any]:
        """Traverse only declared support relationships, not READ relationships."""

        root = self._memory(memory_id)
        if root is None:
            return {
                "memory_id": memory_id,
                "support_paths": [],
                "memory_versions": [],
                "claims": [],
                "support_proposals": [],
                "reviews": [],
                "source_passages": [],
                "unknowns": [],
                "completeness": {
                    "complete": False,
                    "lineage_complete": False,
                    "capped": False,
                    "cycle_detected": False,
                    "missing_support": ["memory_not_found"],
                    "max_depth": max_depth,
                    "max_nodes": self.MAX_EVIDENCE_NODES,
                },
                "read_edges": [],
            }

        memory_nodes: dict[str, dict[str, Any]] = {}
        claim_nodes: dict[str, dict[str, Any]] = {}
        proposal_nodes: dict[str, dict[str, Any]] = {}
        review_nodes: dict[str, dict[str, Any]] = {}
        source_nodes: dict[str, dict[str, Any]] = {}
        support_paths: list[dict[str, Any]] = []
        unknowns: list[str] = []
        missing_support: list[str] = []
        node_count = 0
        capped = False
        cycle_detected = False

        def add_node(bucket: dict[str, dict[str, Any]], node: Any) -> bool:
            nonlocal node_count, capped
            node_id = getattr(node, "id", None)
            if node_id in bucket:
                return True
            if node_count >= self.MAX_EVIDENCE_NODES:
                capped = True
                return False
            bucket[node_id] = self._node_view(node)
            node_count += 1
            return True

        def add_review_data(target_id: str) -> list[dict[str, Any]]:
            reviews = self.store.reviews_for(target_id)
            for review in reviews:
                add_node(review_nodes, review)
            return [self._record(review) for review in reviews]

        def append_path(
            path_nodes: list[str],
            relationships: list[dict[str, Any]],
            relation_kinds: list[str],
            scope_ids: list[str],
            *,
            complete: bool,
            reason: str | None = None,
            cycle: bool = False,
            path_capped: bool = False,
        ) -> None:
            path_id = deterministic_id("support-path", root.id, path_nodes, relationships)
            support_paths.append(
                {
                    "path_id": path_id,
                    "root_memory_id": root.id,
                    "node_ids": list(path_nodes),
                    "relationships": list(relationships),
                    "relation_kinds": self._unique(relation_kinds),
                    "scope_ids": self._unique(scope_ids),
                    "complete": complete,
                    "missing_reason": reason,
                    "cycle_detected": cycle,
                    "capped": path_capped,
                    "read_edges_included": False,
                }
            )

        def relationship(edge: Any) -> dict[str, Any]:
            return {
                "edge_id": edge.id,
                "type": edge.edge_type,
                "from_id": edge.from_id,
                "to_id": edge.to_id,
                "properties": dict(edge.properties),
            }

        def walk_memory(
            memory: MemoryVersion,
            memory_hops: int,
            memory_stack: tuple[str, ...],
            path_nodes: list[str],
            relationships: list[dict[str, Any]],
            relation_kinds: list[str],
            scope_ids: list[str],
        ) -> None:
            nonlocal cycle_detected, capped
            if memory.id in memory_stack:
                cycle_detected = True
                append_path(path_nodes, relationships, relation_kinds, scope_ids, complete=False, reason="cycle_detected", cycle=True)
                return
            if memory_hops > max_depth:
                capped = True
                append_path(path_nodes, relationships, relation_kinds, scope_ids, complete=False, reason="max_depth_reached", path_capped=True)
                return
            if not add_node(memory_nodes, memory):
                append_path(path_nodes, relationships, relation_kinds, scope_ids, complete=False, reason="node_cap_reached", path_capped=True)
                return
            unknowns.extend(memory.unknowns)
            next_stack = memory_stack + (memory.id,)
            claim_edges = self.store.edges_from(memory.id, "ASSERTS")
            if not claim_edges:
                missing_support.append(f"{memory.id}:no_claim")
                append_path(path_nodes + [memory.id], relationships, relation_kinds, scope_ids + [memory.scope_id], complete=False, reason="no_claim")
                return
            found_citation = False
            for claim_edge in claim_edges:
                claim = self.store.get_node(claim_edge.to_id)
                if not isinstance(claim, Claim):
                    missing_support.append(f"{memory.id}:missing_claim:{claim_edge.to_id}")
                    continue
                if not add_node(claim_nodes, claim):
                    continue
                claim_path_nodes = path_nodes + [memory.id, claim.id]
                claim_relationships = relationships + [relationship(claim_edge)]
                claim_scope_ids = scope_ids + [memory.scope_id, claim.scope_id]
                proposal_edges = self.store.edges_from(claim.id, "HAS_PROPOSAL")
                if not proposal_edges:
                    missing_support.append(f"{claim.id}:no_proposal")
                    append_path(claim_path_nodes, claim_relationships, relation_kinds, claim_scope_ids, complete=False, reason="no_proposal")
                    continue
                for proposal_edge in proposal_edges:
                    proposal = self.store.get_node(proposal_edge.to_id)
                    if not isinstance(proposal, SupportProposal):
                        missing_support.append(f"{claim.id}:missing_proposal:{proposal_edge.to_id}")
                        continue
                    if not add_node(proposal_nodes, proposal):
                        continue
                    reviews = add_review_data(proposal.id)
                    accepted = any(review.get("state") == "accepted" and review.get("scope_id") == claim.scope_id for review in reviews)
                    if not accepted:
                        missing_support.append(f"{proposal.id}:not_accepted_in_scope")
                    proposal_path_nodes = claim_path_nodes + [proposal.id]
                    proposal_relationships = claim_relationships + [relationship(proposal_edge)]
                    proposal_relation_kinds = relation_kinds + [proposal.relation_kind]
                    proposal_scope_ids = claim_scope_ids + [claim.scope_id]
                    citation_edges = [
                        edge
                        for edge in self.store.edges_from(proposal.id)
                        if edge.edge_type in {"CITES_MEMORY", "CITES_PASSAGE"}
                    ]
                    if not citation_edges:
                        missing_support.append(f"{proposal.id}:no_citation")
                        append_path(proposal_path_nodes, proposal_relationships, proposal_relation_kinds, proposal_scope_ids, complete=False, reason="no_citation")
                        continue
                    for citation_edge in citation_edges:
                        found_citation = True
                        citation_relationships = proposal_relationships + [relationship(citation_edge)]
                        citation_path_nodes = proposal_path_nodes + [citation_edge.to_id]
                        if citation_edge.edge_type == "CITES_PASSAGE":
                            source = self.store.get_node(citation_edge.to_id)
                            if not isinstance(source, SourcePassage):
                                missing_support.append(f"{proposal.id}:missing_source:{citation_edge.to_id}")
                                append_path(citation_path_nodes, citation_relationships, proposal_relation_kinds, proposal_scope_ids, complete=False, reason="missing_source")
                                continue
                            add_node(source_nodes, source)
                            append_path(citation_path_nodes, citation_relationships, proposal_relation_kinds, proposal_scope_ids + ([source.scope_id] if source.scope_id else []), complete=accepted)
                        else:
                            cited_memory = self._memory(citation_edge.to_id)
                            if cited_memory is None:
                                missing_support.append(f"{proposal.id}:missing_memory:{citation_edge.to_id}")
                                append_path(citation_path_nodes, citation_relationships, proposal_relation_kinds, proposal_scope_ids, complete=False, reason="missing_memory")
                                continue
                            if cited_memory.id in next_stack:
                                cycle_detected = True
                                append_path(citation_path_nodes, citation_relationships, proposal_relation_kinds, proposal_scope_ids + [cited_memory.scope_id], complete=False, reason="cycle_detected", cycle=True)
                                continue
                            walk_memory(
                                cited_memory,
                                memory_hops + 1,
                                next_stack,
                                proposal_path_nodes,
                                proposal_relationships,
                                proposal_relation_kinds,
                                proposal_scope_ids,
                            )
            if not found_citation:
                missing_support.append(f"{memory.id}:no_reachable_citation")

        walk_memory(root, 0, (), [], [], [], [])
        all_read_edges: list[dict[str, Any]] = []
        for node_id in list(memory_nodes) + list(source_nodes):
            for edge in self.store.edges_to(node_id):
                if edge.edge_type in {"READ_MEMORY", "READ_PASSAGE"}:
                    all_read_edges.append(record_to_dict(edge))
        deduped_missing = self._unique(missing_support)
        if support_paths and not any(path["complete"] is False for path in support_paths):
            lineage_complete = not cycle_detected and not capped
        else:
            lineage_complete = False
        if not support_paths:
            lineage_complete = False
        return {
            "memory_id": root.id,
            "root_memory": self._memory_view(root),
            "support_paths": self._deduplicate_by_id(support_paths),
            "memory_versions": sorted(memory_nodes.values(), key=lambda item: item["id"]),
            "claims": sorted(claim_nodes.values(), key=lambda item: item["id"]),
            "support_proposals": sorted(proposal_nodes.values(), key=lambda item: item["id"]),
            "reviews": sorted(review_nodes.values(), key=lambda item: item["id"]),
            "source_passages": sorted(source_nodes.values(), key=lambda item: item["id"]),
            "unknowns": self._unique(unknowns),
            "read_edges": self._deduplicate_by_id(all_read_edges),
            "support_policy": {
                "read_edges_are_support": False,
                "traversed_edge_types": ["ASSERTS", "HAS_PROPOSAL", "CITES_MEMORY", "CITES_PASSAGE"],
            },
            "completeness": {
                "complete": lineage_complete and not cycle_detected and not capped,
                "lineage_complete": lineage_complete,
                "capped": capped,
                "cycle_detected": cycle_detected,
                "missing_support": deduped_missing,
                "max_depth": max_depth,
                "max_nodes": self.MAX_EVIDENCE_NODES,
            },
        }

    def recall(self, scope_id: str, query: str | None = None) -> dict[str, Any]:
        """Compatibility view for lightweight SDK and contract consumers.

        The HTTP/MCP surface uses :meth:`recall_context`.  This compact method
        keeps the public Python integration pleasant for agents that only need a
        scope label, memory IDs, and the evidence-aware status.
        """

        canonical_scope = {
            "reserved-pool": "scope:juniper:reserved-pool",
            "shared-pool": "scope:juniper:shared-pool",
            "juniper/shared-pool": "scope:juniper:shared-pool",
        }.get(scope_id, scope_id)
        result = self.recall_context(canonical_scope)
        if not result.get("ok"):
            if result.get("error", {}).get("code") == "SCOPE_NOT_FOUND":
                result["error"]["code"] = "scope_not_found"
            return result
        memories: list[dict[str, Any]] = []
        for item in result.get("memory_versions", []):
            view = dict(item)
            view["memory_id"] = view.get("id")
            view["requested_scope_id"] = scope_id
            memories.append(view)
        if isinstance(query, str) and query.strip():
            needle = query.strip().lower()
            memories = [
                memory
                for memory in memories
                if needle in str(memory.get("qualified_text", "")).lower()
                or any(needle in str(source.get("text", "")).lower() for source in memory.get("source_versions", []))
            ]
        no_match = isinstance(query, str) and bool(query.strip()) and not memories
        return self._ok(
            operation="recall",
            requested_scope_id=scope_id,
            scope_id=canonical_scope,
            status="no-match" if no_match else result.get("status", "needs-clarification"),
            needs_clarification=True if no_match else result.get("needs_clarification", False),
            memories=memories,
            source_passages=[] if no_match else result.get("source_passages", []),
            support_paths=[] if no_match else result.get("support_paths", []),
            unknowns=(result.get("unknowns", []) + ["No matching memory was found for this query."]) if no_match else result.get("unknowns", []),
            exposure=result.get("exposure", {}),
            completeness=result.get("completeness", {}),
            support_policy=result.get("support_policy", {}),
        )

    def record_exposure(self, run_id: str, memory_id: str) -> dict[str, Any]:
        """Record an explicit memory exposure without promoting it to support."""

        memory = self._memory(memory_id)
        if memory is None:
            result = self._error("MEMORY_NOT_FOUND", "The requested memory version does not exist", {"memory_id": memory_id})
            result["error"]["code"] = "memory_not_found"
            return result
        if not isinstance(run_id, str) or not run_id.strip():
            return self._error("INVALID_RUN", "run_id must be a non-empty string")
        run = AgentRun(
            id=run_id,
            tenant_id=self.store.tenant_id,
            project_id=self.store.project_id,
            role="external-agent",
            session_id=run_id,
            input_manifest_hash=content_hash({"memory_id": memory.id}),
            started_at=self.FIXED_TIME,
            context_coverage="external-memory-exposure",
        )
        try:
            self.store.add_node(run)
            self.store.add_edge("READ_MEMORY", run.id, memory.id, {"coverage": "exposure-only"})
        except (StoreError, TypeError, ValueError) as exc:
            return self._error("EXPOSURE_FAILED", str(exc), {"run_id": run_id, "memory_id": memory.id})
        return self._ok(
            operation="record_exposure",
            relation="READ_MEMORY",
            run_id=run_id,
            memory_id=memory.id,
            is_support=False,
        )

    def inspect_evidence(
        self,
        memory_id: str,
        max_depth: int = 4,
        *,
        max_hops: int | None = None,
    ) -> dict[str, Any]:
        """Inspect a bounded declared support path for one memory version."""

        if max_hops is not None:
            max_depth = max_hops
        memory = self._memory(memory_id)
        if memory is None:
            result = self._error("MEMORY_NOT_FOUND", "The requested memory version does not exist", {"memory_id": memory_id})
            result["error"]["code"] = "memory_not_found"
            return result
        if isinstance(max_depth, bool) or not isinstance(max_depth, int) or max_depth < 0:
            return self._error("INVALID_MAX_DEPTH", "max_depth must be a non-negative integer")
        effective_depth = min(max_depth, self.MAX_EVIDENCE_DEPTH)
        inspection = self._inspect_evidence_internal(memory.id, effective_depth)
        inspection["requested_max_depth"] = max_depth
        inspection["bounded"] = True
        node_records: dict[str, dict[str, Any]] = {}
        node_types = (
            ("MemoryVersion", inspection.get("memory_versions", [])),
            ("Claim", inspection.get("claims", [])),
            ("SupportProposal", inspection.get("support_proposals", [])),
            ("Review", inspection.get("reviews", [])),
            ("SourcePassage", inspection.get("source_passages", [])),
        )
        for node_type, records in node_types:
            for record in records:
                if isinstance(record, Mapping) and record.get("id"):
                    node_records[record["id"]] = {"node_type": node_type, **dict(record)}
        paths = inspection.get("support_paths", [])
        selected_path = next((path for path in paths if path.get("complete")), paths[0] if paths else None)
        relationships = selected_path.get("relationships", []) if isinstance(selected_path, Mapping) else []
        relationship_by_from = {
            relation.get("from_id"): relation
            for relation in relationships
            if isinstance(relation, Mapping) and relation.get("from_id")
        }
        path_nodes: list[dict[str, Any]] = []
        if isinstance(selected_path, Mapping):
            node_ids = selected_path.get("node_ids", [])
            for index, node_id in enumerate(node_ids):
                record = dict(node_records.get(node_id, {"id": node_id}))
                node_type = record.pop("node_type", "EvidenceNode")
                domain_kind = record.get("kind")
                if node_type == "MemoryVersion":
                    label = "scoped correction" if domain_kind == "correction" else "qualified memory"
                elif node_type == "Claim":
                    label = str(record.get("qualified_proposition", "qualified claim"))
                elif node_type == "SupportProposal":
                    label = f"{record.get('relation_kind', 'declared')} support"
                elif node_type == "Review":
                    label = f"{record.get('reviewer', 'review')} / {record.get('state', 'reviewed')}"
                elif node_type == "SourcePassage":
                    label = f"{record.get('artifact_id', 'source passage')} · {record.get('version', 'current')}"
                else:
                    label = str(node_id)
                relation = relationship_by_from.get(node_id)
                path_nodes.append(
                    {
                        **record,
                        "kind": node_type,
                        "node_type": node_type,
                        "record_kind": domain_kind,
                        "id": node_id,
                        "label": label,
                        "edge": f"→ {relation.get('type')}" if relation else "root evidence",
                    }
                )
        inspection["path"] = path_nodes
        inspection["exposure"] = inspection.get("read_edges", [])
        inspection["support"] = inspection.get("support_paths", [])
        source_passages = inspection.get("source_passages", [])
        inspection["source"] = source_passages[0] if source_passages else None
        inspection["rationale"] = (
            "Declared claim, support proposal, review, and source relationships are shown; read exposure is excluded."
        )
        inspection["complete"] = inspection.get("completeness", {}).get("complete", False)
        return self._ok(operation="inspect_evidence", **inspection)

    def apply_correction(
        self,
        base_memory_id: str,
        scope_id: str,
        correction_text: str | None = None,
        reviewer: str = "operator",
    ) -> dict[str, Any]:
        """Create or return an immutable correction bound to one exact scope.

        The method contains the synthetic operator clarification required by the
        MVP.  It never mutates the base memory and never changes applicability
        in a different scope.
        """

        base = self._memory(base_memory_id)
        if base is None:
            return self._error("MEMORY_NOT_FOUND", "The base memory version does not exist", {"memory_id": base_memory_id})
        scope = self._scope(scope_id)
        if scope is None:
            result = self._error("SCOPE_NOT_FOUND", "The correction scope does not exist", {"scope_id": scope_id})
            if correction_text is not None:
                result["error"]["code"] = "scope_not_found"
            return result
        if not isinstance(reviewer, str) or reviewer.strip() not in self.ALLOWED_REVIEWERS:
            return self._error("REVIEWER_NOT_AUTHORIZED", "Only an authorized local operator can accept a correction")
        scope_label = scope_id if scope_id in {"reserved-pool", "juniper/shared-pool"} else scope.id
        if correction_text is not None and (
            not isinstance(correction_text, str)
            or not correction_text.strip()
            or len(correction_text) > self.MAX_BODY_LENGTH
        ):
            return self._error("INVALID_CORRECTION", "correction_text must be a non-empty bounded string")
        try:
            existing = self.store.correction_for(base.id, scope.id)
            if existing is not None:
                if correction_text is not None and content_hash(correction_text.strip()) != existing.content_hash:
                    return self._error(
                        "CORRECTION_CONFLICT",
                        "An immutable correction already exists with different wording",
                        {"base_memory_id": base.id, "scope_id": scope.id, "existing_memory_id": existing.id},
                    )
                review = self.store.reviews_for(existing.id)
                return self._ok(
                    operation="apply_correction",
                    idempotent=True,
                    immutable=True,
                    correction=self._memory_view(existing),
                    review=review[0] if review else None,
                    new_memory_id=existing.id,
                    version=existing.version,
                    scope=scope_label,
                    supersedes=base.id,
                    supersedes_detail={"base_memory_id": base.id, "scope_id": scope.id, "global": False},
                    evidence=self._inspect_evidence_internal(existing.id, self.MAX_EVIDENCE_DEPTH),
                )

            entity_id = scope.company_id
            for claim_id in base.claim_ids:
                claim = self.store.get_node(claim_id)
                if isinstance(claim, Claim):
                    entity_id = claim.entity_id
                    break
            if correction_text is None:
                if scope.environment == "shared-worker-pool":
                    correction_text = (
                        "For Juniper's shared worker pool, overnight refresh readiness is not established; "
                        "run and review a shared-pool rehearsal before making a readiness claim."
                    )
                else:
                    correction_text = (
                        f"For {scope.environment}, applicability of the remembered capability is not established; "
                        "confirm the scoped condition before making a readiness claim."
                    )
            if not isinstance(correction_text, str) or not correction_text.strip() or len(correction_text) > self.MAX_BODY_LENGTH:
                return self._error("INVALID_CORRECTION", "correction_text must be a non-empty bounded string")
            correction_text = correction_text.strip()
            lowered_correction = correction_text.lower()
            if any(phrase in lowered_correction for phrase in self.UNSCOPED_CORRECTION_PHRASES):
                return self._error(
                    "UNSCOPED_CORRECTION",
                    "A correction cannot broaden evidence into an unbounded readiness claim",
                    {"scope_id": scope.id},
                )
            correction_id = deterministic_id("memory-correction", base.id, scope.id)
            claim_id = deterministic_id("claim-correction", correction_id)
            proposal_id = deterministic_id("proposal-correction", correction_id)
            review_id = deterministic_id("review-correction", correction_id)
            run_id = deterministic_id("run-correction", base.id, scope.id)
            unknowns = self._unique(
                list(scope.unknowns)
                + ["A reviewed result for this exact correction scope is still required before universalizing the claim."]
            )
            correction_hash = content_hash(correction_text)
            run = AgentRun(
                id=run_id,
                tenant_id=self.store.tenant_id,
                project_id=self.store.project_id,
                role="operator-review",
                session_id=deterministic_id("session-operator-review", base.id, scope.id),
                input_manifest_hash=content_hash({"base_memory_id": base.id, "scope_id": scope.id}),
                started_at=self.FIXED_TIME,
                context_coverage="operator-clarification",
            )
            claim = Claim(
                id=claim_id,
                tenant_id=self.store.tenant_id,
                project_id=self.store.project_id,
                qualified_proposition=correction_text,
                entity_id=entity_id,
                scope_id=scope.id,
                status="reviewed_assertion",
                exact_quote_refs=base.source_ids,
            )
            proposal = SupportProposal(
                id=proposal_id,
                tenant_id=self.store.tenant_id,
                project_id=self.store.project_id,
                claim_id=claim.id,
                relation_kind="qualifies",
                cited_memory_ids=(base.id,),
                cited_passage_ids=base.source_ids,
                proposing_run_id=run.id,
                rationale="The operator binds the unresolved pool condition to this exact scope; the source does not become shared-pool evidence.",
                created_at=self.FIXED_TIME,
                status="accepted_proposal",
            )
            binding = {
                "base_memory_id": base.id,
                "base_content_hash": base.content_hash,
                "correction_id": correction_id,
                "correction_content_hash": correction_hash,
                "scope_id": scope.id,
                "source_ids": list(base.source_ids),
            }
            review = Review(
                id=review_id,
                tenant_id=self.store.tenant_id,
                project_id=self.store.project_id,
                reviewed_target_id=proposal.id,
                proposal_id=proposal.id,
                memory_version_id=correction_id,
                scope_id=scope.id,
                reviewer=reviewer.strip(),
                state="accepted",
                binding_hash=content_hash(binding),
                cited_source_ids=base.source_ids,
                accepted_at=self.FIXED_TIME,
            )
            correction = MemoryVersion(
                id=correction_id,
                tenant_id=self.store.tenant_id,
                project_id=self.store.project_id,
                qualified_text=correction_text,
                created_at=self.FIXED_TIME,
                writer_run_id=run.id,
                version=base.version + 1,
                scope_id=scope.id,
                source_ids=base.source_ids,
                claim_ids=(claim.id,),
                unknowns=tuple(unknowns),
                status="reviewed_correction",
                content_hash=correction_hash,
                kind="correction",
                supersedes_memory_id=base.id,
                review_id=review.id,
                immutable=True,
            )
            self.store.add_nodes((run, claim, proposal, review, correction))
            self.store.add_edge("WROTE", run.id, correction.id)
            self.store.add_edge("ASSERTS", correction.id, claim.id)
            self.store.add_edge("ABOUT", claim.id, entity_id)
            self.store.add_edge("IN_SCOPE", claim.id, scope.id)
            self.store.add_edge("HAS_PROPOSAL", claim.id, proposal.id)
            self.store.add_edge("CITES_MEMORY", proposal.id, base.id, {"relation_kind": "qualifies"})
            for source_id in base.source_ids:
                if self._source(source_id) is not None:
                    self.store.add_edge("CITES_PASSAGE", proposal.id, source_id, {"relation_kind": "qualifies"})
            self.store.add_edge("REVIEWS", review.id, proposal.id, {"state": review.state, "scope_id": scope.id})
            self.store.add_edge("REVIEWS", review.id, correction.id, {"state": review.state, "scope_id": scope.id, "target": "memory-version"})
            self.store.add_edge("APPLIES_IN", review.id, scope.id, {"scope_id": scope.id})
            self.store.add_edge("SUPERSEDES", correction.id, base.id, {"scope_id": scope.id, "review_id": review.id, "immutable": True})
            return self._ok(
                operation="apply_correction",
                idempotent=False,
                immutable=True,
                correction=self._memory_view(correction),
                review=self._record(review),
                new_memory_id=correction.id,
                version=correction.version,
                scope=scope_label,
                supersedes=base.id,
                supersedes_detail={"base_memory_id": base.id, "scope_id": scope.id, "global": False},
                evidence=self._inspect_evidence_internal(correction.id, self.MAX_EVIDENCE_DEPTH),
            )
        except (StoreError, TypeError, ValueError) as exc:
            return self._error("CORRECTION_FAILED", str(exc), {"base_memory_id": base.id, "scope_id": scope.id})

    def _normalize_citations(self, citations: Any, scope: Scope) -> tuple[list[dict[str, Any]], list[str]] | dict[str, Any]:
        if isinstance(citations, (str, bytes)) or not isinstance(citations, Sequence):
            return self._error("INVALID_CITATIONS", "citations must be a list of memory or source citation objects")
        if not citations:
            return self._error("INVALID_CITATIONS", "at least one exact citation is required")
        if len(citations) > self.MAX_CITATIONS:
            return self._error("TOO_MANY_CITATIONS", f"at most {self.MAX_CITATIONS} citations are allowed")
        normalized: list[dict[str, Any]] = []
        citation_ids: list[str] = []
        for citation in citations:
            if isinstance(citation, str):
                citation = {"memory_id": citation}
            if not isinstance(citation, Mapping):
                return self._error("INVALID_CITATION", "each citation must be a memory ID or object")
            memory_id = citation.get("memory_id", citation.get("version_id"))
            source_id = citation.get("source_id")
            if isinstance(memory_id, str):
                memory = self._memory(memory_id)
                if memory is None:
                    return self._error("CITATION_NOT_FOUND", "cited memory version does not exist", {"memory_id": memory_id})
                if memory.status not in {"reviewed", "reviewed_correction"} or memory.status == "superseded":
                    return self._error(
                        "UNUSABLE_MEMORY_VERSION",
                        "only current reviewed memory versions may be cited in a local draft",
                        {"memory_id": memory.id, "status": memory.status},
                    )
                accepted_reviews = [
                    review
                    for review in self.store.reviews_for(memory.id)
                    if review.memory_version_id == memory.id
                    and review.scope_id == memory.scope_id
                    and review.state == "accepted"
                ]
                if not accepted_reviews:
                    return self._error(
                        "UNREVIEWED_MEMORY_VERSION",
                        "the cited memory version has no accepted review bound to its current scope",
                        {"memory_id": memory.id, "scope_id": memory.scope_id},
                    )
                if memory.scope_id != scope.id:
                    return self._error(
                        "CROSS_SCOPE_CITATION",
                        "a local draft may cite only memory versions bound to its requested scope",
                        {"memory_id": memory.id, "memory_scope_id": memory.scope_id, "requested_scope_id": scope.id},
                    )
                if source_id is not None and source_id not in memory.source_ids:
                    return self._error(
                        "INVALID_CITATION",
                        "the citation source_id is not bound to the cited memory version",
                        {"memory_id": memory.id, "source_id": source_id},
                    )
                requested_version = citation.get("version")
                if requested_version is not None and str(requested_version) != str(memory.version):
                    return self._error("STALE_CITATION", "the cited memory version number does not match", {"memory_id": memory.id, "version": memory.version})
                requested_hash = citation.get("content_hash")
                if requested_hash is not None and requested_hash != memory.content_hash:
                    return self._error("STALE_CITATION", "the cited memory content hash does not match", {"memory_id": memory.id})
                normalized_item = {
                    "kind": "memory",
                    "memory_id": memory.id,
                    "source_id": memory.source_ids[0] if memory.source_ids else None,
                    "version": memory.version,
                    "content_hash": memory.content_hash,
                    "scope_id": memory.scope_id,
                }
                normalized.append(normalized_item)
                citation_ids.append(memory.id)
                continue
            if isinstance(source_id, str):
                source = self._source(source_id)
                if source is None:
                    return self._error("CITATION_NOT_FOUND", "cited source passage does not exist", {"source_id": source_id})
                if source.scope_id != scope.id:
                    return self._error(
                        "CROSS_SCOPE_CITATION",
                        "a local draft may cite only source passages bound to its requested scope",
                        {"source_id": source.id, "source_scope_id": source.scope_id, "requested_scope_id": scope.id},
                    )
                normalized.append({"kind": "source", "source_id": source.id, "version": source.version, "content_hash": source.content_hash, "scope_id": scope.id})
                citation_ids.append(source.id)
                continue
            return self._error("INVALID_CITATION", "citation requires memory_id/version_id or source_id")
        return normalized, citation_ids

    def save_draft(self, scope_id: str, title: str, body: str, citations: Any) -> dict[str, Any]:
        """Save an idempotent local draft with exact same-scope citations."""

        scope = self._scope(scope_id)
        if scope is None:
            return self._error("SCOPE_NOT_FOUND", "The draft scope does not exist", {"scope_id": scope_id})
        if not isinstance(title, str) or not title.strip() or len(title) > self.MAX_TITLE_LENGTH:
            return self._error("INVALID_TITLE", f"title must be a non-empty string of at most {self.MAX_TITLE_LENGTH} characters")
        if not isinstance(body, str) or not body.strip() or len(body) > self.MAX_BODY_LENGTH:
            return self._error("INVALID_BODY", f"body must be a non-empty string of at most {self.MAX_BODY_LENGTH} characters")
        citation_result = self._normalize_citations(citations, scope)
        if isinstance(citation_result, dict):
            return citation_result
        normalized, citation_ids = citation_result
        try:
            content = {"scope_id": scope.id, "title": title.strip(), "body": body, "citations": normalized}
            draft_id = deterministic_id("draft", content)
            existing = self.store.get_node(draft_id)
            if isinstance(existing, Draft):
                return self._ok(operation="save_draft", idempotent=True, draft=self._record(existing), citations=list(normalized), external_side_effect=False)
            owner_run_id = deterministic_id("run-draft", draft_id)
            owner_run = AgentRun(
                id=owner_run_id,
                tenant_id=self.store.tenant_id,
                project_id=self.store.project_id,
                role="cold-consumer",
                session_id=deterministic_id("session-draft", draft_id),
                input_manifest_hash=content_hash({"scope_id": scope.id, "citation_ids": citation_ids}),
                started_at=self.FIXED_TIME,
                context_coverage="cold-session",
            )
            correction_cited = any(
                item.get("kind") == "memory"
                and isinstance(self._memory(item.get("memory_id")), MemoryVersion)
                and self._memory(item.get("memory_id")).kind == "correction"
                for item in normalized
            )
            allowed_action = "request-shared-pool-rehearsal" if correction_cited else "local-review"
            draft = Draft(
                id=draft_id,
                tenant_id=self.store.tenant_id,
                project_id=self.store.project_id,
                owner_run_id=owner_run_id,
                requested_scope_hash=content_hash(self._record(scope)),
                scope_id=scope.id,
                title=title.strip(),
                body=body,
                citations=tuple(normalized),
                created_at=self.FIXED_TIME,
                review_status="local-draft",
                allowed_local_action=allowed_action,
                content_hash=content_hash(content),
            )
            self.store.add_nodes((owner_run, draft))
            self.store.add_edge("CREATED_DRAFT", owner_run.id, draft.id, {"scope_id": scope.id})
            for item in normalized:
                if item["kind"] == "memory":
                    self.store.add_edge("CITES_VERSION", draft.id, item["memory_id"], {"scope_id": scope.id, "version": item["version"], "content_hash": item["content_hash"]})
                else:
                    self.store.add_edge("CITES_PASSAGE", draft.id, item["source_id"], {"scope_id": scope.id, "version": item["version"], "content_hash": item["content_hash"]})
            return self._ok(
                operation="save_draft",
                idempotent=False,
                draft=self._record(draft),
                citations=list(normalized),
                external_side_effect=False,
            )
        except (StoreError, TypeError, ValueError) as exc:
            return self._error("DRAFT_FAILED", str(exc), {"scope_id": scope.id})

    def state(self) -> dict[str, Any]:
        """Return a JSON-safe local state snapshot for the API."""

        try:
            return self._ok(operation="state", state=self.store.snapshot())
        except (StoreError, TypeError, ValueError) as exc:
            return self._error("STATE_FAILED", str(exc))

    def run_demo(self) -> dict[str, Any]:
        """Run the deterministic cold-agent Juniper walkthrough."""

        from .demo import run_cold_agent_walkthrough

        try:
            return run_cold_agent_walkthrough(self)
        except (StoreError, TypeError, ValueError) as exc:
            return self._error("DEMO_FAILED", str(exc))
