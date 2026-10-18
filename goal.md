# HiveMind final-product acceptance goal

This file records the complete product acceptance checklist and its pass criteria.
Creating this file does not start implementation or execution of the checklist.

The goal is a reproducible, useful, polished shared-memory product: a new user can
connect a repository, a fresh assistant benefits from prior learning, Git scope
remains correct under changes and failures, and the graph's contribution is
inspectable. No test suite can guarantee a hackathon win.

## Agreed scope

- **All model-driven integration testing uses OpenCode with OpenCode Zen only.**
- Build and verify an OpenCode adapter for automatic recall and capture through
  HiveMind's local Git bridge and shared service.
- Use fresh, independent OpenCode sessions to test handoffs. Do not use Codex or
  Claude Code sessions as prerequisites for this acceptance run.
- Codex/Claude native hooks, their trust reviews, and cross-client lifecycle
  verification are outside this testing scope. Existing adapters may remain in
  the product, but must not be described as end-to-end verified by OpenCode tests.
- Use independent subagents for usability, adversarial, and unfamiliar-user
  simulations, as explicitly authorized by the user. Label these as simulated
  user testing; do not claim they establish real-human demand or adoption.
- Final submission, publishing, registration, public deployment, demo-video
  production, and other submission packaging are excluded. Retain local product
  documentation and reproducible acceptance scenarios.
- Preserve existing data, the older Juniper regression, and the uncommitted
  OpenTelemetry patch. Keep HiveMind separate from RollbackWitness.
- There is no arbitrary build-duration cap. Work against verified acceptance
  gates; do not weaken evidence or correctness to declare completion.
- Do not bypass native security protections. No missing credentials or manual
  approval for the OpenCode-only path has currently been established. Verify an
  actual failure before requesting user intervention; do not invent blockers.

## Evidence and status rules

Every test needs its setup, independently defined expected result, actual result,
command or procedure, relevant logs, and memory/context/revision IDs where useful.
Mark each test **passed**, **failed**, **untested**, or **outside agreed scope**.
A related passing unit test is not evidence that the entire acceptance item passed.

Distinguish deterministic tests, real model sessions, simulated usability tests,
and any future real-human study. A screenshot, a model's statement, and an
independent assertion establish different things. Retain failed runs and disclose
skips, incomplete coverage, recovery, and manual intervention.

The tables below define requirements, not passing status. Audit existing evidence
before assigning a status. Store the actual execution results separately and link
them to these stable test IDs.

## A. Product delivery and technical ownership

The original submission checklist is adapted here to the final-product-only scope.
Public repository publication, submission tracks/forms/deadlines, deployment, and
demo-video deliverables are not completion gates.

| ID | Test | Pass condition |
| --- | --- | --- |
| A1 | Accessible product source | A reviewer or independent tester can inspect the complete local source without relying on the author's conversation. Public publication is outside scope. |
| A2 | Reproducible setup | README contains complete installation, configuration, startup, and verification instructions. |
| A3 | Graph documentation | The data model and the actual Cypher queries or algorithms used by the product are included and explained. |
| A4 | Working local scenario | A reviewer can execute the complete useful workflow from documented commands. No video or public deployment is required. |
| A5 | Accurate product positioning | The documented problem and supported workflows match what the product demonstrates. Team/company knowledge claims have corresponding evidence. |
| A6 | Work and dependency disclosure | Documentation accurately distinguishes original implementation, reused components, permitted fixture/source data, AI assistance, and unverified claims. |
| A7 | Technical explainability | Architecture, query behavior, tradeoffs, failure cases, and implementation decisions can be explained from the submitted code and documentation. Produce an inspectable technical walkthrough; do not claim to verify a human owner's understanding through an agent test. |

## B. First-time onboarding

Use independent testers without implementation context. Any undocumented repair or
verbal coaching needed to complete setup is an onboarding defect.

| ID | Test | Pass condition |
| --- | --- | --- |
| B1 | Clean-environment installation | A tester follows the README on a fresh supported environment without undocumented fixes. |
| B2 | First useful result | After prerequisites are installed, a new tester connects a repository and receives useful context within ten minutes. |
| B3 | Correct repository detection | Launching from the repository root or a nested directory selects the intended repository consistently. |
| B4 | Multiple repositories | Switching projects never loads another repository's memory or credentials. |
| B5 | Linked worktrees | Each worktree receives its correct branch context and its own working snapshot. |
| B6 | Teammate onboarding | A second clone or machine joins the intended branch through an understandable supported flow. Database editing is unnecessary. |
| B7 | Safe adapter installation | Existing client configuration survives. Reinstalling creates no duplicate hooks, plugins, or MCP entries. |
| B8 | Actionable setup failures | Missing Git, invalid tokens, unavailable database, unsupported OpenCode versions, and actual trust/permission failures produce specific recovery instructions. |

## C. Automatic memory in actual OpenCode sessions

These gates require real OpenCode model runs using Zen. Mock hooks, direct HTTP
calls, deterministic replay, or a subagent impersonating OpenCode cannot close
these integration gates.

| ID | Test | Pass condition |
| --- | --- | --- |
| C1 | Automatic recall | An ordinary task prompt receives relevant memory before the assistant makes its important decision. |
| C2 | Automatic capture | Useful learning is saved without the user requesting a memory write. |
| C3 | Meaningful learning | The saved finding contains a discovered constraint, failed approach, decision, or validation result that helps later work. |
| C4 | Source binding | Code claims retain exact source identities and the checkout where they were observed. |
| C5 | Honest validation claims | A claim that tests passed links to recorded execution evidence, or is clearly labeled as an agent-reported claim. |
| C6 | Separate checkpoint | Unfinished work produces resumable progress, open questions, and concrete next steps separately from durable findings. |
| C7 | No-change behavior | An uneventful turn records no useful change instead of generating filler memories. |
| C8 | Fresh consumer | A new OpenCode process/session retrieves the finding without access to the writer's conversation. |
| C9 | Independent-session handoff | Distinct OpenCode sessions can alternate writer/consumer roles and correctly use each other's scoped findings. The original Codex-to-Claude and reverse native-client proof is outside this run's scope. |
| C10 | OpenCode adapter lifecycle | Verify the installed OpenCode version's actual plugin/MCP schemas and lifecycle behavior, including recall, capture, context changes, and error handling. Use Zen only. |
| C11 | Bounded continuation | Capture causes at most one extra pass and cannot create an agent loop. |
| C12 | Visible capture failure | Failed saves are surfaced and recoverable; the interface never falsely reports successful persistence. |

Initial engineering gate: at least **19 successful automatic capture-and-recall
cycles out of 20 ordinary task runs**. Retain and investigate every failure.
This is an acceptance target, not a reliability certification. A successful
OpenCode run does not validate the native Codex or Claude adapters.

## D. Git correctness

Acceptance requires zero known failures in these deterministic cases.

| ID | Test | Pass condition |
| --- | --- | --- |
| D1 | Same commit, different branches | Learning created on feature stays off main even when both point to commit A. |
| D2 | Existing shared ancestry | Discovering an old common source commit does not publish newly created branch learning. |
| D3 | Same-branch teammates | Teammates on the same recorded branch can see unfinished findings. |
| D4 | Different working snapshots | A teammate's differing snapshot is clearly labeled WIP/requires verification. |
| D5 | Authored successor commit | A subsequent qualifying commit binds matching pending findings correctly. |
| D6 | Fast-forward integration | Appropriate source-branch findings become inherited after verified integration. |
| D7 | Normal merge | Actual integration history and resulting source content determine transfer. |
| D8 | Later learning on an integrated tip | Learning saved after an integration is not retroactively published into the destination. |
| D9 | Rebase | Unique supported mappings retain findings and original provenance. |
| D10 | Cherry-pick | Supported findings transfer through verified mapping without importing unrelated branch knowledge. |
| D11 | Squash merge | Aggregate mapping and matching sources preserve appropriate findings. |
| D12 | Ambiguous mapping | Multiple possible matches remain unresolved and require review. |
| D13 | Changed or deleted sources | Applicability changes without deleting historical findings. |
| D14 | Partial source mismatch | One changed required source prevents a claim from appearing fully verified. |
| D15 | Scoped correction | A correction on one branch cannot overwrite a valid version on another branch. |
| D16 | Concurrent corrections | Applicable conflicting revisions remain visible; timestamps do not select truth. |
| D17 | Branch deletion and recreation | Reusing a branch name does not silently reuse the deleted branch's identity. |
| D18 | Shallow or bounded history | Missing history is explicitly incomplete; absence is not presented as proof. |
| D19 | Checkout changes during observation | The bridge retries or rejects a torn observation rather than combining two checkouts. |
| D20 | LF/CRLF and supported filters | Equivalent clean source content agrees across supported environments. |

## E. FalkorDB and graph-dependent behavior

| ID | Test | Pass condition |
| --- | --- | --- |
| E1 | Actual live path | Acceptance workflow writes, retrieval, and investigation execute against FalkorDB. |
| E2 | Ancestry traversal | The database determines whether a publication is reachable from the caller's HEAD. |
| E3 | Applicability selection | Source bindings and applicable revisions affect what the assistant receives. |
| E4 | Inspectable explanation | Displayed paths correspond to stored nodes and relationships, not generated explanatory prose. |
| E5 | Relationship ablation | Removing relevant relationships while retaining facts and metadata removes inheritance or its explanation. |
| E6 | Decision consequence | The resulting context difference changes a real OpenCode recommendation, edit, or validation plan appropriately. |
| E7 | No hidden fallback | Database failure does not silently switch the advertised live workflow to canned answers or memory mode. |
| E8 | Bounded queries | Large histories cannot trigger an unbounded graph download or traversal presented as complete recall. |

Combine E5 and E6 to show that relationships affect which guidance applies and
that this difference changes real work. A capable notes implementation may
reproduce the behavior with its own provenance index; that is a legitimate
comparison, not grounds to weaken the control.

## F. Authorization, privacy, and trust boundaries

| ID | Test | Pass condition |
| --- | --- | --- |
| F1 | Project isolation | A project token cannot read, inspect, infer, or modify another project's records. |
| F2 | Viewer restrictions | Viewer access cannot write findings, revise memories, promote knowledge, or mint stronger access. |
| F3 | Revocation | Revoked tokens stop working in existing sessions and remain revoked after restart. |
| F4 | Human promotion | An assistant cannot accept its own project-wide convention proposal. Exercise the product's human-session boundary through a test fixture without labeling an agent as a real human reviewer. |
| F5 | Model-supplied context | Model-provided branch names, hashes, or snapshot IDs cannot become authoritative Git context. |
| F6 | Private capture | Configured private paths and credential fixtures are excluded from captures, logs, and retry payloads. |
| F7 | Prompt injection | Instructions embedded in source files or memories do not grant permissions or control tools. |
| F8 | UI injection | HTML/script content in memories renders safely as content. |
| F9 | Legacy-route bypass | Older HTTP/MCP aliases enforce the same project authorization. |
| F10 | Native trust | OpenCode installation and testing respect actual permission/security mechanisms. Codex hook approval is not a prerequisite for OpenCode testing. |

For privacy tests, inspect the graph/database, local cache, outbox, logs, and
exported test artifacts. Checking only visible memory text is insufficient.

## G. Recovery, persistence, and concurrency

| ID | Test | Pass condition |
| --- | --- | --- |
| G1 | Offline capture | An outage queues a capture without claiming it reached the shared service. |
| G2 | Branch switch before retry | Queued work retains its original branch and snapshot. |
| G3 | Duplicate delivery | Repeated lifecycle events and retries produce one logical revision. |
| G4 | Concurrent agents | Simultaneous writers do not lose findings or overwrite another task's checkpoint. |
| G5 | Interrupted save | A crash midway through persistence can be retried without corrupting the memory graph. |
| G6 | Client restart | A fresh client process recovers saved context and pending local work. |
| G7 | Service/database restart | Acknowledged durable memories and revocations survive the advertised restart scenario. |
| G8 | Timeout handling | Slow or unavailable services produce bounded, actionable failures without hanging the coding session. |
| G9 | No useful memory | Empty recall returns honestly and lets ordinary work continue. |
| G10 | Memory overload | Many findings still produce bounded relevant context with explicit truncation. |

Proposed performance gates, measured on a declared setup and workload:

| Operation | Target |
| --- | --- |
| Normal warm recall | p95 below one second. |
| Recurring bridge/plugin overhead, excluding model generation | p95 below two seconds. |
| Automatic context | At most eight findings and two checkpoints, approximately 2,000 tokens including metadata. |
| Initial synchronization | Visible progress and a documented bound. |
| Slow or failing dependency | Clear timeout; no indefinite wait. |

Measure the entire developer-visible operation, including Git work and network
calls. Report cold and warm behavior separately. The fastest Cypher query is not
an end-to-end latency measurement.

## H. Demonstrated usefulness and fair comparison

Task fixtures must include:

- A failed approach the writer has already investigated.
- A build prerequisite discovered during actual work.
- A branch-specific implementation constraint.
- A partially completed task with an actionable checkpoint.
- Guidance that becomes stale after a source change.
- Two conflicting interpretations.
- An integration that changes which guidance applies.
- A task requiring no historical memory, to reveal unnecessary overhead.

| ID | Test | Pass condition |
| --- | --- | --- |
| H1 | Independent task outcomes | Correctness criteria are defined before evaluation and are not supplied to the tested assistant as answers. |
| H2 | Strong alternatives | Compare source access alone, capable source-linked notes/handoffs, and HiveMind. |
| H3 | Fair conditions | Use the same Zen model, task, source access, comparable budgets, and all relevant facts/metadata available to the notes control. |
| H4 | Genuine cold starts | Session/workspace isolation and randomized task order prevent prior-conversation contamination. |
| H5 | Behavioral benefit | Memory avoids a demonstrated mistake, repeated investigation, or incomplete handoff. |
| H6 | End-to-end quality | Final code, draft, or recommendation passes independent checks; successful retrieval alone is insufficient. |
| H7 | Complete cost accounting | Include capture, review, preparation, maintenance, model tokens, tool time, and intervention. Label simulated review effort separately from measured human effort. |
| H8 | Negative-case restraint | Irrelevant or stale memory does not worsen tasks that need no historical guidance. |
| H9 | Repeatability | Report repeated runs and all failures rather than selecting one successful conversation. |
| H10 | Independent simulated users | Several subagents unfamiliar with the implementation complete a handoff and explain its concrete value and friction. This replaces recruiting genuine users for the agreed scope; it is not evidence of real-human demand, adoption, or willingness to pay. |

Initial evaluation design: eight to ten distinct tasks, three runs per condition,
with randomized ordering and isolated sessions. Repeated runs of one task are not
dozens of independent use cases. Test product behavior with actual OpenCode/Zen;
independent evaluation or usability subagents do not replace those runs.

Usefulness decision rule: demonstrate a meaningful improvement in at least one
important outcome (correctness, investigation time, handoff effort, or context
consumption), without a material regression elsewhere.

A 20% reduction in median investigation time or tool/model usage is a proposed
practical target when output quality is maintained. Report distributions and
task-level results. Small samples do not support broad performance claims.

If capable notes are equally correct, easier to prepare, and equally convenient,
competitive advantage is unestablished. Improve the product or narrow its claim.
Never force the baseline to fail by removing qualifications, metadata, source
access, or tools that a competent notes workflow could use.

## I. Interface and simulated first-time usability

Use independent subagents with only the documentation, task, and product access
appropriate for a first-time user. Withhold implementation history, private answer
fixtures, writer transcripts, and author coaching. Record their actions and errors.
Use real browser interaction when evaluating the UI; code inspection cannot
substitute for interactive or visual checks.

| ID | Test | Pass condition |
| --- | --- | --- |
| I1 | Five-second orientation | A new tester identifies the project, branch, and checkout being shown. |
| I2 | Clear memory categories | Conventions, branch findings, WIP, and checkpoints are understandable without graph terminology. |
| I3 | Applicability comprehension | A tester correctly distinguishes verified, WIP, historical, and conflicted guidance. |
| I4 | Useful inspection | One inspect action reveals author, source, revision, and why the memory appears. |
| I5 | Understandable promotion | A tester understands exactly what becomes project-wide and which conditions remain attached. |
| I6 | Context changes | Switching branches refreshes context without presenting earlier guidance as current. |
| I7 | Complete interface states | Loading, empty, offline, unauthorized, failed-save, and reconnecting states are deliberately designed and tested. |
| I8 | Capture visibility | A tester can distinguish successful capture, queued capture, failure, and no useful change. |
| I9 | Visual quality | No clipping, unreadable contrast, overflowing IDs, broken spacing, or confusing button hierarchy. |
| I10 | Keyboard and screen sizes | Primary flows work through keyboard navigation and the declared supported laptop/mobile layouts. |
| I11 | Uncoached usability | An independent subagent completes connection, recall inspection, and a handoff without author coaching. Label the result as simulated usability. |

Proposed simulated-usability gate: four of five unfamiliar subagent testers
complete the main flow without help; all five correctly explain applicable versus
WIP guidance. Record the tested environment and tester limitations. Screenshots
alone cannot pass I3, I5, or I11. Do not relabel agent behavior as real-user research.

## J. Reproducible product walkthrough and adversarial review

These are product-quality gates. They do not require a video, submission package,
public deployment, or presentation assets.

| ID | Test | Pass condition |
| --- | --- | --- |
| J1 | Immediate problem clarity | Within twenty seconds, an unfamiliar tester understands whose problem HiveMind solves. |
| J2 | Ordinary writer task | OpenCode learns something useful during normal work and capture is visibly automatic. |
| J3 | Fresh consumer | A new OpenCode session starts without the old conversation and completes a concrete task using the learning. |
| J4 | Branch-sensitive behavior | The same guidance is excluded or qualified on the wrong branch. |
| J5 | Integration changes applicability | Verified integration changes what a consumer can correctly inherit. |
| J6 | Inspectable explanation | A reviewer can inspect the actual source/publication path supporting the changed applicability. |
| J7 | Unscripted variation | An independent adversarial subagent changes a branch, source file, or question and the product still behaves correctly. |
| J8 | Reliable repetition | Three consecutive full runs complete without configuration repair or database editing between steps. |
| J9 | Honest comparison | The result states what improved, what tied, what failed, and what remains unestablished. |
| J10 | Reproducible handoff | Another independent tester runs the scenario from the documented instructions and recorded commit. |

The complete local acceptance scenario is:

1. OpenCode discovers a real constraint while performing an ordinary task.
2. HiveMind captures it automatically.
3. A different, fresh OpenCode session avoids wasted work using the finding.
4. Another branch correctly does not inherit the finding.
5. Verified integration makes the finding applicable.
6. Inspection exposes the exact graph path and sources.
7. An independent reviewer changes a condition and the result updates correctly.

No prerecorded replay may be presented as a live model run. A walkthrough that
works only for the author's exact prompt is insufficient.

## Release decisions

| Claim | Evidence required |
| --- | --- |
| The Git memory core works | Deterministic Git, authorization, concurrency, persistence, and recovery gates pass. |
| OpenCode integration works | Actual ordinary-prompt capture and fresh-session recall pass on the verified OpenCode version using Zen. |
| The product is useful on evaluated tasks | Independent task outcomes demonstrate a practical benefit against capable alternatives; limitations and costs are disclosed. |
| The product is polished under simulated testing | Uncoached onboarding, UI comprehension, failure recovery, and repeated complete walkthroughs pass. |
| Other native client integrations are verified | Only their own actual lifecycle/session tests can establish this. They are outside the current OpenCode-only testing scope. |
| Real-human demand/adoption is validated | Requires actual human evidence; simulated users cannot establish this claim, and it is outside the current scope. |
| The project will win | Not a verifiable product claim and never guaranteed. |

Zero known failures are allowed in deterministic scope, authorization, immutable
history, and data-preservation gates. Model-run success must satisfy the declared
repetition targets, with no concealed failures or correctness regressions.
Unavailable browser/model execution is recorded as untested, not replaced by
source inspection or a more convenient mock.

## Historical baseline evidence when this goal was recorded

The bullets below describe the pre-implementation baseline. They are intentionally
not current status; current execution evidence and item statuses live in
[testing/git_memory/ACCEPTANCE.md](testing/git_memory/ACCEPTANCE.md).

The existing [verification report](testing/git_memory/RESULTS.md) records:

- 64 tests discovered: 42 offline tests passed and 22 live-only tests skipped.
- 22 live FalkorDB tests passed separately.
- Substantial deterministic Git, concurrency, authorization, persistence, and
  relationship-ablation coverage.
- A deterministic OpenTelemetry bridge capture/recall and service restart, with
  the existing uncommitted patch unchanged.
- A three-case deterministic comparison in which capable source-linked notes
  tied HiveMind on correctness. This does not establish a usefulness advantage.
- No actual native automatic model-session acceptance run for the new workflow.
- No implemented OpenCode adapter or completed OpenCode model-session proof.
- No completed interactive browser/visual usability verification in that run.

These are historical results, not blanket passes for the expanded checklist.
Recheck evidence against the final implementation. The earlier deferred
Codex/Claude hook review is not a blocker for this OpenCode-only acceptance plan.

## Execution priority

1. Implement and verify the OpenCode adapter against its installed version.
2. Prove automatic capture and a useful fresh-session handoff through OpenCode/Zen.
3. Complete deterministic Git, security, recovery, concurrency, and graph audits.
4. Run the fair task comparison and disclose all costs and failures.
5. Use independent subagents for uncoached usability and adversarial simulations.
6. Fix interface and workflow defects, then repeat the full acceptance scenario.
7. Update the evidence ledger and final product documentation with precise claims.

More unit tests alone cannot close real-model, usefulness, or interactive-usability
gaps. Do not substitute submission polish for product correctness.

## Official context previously verified

The event brief emphasizes persistent shared memory, graph-shaped decisions, and
traceable sources. The rules require FalkorDB to perform central product work.
No numerical judging rubric was found in the checked official pages; thresholds
in this goal are engineering proposals, not official judging weights.

- [Event brief and track descriptions](https://www.wemakedevs.org/hackathons/falkordb)
- [Official event rules](https://www.wemakedevs.org/hackathons/falkordb/rules)

These sources provide context only. Final submission and demo-video requirements
remain outside the user's agreed final-product scope.
