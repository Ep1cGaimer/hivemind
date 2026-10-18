# Active final-product goal: OpenCode and Zen

The active objective is everything in [goal.md](goal.md), with execution evidence
in [the acceptance ledger](testing/git_memory/ACCEPTANCE.md). This goal is not
complete. Native Codex/Claude proof and final submission/video work are outside
scope; they are not blockers for the current run.

Implemented an OpenCode 2 native plugin using the installed version's actual
promise plugin/session/tool API. A project-local official `@opencode/cli` 2.0.32
binary is now pinned in `package.json`/`package-lock.json`; its isolated catalog
exposes Zen `opencode/deepseek-v4.1-flash-free` without an extra credential. Real
OpenCode 2.0.32 sessions on Zen automatically saved Git-bound findings to FalkorDB
and fresh sessions cited those revisions.
The fresh frozen 20-cycle engineering workload completed **19/20**, meeting the
declared initial gate. Cycle 13 is retained as a real no-change writer failure;
the consumer still exited and captured successfully. Earlier 18/20 and interrupted
14 completed/13 passed batches remain retained and are not overwritten.
The failed-approach, branch-constraint, stale-guidance and integration-applicability
native pilots passed all three conditions. The build-prerequisite pilot retained
native successes but failed all three independent final-artifact probes; the
no-history pilot retained two passing conditions and one source-linked-notes
timeout. All six single-run pilots are retained; the fair repeated multi-task
comparison and uncoached browser/usability gates remain open.

An independent adversarial tester added 14 focused regressions. All 14 pass after
fixes for branch incarnation/retry identity, offline branch recreation, model
session impersonation, rejected queue quarantine, credential/private text capture
and source observation races. The OpenTelemetry patch hash remains unchanged.
Nine further independent lifecycle regressions pass after fixing old-turn
delivery, hidden failed captures, pending timeout status and premature host
shutdown. Real native fault injection verified exactly one extra pass and visible
failure on unchanged implementation `e6357748...`. The managed launcher waits for
the actual final native terminal receipt. A raw standalone host remains outside
this reliable shutdown path.

The latest native lifecycle fault run on project-local OpenCode 2.0.32 passed both
deferred-save and deliberately dropped-save cases, including exactly one
continuation, no plugin loop, visible failure and owned-host shutdown. Evidence:
`.local/git-memory/opencode-lifecycle-faults/1792316955381627900/`.

A first real code-editing writer/consumer pilot passed independent task outcomes;
it does not establish the full 72-consumer usefulness comparison. A separate
FalkorDB AOF/fsync-always instance passed two SIGKILL crashes, fresh service/client
recovery, exact finding/checkpoint persistence, durable revocation and volume
reattachment. The new Compose profile mounts the actual persistence directory.

The latest deterministic suite passed 140 discovered tests with 37 explicit skips;
the latest isolated FalkorDB live suite passed 23/23. Browser interaction is
currently unavailable in CUA, so project-local Chromium/Playwright was used for
the retained scripted browser run. Five viewport/persona runs passed; uncoached
comprehension and real-human usability remain unclaimed.

The current post-checkpoint verification passed the deterministic suite and 23/23
live FalkorDB tests. A real interrupted OpenCode/Zen writer now produced a separate
checkpoint with unchanged source and a passing simulated semantic review.

Current native-run harnesses preserve failed runs and isolate client configuration,
projects and loopback server credentials. The Windows npm shim host cleanup defect
was fixed; only verified completed-fixture server processes were cleaned up.

The earlier handoffs below are historical evidence.

---

# Historical Git-aware shared project memory handoff (superseded by the current
# OpenCode/Zen status above), 2026-10-18

Implemented the new product direction in the Python service, local Git bridge,
HTTP-backed MCP tools, native Codex/Claude hook adapters, offline SQLite outbox,
and branch-aware project UI. The root brief, graph contract and README now govern
Git-aware memory; previous documents and the Juniper fixture remain preserved as
separate history/regressions. The original OpenTelemetry patch and old trial data
were retained. No commit, push, publication, or deployment was performed.

Core changes: immutable repository/commit/branch/observation/snapshot/source and
memory records; separate branch/source/publication histories; authored/verified
integration bindings; deterministic unique replay/squash mappings with source
checks; WIP/stale labels; scoped supersession and explicit conflicts; separate
session checkpoints; bounded lexical context and graph explanation queries.
FalkorDB performs repository ancestry/applicability/revision/explanation traversal.
HTTP and MCP enforce project membership/viewers, durable issuance/revocation, and
no unsafe default-project fallback. Native hooks request at most one capture pass
using the existing assistant, with no additional model/API key or trust bypass.

Validation: 64 tests discovered, 42 offline passed and 22 live-only skipped;
22/22 live tests passed on FalkorDB 6.0.2 with client 1.2.0 in .venv. Python
compilation, JavaScript syntax and patch whitespace checks passed. The isolated
legacy demo passed all 13 assertions. Both deterministic Git demos passed.
OpenTelemetry bridge capture/cold recall and an actual HTTP service restart
preserved the saved revision. The original binary patch SHA-256 stayed
761cddbf99f7ab93ddc411f8361b932438d423854432c3379a3f8d95c38b8dda.

The capable equal-information source-linked notes control tied HiveMind at 3/3
selection cases and used the same 307-character fact context. It was faster in
these local deterministic calls. There were no model calls; human preparation
and review effort were not measured. No superiority claim is made.

Pending by user request: native Codex-to-Claude and reverse automatic-capture
model-session proof after reviewing native project/MCP/hooks trust in the prepared
.local/git-memory/native-fixture checkout. Do not count transport tests as this
proof. Browser visual QA was unavailable: the runtime exposed no app/browser
surfaces. The UI was served and JavaScript checked, without screenshots or a
responsive-layout claim. See testing/git_memory/RESULTS.md for commands, evidence,
limits and the exact remaining acceptance steps.

Main implementation: hivemind/{git_memory,git_graph,git_queries,bridge,
client_adapters,git_demo}.py; auth/api/domain/store/workspace/MCP entrypoints;
web/{index.html,app.js,styles.css}; tests/test_git_*.py;
testing/git_memory/{workflow.py,README.md,RESULTS.md}. Full usage is in README.md.
Private tokens and run artifacts stay in ignored .local/ or Git-private storage.

The older handoff follows for audit history.

---

# HiveMind — resume point

## Actual real-repository handoff — 2026-10-18

Completed two fresh ephemeral Codex CLI sessions against the prepared OpenTelemetry
project. The writer created `memory:workspace:dfe49fe5fcea9a92:v1` through MCP and
left source unchanged. The consumer retrieved that exact version before editing,
verified its optional-dependency guidance against source, added four lines only
to `content/en/docs/contributing/development.md`, and saved
`memory:workspace:5747eaaba2352cf2:v1` with the writer memory reference.

Final Prettier, direct Markdown validation (one file, 13 custom rules), CSpell,
textlint, and `git diff --check` passed after correcting initial formatting.
The writer also demonstrated successful public-test skips without generated
output and nine passing tests against pre-existing output; neither model ran a
fresh build. `testing/opentelemetry/verify-run.py` passed all seven handoff checks,
including distinct completed threads, retrieval before edit, one-file scope,
and live HTTP persistence of both notes. The patch is local and uncommitted.

Added batch mode to `session.py`, `verify-run.py`, and `RUN_RESULT.md`; updated
the guides and prompts. Raw events/final responses, note snapshots, patch, and
machine-readable result are retained under ignored `.local/opentelemetry-test/`.
No core application code changed.

Clarified implementation limits: workspace memory is project-scoped, not
Git-branch-scoped; capture requires explicit person/agent writes; project-note
listing does not automatically extract an evidence graph or use vector search.
This run proves the functional handoff, not an advantage over ordinary notes or
regular RAG. Branch-aware scope and a deliberate memory-write policy remain
implementation work if that is the intended product behavior. A comparison
using equal facts/model/budget remains a separate validation gate.

## Real-repository trial setup — 2026-10-17

Prepared `open-telemetry/opentelemetry.io` at commit
`5c42532e37db75bdd0ffbf158ff088fb774f4492` on local branch
`hivemind/memory-trial` in `.local/opentelemetry.io`. Source, dependency locks,
and all ten submodule pointers remain unchanged. The dedicated HiveMind app is
at `http://127.0.0.1:8772`, container `hivemind-otel-test`, graph
`hivemind_opentelemetry_trial`, project `project:e3022e4a967eb458`. The existing
FalkorDB service was reused without clearing its other graphs.

Added `testing/opentelemetry/` with setup/smoke helpers, private-token MCP bridge,
Codex session launchers, writer/consumer prompts, focused document checks, and
setup guide/status. Added `.local/` to `.gitignore` and excluded local runtime
data from Docker build context with `.dockerignore`. Linked the trial guide
from `README.md`. No core application code changed.

Validation: `py -3.11 testing/opentelemetry/trial.py smoke` passed live health,
MCP initialization/eight advertised tools, project listing/write, recall in a
fresh MCP process, HTTP visibility, version increment, and cross-project HTTP
denial. Restarting the test app and rerunning setup preserved its project/data.
`session.py check` verified Codex CLI configuration; CLI login is available.
`check-doc.py` passed Prettier and direct Markdown validation of the target doc
with 13 custom rules. `docker exec otel-site-trial npm run build` passed for all
11 languages, including final postprocessing. Trial Python and PowerShell syntax
checked. Windows checkout needed LF shell scripts, long-path support, and Git
index refresh; the source checkout is clean.

Known limits: the upstream Markdown CLI reports zero linted files; the direct
wrapper requires the target file to be checked. The pinned upstream npm audit
reports five high-severity findings, recorded locally without changing locks.
The actual model-backed trial has not run. Next: launch
`py -3.11 testing/opentelemetry/session.py writer`, then exit that conversation
and launch `py -3.11 testing/opentelemetry/session.py consumer` as a fresh session.
Retain actual memory IDs, source verification, local diff, and check outcomes.

## Documentation update — 2026-10-17

Added `PROJECT_SUMMARY.md`, an illustrated guide to the current project workspace
and evidence gateway, with eight Mermaid diagrams, Juniper and project-memory
examples, setup instructions, HTTP/MCP usage, permissions, and validation limits.
Linked it from `README.md`. The product boundary and runtime code are unchanged.

Validation: `py -3.11 -m unittest discover -s tests -p 'test_*.py' -v`
discovered 32 tests: 25 passed, seven opt-in live tests skipped. Executed the
guide's Python cold-handoff example and its PowerShell project/create/edit/token/read
example against an isolated in-memory HTTP server; both passed. Relative document
links and fenced blocks checked. Mermaid source is included; diagram rendering
was not checked with a renderer. No live backend test was rerun for this update.

The guide distinguishes ordinary workspace memories from evidence-backed records,
documents separate stores in memory-mode HTTP/MCP processes, and records existing
permission/token-management gaps without claiming those gaps have been fixed.
Next: review the guide, then validate a real model-backed write-and-cold-read flow
and compare its usefulness/preparation cost with source-linked notes.

## Earlier implementation handoff

Updated 2026-10-16 after the live FalkorDB backend slice.

**Recommendation:** R11 **HiveMind — shared company memory with its evidence and limits**, conditional on usefulness and preparation-cost validation. R06 scoped sales-to-delivery acceptance memory remains a conditional alternative. Muse prefers R06; MiMo's last substantive position remains unresolved leaning H06. No forced consensus.

Start here:

- [Decision memo](HIVEMIND_DECISION_MEMO.md): user, winning argument, strongest counter, proposed demo, minimum scope, four-day plan, controls, rejection/switch conditions.
- [Graph contract](HIVEMIND_GRAPH_CONTRACT.md): schema, provenance, scope/version rules, seven graph operations, responsibilities.
- [Position and availability ledger](HIVEMIND_POSITION_LEDGER.md): exact changes, dissent, failed final calls.
- [Paper review](archive/06-paper-review.md): synthetic inputs and one completed independent interpretation; no runtime benchmark.
- [Validation evidence](archive/02-validation-evidence.md): primary product/research sources and limits.

Completed: independent concepts from chair plus eight peers, normalization to 13 cards, independent scores, attacks, repaired finalists, synthetic blind packets, final direct arguments from Sol/Astra, chair's conditional memo. Scores never mechanically selected the recommendation. Wow replaces feasibility scoring; four-day scope constraint stays.

Network failures prevented some blind/repair/final responses. Last substantive positions are preserved; no response or consensus was invented. Fable had a previously recorded credit block and did not contribute.

**Authorization:** the local deterministic slice now has offline and opt-in live profiles. Model-backed provider integration and the qualified-note comparison remain explicit gates before making production or superiority claims.

**Implementation status:** `hivemind/` contains the gateway, project/membership services, editable workspace memory service, HTTP API, MCP stdio server, deterministic fixture and cold-handoff demo. `web/` contains the projects-first UI, interactive memory graph, editor, people panel, and project-scoped coding-agent connection flow. The default backend is in-memory; explicit `falkordb` selection connects only to its configured graph, uses fixed parameterized Cypher, persists exact dataclasses as canonical JSON, and fails without fallback when unavailable. `tests/` contains 25 offline behavior/API/MCP/backend-selection/project/workspace tests plus seven opt-in live tests. The live suite was run with `falkordb==1.2.0` against the isolated `hivemind-falkordb` / `falkordb/falkordb:6.0.2` server on host port `6380`, graph `hivemind_live_gateway`; all seven passed. No model call, retention benchmark, or configured-competitor comparison has been run. All scenarios are synthetic. Do not claim measured safety, superiority, demand or an unserved market.

Source trail: `archive/00-brief.md`, `archive/00-audit.md`; `archive/01-*` proposals; `archive/02-*` cards/origins/validation; `archive/03-*` scores; `archive/04-*` attacks; `archive/05-*` repairs and packet/oracle; `archive/06-*` direct arguments/paper review; current graph contract, decision memo and position ledger in the workspace root.
