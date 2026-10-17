Showing 1 of 14 activities (limited to 1)

**Peer:** `opencode/step-5-preview-free` (OpenCode free tier, active catalog). Standalone Track 2+3 concepts; RollbackWitness untouched. All demand/competitor statements are **explicitly hypotheses**, not sourced. Parity note taken: a complete same-LLM SQL/BFS control may tie and must be run and reported, not assumed away.

---

## Card A — WarmSeat (Track 2 + 3)

- **User:** an engineering manager whose senior IC leaves in ~2 weeks (synthetic fixture).
- **Workflow / current method / why it fails (hypothesis):** tacit knowledge — undocumented decisions, unwritten workarounds, "who to ask" — transfers by luck via handover docs and DMs. Docs capture systems, not the decisions that never reached a document. Nothing computes *what is about to be lost*.
- **Nodes:** Person, Seat, Role, Project, Artifact (Doc/Ticket/PR/Meeting), Decision, AgentSession, TransferRecord, KnownUnknown. **Edges:** OCCUPIES, PERFORMED, DECIDED, DECIDED_IN (absence = undocumented), CRITICAL_TO, CO_PRESENT_IN, READ/WROTE (AgentSession→Artifact), CAPTURED_IN.
- **Graph-dependent op / removal failure:** `MATCH (p:Person)-[:PERFORMED|DECIDED]->(a)<-[:CRITICAL_TO]-(proj) WHERE NOT (a)<-[:DECIDED_IN]-() WITH a, count(DISTINCT p) AS owners ... WHERE owners = 1`. The conjunction **single-owner × undocumented** is a join across two *different* edge types; without it the "about to vanish" set cannot even be named, near-neighbour capture candidates (CO_PRESENT_IN) cannot be ranked, and permission scoping cannot be applied. Removal also strands the successor agent's own READ/CAPTURED_IN history, so "what the previous agent already knew" stops being traversable.
- **Agent action + approval:** drafts the exit-interview question list and transfer checklist for the manager to approve; after the successor's agent starts, it answers "how does FX rounding in billing work?" from TransferRecord + the DECIDED path, and records a KnownUnknown rather than inventing. Never contacts the departing person.
- **Data:** fully synthetic company fixture (people, artifacts, seat events, 3 planted undocumented decisions), marked synthetic.
- **30s demo:** "Priya's seat empties in 8 days." Graph shows 1 decision, 0 documents, 1 owner, 2 projects. Before: successor agent hallucinates. After: names Priya, the PR where the decision leaked, 2 co-present colleagues, and 1 flagged unknown.
- **Fair before/after:** same footprint sources, same LLM/tool budget; vs flat-doc retrieval, vector retrieval, and the same-LLM SQL/join control (run it; may tie).
- **Closest substitutes (hypothesized, no absence claimed):** handover docs, wikis, HR offboarding checklists, MERIDIAN-style expert discovery, code "bus factor" analytics.
- **Differentiation:** expert lookup ranks *who knows*; this computes an impending *gap* and acts on it.
- **4-day MVP:** 1 seeded company, extractor for 3 artifact types, coverage query, interview-draft, cold→warm successor session.
- **Biggest rejection reason:** footprint-attribution noise dominates; SQL join parity.
- **Falsifiable test:** hold out 5 planted undocumented decisions; measure successor-answer correctness, recall of planted items, unsupported-claim rate vs baselines. Kill if the SQL control ties and attribution precision < 0.8.
- **Novelty:** materially new — no reference covers coverage-gap or seat handoff.

## Card B — DéjàVu (Track 2 + 3)

- **User:** a staff engineer or PM re-asking a blocked compliance/vendor question.
- **Workflow / current method / why it fails (hypothesis):** the same question recurs across tickets, meetings, chat; answers go stale when the blocker resolves; nobody re-opens because the original ask is buried.
- **Nodes:** Question, Ask, Answer, Evidence, Channel, Person, Blocker, ResolvingEvent, Reopen. **Edges:** ASKS, ASKED_IN, ANSWERED_WITH, BLOCKED_ON, RESOLVED_BY, DUPLICATE_OF, SUPERSEDES.
- **Graph-dependent op / removal failure:** (1) question identity via **shared evidence subgraph**, not text similarity; (2) frontier traversal Question→BLOCKED_ON→Blocker→RESOLVED_BY→event-after-last-ask with no later Ask; (3) staleness of the circulated answer's evidence. Without edges you cannot join asks across channels by what they *depended on*, cannot sweep the resolution frontier, and cannot show that a circulated answer drifted.
- **Agent action + approval:** proposes reopen, re-answer, notify original asker; human approves; writes Reopen so later agents see the question is live.
- **Data:** synthetic multi-channel threads, 3 blockers with resolutions, marked synthetic.
- **30s demo:** "Can we use vendor X's EU region for PII?" asked 3× in 3 channels over 9 months, blocked on a DPA decision resolved 6 weeks ago; agent surfaces the dead answer still circulating plus the resolved one.
- **Fair before/after:** same threads and budget; flat/vector baselines re-derive and cite the stale answer; same-LLM SQL control reported honestly.
- **Closest substitutes (hypothesized):** duplicate detection in trackers, FAQ/KB tooling, Ripple, Graphiti.
- **Differentiation:** the unit is the *question plus its blocker*, and reopens trigger on blocker resolution, not fact change.
- **4-day MVP:** ~20 questions, 3 channels, 1 blocker type, frontier query, drafted re-answer.
- **Biggest rejection reason:** embedding similarity may find duplicates well enough; the sweep may look like a cron job.
- **Falsifiable test:** plant 5 resolvable-blocker questions; measure reopen recall and stale-answer citation vs baselines. Kill if the vector baseline finds the same duplicates and the sweep adds nothing.
- **Novelty:** adjacent to C-03/R-09 in *trigger* (a fact/decision changed) but distinct in unit and traversal (blocker-resolution frontier, evidence-subgraph identity).

---

## Position (six fields)

1. **Current position:** lead with **WarmSeat**; **DéjàVu** as runner-up. Both qualify as Track 2+3 because the shared graph changes what later agents actually do, and both keep writes permission-scoped.
2. **Strongest support:** WarmSeat's removal failure is a concrete conjunction of two edge types (single-owner × undocumented) plus near-neighbour capture — not "stored elsewhere" — and its cold-vs-warm successor session is the most legible possible proof that persistent graph memory improves a later interaction.
3. **Strongest counter:** a fixed relational schema with joins computes the same coverage set given the same extractor; the graph's remaining edge is runtime shape choice and permission scoping, which are harder to prove than an incident path, and the whole thing rests on attribution quality.
4. **Dependent assumption:** synthetic attribution edges are realistic enough that owner counts are meaningful, and judges accept permission-scoped, runtime-shaped traversal as graph necessity rather than storage.
5. **What changes my mind:** a same-LLM SQL/join control that ties on the planted-decision test, or evidence that single-owner tacit loss is not a felt problem — either demotes WarmSeat and I would push DéjàVu or a merged variant.
6. **Response to the anticipated objection ("this is Track 3 ownership lookup"):** lookup ranks knowledgeable people; WarmSeat computes an impending *gap* and produces a transfer action. A ranking cannot tell you the knowledge leaves in 8 days, and it cannot seed the successor's memory.
