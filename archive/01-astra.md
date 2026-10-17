Showing 1 of 67 activities (limited to 1)

---

These are separate Track 2 + 3 proposals. RollbackWitness remains the approved main direction. All demand and competitive-gap claims below are hypotheses pending validation.

**Concept A — DemandRoots: company memory that remembers where demand actually originated**

**User and workflow.** A product operations lead preparing weekly roadmap triage. Sales, support, and product agents summarize customer requests into different documents. Hypothesized failure: one request copied through several summaries appears to be several corroborating requests, while its original qualification disappears.

**Novelty.** Materially new relative to `ideas.md`: evidence-origin tracing for demand aggregation, rather than fact invalidation, generic research coordination, or rejecting unsupported memory writes. It retains derived summaries but prevents their multiplication from masquerading as additional observations.

**Graph.** Nodes: `RequestClaim`, `SourcePassage`, `Interaction`, `Account`, `Opportunity`, `Summary`, `AgentSession`, `Decision`, and `Owner`. Edges: `EXTRACTED_FROM`, `DERIVED_FROM`, `OCCURRED_IN`, `CONCERNS_ACCOUNT`, `SUMMARIZES`, `SUPPORTS`, and `OWNED_BY`.

**Exact operation/removal failure.** Starting from a proposed feature, traverse supporting claims backward through derivation paths to documented original interactions; group by account and preserve unknown ancestry. Removing relationship tools removes this implementation’s origin-collapse and citation-path operation, although raw facts remain available and SQL could reconstruct it. Distinct origins are not automatically statistically independent.

**Agent work and approval.** A sales-role session extracts a qualified request with cited wording. A later cold-start product-role session investigates whether apparently similar claims express the same requested outcome, distinguishes copied wording from separately observed requests, and asks about ambiguous provenance. It drafts a revised demand brief; the lead approves memory merges and prioritization changes.

**Data and 30-second demo.** Twelve synthetic source passages, three fictional accounts, and two sessions. “Five reports support this feature” becomes “four trace to one conditional request; the fifth is a different requirement.” The agent requests one missing clarification instead of recommending a broad build. Restart the product session: the accepted distinctions persist.

**Comparison and substitutes.** Compare isolated agents, flat/vector shared memory, and provenance SQL with the same LLM, sources, links, permissions, and budgets. Substitutes include product-feedback repositories, CRM reports, manual spreadsheets, and provenance-aware memory systems; their exact coverage is unverified. Proposed differentiation: shared agents preserve *observation ancestry*, not merely citations.

**Four-day minimum and falsification.** Day one fixture and origin oracle; day two bounded graph tools; day three two-session investigation/approval; day four controls and demo. On eight small cases, require valid origin paths, no invented account independence, and unknown ancestry preserved. Biggest rejection reason: maintaining derivation links may cost more than manual deduplication. Reject if the agent merely recounts preclassified copies or a feedback table resolves everything equally well.

**Concept B — PromiseRelay: company memory that distinguishes “we mentioned it” from “delivery accepted it”**

**User and workflow.** An implementation manager taking over a newly sold customer deployment. Hypothesized failure: a sales summary describes requested outcomes as agreed deliverables, while engineering acceptance covers only a narrower scope. Agents repeatedly transfer polished summaries without preserving who accepted what.

**Novelty.** A new commercial-to-delivery workflow with a narrower mechanism than ResearchOS: matching customer-facing commitments to scoped internal acceptance evidence. It borrows provenance and durable handoffs but is not temporal invalidation or a generic task queue.

**Graph.** Nodes: `Account`, `ConversationPassage`, `RequestedOutcome`, `Commitment`, `DeliveryScope`, `Acceptance`, `Team`, `Dependency`, and `Handoff`. Edges: `REQUESTED_IN`, `PROMISED_IN`, `REQUIRES`, `ACCEPTS_SCOPE`, `ACCEPTED_BY`, `DEPENDS_ON`, and `HANDED_TO`.

**Exact operation/removal failure.** Traverse each stated commitment through its required delivery scopes to explicit team acceptances and prerequisites. Identify uncovered or ambiguous scope with source paths. Removing relationship tools removes this implementation’s commitment-to-acceptance coverage check. A complete relational implementation may tie.

**Agent work and approval.** A sales session proposes source-grounded commitments. A cold-start implementation session compares their conditions with acceptance passages and asks a targeted clarification. “Can explore CSV import” cannot silently become “will deliver automated historical migration.” The manager approves the resulting handoff draft; no external messages or contractual determinations occur.

**Data and demo.** Ten synthetic passages, one fictional account, three commitments, two teams. Sales memory says “migration included.” The delivery agent finds acceptance only for a one-time CSV import and surfaces the unsupported automation scope. After a simulated manager clarification, the next session preserves the narrowed handoff.

**Comparison, substitutes, and build.** Same-information isolated/flat/vector agents and SQL coverage plus the same LLM. CRM handoffs, project checklists, and customer-success tools are strong unvalidated substitutes. Four days cover fixtures, graph coverage, one clarification/approval loop, and eight handoff controls.

**Rejection test.** Reject if scope matching needs hand-authored answer labels, missing acceptance is presented as refusal, or a checklist supplies equivalent usefulness with less preparation. No inferred promise becomes authoritative without review.

**Six position fields**

- **Position:** Prefer DemandRoots provisionally.
- **Support:** Its origin-chain discovery can visibly change a recommendation across sessions.
- **Counter:** Provenance maintenance may dominate value.
- **Assumption:** Reused summaries obscure origins often enough to matter.
- **Mind-change:** Easy manual deduplication or equivalent incumbent coverage.
- **Direct objection:** “Just SQL” is acceptable; “just counting curated roots” is not. Interpretation must change claim grouping or the next evidence request.

Both enforce source permissions before retrieval, including derived memories; neither treats document text as tool instructions.
