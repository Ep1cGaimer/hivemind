# Independent acceptance-core audit — 18 October 2026

This is deterministic adversarial testing by an independent agent. It is not a
model-session test or real-human study. The audit changed only
`tests/test_acceptance_adversarial.py` and this report. The parent agent made the
production repairs after receiving reproductions. No existing graph was cleared,
no existing container was restarted, and no OpenTelemetry checkout was changed.

## Findings and repairs

Four defects were reproduced before repair. The failed runs remain described
below; a later passing run does not erase them.

| Severity / IDs | Original defect and reproducer | Observed result | Current repair location |
| --- | --- | --- | --- |
| High — G5, D14, E3 | Interrupt `save` at the second of two `SUPPORTED_BY` writes. Recall before retry. | Service returned `STORAGE_UNAVAILABLE`, yet the partly linked finding appeared `applicable` with only one required source. Replaying the same event repaired it. Reproduced in memory and FalkorDB. Example original live revision: `revision:271feab6aa7962ac`. | `hivemind/git_memory.py:339`: sources/revision relationships precede activation; `_matches` at line 236 requires activation and all declared source paths; recall at line 358 checks expected source cardinality. |
| High — D7, D9 | On feature save a finding at B; reset feature to A; create replacement C; fast-forward main from A to C. The bound guide is unchanged, but B is not an ancestor of C. | Finding from abandoned B was incorrectly inherited on main. Reproduced in memory and FalkorDB. Example original live revision: `revision:58383602aed9790b`. | `hivemind/git_memory.py:255` and line 278: authored and integration publication require origin-head reachability; unsupported abandoned origins require review. |
| Medium — G4, G7 | Two first-start `AuthManager` instances both read the durable signing-secret key as absent, then attempt insertion. | One instance raised `ImmutableConflictError` instead of starting with the winning durable secret. Deterministic barrier reproducer; this is a startup race, not a demonstrated memory loss. | `hivemind/auth.py:73`: immutable-conflict loser loads the winning signing secret. |
| Medium — F6 | Configure private root file `plan.txt`. Capture body `Follow plan.txt before doing the release.`, decision classification, no paths. Try online and offline. | The private filename entered the shared graph and SQLite retry payload. No private file contents needed to be copied. HTTP/memory backend reproduction. | `hivemind/bridge.py:238`: textual private-path detection includes root basenames with extensions. |

The interrupted-save regression also advances Git and synchronizes before retry,
so publication cannot activate an unfinished record found through `list('finding')`.
A separate source-edge ablation retains the finding, both path declarations and
source nodes while deleting one actual support edge; partial support must not
become fully applicable. These strengthened cases pass after repair.

## Execution record

Environment: Windows PowerShell; project-local Python 3.11 venv; real local Git;
FalkorDB at `127.0.0.1:6380`. No model calls were made. Each live audit run creates
a fresh random graph and fresh projects. Fixture-owned relationship ablations
cannot affect another project. Live graphs are retained rather than reset.

Commands:

```powershell
.venv\Scripts\python.exe -m unittest discover -s tests -p test_acceptance_adversarial.py -v

$env:HIVEMIND_LIVE_TESTS='1'
$env:FALKORDB_HOST='127.0.0.1'
$env:FALKORDB_PORT='6380'
.venv\Scripts\python.exe -m unittest discover -s tests -p test_acceptance_adversarial.py -v

.venv\Scripts\python.exe -m unittest discover -s tests -p 'test_git*.py' -v
.venv\Scripts\python.exe -m unittest discover -s tests -p test_backend.py -v
```

The separate existing live Git-suite command explicitly set
`FALKORDB_GRAPH=hivemind_core_reference_24db6494640c43958f0d4bf4efedc616` and selected
`test_git_live.py`. It did not run the legacy suite that can reset a selected graph.

| Run | Actual result |
| --- | --- |
| Initial independent audit, 7 discovered | **failed**: 3 offline failures, 1 linked-worktree pass, 3 live skips. |
| Initial independent audit with live opt-in, 7 discovered | **failed**: 5 failures (the first two defects in each backend, startup race offline); 2 linked-worktree passes; no skips. |
| Private-basename extension, 8 discovered | **failed**: earlier failures plus both online/offline basename subtests failed; 3 live skips. |
| Existing Git/bridge suite | **passed**: 50 discovered, 34 passed, 16 explicit live skips; 63.494 s. |
| Existing live Git suite | **passed**: 16/16, no skips; 36.850 s; reference graph named above. |
| Backend factory/failure suite | **passed**: 8/8, 0.291 s; explicit live selection fails without falling back to memory. |
| First post-repair independent run | **passed**: 12/12, no skips; 20.351 s; graph `hivemind_core_audit_edb4d6d2e128009ea4ab5cc9`. |
| Post-repair authorization matrix added | **passed**: 14/14, no skips; 24.108 s; graph `hivemind_core_audit_05fc7ea8a4e747c7864cb681`. |
| Post-repair source-support ablation added | **passed**: 16/16, no skips; 25.947 s; graph `hivemind_core_audit_5cecdce18f6614979ac7bc36`. |
| Final audit including successful cherry-pick and concurrent bridge checkpoint updates | **passed**: 19/19, no skips; 36.331 s; graph `hivemind_core_audit_f8e1bc03814e8eb2abf88a34`. Seven cases execute against FalkorDB, seven corresponding offline cases and five HTTP/auth/privacy cases pass. |

Original failure log excerpts:

```text
AssertionError: 'revision:271feab6aa7962ac' unexpectedly found ...
An unacknowledged partial save appeared as applicable before retry repaired its required sources

AssertionError: 'revision:58383602aed9790b' unexpectedly found ...
Matching unchanged source text must not publish learning from an unintegrated abandoned commit

Concurrent first startup rejected one process:
ImmutableConflictError('Immutable node already exists with different content: auth:signing-secret')

AssertionError: True is not false : Configured private basename reached graph or retry payload
```

Elapsed suite durations are test-run durations. They do not measure recall p95,
plugin overhead, cold-start latency or the end-to-end developer-visible operation.

Post-run SHA-256 identities (the workspace contains uncommitted changes):

```json
{
  "hivemind/git_memory.py": "068e3a352a4e241985495840d476582a1195e6370042d964a9b86dd96a8d10fe",
  "hivemind/auth.py": "58de1e90f2d4b7d93475e50c128c9e5d0d99ab4711ca3a3ca8cf56781f2b4d16",
  "hivemind/bridge.py": "f332ca07ee0b62fd7d6bb445eeb1f472a99e24fac75703cd180a0a3f40c02a61",
  "hivemind/git_graph.py": "4567e15547c7826062f83d3c60e573dba6e67a6a819b8c67eb801051fe31e5d8",
  "hivemind/git_queries.py": "0859ee6e3d20ec6dd3215bec0494658d4be0ca99428bcccfbe29edfb34d34fa2",
  "tests/test_acceptance_adversarial.py": "b35ead51816e8ae65e81492e54b492e2f77d88611974db196ae5a9cbf1e1436a"
}
```

## Acceptance evidence map

The status is for this audit's precise stated case. A passing focused case does
not certify every possible history, client, failure timing or operating system.
`untested` means an acceptance branch still lacks sufficient executed evidence
here, even when related tests pass. Existing tests named below were rerun as
recorded above unless explicitly described as historical or inspected only.

Abbreviations: **core** = `tests/test_git_memory.py`; **bridge** =
`tests/test_git_bridge_http.py`; **security** = `tests/test_git_bridge_security.py`;
**recovery** = `tests/test_git_bridge_recovery.py`; **live** = `tests/test_git_live.py`;
**audit** = `tests/test_acceptance_adversarial.py`.

### Git cases

| ID | Status | Authoritative evidence / remaining limitation |
| --- | --- | --- |
| D1 | passed | Core `same_commit_branches_and_same_branch_teammate_wip`; audit linked-worktree isolation; actual Git, both stores. |
| D2 | untested | Same-commit isolation and no retroactive publication pass, but a focused old-common-ancestor discovery/deepening scenario with newly authored branch learning was not run. |
| D3 | passed | Core same-branch fixture uses a distinct connector joined to the recorded identity and sees the unfinished finding. This does not establish understandable second-machine onboarding. |
| D4 | passed | Core teammate differing snapshot is explicitly `wip_requires_verification`; audit worktrees have separate snapshots. |
| D5 | untested | Authored-successor path is exercised by the integration fixtures, but no isolated assertion proves the exact pending-finding publication receipt for only a qualifying authored successor. |
| D6 | passed | Core `fast_forward_and_normal_merge_publish_once` asserts branch exclusion before real fast-forward integration and inclusion afterward. |
| D7 | untested | Real normal merge and independently reproduced abandoned-B/replacement-C case pass after repair. A conflict-resolving merge that discards a required source remains untested. |
| D8 | passed | Core fast-forward fixture saves later learning at already-integrated feature tip and asserts it stays off main. |
| D9 | passed | Core unique real rebase mapping retains finding; audit abandonment regression prevents unsupported rewrite transfer. Broader mapping arrangements remain untested. |
| D10 | passed | Audit real cherry-pick replays C only, includes C's finding, excludes separate finding at unpicked B; both stores. |
| D11 | passed | Core real aggregate squash mapping transfers source-compatible finding. Source-mismatched squash and competing aggregate mappings were not separately exercised. |
| D12 | passed | Core ambiguous mapping fixture sets observed `new_matches=2`; server leaves finding local and returns `needs_review`. Real duplicate-patch discovery, rather than the server-policy input, remains untested. |
| D13 | untested | Source change preserves record and marks historical in core. A deleted required file was not independently exercised. |
| D14 | passed | Audit two required files, change only one: counts 2/1 and `historical_source_changed`; interrupted-save and support-edge ablation also prevent partial verification. |
| D15 | passed | Core scoped correction on another branch leaves original revision visible on main. |
| D16 | passed | Core concurrent corrections retain both applicable revisions and an unresolved conflict; no timestamp winner. |
| D17 | passed | Security tests cover same-second identical reflog text, online recreation, and offline queued work from a deleted incarnation. Historical finding remains preserved. |
| D18 | passed | Core actual shallow clone/deepen and bounded-coverage checks report incomplete history rather than absence proof. |
| D19 | untested | Security source-read/hash races and metadata-preserving edits pass. An actual branch checkout between observation stages was not injected in this audit. |
| D20 | untested | Audit explicit Git text rule proves LF/CRLF source identity, including HEAD blob comparison, in both stores. Arbitrary supported clean/smudge filters remain untested. |

### Graph cases

| ID | Status | Authoritative evidence / remaining limitation |
| --- | --- | --- |
| E1 | passed | Existing 16-case live suite and independent live core cases execute writes, recall and explanation against actual FalkorDB. HTTP authorization/privacy tests use the memory fixture and are labeled accordingly. |
| E2 | passed | Live synthetic 79-commit diamond DAG has 2**26 possible routes; actual stored `PARENT` reachability determines inherited candidates, including zero-length ancestry. |
| E3 | passed | Audit partial source mismatch, missing support-edge ablation, interrupted save, and existing applicable-revision conflicts affect returned context. |
| E4 | passed | Live synthetic explanation verifies every returned node pair against actual stored PARENT/PUBLISHES edges. Existing integration explanation is also asserted. |
| E5 | passed | Existing fixture-owned PARENT/PUBLISHES ablation removes inherited finding/explanation; audit source-support ablation retains facts/metadata but removes full verification. |
| E6 | untested | This audit made no OpenCode calls; deterministic context differences cannot establish a model's changed decision. |
| E7 | passed | Backend suite rejects unavailable explicitly selected FalkorDB; recovery suite surfaces structured storage failure/503. No synthetic-memory fallback is accepted as live. |
| E8 | untested | Query source has bounded limits and shortest-path traversal; the exponential-route live DAG passes. Recall beyond finding/observation page limits and adversarial maximum-sized payload fanout were not stress-tested. |

### Authorization and privacy cases

| ID | Status | Authoritative evidence / remaining limitation |
| --- | --- | --- |
| F1 | passed | Audit cross-project existing/absent targets produce identical 403 bodies across detail, graph, overview, memories and write routes; project listing exposes only token project. This is response-level isolation, not a timing-side-channel study. |
| F2 | passed | Audit viewer denied before validation on register/sync/finding/checkpoint/no-change/propose/accept, legacy memory creation, token mint and project creation. Existing scoped correction permissions also pass. |
| F3 | passed | Existing bridge transport immediately rejects revoked token; live fresh AuthManager/store sees persistent revocation. Actual database-crash durability is separate evidence, below. |
| F4 | passed | Core human-session fixture proposes/accepts exact revision with conditions preserved; audit bearer plus genuine fixture cookie and `human=true` payload is still rejected. Fixture is not labeled a real human reviewer. |
| F5 | passed | Existing local MCP rejects model-provided branch arguments; bridge supplies its own context and owns task session. Direct editor synchronization remains a connector trust boundary, not cryptographic proof of source truth. |
| F6 | untested | Known credentials, configured private text, Windows/absolute paths, private root basename, graph and retry payload probes pass after repair. A comprehensive graph/cache/outbox/log/export-artifact scan over all capture forms was not completed. |
| F7 | untested | No model-driven source/memory prompt-injection attempt was run here. Schema checks alone do not establish model behavior. |
| F8 | untested | No interactive browser injection test was performed by this audit. |
| F9 | passed | Executed legacy HTTP project/viewer tests, audit alias restrictions and repeated local MCP authorization tests. The full legacy route permutation space is not certified. |
| F10 | untested | This core audit did not exercise OpenCode native permissions. Codex/Claude native trust/lifecycle proof is outside agreed scope. |

### Recovery and concurrency cases

| ID | Status | Authoritative evidence / remaining limitation |
| --- | --- | --- |
| G1 | passed | Bridge outage and HTTP 503 fixtures queue captures and expose queued state; recovery marks saved only after delivery. |
| G2 | passed | Existing offline branch switch and deleted/recreated ref tests retain original observation/branch and exclude finding from replacement context. |
| G3 | passed | Concurrent repeated event delivery yields one revision; retries retain immutable event identity; replay repairs interrupted source writes. |
| G4 | passed | Core simultaneous findings/corrections preserve both records; audit independent LocalBridge/SQLite sessions concurrently create and revise their own checkpoints, both final task revisions survive; startup-secret race repaired. |
| G5 | passed | Audit injects interruption at second required source relationship, recalls immediately and after successor Git sync, then retries exact event and verifies both source links. This does not test OS-kill at every storage instruction. |
| G6 | untested | Existing fresh LocalBridge retrieves saved memory. Fresh-process recovery of pending outbox work after abrupt local-process termination was not run in this audit. |
| G7 | untested | Existing live test reconstructs client/store, not database process. Historical actual crash/volume-reattach artifact passes for an earlier implementation manifest; see below. No existing database/container was restarted by this audit. |
| G8 | untested | Immediate HTTP 503 and storage rejection recover correctly; configured HTTP/Git timeouts were inspected. A deliberately slow/stalled dependency was not timed end-to-end here. |
| G9 | untested | Fixture starts empty and many first recalls exercise it, but no independent explicit empty-envelope and ordinary-work-continuation assertion was added here. |
| G10 | passed | Core 10 long findings returns at most eight within 8,000 serialized characters and explicit truncation. Page-limit overload and relevance under a large realistic corpus remain untested. |

Historical actual persistence evidence was read, not rerun:
`.local/git-memory/database-restarts/1792271944364711800-7397a4/result.json`.
It records acknowledged finding `revision:97301f84ca9127cf`, checkpoint
`revision:84997ead54f453ae`, preserved revocation, actual SIGKILL without SAVE, a
new service after container restart, and volume reattachment to a recreated
database. It reports `passed: true` and `implementation_unchanged: true` for its
own manifest. The audit's production repairs happened afterward, so this is not
represented as a new crash test of the current revision.

No p95 performance gate, model reliability threshold, complete privacy scan,
interactive UI gate or global acceptance completion is established by this report.
