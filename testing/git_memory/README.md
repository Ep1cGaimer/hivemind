# Git-aware proof workflow

The independent fixture lives in `tests/test_git_memory.py`; no expected answer
labels are passed into the runtime. `test_git_live.py` repeats the contract against
FalkorDB and includes graph relationship ablation and restart durability.
`test_git_bridge_http.py` exercises cold MCP transports, permissions, revocation,
and an outage followed by a branch switch before retry.

Run `python -m hivemind.git_demo` for a deterministic branch/integration walkthrough
and equal-information source-linked notes control. Set the live profile to run it
against FalkorDB. It makes no model calls, so its output is not native-client proof.
See [RESULTS.md](RESULTS.md) for the recorded runs and limits.

## Native Codex and Claude Code sessions

Start a durable service (use an isolated development graph and your own credentials):

```powershell
$env:HIVEMIND_BACKEND='falkordb'
$env:FALKORDB_HOST='127.0.0.1'
$env:FALKORDB_PORT='6380'
$env:FALKORDB_GRAPH='hivemind_git_workflow_20261018'
.venv/Scripts/python.exe -m hivemind.api --port 8773
```

`workflow.py` defaults to the loopback development login `operator` / `operator`.
Set `HIVEMIND_TRIAL_PASSWORD` for a different configured operator password.

```powershell
.venv/Scripts/python.exe testing/git_memory/workflow.py prepare
cd .local/git-memory/native-fixture
codex
```

Review the project configuration and `/hooks`; trust the exact installed
definitions through the client's native interface. Then review Claude Code's
project/MCP connection through its native interface. The installer never edits
trust records or uses trust-bypass flags. Installed versions in the recorded
preparation were Codex 0.163.0 and Claude Code 2.1.302.

Use ordinary prompts, without requesting memory writes. For example:

1. Codex writer: “Read guide.txt and worker.py. Explain the queue constraint and
   identify one validation step before using shared queues. Leave files unchanged.”
2. Exit. Fresh Claude consumer: “Would an unbounded shared queue be suitable here?
   Give a source-grounded recommendation for this checkout.”
3. Claude writer: “Inspect the current queue limit. Explain what remains untested
   and propose the next focused validation step. Leave files unchanged.”
4. Exit. Fresh Codex consumer: “What should I verify before changing the queue
   behavior? Use the current project context and explain any uncertainty.”

Record actual MCP calls and the automatically created finding/checkpoint or
no-change receipt, fresh session IDs, retrieval before decisions, exact revisions,
source bindings and graph explanation. Do not give a consumer the writer's prompt,
transcript, or final output. Continue with source-branch versus same-commit-main
and verified integration scenarios from the independent fixture. Retain failed
captures and trust warnings as failures; do not label a replay as a model run.
At most one extra completion pass is requested. `python -m hivemind status --repo .`
reports capture warnings and pending/rejected deliveries.

**Current state:** the OpenCode/Zen native proof now has a passing narrow smoke
workflow, a passing failed-approach three-condition pilot, and a 19/20 frozen
reliability batch. Codex/Claude native model-session proof remains outside the
agreed acceptance run and is still pending. The prepared checkout and definitions
are concrete and reviewable. No hook trust was bypassed.

## Existing OpenTelemetry checkout

```powershell
.venv/Scripts/python.exe testing/git_memory/workflow.py opentelemetry
```

The default repository is `.local/opentelemetry.io`. The helper verifies actual
dependency-guide content, saves a source-bound finding, cold-recalls it through
the bridge/HTTP service, and checks that the complete existing binary patch hash
is unchanged. It writes evidence under ignored `.local/git-memory/`. It does not
install/replace that repository's earlier client adapters or alter its source
files, Git refs, submodules, or original trial evidence. This check uses no model.

The earlier `testing/opentelemetry/` trial remains a separate explicit-notes
handoff, including its original four-line uncommitted patch. Do not present it as
evidence of the new automatic capture hooks.
