Showing 1 of 68 activities (limited to 1)

## Concept A: ClearanceMemory (new mechanism)

- **Named user:** The internal AI-platform owner who has to show a shared agent memory won't leak. The employees who query it are the end users.
- **Workflow, current method, failure (hypotheses):**
  - Agents write conclusions into shared memory from sources with different access rights. Later agents answer other employees from it.
  - Today teams either keep per-user memory silos or share a vector memory with document-level filters at retrieval.
  - I suspect derived conclusions lose their sources' access rules. This is unsourced.
- **Nodes and edges:**
  - Nodes: `Principal`, `Group`, `Source`, `Claim`, `SupportSet`, `Agent`, `Session`.
  - Edges: `MEMBER_OF`, `CAN_READ(Source)`, `WRITTEN_BY`, `DERIVED_FROM(Claim→Claim)`, and `SUPPORTED_BY` linking a claim to the sources in each support set.
- **Graph operation:** A claim is visible to a principal if some support set has every source readable, recursively through `DERIVED_FROM`. Revoking access or adding an independent source recomputes visibility.
- **Removal failure:** The text and sources remain, but derived-claim visibility and the "second independent source unlocks it" path are lost.
- **Agent decision:**
  - Answer from visible claims, say a restricted topic exists without detail, or route an access request to the source owner.
  - When writing a new memory, propose which existing claims support it. A reviewer approves that support set, so the access rule cannot be forged from an unreviewed guess.
  - Deterministic code computes visibility. The LLM composes the answer and proposes support sets.
- **Data:** Synthetic: 3 roles, 12 sources, 20 claims, planted canary strings. Clearly labelled fictional.
- **30-second demo:**
  - An HR-role agent records a reorg claim from a restricted document.
  - An engineer asks about it. A flat shared memory leaks the canary. ClearanceMemory answers "nothing shareable."
  - A public all-hands notice is added, and the claim becomes visible through the second support path, with the path shown.
  - Revoking the notice hides it again.
- **Fair before/after:** Same sources and LLM. Arms: isolated agents, flat shared memory with a retrieval-time document filter, and the strongest control, SQL support-set ACLs plus the same LLM. Measure canary leaks, authorized recall, revocation propagation and provenance validity.
- **Closest substitute (unverified):** Permission-aware enterprise search and memory APIs with user scoping. I do not know whether they handle derived-claim access rules.
- **Differentiation:** Visibility computed over derivation and alternative support, not documents.
- **Four-day MVP:** 3 principals, 12 sources, 20 claims, 5 queries.
- **Biggest rejection reason:** The access computation is deterministic and SQL can tie it. The LLM role is thin, and demand and competitor gaps are unvalidated.
- **Falsifiable test:** Zero canary leaks across 30 queries, revocation hiding the claim within one recompute, and authorized recall at least matching the filter-only arm. Kill it if a rule engine without the agent gives identical answers, or a documented incumbent already handles derived-claim access.
- **Novelty:** The references touch tenant isolation only, so this is a new mechanism.

## Concept B: SuccessionGraph (partly new)

- **Named user:** An engineering or ops manager handling a departure, and the successor.
- **Workflow, current method, failure (hypotheses):** Offboarding uses a handoff document and a generic exit interview. It misses knowledge only the leaver holds.
- **Nodes and edges:**
  - Nodes: `Person`, `Artifact` (service, runbook, job, vendor contract), `Decision`, `CapturedClaim`.
  - Edges: `AUTHORED`, `REVIEWED`, `ON_CALL_FOR`, `ANSWERED_QUESTION_ON`, `DEPENDS_ON`, `CAPTURED_FROM`.
- **Graph operation:**
  - Find artifacts whose recent author, reviewer and answerer paths all run through the leaver.
  - Rank them by transitive dependents.
  - Suggest successors by co-review overlap.
  - After capture, recompute the residual concentration.
- **Removal failure:** The single-point ranking, dependents and successor overlap disappear.
- **Agent decision:**
  - Run a short targeted interview for each risky artifact and write answers as claims with provenance.
  - The leaver and manager approve each claim before it enters company memory.
  - A cold-start successor session later answers questions from it.
- **Data:** Synthetic: 12 people, 25 artifacts, 6 months of edges, planted single-person artifacts and decoys.
- **30-second demo:** The graph shows three artifacts only the leaver touches, one with four dependents. The agent asks targeted questions. A new session answers a successor's question with a cited claim.
- **Fair before/after:** A generic exit-interview LLM, flat memory, and SQL set difference plus the same LLM. Measure single-point recall and precision, question relevance, and the successor's answer correctness with provenance.
- **Closest substitutes (unverified):** Service catalogs with ownership, bus-factor tools, knowledge-management tools.
- **Differentiation:** It closes the loop from concentration analysis to interview to durable successor memory.
- **Four-day MVP:** The synthetic graph, one interview loop, one successor query.
- **Biggest rejection reason:** Concentration is a set computation that SQL ties. Bus-factor tools exist, and synthetic edges are cleaner than reality.
- **Falsifiable test:** Five planted single-person artifacts and three decoys with multiple reviewers. Kill it if a bus-factor script plus the same LLM matches recall and the successor answers.
- **Novelty:** Partly new. The mechanism is new, but expertise lookup is adjacent to R-01.

## Position

- **Preferred:** A, ClearanceMemory.
- **Strongest support:** It addresses a safety concern that is central to shared company memory. The wow is a claim that unlocks through a second independent source. It also meets the brief's point that shared memory should not mean everyone reads everything.
- **Strongest counter:** The agent's work is thin, and the result may be an ACL rule engine with an LLM front.
- **Assumption:** Support-set proposals by the LLM are non-trivial and reviewable.
- **What changes my mind:** An incumbent documenting derived-claim access rules, or a rule engine matching the agent arm. That would move me to B.
- **Response to the strongest anticipated objection (SQL ties):** Parity is allowed. FalkorDB computes the visibility inside the runtime, and the agent's support proposal and routing change what is stored and answered. If those add nothing, I reject A.
