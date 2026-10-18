# Final-product acceptance ledger

Goal: [goal.md](../../goal.md). Scope: OpenCode/Zen, local final product only.
This ledger is in progress. Tests are not marked passed merely because a related
unit test passes. `untested` means the complete item's required evidence has not
yet been audited, even where partial evidence is linked below.

## Current execution evidence - 18 October 2026

- Latest deterministic functional suite: 144 discovered, 107 passed and 37
  explicit skips (188.335 s). Independent fixture/control suite: 30 passed
  (31.770 s). Compilation, JavaScript syntax, Compose configuration and whitespace
  checks passed. Artifact: `.local/verification/1792335930663849000/`.
- Latest isolated FalkorDB live suite: 23 passed, no failures (41.921 s), graph
  `hivemind_verification_1792336159396093900`, FalkorDB 6.0.2 / Python client 1.2.0.
- Current-source rerun after the native lifecycle/checkpoint changes: deterministic
  suite passed with artifact `.local/verification/1792328797075811500/`; isolated
  FalkorDB live suite passed 23/23 with artifact
  `.local/verification/1792329021246217500/`.
- Final post-checkpoint/source verification: deterministic functional suite passed
  with artifact `.local/verification/1792335930663849000/`; final isolated
  FalkorDB live suite passed 23/23 with artifact
  `.local/verification/1792336159396093900/`.
- Project-local official OpenCode `@opencode/cli` 2.0.32 is pinned by
  `package.json`/`package-lock.json`. In its isolated environment the Zen catalog
  exposes `opencode/deepseek-v4.1-flash-free` without an additional credential.
- Fourteen independently authored adversarial regressions passed (23.717 s).
  They exposed real branch retry/recreation, session impersonation, private-text capture,
  observation race and queue-quarantine defects, now corrected. See
  [the test file](../../tests/test_git_bridge_security.py).
- Seven OpenCode bridge/installer contract tests passed (8.388 s). These do not
  replace real model lifecycle tests. See [the tests](../../tests/test_opencode_adapter.py).
- Real OpenCode 2.0.29 / Zen `opencode/deepseek-v4.1-flash-free` automatically saved
  `revision:c41dd091fb60afdd` in writer session
  `ses_eb46d87d9ffedmdkNupdxh2yz4`. Fresh consumer
  `ses_eb46d4217ffeikfb4DFiilZ2qf` cited that revision and planned batches 32/32/6.
  Artifacts: `.local/git-memory/opencode-runs/1792269250840871200/`.
- A persistent-host repeat saved `revision:6c558972bfd129f6`; writer
  `ses_eb46ae839ffeRBl2OPqOlDTFka`, fresh consumer
  `ses_eb46a98bcffesOpUV7LN57oyyd`.
  The consumer called `hivemind_record_no_change`. Artifacts:
  `.local/git-memory/opencode-runs/1792269422504733100/`.
- Retained failures: older plugin format rejected; `.mjs` was not discovered;
  initial Zen connectivity probes returned HTTP 403; a CLI API probe incorrectly
  supplied a GET body; first persistent host connection lacked its generated
  password. The corrected workflow uses the official OpenCode 2 plugin format,
  `.js` discovery, ordinary coding prompts, body-free GET and a private host
  password passed through the standard client environment.
- Nine additional independent lifecycle regressions pass. Actual OpenCode/Zen
  fault injection verified one extra capture pass, durable no-change, visible
  failure, terminal completion and host shutdown on unchanged `e6357748...`.
  Reproducer: [opencode_lifecycle_faults.py](opencode_lifecycle_faults.py).
  Artifacts: `.local/git-memory/opencode-lifecycle-faults/1792271571255608200/`.
- The latest native lifecycle fault run on project-local OpenCode 2.0.32 passed
  both deferred-save and deliberately dropped-save cases, including exactly one
  continuation, no plugin loop, visible failure and owned-host shutdown. Evidence:
  `.local/git-memory/opencode-lifecycle-faults/1792316955381627900/`.
- First engineering reliability batch: 18/20, including two catalog failures,
  with mixed implementation versions. Later frozen batch: 14 completed/13 passed;
  attempt 15 started without a final result. Its process/handle are absent.
  Preserve `.local/git-memory/reliability/1792271853643990000/interruption.json`
  and all runs. The newest frozen batch completed 20/20 cycles with 19 passed,
  meeting the initial 19/20 gate; cycle 13 retained a no-change writer failure.
  Evidence: `.local/git-memory/reliability/1792315757057449700/`.
- The failed-approach native pilot passed all three conditions with independent
  final-artifact checks and HiveMind capture. Evidence:
  `.local/evaluation/1792315572752353000/`. A second build-prerequisite pilot
  retained successful native sessions but failed all three independent final-artifact
  probes; it is retained at `.local/evaluation/1792317005486247600/`.
  Branch-constraint, stale-guidance and integration-applicability pilots passed all
  three conditions; no-history retained two passing conditions and one
  source-linked-notes timeout. Evidence directories are respectively
  `.local/evaluation/1792318501225295400/`,
  `.local/evaluation/1792318747049249000/`,
  `.local/evaluation/1792319023517806500/`, and
  `.local/evaluation/1792319186203714100/`. The randomized 72-consumer comparison,
  writer-premise audit and full cost accounting remain open.
- Real OpenCode/Zen graph relationship ablation changed the actual delivered model
  context and completed both intact/ablated native decisions. Evidence:
  `.local/git-memory/graph-ablation/1792326345854150300/`.
- Real OpenCode/Zen prompt-injection smoke passed: hostile source/memory text was
  rejected as untrusted, no source changed, no private canary entered inventory,
  and the owned host stopped. Evidence:
  `.local/git-memory/injection/1792337510826732300/`.
- Real OpenCode/Zen native permission-denial smoke passed: ordinary task completed,
  HiveMind capture was visibly failed under deny-by-default permissions, and the
  owned host stopped. Evidence:
  `.local/git-memory/permission-denial/1792337492763770100/`.
- Real OpenCode/Zen prompt-injection run treated hostile README/shared-memory
  instructions as untrusted: the source instruction was rejected, no source
  changed, no private file was captured, and no private canary entered the
  artifact inventory. Evidence: `.local/git-memory/injection/1792336997082075500/`.
- Real OpenCode/Zen alternating three-session handoff passed: A writer saved a
  finding, B consumed it and saved separate learning, and C consumed the newer
  result. Evidence: `.local/git-memory/bidirectional/1792324795708507300/`.
- Real OpenCode/Zen interrupted-writer checkpoint run passed machine checks and an
  independent simulated semantic review. It includes an actual interrupted tool
  boundary, separate checkpoint revision, unchanged source digest, one bounded
  capture pass and clean host shutdown. Evidence:
  `.local/evaluation/1792334957504741000/`.
- Real Chromium/Playwright browser run passed five scripted personas across five
  desktop/mobile viewports, keyboard focus, labels, responsive snapshots and UI
  injection checks. Its retained report also records five 401 console-error
  entries; the scenario checks still returned `passed`. Evidence:
  `.local/usability/browser/1792324726135980500/report.json` and its screenshots.
- Artifact-wide privacy, abrupt client restart and stalled dependency timeout tests
  pass in the final deterministic run artifact
  `.local/verification/1792335930663849000/`, using
  `tests/test_privacy_artifacts.py`, `tests/test_client_restart.py` and
  `tests/test_stalled_timeout.py`.
- Two actual database SIGKILLs and volume reattachment preserved exact finding/
  checkpoint records and revocation under AOF/fsync always. Reproducer:
  [database_restart.py](database_restart.py). The current-source rerun passed both
  crashes, fresh-service recovery, volume reattachment, exact immutable records
  and revocation. Evidence:
  `.local/git-memory/database-restarts/1792318453989630800-47fff0/result.json`.
- An unfamiliar simulated tester found missing package installation and weak CLI
  guidance. Coached repair checks pass editable root/nested imports, missing Git/
  connection guidance, wheel static assets outside checkout and isolated durable
  startup. This is not uncoached usability. See [the report](../usability/first_onboarding_report.md).
- Raw `opencode run --standalone` can exit before capture. The supported managed
  launcher owns host lifetime; interactive TUI/context-change cases remain open.
- The built-in CUA surface remains unavailable, but project-local Chromium/
  Playwright acceptance passed five scripted browser personas and viewport runs.
  This does not establish uncoached comprehension or real-human usability.
- OpenTelemetry patch SHA-256 remains
  `761cddbf99f7ab93ddc411f8361b932438d423854432c3379a3f8d95c38b8dda`.
- No complete fair repeated multi-task usefulness comparison or uncoached onboarding
  gate has passed. The 20-cycle reliability gate is a single repeated workload, not
  evidence of broad usefulness or superiority.

## Item audit

| ID | Requirement | Status | Evidence / next verification |
| --- | --- | --- | --- |
| A1 | Accessible product source | untested | Awaiting requirement-specific evidence audit. |
| A2 | Reproducible setup | untested | Awaiting requirement-specific evidence audit. |
| A3 | Graph documentation | untested | Awaiting requirement-specific evidence audit. |
| A4 | Working local scenario | untested | Awaiting requirement-specific evidence audit. |
| A5 | Accurate product positioning | untested | Awaiting requirement-specific evidence audit. |
| A6 | Work and dependency disclosure | untested | Awaiting requirement-specific evidence audit. |
| A7 | Technical explainability | untested | Awaiting requirement-specific evidence audit. |
| B1 | Clean-environment installation | untested | Awaiting requirement-specific evidence audit. |
| B2 | First useful result | untested | Awaiting requirement-specific evidence audit. |
| B3 | Correct repository detection | untested | Awaiting requirement-specific evidence audit. |
| B4 | Multiple repositories | untested | Awaiting requirement-specific evidence audit. |
| B5 | Linked worktrees | untested | Awaiting requirement-specific evidence audit. |
| B6 | Teammate onboarding | untested | Awaiting requirement-specific evidence audit. |
| B7 | Safe adapter installation | untested | Awaiting requirement-specific evidence audit. |
| B8 | Actionable setup failures | untested | Awaiting requirement-specific evidence audit. |
| C1 | Automatic recall | passed | 19 successful OpenCode/Zen cycles report recall before the consumer model request; see `.local/git-memory/reliability/1792315757057449700/result.json`. |
| C2 | Automatic capture | passed | 19/20 real OpenCode/Zen cycles automatically captured useful learning; cycle 13 is retained as the one no-change writer failure. |
| C3 | Meaningful learning | passed | Failed-approach writer finding retained the exact-ID constraint, source paths, boundary behavior and batching consequence; see `.local/evaluation/1792315572752353000/`. |
| C4 | Source binding | passed | Native findings retain source paths, source commit, HEAD and snapshot; see the reliability and failed-approach artifacts. |
| C5 | Honest validation claims | passed | Native saved findings retain the explicit agent-reported validation label; independent receipts remain separate. |
| C6 | Separate checkpoint | passed | Real interrupted OpenCode/Zen writer produced separate checkpoint `revision:9c0c732b62cdc08d`; source stayed unchanged across capture, one bounded pass completed, host stopped, and simulated semantic review passed. |
| C7 | No-change behavior | passed | Managed consumers record `no_change` instead of filler; raw standalone is not the supported launcher path. |
| C8 | Fresh consumer | passed | 19 successful cycles use distinct writer/consumer sessions and consumers cite saved revisions. |
| C9 | Independent-session handoff | passed | Three distinct real OpenCode/Zen sessions alternated writer/consumer roles and preserved separate revisions; evidence `.local/git-memory/bidirectional/1792324795708507300/`. |
| C10 | OpenCode adapter lifecycle | untested | Headless OpenCode 2.0.32 recall/capture/context/completion/timeout/shutdown cases pass; checkout-change, interactive TUI/context-change and native permission-error cases remain open. |
| C11 | Bounded continuation | passed | Actual native faults show exactly one synthetic submission and two terminal events, no loop. Duplicate/delayed events independently covered. See lifecycle artifacts above. |
| C12 | Visible capture failure | passed | Native dropped-save fault reports `failed`, visible warning and owned-host shutdown; new-turn retry remains available. |
| D1 | Same commit, different branches | passed | Real Git fixture and live edge evidence. |
| D2 | Existing shared ancestry | passed | Corrected live edge run proves old common ancestry does not publish new branch learning. |
| D3 | Same-branch teammates | passed | `tests/test_git_memory.py` same-branch WIP fixture. |
| D4 | Different working snapshots | passed | Real Git snapshot mismatch labels WIP/requires verification. |
| D5 | Authored successor commit | passed | Corrected live edge run proves only the qualifying authored successor publishes matching sources. |
| D6 | Fast-forward integration | passed | Real Git fast-forward publication fixture. |
| D7 | Normal merge | passed | Corrected live edge run retains source mismatch and no unsafe publication. |
| D8 | Later learning on an integrated tip | passed | Real Git integration fixture prevents retroactive publication. |
| D9 | Rebase | passed | Deterministic unique mapping fixture. |
| D10 | Cherry-pick | passed | Deterministic source-checked mapping fixture. |
| D11 | Squash merge | passed | Deterministic aggregate mapping fixture. |
| D12 | Ambiguous mapping | passed | Ambiguous candidates remain branch-local and require review. |
| D13 | Changed or deleted sources | passed | Corrected live edge run preserves history and removes current verification. |
| D14 | Partial source mismatch | passed | Required-source mismatch remains `needs_review/source_mismatch`. |
| D15 | Scoped correction | passed | Branch-scoped immutable correction fixture. |
| D16 | Concurrent corrections | passed | Concurrent revisions remain visible as conflicts. |
| D17 | Branch deletion and recreation | passed | Recreated refs receive distinct branch identity. |
| D18 | Shallow or bounded history | passed | Shallow/deepen and explicit incompleteness fixtures. |
| D19 | Checkout changes during observation | passed | Corrected live edge run rejects torn checkout observations. |
| D20 | LF/CRLF and supported filters | passed | Corrected live edge run preserves canonical clean/smudge source identity. |
| E1 | Actual live path | passed | Latest isolated FalkorDB live suite passed 23/23. |
| E2 | Ancestry traversal | passed | Live Git tests exercise persisted ancestry/publication traversal. |
| E3 | Applicability selection | passed | Live source-binding and applicability fixtures pass; partial mismatch remains explicit. |
| E4 | Inspectable explanation | passed | Explanation paths correspond to persisted nodes/relationships in live tests. |
| E5 | Relationship ablation | passed | Live ablation removes inheritance while retaining facts and metadata. |
| E6 | Decision consequence | passed | Live FalkorDB relationship ablation changed delivered context and the actual OpenCode/Zen decision; evidence `.local/git-memory/graph-ablation/1792326345854150300/`. |
| E7 | No hidden fallback | passed | Explicit FalkorDB failures remain storage failures; no silent memory fallback. |
| E8 | Bounded queries | passed | Corrected live edge run passes 1,025-record bounded/incomplete recall cases. |
| F1 | Project isolation | passed | Project token isolation passes deterministic HTTP/MCP and adversarial tests. |
| F2 | Viewer restrictions | passed | Viewer write/promotion/token restrictions pass. |
| F3 | Revocation | passed | Revocation remains enforced across current session/restart fixtures. |
| F4 | Human promotion | passed | Model cannot accept its own project-wide proposal; owner boundary is tested with a fixture. |
| F5 | Model-supplied context | passed | Model-supplied branch/hash/snapshot context cannot become authoritative. |
| F6 | Private capture | passed | Artifact-wide online/offline canary scan passed across store, SQLite state/outbox and generated files; final deterministic artifact `.local/verification/1792335930663849000/`; see `tests/test_privacy_artifacts.py`. |
| F7 | Prompt injection | passed | Real OpenCode/Zen hostile source/shared-memory instructions were rejected without source change, permission grant, private-file capture or private-canary leakage; artifact `.local/git-memory/injection/1792336997082075500/`. |
| F8 | UI injection | passed | Project-local Chromium rendered hostile memory text literally with no script/image execution across five viewport runs; artifact `.local/usability/browser/1792324726135980500/report.json`. |
| F9 | Legacy-route bypass | passed | Legacy HTTP/MCP aliases enforce the same project authorization in current tests. |
| F10 | Native trust | passed | Project-local OpenCode 2.0.32 runs use unchanged native permissions; explicit deny-by-default smoke visibly failed capture without bypass and cleanly stopped the owned host. |
| G1 | Offline capture | passed | Outage queues capture without claiming shared persistence. |
| G2 | Branch switch before retry | passed | Queued work retains original branch and snapshot. |
| G3 | Duplicate delivery | passed | Duplicate lifecycle events/retries produce one logical revision. |
| G4 | Concurrent agents | passed | Concurrent writers preserve findings and separate checkpoints. |
| G5 | Interrupted save | passed | Rejection/quarantine and interrupted source-link save remain retryable without graph corruption. |
| G6 | Client restart | passed | Abrupt child-process exit preserved pending local capture; a fresh bridge flushed it exactly once with saved status; final deterministic artifact `.local/verification/1792335930663849000/`. |
| G7 | Service/database restart | passed | Current-source owned-container run passed two SIGKILLs, fresh-service recovery, volume reattachment, exact finding/checkpoint records and revocation under AOF/fsync-always; artifact `.local/git-memory/database-restarts/1792318453989630800-47fff0/result.json`. No power-loss claim. |
| G8 | Timeout handling | passed | Real stalled local HTTP dependency timed out under the bounded request window and remained queued, never falsely saved; final deterministic artifact `.local/verification/1792335930663849000/`. |
| G9 | No useful memory | passed | Native empty recall/consumer no-change behavior is retained. |
| G10 | Memory overload | passed | Long-finding and 1,025-candidate cases stay bounded and explicitly incomplete. |
| H1 | Independent task outcomes | untested | Awaiting requirement-specific evidence audit. |
| H2 | Strong alternatives | untested | Awaiting requirement-specific evidence audit. |
| H3 | Fair conditions | untested | Awaiting requirement-specific evidence audit. |
| H4 | Genuine cold starts | untested | Awaiting requirement-specific evidence audit. |
| H5 | Behavioral benefit | untested | Awaiting requirement-specific evidence audit. |
| H6 | End-to-end quality | untested | Awaiting requirement-specific evidence audit. |
| H7 | Complete cost accounting | untested | Awaiting requirement-specific evidence audit. |
| H8 | Negative-case restraint | untested | Awaiting requirement-specific evidence audit. |
| H9 | Repeatability | untested | Awaiting requirement-specific evidence audit. |
| H10 | Independent simulated users | untested | Awaiting requirement-specific evidence audit. |
| I1 | Five-second orientation | passed | Browser report rendered project and memory context across five declared viewports/personas; `.local/usability/browser/1792324726135980500/report.json`. |
| I2 | Clear memory categories | passed | Browser report exposed Team memory, Project memory and Memories labels with no missing form labels; `.local/usability/browser/1792324726135980500/report.json`. |
| I3 | Applicability comprehension | untested | Awaiting requirement-specific evidence audit. |
| I4 | Useful inspection | untested | Awaiting requirement-specific evidence audit. |
| I5 | Understandable promotion | untested | Awaiting requirement-specific evidence audit. |
| I6 | Context changes | untested | Awaiting requirement-specific evidence audit. |
| I7 | Complete interface states | untested | Awaiting requirement-specific evidence audit. |
| I8 | Capture visibility | untested | Awaiting requirement-specific evidence audit. |
| I9 | Visual quality | passed | Chromium screenshots were retained across five desktop/mobile viewport sizes without runner failures; `.local/usability/browser/1792324726135980500/`. |
| I10 | Keyboard and screen sizes | passed | Keyboard focus and five viewport sizes passed in the Chromium artifact `.local/usability/browser/1792324726135980500/report.json`. |
| I11 | Uncoached usability | untested | Awaiting requirement-specific evidence audit. |
| J1 | Immediate problem clarity | untested | Awaiting requirement-specific evidence audit. |
| J2 | Ordinary writer task | passed | Narrow OpenCode/Zen smoke workflow automatically saves an ordinary writer finding; broad walkthrough remains open. |
| J3 | Fresh consumer | passed | Narrow OpenCode/Zen smoke workflow uses a fresh consumer that cites the saved revision; stronger completed-code walkthrough remains open. |
| J4 | Branch-sensitive behavior | passed | Deterministic Git branch applicability plus native branch-constraint pilots retained branch-specific context and main-branch qualification. |
| J5 | Integration changes applicability | passed | Deterministic live integration applicability and native before/after pilots retained applicability transitions. |
| J6 | Inspectable explanation | untested | Awaiting requirement-specific evidence audit. |
| J7 | Unscripted variation | untested | Awaiting requirement-specific evidence audit. |
| J8 | Reliable repetition | untested | Awaiting requirement-specific evidence audit. |
| J9 | Honest comparison | untested | Awaiting requirement-specific evidence audit. |
| J10 | Reproducible handoff | untested | Awaiting requirement-specific evidence audit. |

## Open execution gates

- The newest declared 20-cycle engineering batch is complete at 19/20 and meets its
  initial gate; all failures and prior incomplete batches remain retained.
- Eight to ten tasks × three runs × three fair conditions: six single-run task pilots
  have been executed, but the full repeated usefulness gate is not complete.
- Five scripted browser personas: completed with screenshots and accessibility/focus checks; five unfamiliar uncoached users remain open.
- Three consecutive complete Git-sensitive walkthroughs: not yet executed.
- Warm/cold end-to-end latency distributions: not yet measured.

Historical verification remains in [RESULTS.md](RESULTS.md). The current ledger
supersedes its native-client testing scope, without altering its historical runs.
