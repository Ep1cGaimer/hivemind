# Git-aware memory verification — 18 October 2026

The Git memory core, local bridge, HTTP/MCP operations, both native adapter
installers, offline outbox and branch-aware UI are implemented. Native
Codex↔Claude automatic model-session proof remains pending at the user's explicit
request. Browser visual QA was unavailable because the computer-use runtime
reported no browser or app surfaces. Neither limit is counted as a passing test.

## Executed checks

| Check | Observed result |
| --- | --- |
| `py -3.11 -m unittest discover -s tests -q` | 64 discovered: 42 passed, 22 live-only skipped; 40.058 s |
| Live suite, command below | 22 passed, no skips; 37.560 s |
| `py -3.11 -m compileall -q hivemind tests testing/git_memory` | Passed |
| `node --check web/app.js` | Passed |
| `git -c core.safecrlf=false diff --check` | Passed |
| `git -C .local/opentelemetry.io diff --check` | Passed |
| `py -3.11 -m hivemind.demo` | Separate synthetic fixture passed all 13 assertions |
| Independent Git demonstration in memory and FalkorDB | Branch isolation, verified integration and publication explanation passed |
| Service process restart, fresh HTTP login and recall | Version 0.2.0 returned the saved OpenTelemetry revision |
| Served UI HTML | Repository, checkout, findings and provenance controls present; no visual/layout claim |

Live test command in PowerShell:

```powershell
$env:HIVEMIND_LIVE_TESTS='1'
$env:FALKORDB_HOST='127.0.0.1'
$env:FALKORDB_PORT='6380'
$env:FALKORDB_GRAPH='hivemind_git_final_tests_20261018_v2'
.venv/Scripts/python.exe -m unittest discover -s tests -p '*live.py' -q
```

The server was the existing `falkordb/falkordb:6.0.2` container on port 6380;
the isolated graphs are separate from the older OpenTelemetry and RollbackWitness
graphs. Python client `falkordb==1.2.0` was installed in the project-local venv.
The legacy live suite resets only the explicitly selected test graph.

The real-Git fixture covers same-commit branch isolation, same-branch teammate
WIP, fast-forward and normal integration, no retroactive publication of later
learning, scoped corrections, applicable conflicts, separate task checkpoints,
concurrent duplicate delivery, concurrent revisions, source changes, deterministic
rebase/squash mapping, ambiguous mapping, ref recreation and preserved history,
an actual shallow clone that deepens without rewriting commit metadata,
credential/path exclusions and the complete serialized context budget.

Bridge/HTTP tests cover fresh cross-client MCP transports, reverse-direction
writes, project scope, viewer denial, durable token revocation, offline capture
followed by switching branches before retry, and duplicate-safe recovery.
These are transport and deterministic behavior tests, not native model sessions.

The live ablation retains facts and metadata while removing PARENT/PUBLISHES
relationships in the fixture-owned project. Inherited recall and its inheritance
explanation disappear. The old Juniper support/exposure/correction regressions
continue to pass separately.

## OpenTelemetry checkout

`workflow.py opentelemetry` verified the actual dependency guide, saved a
source-bound finding through the new bridge/HTTP service, and recalled it using
a fresh bridge. It did not replace the previous trial's client configuration.

- Repository HEAD: `5c42532e37db75bdd0ffbf158ff088fb774f4492`.
- Finding revision: `revision:cac91e8608e82ff2`.
- Source: `content/en/site/build/dependencies.md`.
- Isolated project: `project:3b71ed2564a6c2b5`.
- Original uncommitted patch SHA-256 before and after:
  `761cddbf99f7ab93ddc411f8361b932438d423854432c3379a3f8d95c38b8dda`.
- The same revision remained available after stopping and restarting the actual
  HTTP service process. The patch hash was checked again and remained identical.
- The bounded history and manifest correctly reported incomplete coverage for
  this large repository. The explicitly referenced source matched.

This was deterministic integration validation with no model calls. No new site
build, lint run, Git integration, or model-driven source edit is claimed here.
The older explicit-notes handoff and its four-line uncommitted patch remain
intact under `testing/opentelemetry/` and `.local/opentelemetry-test/`.

## Equal-information comparison

`python -m hivemind.git_demo` compares three independent deterministic selection
cases: other branch at the same commit, source branch, and integrated destination.
Both systems receive the same 15 records, nine relationships, source facts,
metadata and traversal access. The capable source-linked notes control implements
a provenance index and ancestry traversal. It is permitted to succeed.

| Measurement | HiveMind | Capable source-linked notes |
| --- | --- | --- |
| Correct selection cases | 3 / 3 | 3 / 3 |
| Model calls / model token budget | 0 / 0 | 0 / 0 |
| Same-format selected fact context | 307 characters | 307 characters |
| Memory-mode median retrieval | 0.073 ms | 0.006 ms |
| FalkorDB-run median retrieval | 5.315 ms | 0.021 ms |

HiveMind's complete recall envelope was 1,284 characters, approximately 321 tokens,
including provenance, applicability and completeness. The control timings use its
in-process index; HiveMind's live timings include database requests. These are
warm local tool timings, not an equal-infrastructure database performance study.
Neither system used a model, and the character estimates are not measured model
usage. Both received the same automatically prepared fixture. Human preparation
and review effort were not measured. This small comparison demonstrates parity,
not superiority, causal usefulness, demand or production economics.

## Pending acceptance and operational limits

The prepared native fixture is `.local/git-memory/native-fixture`. Adapter
preparation recorded Codex 0.163.0 and Claude Code 2.1.302. JSON/TOML schemas and
hook payload/output handling are covered by tests. Codex local MCP discovery did
not expose the untrusted project entry; native project/hook review remains a real
prerequisite, and no bypass flag or trust-record mutation was used. The user
explicitly chose to leave native proof pending. Follow [README.md](README.md)
to complete fresh ordinary-prompt sessions in both directions after review.

The workspace UI was served and JavaScript parsed successfully. No browser was
available for screenshots, interaction, responsive-layout or visual inspection.

The bridge defaults to 64 commits and 128 prioritized paths, with explicit
incompleteness; supported maxima are 256/2,048 and ancestry depth 256. Repository
pages cap at 1,024 candidates with sentinel completeness. Cross-clone branch
joining is explicit to avoid guessing branch identity from names. Memory-mode
service state is ephemeral; use FalkorDB for durability. Private-path/credential
exclusion is a bounded capture safeguard, not full DLP or remote Git attestation.

Machine-readable run artifacts are retained in ignored `.local/git-memory/`:
`demo-memory.json`, `demo-falkordb.json`, `opentelemetry-result.json`, and
`restart-result.json`. Tokens/configuration stay in ignored local storage.
