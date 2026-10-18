> Current direction: Git-aware team coding-assistant memory. This memo is the
> historical Juniper capability-planning decision record. Current implementation,
> comparison and pending acceptance are in `testing/git_memory/RESULTS.md`.

# Additional concept decision memo — HiveMind

Date: 2026-10-15. Chair's conditional recommendation, not a declaration of consensus or build authorization. This memo evaluates HiveMind as a Track 2 + 3 company-agent memory tool.

## Recommendation and pitch

**Preferred concept: R11, HiveMind — shared company memory with its evidence and limits.**

One role learns something; another role starts fresh and can use that learning, inspect its basis, ask about missing conditions, and retain a correction without broadening it.

**Conditional runner-up: R06, scoped sales-to-delivery acceptance memory.** It preserves what was requested, proposed, and actually accepted so a fresh delivery agent can draft the right plan. It remains a serious alternative, not an approved fallback.

> We propose building **HiveMind** for **an operations lead coordinating technical customer walkthroughs**, who has **role agents repeatedly restating capability claims while losing their conditions**. FalkorDB is indispensable to this implementation because **bounded traversal connects a remembered assertion through earlier memories to source passages, applicable scoped corrections, and drafts citing the affected version**. The agent will **interpret those passages, ask a condition-specific question, and use a reviewed clarification in a later cold session's planning draft**. The before/after demo will compare **scope correctness, valid evidence paths, retained corrections, and preparation effort**. The minimum version is scoped to four days using **a clearly synthetic company fixture**. The main risk is **that qualified source-linked notes deliver equal useful work with less preparation**; the first experiment compares one actual write-and-cold-read loop against that control.

“We propose” is intentional: the extra concept's unresolved empirical risks and memo have not been accepted by the owner. No extra application has been implemented.

## User, painful workflow, and evidence boundary

The first user is an operations lead preparing a customer walkthrough with engineering, support, and account-planning agents. The proposed recurring problem is that a pilot observation becomes an unqualified capability statement as it passes between sessions. A subsequent agent sees several summaries and misses the original limitation.

Current substitutes include source-linked shared notes, direct document retrieval, enterprise search agents, and provenance-aware memory systems. The recurrence, severity, willingness to adopt, and effort saved for this particular user remain **unvalidated hypotheses**.

The general mechanisms are already researched or supplied by existing systems. [Graphiti](https://github.com/getzep/graphiti) provides temporal graph memory and supports FalkorDB; [Glean describes agents using company context](https://docs.glean.com/agents/how-agents-work). [Beyond Memory Majority](https://arxiv.org/abs/2608.19701) studies correlated agent memories. These sources prevent a claim that shared memory, provenance, or source-correlation reasoning is our invention. They do not establish whether our exact proposed workflow is better or worse than a configured competitor.

The defensible product hypothesis is narrow: preserving qualified learning and its correction across roles may reduce repeated investigation or inappropriate reuse. A graph diagram or repeated correct answer does not prove it.

## Winning argument and strongest objection

The argument for R11 has four steps:

1. The user's requested product is a reusable company-agent memory layer. Several cold roles must use and revise what another learned.
2. That requires more than storing chats: scope, source/version links, unresolved conditions, and scoped corrections must survive the handoff.
3. Graph tools can select the relevant source and correction paths. The LLM must still read the actual language and decide whether this situation satisfies the conditions, or ask.
4. A later cold role must change a concrete draft using newly persisted learning. This makes the graph and interpretation part of the working loop.

R06 also has legitimate cross-session learning. R11 is preferred for its fit to the requested reusable memory layer, not because R06 lacks agents or because CRM is prohibited. R06's recipient-acceptance workflow is more immediately concrete, but capable checklists and commercial handoff tools directly challenge it. [Gong](https://www.gong.io/customer-success-software) and [Gainsight](https://www.gainsight.com/blog/aligning-your-sales-to-cs-handoff-in-the-age-of-ai/) advertise relevant continuity workflows; their advertising is not an independently tested equivalence.

**The strongest objection remains open:** reading the full original passage and saving a qualified note may achieve all of the useful behavior with less instrumentation and review. R11's extra support structure could be bureaucracy. This is bounded as an explicit rejection experiment, not answered by claiming algorithmic novelty or declaring an unserved market.

R03 knowledge handover loses appeal because [Flamekeeper](https://www.useflamekeeper.com/), [Implix](https://implix.io/en), and [Culturro](https://culturro.com/hr-agents/offboarding-alumni/knowledge-capture-agent/) advertise much of its capture/interview/handover workflow. A thin dependency-path variant alone has not established a better product.

## Graph, critical traversal, and removal test

The detailed proposed schema and seven tool operations are in [HIVEMIND_GRAPH_CONTRACT.md](HIVEMIND_GRAPH_CONTRACT.md). It defines identity, source versions, temporal validity, scoped updates, incomplete lineage, permissions, and deletion limits.

Core nodes: CompanyEntity, Scope, SourcePassage, AgentRun, MemoryVersion, Claim, SupportProposal, Review, MemoryUse, Draft.

Core directed paths:

- AgentRun → WROTE → MemoryVersion → ASSERTS → Claim → HAS_PROPOSAL → SupportProposal → CITES_PASSAGE → SourcePassage.
- A proposal may CITES_MEMORY → an earlier MemoryVersion, enabling bounded transitive source investigation.
- Claim → IN_SCOPE → Scope; Review → REVIEWS → an exact proposal/version and APPLIES_IN → Scope.
- A correction explicitly SUPERSEDES a version within its reviewed scope.
- Draft → CITES_VERSION → MemoryVersion identifies declared consumers of an outdated assertion.

READ and MemoryUse receipts record exposure only. They never automatically become semantic support. Proposed citations, reviewed interpretations, and actual source text remain distinguishable.

**Critical question:** “Does the memory about overnight refresh apply to this customer's planned environment, and what evidence or correction supports that?”

**Without the relationships:** this implementation loses transitive memory-to-source investigation, exact scoped correction selection, and version-specific consumer discovery. Raw text remains readable and another relational implementation could reconstruct these operations. We do not claim FalkorDB is the only possible representation. Complete SQL plus the same LLM is an allowed control.

Seven realistic operations are specified in the contract: scoped recall; transitive support inspection; shared cited-origin investigation without vote counts; missing-condition investigation; hash/scope-bound correction; discovery of citing drafts; and current recall by a cold role. Each includes question, traversal, result shape, model use, and flat/vector limitations.

No memory queries have been executed. The proposed FalkorDB pin and each chosen query primitive must be verified before implementation claims. No APOC or unrestricted generated Cypher is assumed.

## Agent loop, interface, and approval boundary

1. Engineering-role agent records a qualified observation with exact source spans through a bounded memory gateway.
2. A genuinely fresh planning-role agent retrieves matching memory and follows its support path. It asks a targeted question when applicability is unresolved.
3. The operator supplies a scoped clarification and accepts its saved wording. A new immutable memory version retains that scope.
4. A later cold role retrieves the accepted clarification and revises a local walkthrough draft with citations.

The screen uses ordinary language: **What we learned / Where it applies / Why / What needs checking**. Internal support states belong in evidence details.

Deterministic code controls identity, tenant/source access, receipts, limits, version/hash bindings, query templates, idempotency, and local writes. The LLM interprets source language, proposes support and scope, asks, and drafts.

Review means acceptance of a scoped interpretation, not universal truth or business authorization. An agent can give a clearly attributed uncertain answer without an invented mandatory approver. Source content cannot grant tool permissions. No external messages, customer promises, deployment, or contract changes occur in the MVP.

## Thirty-second demonstration and minimum scope

**Authored synthetic scenario, proposed behavior:**

- Several department summaries say “overnight refresh is ready.”
- The agent follows their declared support to a pilot note: it was observed on a **reserved worker pool**; shared-pool behavior was not exercised.
- It asks which pool the Juniper walkthrough will use, rather than counting summaries as confirmations.
- A scripted operator clarification identifies Juniper evaluation's shared pool. The accepted memory says the supplied evidence does not establish refresh there.
- Restart the planner without the old chat. Its draft now requests a shared-pool rehearsal before promising overnight refresh. Another environment does not inherit Juniper's correction.

The useful surprise is that repeated agreement hid a consequential condition. The reusable learning is the scoped clarification, not a “false consensus” score. This scenario establishes no actual refresh behavior.

P0: one synthetic company, one capability, two environments/scopes, at most eight visible items per case, one gateway, bounded graph tools, two independent client sessions and a restarted consumer. Role clients can run serially using the same model. No autonomous swarm, broad connector suite, or general enterprise platform.

The existing four paper packets and separate oracle exercise distinct observations, omitted conditions, scoped corrections, and unknown support. Only Astra's completed blind interpretation was captured at the final stage; Sol authored the cases. Other blind attempts failed in transport. No accuracy rate or runtime retention follows. See [06-paper-review.md](archive/06-paper-review.md).

## Four-day implementation plan — only after approval

| Day | Deliverable and exit condition |
|---|---|
| 1 | Pin/check FalkorDB and client; independently author fixture/oracle; run one real write/cold-read comparison against source-linked notes. Stop if preparation dominates or support boundaries fail. |
| 2 | Implement bounded recall/support/correction tools and immutable scoped versions. Capture real gateway receipts; preserve cycles, unknowns and incomplete traversal. |
| 3 | Connect role clients and operator clarification. Restart the consumer; show its cited local draft changes without old chat. Keep interface to the four plain-language questions. |
| 4 | Run the agreed controls and negative cases, record effort and failures, rehearse the demo and document limitations. Drop optional origin/consumer visualization before weakening evidence controls. |

This is a scope estimate, not a build-feasibility score. The owner requested wow in that rubric slot; the four-day constraint remains.

## Evaluation, rejection experiment, and switching rule

Use identical passages, qualifications, corrections, model, access and comparable budgets for:

- isolated sessions and flat/vector shared memory;
- complete qualified source-linked notes plus the same LLM;
- origin/provenance tables or SQL plus the same LLM;
- this FalkorDB gateway;
- a configured capable memory product where accessible, with any untested comparator explicitly labeled.

No control is forced to omit source qualifications, corrections, approvals or origin IDs.

Record scope/action correctness, exact evidence-path validity, unknown preservation, inappropriate cross-scope reuse, cold-session correction recall, question usefulness, and operator preparation/review effort separately from model time. Include separate observations sharing background, missing support, scoped correction, and stale/cyclic lineage. Tiny synthetic results cannot establish production demand.

**Smallest overturning experiment:** one capability, two scopes, one actual learned correction, then a cold draft. Have an independent reviewer compare useful output and total preparation against the qualified-note control. Reject the product argument if equal useful work requires less preparation in that control; reject the design if it promotes READ to support, guesses applicability, leaks corrections across scope, or relies on hidden chat context. Correctness parity alone neither disqualifies the graph implementation nor demonstrates an advantage.

Switch to R06 only if independent raw sales/delivery passages and a recipient clarification produce useful durable scope reuse that a capable checklist cannot supply as cheaply. Missing acceptance must remain unknown, never refusal. Failure of R11 does not automatically approve R06. Reject both if their controls provide equal usefulness with less setup.

## Positions, dissent, and verdict

[HIVEMIND_POSITION_LEDGER.md](HIVEMIND_POSITION_LEDGER.md) records exact stages, changes, and availability. No averages, votes or silent peers select this concept.

Sol and Astra completed final conditional R11 recommendations. Opus/Sonnet's latest substantive repair recommendations also favor conditional R11. Gemini pivoted toward R11, but its unserved-market assertion and correctness-parity veto are unsupported and excluded. Step's latest attack supports the narrowed H11 direction, not a later repair it never returned. MiMo's last substantive position remains unresolved, leaning H06. **Muse retains R06 preference** because its recipient-facing behavior is clearer; its later connection error does not withdraw that dissent.

**Verdict: conditional recommendation for the extra concept; no-go for starting its implementation yet.** No fatal contradiction has been established in the narrowed design, but demand, support accuracy, review economics, and configured-substitute differentiation remain open. The owner has not accepted those risks for the extra. This memo completes the concept proposal without manufacturing final group convergence or reopening the approved main direction.
