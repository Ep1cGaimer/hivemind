# HiveMind: project memory that follows Git

HiveMind gives small teams shared memory for Codex and Claude Code across machines.
After connecting a repository once, a local bridge derives its branch incarnation,
HEAD, source hashes and working snapshot. Native lifecycle hooks recall relevant
context and ask the assistant's existing model to capture useful findings and
separate task checkpoints. A fresh teammate resumes without the original chat.
No separate summarization model, embeddings provider, or API key is required.

Project-wide conventions belong to one connected repository. Cross-project
personal memory is outside this version. HiveMind remains separate from
RollbackWitness.

## Intended workflow

1. Create a project, connect a checkout, and review native hook/MCP trust.
2. Give Codex or Claude Code an ordinary coding task.
3. Receive relevant inherited knowledge, branch findings and resumable checkpoints,
   including applicability, provenance, uncertainty and disagreements.
4. After meaningful work, save concise source-bound findings and task progress,
   or explicitly record that nothing useful changed, in one bounded extra pass.
5. Refresh context when Git changes. Earlier loaded memories are identified as
   belonging to the previous checkout.
6. Another teammate or assistant resumes from the shared service.

## Invariants

New learning on feature at commit A stays branch-local even if main also contains
A. A source commit describes observation; publication controls inheritance.
Authored successor commits and newly observed integrations can publish findings
only with matching sources. Old shared ancestry cannot retroactively publish new
learning. Unique deterministic replay/squash mappings also require matching
source content; incomplete or ambiguous mapping needs review.

Same-branch teammates can see unfinished work. Snapshot mismatches are WIP and do
not override checkout-verified facts. Changed sources become historical or need
revalidation. Exact immutable revisions retain explicit scoped supersession;
concurrent applicable revisions remain unresolved disagreements, not timestamp
winners. Concurrent tasks retain separate checkpoints. Another clone explicitly
joins a recorded branch ID; names alone never prove identity. Deleted/rewritten
refs preserve history. Retries are delivery events, not independent evidence.

Agents propose project conventions; a human owner accepts the exact revision.
Promotion retains source conditions. Private paths and credentials are excluded;
no transcript capture is required. Offline writes keep their original branch and
snapshot. HTTP and MCP share project authorization, viewer restrictions, durable
token issuance and revocation, without default-project fallbacks.

## Architecture and graph-dependent question

Retain the Python service, project workspace, MCP integration, and pinned
FalkorDB 6.0.2 backend. Add a local Git bridge per developer. The hard question is:
**which learning is carried into this checkout, does its source still match,
and which publication/evidence path explains it?**

FalkorDB executes fixed bounded ancestry, applicability, supersession and
explanation queries scoped to project/repository. The service does not collect the
entire persistent graph for Python filtering. Start with lexical/file relevance.
Automatic context is at most eight findings and two checkpoints in about 2,000
estimated tokens; deeper provenance is available through inspection. Shallow or
capped history and manifests are explicitly incomplete. Connector provenance is
not proof of semantic truth.

The UI presents conventions, branch findings, team WIP, checkpoints, changed
sources, conflicts and promotion proposals. Explain why each item appears, who
recorded it and what supports it. Graph terminology belongs behind inspection.

## Milestones

1. Git-aware immutable memory core, source/publication separation, fixed scoped
   FalkorDB queries and consistent authorization.
2. Both native adapters, onboarding, automatic hook protocol, checkpoints,
   offline recovery and branch-aware UI.
3. Independent real-Git proof, OpenTelemetry validation, relationship ablation,
   and a capable equal-information source-linked notes comparison.

See [actual results](testing/git_memory/RESULTS.md). Native Codex/Claude model-session
proof remains pending hook trust at the user's request. Browser visual QA was
unavailable. Adapter/transport tests are not fresh assistant acceptance. Baseline
correctness parity is allowed and reported honestly. There is no fixed duration
cap. OpenCode implementation delegation, if introduced, remains subject to the
supplied Zen-only constraint.

The older Juniper capability-planning brief is preserved in
[archive/legacy-capability-brief.md](archive/legacy-capability-brief.md); the
synthetic fixture remains a separate regression/example.
