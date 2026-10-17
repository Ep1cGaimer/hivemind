Showing 1 of 77 activities (limited to 1)

---

These are separate proposals for the additional Track 2 + 3 product. RollbackWitness remains the approved main direction. All demand, prevalence, and competitive-gap claims below are hypotheses pending validation.

**Concept 1 — EchoCheck: a company brain that remembers where agreement came from**

**User/workflow.** A product lead deciding whether customer evidence justifies prioritizing a feature. Sales, support, and research agents summarize different company documents. The hypothesized failure: five apparently corroborating statements originate from one customer conversation, copied through presentations, tickets, and agent summaries. Shared memory amplifies apparent agreement without adding independent evidence.

**Novelty.** Materially new relative to ideas.md: the core operation is detecting evidence convergence and circular corroboration during product prioritization. It concerns source independence, rather than temporal invalidation or generic evidence-gated writes.

**Graph.** Nodes: `Feature`, `Claim`, `Observation`, `Artifact`, `AgentRun`, `Account`, `Review`. Edges: `SUPPORTS`, `DERIVED_FROM`, `QUOTES`, `GENERATED_FROM`, `ABOUT`, `REVIEWED_BY`. Provenance includes exact spans, versions, scope, and permissions.

**Exact operation/removal failure.** Traverse supporting claims backwards through derivation paths to recorded originating observations; identify shared roots, unknown origins, and cycles. Removing relationship tools removes this implementation’s origin grouping and circular-support witnesses. Raw records remain available for reconstruction; SQL plus the same agent can tie.

**Agent/action.** One session proposes source-grounded lineage links from raw documents. Uncertain derivations remain proposed. A cold-start prioritization session retrieves origin groups, investigates apparent corroboration, and drafts a recommendation or asks for genuinely additional evidence. Deterministic traversal groups origins; the LLM interprets source language and selects the unresolved evidence question. The product lead approves any local roadmap draft. Origin independence never proves truth or statistical significance.

**Data/demo.** Twelve synthetic artifacts, two features, three fictional accounts, and two cold-start roles. In thirty seconds: “Five teams support this feature.” Reveal that four statements descend from one interview and the fifth has unknown provenance. The agent changes its recommendation to “insufficient distinct observations,” citing paths. Add a separately recorded observation; a later session incorporates it without counting copied summaries again.

**Fair proof.** Same documents, relationships, permissions, model, and budgets across isolated sessions, flat/vector memory, and provenance-aware SQL plus the same agent. Measure correct origin grouping, unsupported independence claims, targeted questions, and cold-start retention—not promised prioritization accuracy.

**Substitute/differentiation.** Research repositories, CRM evidence boards, citation tracking, Graphiti/Cognee, and careful human review. Exact current coverage is unverified. The hypothesis is durable cross-agent protection against company-wide evidence echo.

**Four-day minimum.** Day 1 fixture/oracle; Day 2 bounded provenance tools; Day 3 intake-to-prioritization handoff; Day 4 controls and evidence view. Permission filtering precedes retrieval; inaccessible sources cannot leak through counts.

**Biggest rejection reason/test.** Reliable provenance could require excessive annotation. Blindly author ten copied, independent, ambiguous, and cyclic cases. Reject if the agent declares unknown origins independent, or lineage preparation outweighs manual review.

**Concept 2 — PromiseMesh: shared memory of who has actually accepted the handoff**

**User/workflow.** A customer-success lead coordinating one enterprise onboarding. The hypothesized failure: sales remembers a promise, implementation remembers a prerequisite, and support remembers an unresolved exception—but each agent reports its own task as complete. Nobody owns the unmet acceptance condition between them.

**Novelty.** Reference-adjacent to GraphMem/ResearchOS, but focused on two-sided company commitments: a completed producer task is not automatically an accepted consumer deliverable. It is not a generic task queue.

**Graph.** Nodes: `Onboarding`, `Commitment`, `Deliverable`, `AcceptanceCondition`, `TeamRole`, `Evidence`, `AgentRun`. Edges: `PROMISED_BY`, `OWNED_BY`, `PRODUCES`, `REQUIRES`, `ACCEPTED_BY`, `SUPPORTED_BY`. Requests, accepted obligations, and reported completion remain distinct states.

**Exact operation/removal failure.** Traverse an onboarding outcome backwards through required deliverables and acceptance conditions; expose unaccepted handoffs, missing owners, and circular prerequisites. Removing relationships removes the cross-team acceptance frontier and its witnesses.

**Agent/action.** An intake session interprets promises and proposed acceptance conditions from synthetic notes. A later coordinator session investigates mismatched meanings—“integration ready” versus “customer validated”—and drafts one precise acceptance question. Only an authorized human can approve an obligation or acceptance receipt; no messages are sent.

**Data/demo.** Eight notes, three fictional teams, six commitments. “Everyone finished, but onboarding cannot start.” Show a completed export that implementation never accepted because its identifier format differs. The agent retrieves the original promise and drafts the exact unresolved handoff question; a later session remembers the approved answer.

**Proof/substitutes.** Compare identical sources against isolated agents, flat shared memory, and dependency-aware workflow software plus the same LLM. Measure missed acceptance obligations, invented approvals, scope-correct reuse, and valid paths. Project-management and customer-success platforms are strong substitutes; differentiation is unverified.

**MVP/rejection test.** Four days: fixture, acceptance graph, one cold-start handoff loop, evaluation. Reject if explicit forms capture the same useful distinctions with less preparation, or any completion statement becomes acceptance without approval.

My preferred position is **EchoCheck**. Its strongest support is a memorable shared-memory failure: repetition masquerading as corroboration. Its strongest counter is provenance curation. The assumption is that cross-agent reuse creates material evidence confusion. Independent-source errors or equivalent lower-effort incumbent handling would change my mind. Against “this is citation deduplication”: exact duplicates are insufficient; the proposed test must include paraphrased, multi-hop derivations and unknown roots. If those require preclassified answers, reject it.
