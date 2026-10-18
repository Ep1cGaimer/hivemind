# Git-aware acceptance

`test_git_memory.py` creates an independent real Git repository; it tests
same-commit branch isolation, WIP, forward/normal integration, scoped revisions,
conflicts, checkpoints, deterministic rebase/squash mappings, ambiguous mappings,
ref recreation, actual shallow clone deepening, privacy and context budgets.
`test_git_bridge_http.py` verifies the HTTP/MCP bridge, token revocation, project
and viewer restrictions, cold cross-client transport and offline retry bindings.
`test_git_live.py` repeats the Git contract against pinned FalkorDB and tests
restart durability and relationship ablation. These deterministic tests do not
replace the separate OpenCode/Zen native proof in `testing/git_memory/ACCEPTANCE.md`;
they also do not prove Codex/Claude hook trust or lifecycle behavior.

Use `python -m unittest discover -s tests -q`. Live tests require
`HIVEMIND_LIVE_TESTS=1` and explicit isolated `FALKORDB_HOST`, `FALKORDB_PORT`,
`FALKORDB_GRAPH`, then `python -m unittest discover -s tests -p '*live.py' -q`.
The legacy live suite resets its configured graph. See
[the current proof report](../testing/git_memory/RESULTS.md).

# HiveMind behavior tests

The offline tests use only the Python standard library and exercise the public
memory gateway, HTTP API, and MCP tool surface. `test_falkordb_live.py` is an
opt-in suite for the live backend and is skipped by the normal test command.

```python
from hivemind import HiveMindGateway, run_demo, seed_demo_store

gateway = HiveMindGateway(seed_demo_store())
gateway.recall_context("scope:juniper:shared-pool")
gateway.inspect_evidence("memory:juniper:overnight-refresh:reserved:v1", max_hops=4)
gateway.record_exposure("run:external-agent", "memory:juniper:overnight-refresh:reserved:v1")
gateway.apply_correction(
    "memory:juniper:overnight-refresh:reserved:v1",
    "scope:juniper:shared-pool",
    correction_text="Request a shared-pool rehearsal before promising readiness.",
)
run_demo()
```

The suite covers:

- qualified reserved-pool evidence and shared-pool unknowns;
- bounded support paths to exact source passages;
- `READ_MEMORY` exposure remaining separate from support;
- immutable, duplicate-safe and scope-limited corrections;
- correction wording conflicts and safe invalid-input errors;
- cold-session recall and cited draft changes;
- HTTP state/demo/auth behavior;
- MCP tool registration, notifications, and structured calls;
- backend selection, normalization, startup fail-fast behavior, and the
  guarantee that a runtime reset does not change backend because the process
  environment changed.
- local sign-in, bearer-token agent access, shared-memory create/edit/readback,
  and MCP workspace tools.
- projects, project roles, project-scoped memories, graph responses, and
  project-scoped agent tokens.

Run from the project root with:

```bash
python -m unittest discover -s tests -p 'test_*.py' -v
```

Run the live suite only with an isolated FalkorDB server and an explicit
project-specific graph:

```bash
HIVEMIND_LIVE_TESTS=1 \
PYTHON=.venv/bin/python \
FALKORDB_HOST=127.0.0.1 \
FALKORDB_PORT=6380 \
FALKORDB_GRAPH=hivemind_live_gateway \
make test-live
```
