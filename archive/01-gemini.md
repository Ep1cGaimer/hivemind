Showing 1 of 4 activities (limited to 1)

### Concept 1: ConstraintMesh — Multi-Agent Invariant & Policy Collision Auditor

- **Novelty Relative to `ideas.md`**: Materially new direction. Unlike temporal fact invalidation (C-03/R-09) or task-leasing research queues (C-06), ConstraintMesh tracks *cross-functional operational invariants and mutual-exclusion constraints* asserted by independent departmental agents across projects.
- **Target User**: Enterprise Cross-Functional Program Manager / Launch Lead.
- **Workflow & Failure**: Autonomous department agents (SecOps, Legal/Compliance, Cloud Architecture, Commercial Operations) execute siloed project tasks. Current method: periodic review meetings and document search. Failure: Vector search finds semantic topic matches, but fails to trace indirect, multi-hop constraint collisions (e.g., Compliance Agent mandates EU-only data residency; Architecture Agent selects a US-replicated global cache for low latency; Commercial Agent commits to a sub-50ms SLA). The clash is invisible until integration failure or regulatory breach.
- **Graph Nodes & Edges**:
  - *Nodes*: `Project`, `AgentRole`, `InvariantConstraint` (e.g., `DATA_RESIDENCY`, `SLA_CAP`), `ArchitectureChoice`, `VendorService`, `Jurisdiction`, `EvidenceSource`.
  - *Edges*: `(:AgentRole)-[:ASSERTED]->(:InvariantConstraint)-[:APPLIES_TO]->(:ArchitectureChoice)-[:USES_SERVICE]->(:VendorService)-[:OPERATES_IN]->(:Jurisdiction)`, `(:InvariantConstraint)-[:FORBIDS_ROUTE]->(:ArchitectureChoice)`.
- **Exact Graph Traversal & Removal Failure**:
  - *Traversal*: Starting from a proposed new architecture or commercial plan, traverse `(:ArchitectureChoice)-[:USES_SERVICE*1..3]->(:Jurisdiction)` and intersect with `(:InvariantConstraint)-[:FORBIDS_ROUTE]->(:Jurisdiction)`.
  - *Removal Failure*: If relationships are removed, flat record search retains isolated policy sentences, but cannot compute multi-hop topological reachability between architectural components and distant jurisdictional prohibitions asserted weeks earlier by a different agent.
- **Agent Decision & Action**: Identifies the 3-hop policy collision path, formulates an approval-gated conflict memo explaining the exact clashing invariant, and prompts human leads with explicit trade-off options before infrastructure provisioning.
- **Data**: Synthetic 3-department corporate launch fixture (SecOps, FinOps, Compliance) with 15 components, 8 invariant rules, and 3 cross-cutting vendor dependencies.
- **30-Second Demo**: Architecture Agent proposes a multi-region caching layer. ConstraintMesh instantly halts the proposal, displaying a 3-hop path showing a Compliance Agent’s data-sovereignty invariant asserted two weeks prior in an unrelated ticket.
- **Fair Before/After**: Flat vector memory retrieves generic "data policy" docs without detecting the clash; recursive SQL/graph agent isolates the exact conflicting path and blocks the invalid deployment plan.
- **Closest Substitute / Competitor**: ServiceNow Strategic Portfolio Management, AWS Config / OPA (Open Policy Agent). Incumbent gap: OPA validates static declarative code at deploy time, but does not reconcile cross-department agent assumptions and commercial commitments across planning phases.
- **Differentiation**: Live cross-agent constraint reconciliation at planning time rather than post-commit CI/CD policy linting.
- **4-Day MVP**: Synthetic 3-agent launch project, 8 invariant constraints, 1 cache component, 2 simulated collision scenarios.
- **Biggest Rejection Risk**: Evaluators viewing it as an overly rigid constraint solver rather than an agent context layer.
- **Falsifiable Success Test**: Over 10 paired launch plans (5 compliant, 5 containing 2- to 3-hop indirect policy clashes), ConstraintMesh detects 100% of clashes while flat vector memory misses $\ge 80\%$.

---

### Concept 2: EpistemicLoom — Cross-Session Agent Handoff & Belief Provenance Ledger

- **Novelty Relative to `ideas.md`**: Materially repaired and extended from C-06 (ResearchOS) and R-08 (Honest Memory). Shifts focus from task queues to *epistemic status propagation* (hypothesis vs. verified fact vs. assumption) across cold-start agent sessions.
- **Target User**: Enterprise AI Operations Lead managing multi-agent support and triage pipelines.
- **Workflow & Failure**: Multi-agent pipelines pass text summaries across sessions (Triage Agent $\rightarrow$ Diagnostic Agent $\rightarrow$ Action Agent). Current method: chat transcripts and vector memory. Failure: Agents treat prior agents' conversational claims as verified ground truth. A tentative hypothesis in Step 1 (*"likely a bad tenant token"*) is treated by Step 3 as an authoritative fact, executing unjustified automated account resets.
- **Graph Nodes & Edges**:
  - *Nodes*: `AgentSession`, `Claim`, `EpistemicStatus` (`HYPOTHESIS`, `VERIFIED_FACT`, `UNVERIFIED_ASSUMPTION`), `EvidenceReceipt`, `SystemEntity`, `ActionProposal`.
  - *Edges*: `(:AgentSession)-[:PRODUCED]->(:Claim)-[:HAS_STATUS]->(:EpistemicStatus)`, `(:Claim)-[:SUPPORTED_BY]->(:EvidenceReceipt)`, `(:Claim)-[:DERIVED_FROM*1..3]->(:Claim)`, `(:ActionProposal)-[:PREDICATED_ON]->(:Claim)`.
- **Exact Graph Traversal & Removal Failure**:
  - *Traversal*: For an `ActionProposal`, traverse backwards `[:PREDICATED_ON] $\rightarrow$ [:DERIVED_FROM*] $\rightarrow$ [:SUPPORTED_BY]` to verify that every foundational claim terminates in a valid, unexpired `EvidenceReceipt` rather than an unverified `HYPOTHESIS`.
  - *Removal Failure*: Flat memory treats all historical claims as equally weighted text chunks, losing the lineage between an automated action and the unverified premise that generated it.
- **Agent Decision & Action**: The agent gates execution: if an action is predicated on an unverified hypothesis, it downgrades the action to `REQUIRE_PROBE` or prompts the human reviewer with the exact unverified claim in the handoff chain.
- **Data**: Synthetic multi-session IT support and access-remediation logs (30 claims, 10 handoffs, 5 action proposals).
- **30-Second Demo**: Remediation Agent prepares an automated credential revocation based on a 3-agent handoff. EpistemicLoom blocks the action, revealing that the root claim was marked `HYPOTHESIS` by Triage and never verified with raw telemetry.
- **Fair Before/After**: Flat/vector shared memory executes the destructive reset because the summary sounds confident; EpistemicLoom blocks it due to the missing evidence edge in the belief lineage.
- **Closest Substitute / Competitor**: LangGraph checkpoints, Mem0, Zep. Incumbent gap: They store conversational state and raw facts, but do not maintain typed epistemic status or backward evidence provenance gates for actions.
- **Differentiation**: Epistemic pedigree checking that prevents multi-agent "telephone game" hallucinations from triggering actions.
- **4-Day MVP**: 3-stage cold-start pipeline (Triage $\rightarrow$ Investigator $\rightarrow$ Actuator), 15 claims, 2 simulated unverified action traps.
- **Biggest Rejection Risk**: Skepticism that teams care about epistemic typing over simple confidence scores.
- **Falsifiable Success Test**: In 10 handoff chains containing unverified hypotheses, EpistemicLoom blocks 100% of premature actions, while flat memory baselines authorize $\ge 70\%$ of them.

---

### Position Statement

- **Current Preferred Position**: Champion **Concept 1 (ConstraintMesh)** as the stronger direction; retain **Concept 2 (EpistemicLoom)** as a viable alternative.
- **Strongest Support**: ConstraintMesh captures a high-severity, genuine Track 2 + 3 pain (cross-department agent collisions) with an undeniable multi-hop graph structure that flat vector search cannot emulate.
- **Strongest Counter**: Modeling organizational constraints requires careful scoping to avoid turning into an abstract constraint-satisfaction engine.
- **Dependent Assumption**: A 3-department synthetic launch scenario can expose multi-hop policy clashes clearly within a 30-second before/after contrast.
- **What Changes Mind**: I will switch to EpistemicLoom if evaluators argue that multi-agent handoff drift is more immediately relatable to hackathon judges than cross-department project planning.
- **Direct Response to Strongest Anticipated Objection**: *"Isn't ConstraintMesh just OPA/Linters?"* No. Static linters check declarative code at build time; ConstraintMesh reconciles dynamic, multi-agent planning invariants across siloed enterprise departments *before* code or infrastructure commitments are finalized.
