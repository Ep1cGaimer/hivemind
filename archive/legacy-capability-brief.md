# HiveMind — standalone product idea

## Pitch

**A shared company brain that remembers what was learned, why, and where it applies.**

One role agent learns something. Another starts fresh, retrieves that learning with its source and limitations, resolves a missing condition, and leaves a scoped correction for the next role.

## Current decision and boundary

HiveMind is a standalone Track 2 + 3 product. The first deterministic local
vertical slice is implemented in `hivemind/`, `web/`, and `tests/`. The default
backend is in-memory; live FalkorDB queries, model-backed provider calls, and a
runtime retention comparison remain unvalidated gates.

This file is self-contained and can move with the project to a different folder.
It does not require another project, its agents, or the historical debate files.

## User and painful workflow

The first user is an operations lead preparing technical customer walkthroughs with engineering, support and account-planning agents.

The hypothesized failure is qualifier loss across agent sessions: “the pilot worked on a reserved worker pool” becomes “the capability is ready.” Several summaries then look like corroboration even though they repeat one limited observation.

The broad product is reusable company-agent memory. Its first demonstration stays within one capability-planning workflow rather than attempting a full enterprise platform.

Current substitutes include qualified shared notes, direct-source retrieval, enterprise search agents, provenance-aware memory products, and ordinary operator review.

## What the memory preserves

Every useful learning should retain:

- What was observed or asserted.
- Its exact source and version.
- The context and conditions under which it applies.
- What is still unknown.
- Any explicitly reviewed correction and its scope.
- Which later drafts cite the affected memory version.

Three things must remain distinct: **an agent saw a source; an agent claimed that source supports a statement; a reviewer accepted a specific interpretation.**

None automatically implies the others. Review does not establish universal truth or authorize business action.

## Proposed agent loop

1. An engineering-role agent records a qualified finding with exact source spans through a bounded memory gateway.
2. A fresh planning-role agent recalls relevant memories and follows their declared support to earlier memories or original passages.
3. It interprets the conditions against the current request and asks a targeted question when applicability is unresolved.
4. An operator supplies a scoped clarification and accepts its saved wording.
5. A later cold role retrieves that clarification and changes a concrete local plan or draft without access to the original chat.

Role clients can run serially using the same model. The value comes from persistent learning across contexts, not a large simultaneous swarm.

The interface presents **What we learned / Where it applies / Why / What needs checking**. Internal evidence states stay in the details.

## Why FalkorDB matters

The critical question is:

**Does this remembered capability apply to the current company context, what supports it, and which correction should the next role use?**

Critical path:

**MemoryVersion → Claim → SupportProposal → earlier MemoryVersion → its support → SourcePassage**, joined to applicable **Scope** and **Review**.

Consumer path:

**corrected MemoryVersion ← CITES_VERSION ← Draft**

The graph selects the relevant evidence, correction and consumer frontier. The agent reads the actual passages and decides what remains unresolved.

Removing the relationships leaves raw notes but removes this implementation's transitive support investigation, scoped version selection, and version-specific consumer discovery. Full SQL/provenance plus the same LLM can reproduce these operations; FalkorDB exclusivity is not the claim.

## Proposed graph model

| Node | Main identity and properties |
|---|---|
| CompanyEntity | Canonical company/project/account/system/capability ID; explicit aliases |
| Scope | Entity IDs, environment/stage, qualifiers and known validity interval |
| SourcePassage | Artifact/version, exact span, text, content hash and observation time |
| AgentRun | Role, independent session ID, input manifest, logging coverage |
| MemoryVersion | Qualified text, immutable version, writer, scope and source references |
| Claim | Qualified proposition, entity/scope candidates and workflow status |
| SupportProposal | Exact cited spans, relation kind, proposing run and rationale |
| Review | Exact version/proposal/scope hash, reviewer, decision and time |
| MemoryUse | Returned versions and retrieval manifest; exposure receipt only |
| Draft | Requested scope, declared citations, local action and review status |

Directed edges include AgentRun-WROTE→MemoryVersion, MemoryVersion-ASSERTS→Claim, Claim-HAS_PROPOSAL→SupportProposal, SupportProposal-CITES_PASSAGE→SourcePassage or CITES_MEMORY→MemoryVersion, Claim-IN_SCOPE→Scope, Review-REVIEWS→an exact item, and scoped MemoryVersion-SUPERSEDES→MemoryVersion.

READ and retrieval edges record exposure only. They never automatically create semantic support. A shared background document does not merge separate observations, and different run IDs do not establish statistical independence.

Identity is tenant/project-qualified and version/hash-bound. The LLM proposes ambiguous entity/scope matches instead of silently merging them. Missing qualifiers remain unknown. Corrections create immutable scoped versions; they do not overwrite every statement about the company.

## Essential graph operations

| User question | Traversal and result | Agent use |
|---|---|---|
| What do we know for this context? | Entity/scope → applicable memory versions, source references and review state | Select learning or ask about context |
| Why does this memory say that? | Memory → claim → proposed support → earlier memories/passages | Read exact support and identify lost qualifiers |
| Are these summaries citing the same observation? | Declared support paths → source identities, keeping exposure separate | Investigate repeated evidence without counting votes as truth |
| What is missing for this situation? | Requested scope → support qualifiers and unresolved frontier | Ask a condition-specific question or draft a bounded statement |
| Does this correction apply here? | Review → exact version/proposal/scope → replacement | Apply only the accepted qualification |
| Which later work should be reconsidered? | Corrected version ← explicit draft citations; retrievals listed separately | Propose local review without claiming causal influence |
| What should a fresh role use now? | Independent session → current scoped recall and source paths | Change its draft using persistent learning |

Vector similarity can seed retrieval but does not itself establish transitive justification, exact scope, or supersession. Equivalent relational and complete-source controls remain valid.

Cycles, traversal caps and missing lineage return an incomplete frontier, never a claim of complete evidence or absence of real support.

## Deterministic and model responsibilities

Deterministic code controls access, tenant-selected graph keys, identities, receipts, bounded tools, source/version bindings, idempotency, and scoped local writes.

The LLM interprets source support and qualifiers, proposes mappings/corrections, asks, and drafts. It cannot turn root counts into truth, READ into support, or reviewer acceptance into business permission.

Only synthetic or explicitly permitted data enters the MVP. Source visibility is enforced before recall; derived memories cannot bypass required source access. Source text cannot instruct tools or grant privileges. No external messages or customer commitments are sent.

## Thirty-second demo

Several departmental summaries say “overnight refresh is ready.”

The agent follows their support to a pilot note: refresh was observed on the **reserved worker pool**; shared-pool behavior was not exercised.

It asks which pool Juniper's evaluation walkthrough uses. A scripted operator clarification identifies the shared pool. The saved correction says the supplied evidence does not establish refresh for that context.

Restart the planner without its old chat. Its draft now requests a shared-pool rehearsal before promising overnight refresh. Another environment does not inherit Juniper's correction.

The memorable change is a condition-specific plan replacing unsupported generalization. This synthetic scenario does not establish actual refresh behavior, successful retention, or superiority over notes.

## Minimum version and four-day scope

One synthetic company, one capability, two environments/scopes, at most eight visible items per case, one memory gateway, bounded graph tools, independent role sessions, a restarted consumer, and one local draft view.

Exclude broad connectors, autonomous business actions, generic enterprise permissions engineering, and a large swarm.

| Day | Deliverable, only after approval |
|---|---|
| 1 | Pin/verify FalkorDB and client; independent fixture/oracle; one actual write-and-cold-read versus qualified notes |
| 2 | Bounded recall/support/correction tools; immutable scoped versions and real receipts |
| 3 | Role clients, operator clarification, cold consumer and cited draft change |
| 4 | Fair controls, negative cases, preparation measurements, reproducibility and demo |

The first comparison can stop the project. FalkorDB query support is still to be checked against the pinned version; no Neo4j/APOC assumptions.

## Evaluation, competition and rejection criteria

Use identical passages, corrections, scopes, access and comparable model budgets for isolated sessions, flat/vector memory, complete qualified source-linked notes, SQL/provenance with the same LLM, and this graph gateway. Include a configured capable memory product where accessible.

Measure scope correctness, useful questions, exact citations, unknown preservation, correction reuse after restart, cross-scope errors, and total preparation/review effort. Include separate observations sharing background, missing support, scoped correction, and stale/cyclic lineage.

Existing systems already provide graph memory, provenance and company-context agents; correlated-memory reasoning is also researched. The claim is an applied workflow hypothesis, not a new memory algorithm or an established unserved market.

The largest risk is that qualified notes deliver equal useful work with less setup. Reject the product argument if they do. Reject the design if it invents support, guesses applicability, leaks corrections across scope, relies on hidden chat context, or needs answer-coded lineage.

Paper review has exercised logical distinctions only. Demand, semantic accuracy, review economics, actual retention and configured-competitor differentiation remain unvalidated.

The conditional alternative is scoped sales-to-delivery acceptance memory: preserve requested, proposed and explicitly accepted scope for a cold delivery agent. Some peers prefer its clearer recipient workflow. It requires its own checklist comparison and is not automatically selected if HiveMind fails.

The local slice does not establish demand, production safety, retention, or
competitive superiority. Those claims still require the validation gates in the
decision memo before external use or submission.
