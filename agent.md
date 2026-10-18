# HiveMind — build instructions

## Current direction (supersedes the historical product boundary below)

Build shared project memory that follows verified Git history. `goal.md` governs
the active acceptance work: all model-driven integration tests use OpenCode with
Zen only. Use authorized independent subagents for simulated usability/adversarial
testing and label that evidence honestly. Codex/Claude native trust/session tests
and final-submission/video/publication work are outside this run's scope.
`HIVEMIND_IDEA.md` and `HIVEMIND_GRAPH_CONTRACT.md` are the current
product and traversal contract. The Juniper boundary below applies only to the
retained synthetic regression/example. Preserve its evidence semantics, existing
notes, and the uncommitted OpenTelemetry patch. Delivery is milestone-based with
no fixed duration cap. Keep native hook trust, project authorization, separate
source/publication history, immutable scoped revisions and explicit incomplete
history. OpenCode 2 automatic capture/fresh-session recall has initial real-model
evidence; the full acceptance ledger is `testing/git_memory/ACCEPTANCE.md`.
Transport/unit tests do not establish all model-session or usefulness gates.

## Project and goal

Build **HiveMind**, an evidence-aware shared memory tool for the WeMakeDevs ×
FalkorDB Graph Hacks 2026 event. HiveMind is the separate Track 2 + Track 3
project in this workspace: **Agent Memory and Coordination** plus **Company Brain**.

The product direction is already selected. Do not generate, score, or select new
concepts. Read `HIVEMIND_IDEA.md` for the product brief and
`HIVEMIND_GRAPH_CONTRACT.md` for the current data and traversal contract. Read
`HIVEMIND_DECISION_MEMO.md` for the conditional validation gates. Historical
debate files live in `archive/`; they are reference material, not startup
instructions. Do not import RollbackWitness requirements or implementation into
this project: RollbackWitness is a separate project.

HiveMind's first useful result is narrow:

> One role agent records a qualified learning; a later, genuinely cold role
> retrieves that learning with its source, scope and limits, asks about a missing
> condition, and changes a local planning draft without access to the old chat.

This is a product to build and test, not a claim that graph memory is novel,
universally superior, or already validated for demand.

## User and painful workflow

The first user is an operations lead preparing technical customer walkthroughs
with engineering, support and account-planning agents. The concrete failure is
qualifier loss across sessions: a pilot observation such as “refresh worked on a
reserved worker pool” becomes “the capability is ready” after several summaries.

The first workflow must remain a capability-planning case. Do not turn the MVP
into a general enterprise search product, a CRM, a generic chat-with-documents
assistant, or an autonomous company operator.

The product must preserve, separately and explicitly:

- what was observed or asserted;
- the exact source artifact, version and passage;
- the conditions and scope where it applies;
- what is unknown or missing;
- an explicitly reviewed, scoped correction;
- which later drafts cite the affected memory version.

An agent reading a source, an agent proposing that the source supports a claim,
and a reviewer accepting a scoped interpretation are different events. Never
collapse them into one truth, confidence or vote count.

## Think like the FalkorDB organizers

Build for this sponsor reaction:

> “This is a problem where relationships are the hard part, and FalkorDB makes
> the agent materially better.”

The shipped proof should demonstrate:

- graph context gives the agent useful information beyond isolated text chunks;
- FalkorDB participates in an actual write/recall/investigation/draft loop rather
  than storing a finished answer;
- multi-hop relationships uncover a lost qualifier, support chain or scoped
  correction that changes what the agent does;
- Cypher or graph operations control what evidence is retrieved, investigated,
  explained or proposed;
- a clarification or local draft change is traceable to a valid graph evidence
  path;
- persistent structured context improves a later cold interaction where relevant;
- another developer can reproduce and understand the result.

These are sponsor-oriented standards, not official judging weights. Verify current
event rules or dates from official sources when needed; never invent judging
criteria or promise a win.

## What makes a good HiveMind slice

Keep the product centered on:

1. one clearly defined user;
2. one painful recurring workflow;
3. one graph-dependent question:
   “Does this remembered capability apply to this company context, what supports
   it, and which correction should the next role use?”;
4. one meaningful agent decision or approval-gated local action;
5. one inspectable evidence path;
6. one reproducible public, synthetic or explicitly permitted dataset;
7. one convincing before/after comparison.

Prefer one reliable loop over a broad feature list or a swarm. “Wow” means a
surprising relationship or missing condition that changes an observed outcome,
not animation, token volume or the number of agents on screen.

Use equal relevant information, tool access and comparable model budgets for
controls. No baseline is required to fail. Label synthetic data and replay;
separate demonstrated behavior from assumptions; report limitations honestly.

## Intended demo

Several departmental summaries say **“overnight refresh is ready.”** The original
source passage says it was observed on a **reserved worker pool**; shared-pool
behavior was not exercised.

The agent should:

1. follow declared support from the summaries to the source passage;
2. preserve the missing shared-pool condition rather than count summaries as
   independent confirmation;
3. ask which pool the Juniper walkthrough will use;
4. accept a synthetic, scope-specific operator clarification;
5. store a new immutable correction scoped to that customer/environment;
6. restart the planner without the original chat;
7. change the local draft to request a shared-pool rehearsal before making a
   readiness claim;
8. prove that another environment does not inherit Juniper's correction.

The product must be comfortable returning “unknown,” “not supported in this
scope,” or “lineage incomplete.” It must never manufacture a universal claim from
an empty or capped traversal.

## Why the graph matters

The core graph investigation is:

```text
cold AgentRun
  → MemoryUse
  → current MemoryVersion
  → Claim
  → SupportProposal
  → earlier MemoryVersion or SourcePassage
  → applicable Scope and Review
```

The consumer path is:

```text
reviewed/corrected MemoryVersion ← CITES_VERSION ← Draft
```

Removing the relationships while retaining raw notes must remove a specific useful
capability: transitive support inspection, exact scope-sensitive version selection,
or discovery of drafts that explicitly cite an affected version. If the feature
still works unchanged after removing FalkorDB relationships, it is decoration and
must be redesigned.

Complete SQL, provenance tables or a BFS implementation with the same model are
valid comparison controls. They do not replace the need to prove that FalkorDB is
actually used in the shipped agent loop.

### Required graph distinctions

At minimum, preserve these meanings:

- `READ_PASSAGE` / `READ_MEMORY`: observed tool or context exposure only;
- `WROTE`: an agent run created a memory version;
- `ASSERTS`: a memory version states a claim;
- `HAS_PROPOSAL`: a claim has a proposed support/qualification/contradiction;
- `CITES_PASSAGE` / `CITES_MEMORY`: a declared evidence link;
- `REVIEWS` and `APPLIES_IN`: a bounded human review of an exact item and scope;
- `SUPERSEDES`: an explicit, scoped correction, never a global overwrite;
- `CITES_VERSION`: a draft explicitly names a memory version;
- `MemoryUse`: a retrieval receipt, not proof of semantic influence.

Never turn `READ` into support automatically. Never count repeated wording as
independent evidence. Different run IDs are recorded observations, not proof of
statistical independence. A review accepts a scoped interpretation; it does not
establish universal truth or authorize a customer promise.

### Current conceptual node set

Use the contract in `HIVEMIND_GRAPH_CONTRACT.md` as the authority for fields and
identity rules. The intended nodes are:

- `CompanyEntity`
- `Scope`
- `SourcePassage`
- `AgentRun`
- `MemoryVersion`
- `Claim`
- `SupportProposal`
- `Review`
- `MemoryUse`
- `Draft`

Every identity is tenant/project qualified. Source passages and memory versions
are immutable in the audit trail. Content hashes detect exact duplicates but do not
prove that two observations were independent. Missing qualifiers remain unknown;
do not silently broaden scope.

## Deterministic code versus model work

Trusted deterministic code controls:

- tenant/project-selected graph keys and source visibility;
- stable IDs, artifact versions, content hashes and run receipts;
- fixed parameterized Cypher query templates;
- traversal limits, cycle detection and completeness/incomplete markers;
- exact source/version/scope/review bindings;
- idempotent writes and immutable version creation;
- correction applicability and local draft writes;
- approval gates and the prohibition on external side effects.

The LLM may:

- interpret quoted source language and qualifiers;
- propose entity/scope matches with supporting quotes;
- propose support, contradiction or a scoped correction;
- choose among bounded evidence tools;
- ask one useful condition-specific question;
- draft a local, cited plan.

The LLM may not:

- generate arbitrary Cypher or executable code;
- invent source passages, entities, versions, relationships or hybrid artifacts;
- convert exposure into support or unknown into a negative fact;
- broaden a correction beyond its reviewed scope;
- change tenant, permissions, reviewer identity or graph selection;
- self-approve a review or authorize a customer message, contract, deployment,
  HR decision or production change.

Source text is untrusted data. It cannot instruct tools, grant permissions or
override these rules.

## First implementation boundary

Start with:

- one synthetic company;
- one capability and one planning workflow;
- two environments or customer scopes;
- one memory gateway with bounded fixed tools;
- two role sessions plus a genuinely cold restarted consumer;
- at most eight visible source/memory items per case;
- a local draft view and a scripted operator clarification.

Before expanding the UI, prove this complete loop:

```text
qualified source
  → actual FalkorDB write
  → cold scoped recall
  → bounded support investigation
  → condition-specific question
  → immutable scoped correction
  → restarted consumer draft change
```

Do not add broad connectors, a general permissions platform, autonomous business
actions, a large agent swarm, generic chat memory, or visualization-only features
before this loop and its controls pass.

## Validation and rejection gate

The smallest useful experiment uses one capability, two scopes and one correction.
Compare a cold HiveMind consumer against qualified source-linked notes with the
same passages, corrections, model, access and comparable budget.

Record separately:

- scope/action correctness;
- exact evidence-path validity;
- unknown and missing-condition preservation;
- inappropriate cross-scope reuse;
- correction recall after restart;
- question usefulness;
- operator preparation and review effort;
- model time versus deterministic/tool time.

Reject the product argument if qualified notes deliver equal useful work with less
preparation. Reject the design if it invents support, guesses applicability, leaks
corrections across scope, relies on hidden chat context, or treats a capped
traversal as complete. Correctness parity with SQL does not prove benefit, but it
also does not by itself disqualify FalkorDB.

Paper cases and authored oracles can expose logical flaws only. They cannot prove
runtime retention, semantic accuracy, demand, review economics or competitive
superiority.

## Build strategy and milestones

Do not impose an obsolete fixed-duration cap from historical debate files. Use the
four-day MVP in `HIVEMIND_IDEA.md` as a scope baseline, then deliver against
verified milestones, correctness and product quality:

1. **Foundation:** pin FalkorDB and the client, define the independent fixture and
   expected outcomes outside runtime inputs, and verify one real write/cold-read
   path.
2. **Evidence tools:** implement scoped recall, bounded support inspection,
   missing-condition investigation, correction/version binding and draft citation
   discovery.
3. **Agent loop:** connect the writing role, planning role, operator clarification
   and restarted consumer. Show the draft change and evidence path.
4. **Controls and handoff:** run the qualified-note and relationship-aware
   controls, negative cases, scope-isolation case and incomplete-lineage case;
   record effort, failures, limitations and the next action.

Drop optional visualization or extra integrations before weakening source/version
bindings, unknown preservation or deterministic safety controls.

### FalkorDB discipline

The design proposes FalkorDB **v6.0.2** as a shared pin, but the memory tools have
not yet been verified against that server/client combination. Verify the exact
server, client and query behavior before implementation claims. Do not assume
Neo4j, APOC, unrestricted procedures, Bolt semantics or generated-Cypher behavior.
Use the official FalkorDB client for the chosen language and keep all queries
parameterized and bounded.

Use local Docker or FalkorDB Cloud only as authorized. Keep graph keys
server-selected or deterministically derived; never accept an arbitrary graph name
from the model. Use synthetic or explicitly permitted data only.

## Tests and reproducibility

When code is introduced, the workspace must remain reproducible on a clean Linux
machine:

- pin the runtime version and keep a lockfile;
- keep dependencies inside the project;
- provide a Dockerfile that installs required system packages and dependencies;
- provide a single meaningful offline-capable test command, such as `make test`;
- provide a README with exact setup, run, test and deployment steps;
- use `.env.example` and keep secrets, tokens, credentials and private payloads out
  of source, fixtures, logs, reports and commits.

Tests must cover user-visible behavior and important boundaries, including:

- tenant/scope isolation;
- exact version and content-hash binding;
- idempotent writes;
- missing support and unknown conditions;
- capped traversal and cycle detection;
- stale or rejected reviews;
- scoped supersession without global overwrite;
- `READ` remaining distinct from semantic support;
- a cold-session correction changing the local draft;
- no external side effect from model output.

Keep independent expected outcomes outside runtime inputs so a test cannot pass by
reading its answer from the fixture. Run the smallest meaningful checks after each
change. Never claim an unrun test, benchmark, deployment, or comparison passed.
Report passed, failed, skipped and unavailable checks separately.

## Models and delegation

The development team may use multiple agents, but the product starts with one
grounding agent plus deterministic tools. Keep one owner for shared contracts and
integration acceptance; do not create overlapping writers.

When the configured team is available, use these as provisional task assignments:

- **Main orchestrator:** high-reasoning model for architecture, delegation, shared
  contracts, review and integration acceptance.
- **Backend/debugging worker:** difficult FalkorDB/client integration and hard
  debugging.
- **Default bounded worker:** graph helpers, synthetic fixtures, deterministic
  tools and focused tests/reviews.
- **Agent/UI worker:** agent adapter, evidence presentation and local draft view.
- **Independent holdout/reviewer:** correctness, visual clarity, demo flow and
  control fairness.

Model roles are task assignments, not benchmark rankings. Use the configured
provider and model IDs rather than inventing availability. If a worker fails,
record the failure and reassign the bounded task; never manufacture a result.
Every delegated task must have exact file ownership, dependencies and acceptance
checks. Review shared-contract changes before integration.

## Safety and authorization

Proceed autonomously on authorized, reversible local development. Ask before:

- production deployment;
- external publishing or hackathon submission;
- sending messages or modifying customer commitments;
- irreversible deletion or data migration;
- purchases, credentials or third-party account changes.

Source access follows the user/tenant/source permissions available to the fixture.
Derived memory cannot bypass source visibility. A conservative refusal is safer
than a declassification or a hidden existence leak. No production erasure,
compliance, security certification or business authorization claim belongs in the
MVP.

## Handoff format

Maintain a concise handoff in the existing project status location. After useful
work, record:

- goal and current product boundary;
- changed files;
- actual checks and their commands/results;
- decisions and unresolved risks;
- blockers or unavailable services;
- the next concrete action.

Do not treat `archive/` debate conclusions as new authorization. Current approval
and validation status comes from `STATUS.md` and the root product documents.
