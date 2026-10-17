Showing 1 of 9 activities (limited to 1)

## Peer: `opencode/muse-spark-1.3-contributor-free` — Track 2+3 hive mind, 2 cards

### CARD A — PromiseLedger: shared commitment memory [MATERIALLY NEW]
- **User:** Maya, delivery lead, 40-person SaaS co. Recurring pain (hypothesis): promises made in meetings/docs/tickets fall through across shifts/roles.
- **Now/why fails:** Checks Slack/Notion/Linear + asks LLM. Flat/vector finds mentions of task, loses who currently owes it after delegation/departure/blockers.
- **Graph:** `Person, Agent, Commitment, Task, Blocker, Source, Team`; `PROMISED_TO, OWES, DELEGATED_TO, BLOCKED_BY, SUPERSEDED_BY, EVIDENCED_BY, ON_TEAM`.
- **Graph op / removal failure:** Resolve live owner: `(c:Commitment)-[:DELEGATED_TO*0..3]->(owner:Person)` + liveness + `BLOCKED_BY` chain. Removal: raw facts still say "Alice owns launch checklist" but miss Alice→Ben→vacant delegation + blocker; flat/SQL with same LLM returns stale owner (SQL parity accepted — same answer possible only with hand-built joins, not from agent's text retrieval).
- **Agent decision/approval:** Daily sweep proposes `NAG owner / ESCALATE / REASSIGN to successor`; writes only `ProposedAction` + evidence path; human approves reassign/escalate. No auto-messaging.
- **Data:** Fully synthetic 60-commitment fixture: meetings, tickets, 2 delegations, 1 departure, 1 blocked launch. Marked synthetic.
- **30s demo:** "Who owns SOC2 evidence pack?" Baseline: "Alice." Ledger traverses Alice→Ben→orphaned + blocked-by-vendor-doc, proposes reassign to Cara with path.
- **Before/after:** Same sources+LLM+budget: flat/vector memory vs ledger. Metrics: correct-live-owner rate, orphan recall, unsupported-claim rate.
- **Substitute (hypothesis gap):** Linear/Motion follow-ups + Mem0/Graphiti memory. Claim only hypothesis: they store tasks/facts, not delegation-orphan accountability as queryable path.
- **Diff:** Memory keyed on social obligation + liveness, not facts/decisions.
- **4-day MVP:** Ingest script, 5 parameterized Cypher tools (read-only + propose-action), one sweep agent, approval UI, ablation toggle.
- **Reject reason:** Could be a task tracker with assignee field.
- **Falsifiable test:** 20 seeded delegation/orphan cases; ledger ≥80% live-owner correct, baseline ≤50%; else kill.
- **Novelty:** New vs ideas.md: not C-03 invalidation, C-06 task-lease, R-08 write-gate, R-09 fact-ripple. Obligation/delegation-orphan mechanism is new workflow+mechanism.

### CARD B — GhostOwner: turnover-proof expertise reroute [NEW VARIANT]
- **User:** Dev, week 2 after senior departure. Pain (hypothesis): "who knows deploy pipeline now?" Flat docs point to leaver.
- **Now/why fails:** Searches docs/Slack, vectors return leaver's doc. No live successor notion.
- **Graph:** `Person(status,team), Agent, System, Doc, Skill, Ticket`; `KNOWS, CONTRIBUTED_TO, ON_TEAM, OWNS, EVIDENCED_BY, SUPERSEDED_BY`.
- **Graph op/removal failure:** `MATCH (s:System)<-[:OWNS|CONTRIBUTED_TO]-(p:Person{active})` ranked by recency + `shortestPath((leaver)-[:ON_TEAM|CONTRIBUTED_TO*1..3]-(successor))`. Removal: flat finds correct skill text but cannot reroute to live successor via team/contribution paths.
- **Agent action/approval:** Answers with live owner + 2 evidence paths + draft handoff note; human approves contact/reassign. Read-only answer default.
- **Data:** Synthetic 25-person org, 3 departures, deploy/auth systems, docs/tickets. Marked synthetic.
- **30s demo:** "Who can approve hotfix for billing-worker?" Baseline names departed Ravi. Graph reroutes Ravi→same-team Priya (2 merged PRs + on-call) with path.
- **Before/after:** Same corpus/LLM: vector RAG vs graph reroute. Metrics: live-owner precision, dead-pointer rate, provenance validity.
- **Substitute (hypothesis):** Atlassian/Confluence + Graphiti/Cognee expertise lookup. Hypothesis gap: they retrieve authors, not liveness-aware successor traversal.
- **Diff:** Company brain treats departure as first-class graph event, not metadata filter.
- **4-day MVP:** Org fixture, 4 Cypher tools, one Q&A agent, departure simulator, dead-pointer metric.
- **Reject reason:** Overlaps MERIDIAN/Unspool expert discovery; wow weaker than Card A.
- **Falsifiable test:** 15 departure queries; graph halves dead-pointers vs vector baseline; else kill.
- **Novelty:** Reference-derived domain (expertise lookup in §2/§5) but new mechanism: departure-event reranking via contribution/team paths.

### Position
1. **Preferred:** A > B.
2. **Strongest support:** A has daily recurring pain, one-loop agent, crisp orphan wow that flat memory structurally misses; permissions natural (team-scoped commitments).
3. **Strongest counter:** A risks looking like a ticket tracker; delegation chains need careful fixtures or demo looks staged.
4. **Depends on:** Delegation/orphan cases occur often enough to matter (hypothesis, unvalidated).
5. **Changes mind:** If fixture review shows <10% real follow-ups involve delegation/departure, or same-LLM SQL/traversal ties without extra authoring, switch to B.
6. **Vs top objection ("SQL/BFS can do it"):** Agreed parity possible — claim is not mathematical uniqueness. Win is agent-reliability: bounded Cypher tools + evidence paths stop stale-owner hallucinations that flat/vector agents emit under same budget; test measures that, not query expressiveness.
