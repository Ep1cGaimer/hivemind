# HiveMind

Git-aware shared memory for coding agents.

HiveMind helps OpenCode carry useful project knowledge between separate coding
sessions. It connects findings and unfinished work to the exact repository,
branch, commit, snapshot, and source files where they were observed.

## Why HiveMind?

Coding agents often rediscover the same constraints after a context reset. HiveMind
stores useful findings in a graph and only recalls them when the current Git
context makes them relevant.

It is designed to answer questions like:

- What did the previous agent learn about this repository?
- Does that finding still apply on this branch and commit?
- Where did the finding come from?
- What work was left unfinished?

## How it works

1. Connect a local Git repository to a HiveMind project.
2. Before an OpenCode task, HiveMind recalls applicable project memory.
3. OpenCode works normally with its native permissions.
4. After the task, HiveMind records a finding, checkpoint, or explicit no-change result.
5. A new OpenCode session can use that context without sharing the old chat.

HiveMind does not replace Git, OpenCode, or your model provider. It adds a
Git-scoped memory layer between them.

## Quick start

### Requirements

- Python 3.11+
- Git
- Node.js 18+ and npm for the pinned OpenCode command-line client
- Docker Desktop only if you want durable FalkorDB storage

### 1. Start HiveMind

From this repository:

```bash
python -m venv .venv
source .venv/bin/activate       # Windows: .venv\Scripts\Activate.ps1
python -m pip install -e .
python -m hivemind.api --port 8000
```

Open <http://127.0.0.1:8000>, sign in with the local development account
`operator` / `operator`, create a project, and choose **Connect agent**. Copy
the project ID and token.

### 2. Connect a repository

Clone or open the repository you want an agent to work on:

```bash
git clone https://github.com/OWNER/REPOSITORY.git
cd REPOSITORY
```

Use the Python environment where HiveMind is installed:

```bash
export HIVEMIND_AGENT_TOKEN=YOUR_PROJECT_TOKEN
python -m hivemind connect \
  --repo . \
  --url http://127.0.0.1:8000 \
  --project project:YOUR_PROJECT_ID \
  --client opencode
```

On PowerShell:

```powershell
$env:HIVEMIND_AGENT_TOKEN = "YOUR_PROJECT_TOKEN"
python -m hivemind connect `
  --repo . `
  --url http://127.0.0.1:8000 `
  --project project:YOUR_PROJECT_ID `
  --client opencode
```

This creates a project-local OpenCode plugin and private connection state under
`.git/hivemind/`. Do not commit the token.

### 3. Run two fresh sessions

From the HiveMind checkout, install the pinned OpenCode client:

```bash
npm ci
export HIVEMIND_OPENCODE_BIN="$PWD/node_modules/@opencode/cli/bin/opencode"
```

Return to the target repository before running the sessions. On Windows, point
`HIVEMIND_OPENCODE_BIN` at the equivalent absolute path ending in
`node_modules\@opencode\cli\bin\opencode.exe`.

Run a first session that creates useful memory:

```bash
python -m hivemind run \
  --repo . \
  --model opencode/deepseek-v4.1-flash-free \
  "Review this repository and identify one important implementation constraint."
```

Then run a new process and ask it to use the shared context:

```bash
python -m hivemind run \
  --repo . \
  --model opencode/deepseek-v4.1-flash-free \
  "Use the shared project memory and explain how I should safely continue this work."
```

Inspect the result with:

```bash
python -m hivemind status --repo .
```

Use the managed `hivemind run` command for this lifecycle. It keeps the native
OpenCode host alive through the bounded memory-capture pass.

## Durable local deployment

The default memory backend is convenient for a demo but is cleared when the
server exits. For durable local storage, start FalkorDB:

```bash
python -m pip install -e ".[live]"
docker compose up -d --wait
export HIVEMIND_BACKEND=falkordb
export FALKORDB_HOST=127.0.0.1
export FALKORDB_PORT=6380
export FALKORDB_GRAPH=hivemind_team_memory
python -m hivemind.api --port 8000
```

On Windows, use PowerShell environment syntax (`$env:NAME = "value"`) and
`.venv\Scripts\python.exe`. The Compose file pins FalkorDB 6.0.2 and persists
its data in a Docker volume.

## Graph model

HiveMind stores immutable Git-bound records such as repositories, commits,
branches, snapshots, sources, findings, checkpoints, and capture receipts.
Important relationships include:

- `PARENT` — bounded commit ancestry;
- `BRANCH_MEMORY` — memory observed on a branch incarnation;
- `PUBLISHES` — a finding published by a commit;
- `SUPPORTED_BY` — source files supporting a finding;
- `REVISES` — a later revision of applicable memory;
- `ACCEPTS` — a human-accepted promotion.

Recall combines ancestry reachability, branch scope, source applicability, and
revision rules. The full model is documented in
[`HIVEMIND_GRAPH_CONTRACT.md`](HIVEMIND_GRAPH_CONTRACT.md). The parameterized
Cypher queries live in [`hivemind/git_queries.py`](hivemind/git_queries.py), and
graph construction is in [`hivemind/git_graph.py`](hivemind/git_graph.py).

## Development

Run the offline test suite:

```bash
make test
```

Or on Windows without `make`:

```powershell
python -m unittest discover -s tests -p "test_*.py" -q
```

Run syntax checks and tests together with:

```bash
make check
```

## Project status

HiveMind is an experimental local-first integration for OpenCode 2. The
headless managed lifecycle, Git provenance, checkpoint handling, privacy
boundaries, and durable FalkorDB profile are covered by the included tests.
The interactive OpenCode TUI path is not the supported demo path yet.

## Demo and additional documentation

- [`DEMO.md`](DEMO.md) — short hackathon demo script and requirement mapping.
- [`HIVEMIND_GRAPH_CONTRACT.md`](HIVEMIND_GRAPH_CONTRACT.md) — graph data model.
- [`PROJECT_SUMMARY.md`](PROJECT_SUMMARY.md) — detailed architecture overview.
- [`testing/git_memory/ACCEPTANCE.md`](testing/git_memory/ACCEPTANCE.md) — test evidence and known limitations.
