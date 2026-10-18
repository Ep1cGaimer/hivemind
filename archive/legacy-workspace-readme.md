# HiveMind

**A simple shared memory workspace for people and coding agents.**

HiveMind is the separate Track 2 + Track 3 concept for the WeMakeDevs × FalkorDB
Graph Hacks 2026 event. One role agent records a qualified learning; a later,
cold role retrieves the learning, follows its evidence and scope, asks about a
missing condition, and changes a concrete local draft without seeing the old chat.

This checkout contains a usable project workspace: sign in, create projects,
view each project's memory graph, edit memories by hand, add configured people,
and mint a project-scoped bearer token for each coding agent. The HTTP API and
MCP server expose the same project memory, with an in-memory default and an
opt-in live FalkorDB backend. The underlying evidence graph remains available
for the agent layer, but the primary UI does not require users to understand
graph internals.

## Product in one minute

HiveMind has one primary job: give a team project-based memory and give each
coding agent a direct, identity-bound connection to the right project.

People sign in, create a project such as “Platform migration,” and use its
interactive memory graph to write and update context. Project owners can add
configured workspace users as editors or viewers. A project owner can mint a
separate project-scoped token for Claude Code, Codex, Cursor, or any other tool
that can call HTTP or MCP.

The evidence graph underneath preserves the older qualified-memory behavior for
agent workflows, but it is an implementation detail. The main screen is a
memory list and editor, not a graph inspector. No route sends messages,
deploys code, changes contracts, or performs another irreversible action.

## Start here

For a complete illustrated overview, read [`PROJECT_SUMMARY.md`](PROJECT_SUMMARY.md):
architecture, worked examples, Mermaid diagrams, setup, API/MCP usage, and current limitations.

For the prepared real-repository MCP trial, see
[`testing/opentelemetry/README.md`](testing/opentelemetry/README.md).

1. [`agent.md`](agent.md) — implementation and review constraints.
2. [`HIVEMIND_IDEA.md`](HIVEMIND_IDEA.md) — product pitch, user, workflow, demo,
   graph model, scope and rejection criteria.
3. [`HIVEMIND_GRAPH_CONTRACT.md`](HIVEMIND_GRAPH_CONTRACT.md) — identities,
   nodes, edges, provenance, scopes, versions and bounded graph operations.
4. [`HIVEMIND_DECISION_MEMO.md`](HIVEMIND_DECISION_MEMO.md) — conditional
   recommendation, strongest objection, validation experiment and gates.
5. [`HIVEMIND_POSITION_LEDGER.md`](HIVEMIND_POSITION_LEDGER.md) — recorded
   positions and dissent.
6. [`STATUS.md`](STATUS.md) — current authorization and next step.

The [`archive/`](archive/) folder contains the historical concept-generation,
scoring, attack, repair and paper-review record. It is auditable reference
material, not implementation instructions or runtime evidence.

## Runtime profiles and prerequisites

The default profile is intentionally dependency-light:

- Python standard library only for the backend, UI server, MCP server, and tests.
- Python 3.11 is the local runtime baseline. The container runtime is pinned to
  `python:3.11.11-slim-bookworm` in [`Dockerfile`](Dockerfile).
- GNU Make is needed for the provided commands.
- Node.js is needed only for the JavaScript syntax check in `make check`; Node
  18 or newer is suitable.
- No FalkorDB server is required for memory mode.
- The live profile additionally needs `falkordb==1.2.0` from
  [`requirements.lock`](requirements.lock) and a FalkorDB 6.0.2 server.

For an isolated local setup, use a project-local virtual environment. The base
requirements file is intentionally empty of third-party packages, so this step
does not need network access:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install --require-virtualenv --no-deps -r requirements.txt
```

Use the local interpreter explicitly for the offline profile:

```bash
PYTHON=.venv/bin/python make test
PYTHON=.venv/bin/python NODE=node make check
```

The `.env.example` file contains non-secret local and live-profile settings.
The HTTP and MCP entry points read the process environment, but do not
automatically load a `.env` file. An unset or blank value, or an explicit
`memory`, selects the seeded offline fixture. An explicit `falkordb` selection
requires `FALKORDB_HOST`, `FALKORDB_PORT`, and `FALKORDB_GRAPH`, connects to
that graph, checks it with a bounded query, and seeds the fixture idempotently.
It never silently falls back to memory. Pass `HOST`, `PORT`,
`HIVEMIND_BACKEND`, the `FALKORDB_*` values, or `PYTHON` directly to Make as
needed. If `HIVEMIND_API_KEY` is set in the process environment, mutating HTTP
routes require the matching `X-HiveMind-Key` header.

## Commands

| Command | Purpose |
| --- | --- |
| `make test` | Run the offline standard-library unittest suite. |
| `make test-live` | Run the opt-in live FalkorDB suite against the configured graph. |
| `make check` | Compile Python, check `web/app.js` syntax with Node, then run `make test`. |
| `make run` | Serve the local HTTP API and UI on `127.0.0.1:8000`. |
| `make mcp` | Run the newline-delimited JSON-RPC MCP server on stdin/stdout. |

Overrides are available without editing files:

```bash
make run HOST=0.0.0.0 PORT=8000
make run HIVEMIND_BACKEND=memory
make mcp HIVEMIND_BACKEND=memory
PYTHON=.venv/bin/python make run
HIVEMIND_LIVE_TESTS=1 PYTHON=.venv/bin/python FALKORDB_HOST=127.0.0.1 FALKORDB_PORT=6380 FALKORDB_GRAPH=hivemind_live_gateway make test-live
```

## Run the local API and UI

Start the dependency-free server:

```bash
make run
```

Open <http://127.0.0.1:8000/>. Sign in with the configured local workspace
credentials, create a project, select it, and use the memory graph. The project
page has **Add memory**, **People**, and **Connect agent** actions. The default local account
is `operator` / `operator`; set `HIVEMIND_OPERATOR_PASSWORD` before sharing the
server.

The same app can be run in a container:

```bash
docker build -t hivemind:local .
docker run --rm -p 8000:8000 hivemind:local
```

The container binds the server to `0.0.0.0:8000`; the browser URL remains
<http://127.0.0.1:8000/> on the host. The image copies only the Python package,
static UI, and dependency manifests needed by the local app.

## HTTP endpoints

All JSON API success and error responses are JSON objects. Invalid requests use
an envelope such as `{"ok":false,"error":{"code":"...","message":"..."}}`.
The canonical scope IDs used by the HTTP/MCP surfaces are:

- `scope:juniper:reserved-pool`
- `scope:juniper:shared-pool`

### `GET /health`

Returns process health and reports the selected backend (`memory` by default):

```json
{
  "ok": true,
  "service": "hivemind",
  "version": "0.1.0",
  "backend": "memory",
  "falkordb_adapter": {"optional": true, "server_checked": false}
}
```

For `backend: "falkordb"`, startup and this endpoint run a bounded fixed
`RETURN 1` query against the configured graph and report
`server_checked: true, reachable: true` only after it succeeds. A later server
failure returns a structured health failure; the process does not switch to
memory.

### `POST /api/auth/login`

Request:

```json
{"username":"operator","password":"operator"}
```

Sets an HTTP-only session cookie. Credentials come from
`HIVEMIND_OPERATOR_PASSWORD` or the optional `HIVEMIND_USERS` setting.

### `GET /api/workspace`

Requires the session cookie or `Authorization: Bearer <agent-token>`. Returns
the signed-in user and the latest version of each shared workspace memory.

### Project routes

The primary product API is project-scoped:

- `GET /api/projects` — list projects available to the signed-in user.
- `POST /api/projects` — create `{name, description}`; the creator becomes owner.
- `GET /api/projects/<project_id>` — project details and members.
- `GET /api/projects/<project_id>/graph` — memory/person graph data for the UI.
- `GET/POST /api/projects/<project_id>/memories` — list or create memories.
- `PATCH /api/projects/<project_id>/memories/<memory_id>` — edit a memory version.
- `GET/POST /api/projects/<project_id>/members` — inspect or add configured users.
- `GET/POST /api/projects/<project_id>/agents` — inspect or create project tokens.

Project roles are `owner`, `editor`, and `viewer`. Project tokens are scoped to
one project and cannot be used against another project.

### `POST /api/memories`

Requires identity. Creates a memory from `{title, body, tags}` and returns its
versioned record.

### `PATCH /api/memories/<memory-id>`

Requires identity. The owner or an operator can edit a memory. Editing creates a
new version and keeps the prior version immutable.

### `POST /api/agents`

Requires a human session. Request `{"label":"Claude Code"}` to create a
signed bearer token. The full token is returned once; use it in a coding agent
with `Authorization: Bearer <token>` or as `HIVEMIND_AGENT_TOKEN` for the MCP
server.

### `GET /api/state`

Returns the lower-level gateway snapshot for diagnostics. The normal product
screen uses `/api/workspace` instead.

### `POST /api/reset`

Accepts `{}` and replaces the selected runtime's HiveMind fixture. In memory
mode this replaces the process-local graph. In live mode it clears only the
configured HiveMind graph's bound tenant/project data, then reseeds the
fixture; other configured graphs and the unrelated server are untouched.

### `POST /api/recall`

Request:

```json
{"scope_id":"scope:juniper:shared-pool"}
```

Returns the bounded memory versions, source passages, unknowns, exposure receipt,
support paths, review state, and scope-specific completeness metadata. A
shared-pool request before correction preserves the reserved-pool observation as
nearby evidence and reports the missing condition instead of claiming readiness.

### `POST /api/evidence`

Request:

```json
{"memory_id":"memory:juniper:overnight-refresh:summary-b:v1","max_depth":4}
```

Traverses only declared support relationships, with a maximum depth of four and
a bounded node cap. `READ_MEMORY` and `READ_PASSAGE` exposure edges are reported
separately and are never treated as semantic support.

### `POST /api/exposure`

Request:

```json
{
  "run_id":"run:external-agent:42",
  "memory_id":"memory:juniper:overnight-refresh:reserved:v1"
}
```

Records that an agent saw a memory. The resulting `READ_MEMORY` relationship is
an exposure receipt only and cannot become semantic support through recall.

### `POST /api/correction`

Request:

```json
{
  "base_memory_id":"memory:juniper:overnight-refresh:reserved:v1",
  "scope_id":"scope:juniper:shared-pool",
  "correction_text":"The supplied evidence does not establish shared-pool readiness; request a rehearsal before promising readiness.",
  "reviewer":"operator"
}
```

Creates or returns an immutable correction version for exactly that scope. The
correction is accepted only for the local `operator`/`demo-operator` reviewer
identity, must remain a bounded qualification, and is duplicate-safe. The base
reserved-pool memory is not overwritten and the correction does not leak into
the reserved scope. Changed wording for an existing immutable correction returns
a structured conflict.

### `POST /api/draft`

Request shape:

```json
{
  "scope_id":"scope:juniper:shared-pool",
  "title":"Juniper shared-pool walkthrough plan",
  "body":"Request a shared-pool rehearsal before promising readiness.",
  "citations":[{"memory_id":"<same-scope-memory-id>"}]
}
```

The citation list must contain exact memory-version or source-passage bindings in
the requested scope. The operation creates only a local draft and reports
`external_side_effect: false`.

### `POST /api/demo`

Accepts `{}` and runs the complete deterministic Juniper cold-agent walkthrough.
The response includes named `steps`, `correction`, `draft`, `assertions`, and
`state_counts` fields so the handoff can be inspected without parsing logs.

Static UI routes are `/`, `/index.html`, `/app.js`, and `/styles.css`.

## Coding-agent connection

After signing in, open a project, click **Connect agent**, name the agent, and copy the token.
The token is identity-bound and can use the memory tools without a browser
session:

```bash
curl -s http://127.0.0.1:8000/api/workspace \
  -H 'Authorization: Bearer <token>'
curl -s -X POST http://127.0.0.1:8000/api/memories \
  -H 'Authorization: Bearer <token>' \
  -H 'Content-Type: application/json' \
  -d '{"title":"Deploy note","body":"Run staging checks first.","tags":["deploy"]}'
```

## MCP stdio usage

`make mcp` starts a newline-delimited JSON-RPC server. It reads one request per
line from stdin and writes one response per line to stdout; diagnostics are not
written to stdout. The server starts with a deterministic fixture for each
process, using the selected backend (memory by default). The MCP `initialize`
response reports that backend in `serverInfo`; a live selection connects to and
seeds only its configured graph, while an unavailable or malformed live
configuration fails before the server starts.

For a complete initialize/list/recall exchange:

```bash
printf '%s\n' \
  '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"shell","version":"0"}}}' \
  '{"jsonrpc":"2.0","method":"notifications/initialized","params":{}}' \
  '{"jsonrpc":"2.0","id":2,"method":"tools/list","params":{}}' \
  '{"jsonrpc":"2.0","id":3,"method":"tools/call","params":{"name":"recall_context","arguments":{"scope_id":"scope:juniper:shared-pool"}}}' \
  | make mcp
```

The fixed tool registry includes the human-facing workspace tools:

- `list_memories()`
- `create_memory(title, body, tags)`
- `edit_memory(memory_id, title, body, tags)`

It also retains the lower-level evidence tools for agents that need them:

- `recall_context(scope_id)`
- `inspect_evidence(memory_id, max_depth)`
- `record_exposure(run_id, memory_id)`
- `apply_correction(base_memory_id, scope_id, correction_text, reviewer)`
- `save_draft(scope_id, title, body, citations)`

The MCP boundary accepts no raw Cypher. Tool failures are returned as structured
results with `isError: true`; malformed JSON-RPC requests receive JSON-RPC error
objects. The stdio server is suitable for an AI assistant configured with a
command such as `make mcp` from the project root.

## Synthetic Juniper scenario and cold handoff

The fixture contains one synthetic company, Juniper; a source passage; a
reserved-worker-pool scope; a shared-worker-pool scope; one qualified base
memory; and two summaries that derive from the same source. The source says that
overnight refresh completed on the reserved pool and that shared-pool behavior
was not exercised. Repeated summaries are therefore not independent support.

To try the complete flow from a running server:

```bash
make run
# In another terminal:
curl -s http://127.0.0.1:8000/health | python3 -m json.tool
curl -s -X POST http://127.0.0.1:8000/api/demo \
  -H 'Content-Type: application/json' \
  -d '{}' | python3 -m json.tool
```

Or open the UI and click **Run cold handoff**. The server-side walkthrough does
the following:

1. Recalls the qualified reserved-pool memory and inspects its bounded source
   path.
2. Recalls the shared-pool scope and preserves the unresolved condition.
3. Creates an operator-reviewed immutable correction bound only to the shared
   pool.
4. Instantiates a fresh consumer gateway over the persisted selected graph,
   with no writer chat context.
5. Saves a local draft citing the correction and requesting a shared-pool
   rehearsal.
6. Checks that the correction is visible in the shared scope, absent from the
   reserved scope, and that read exposure is not support.

Use `POST /api/reset` or the UI **Reset** button to return to the initial fixture.
The UI's offline fallback is also synthetic and must not be confused with a
successful API or FalkorDB write.

## FalkorDB live profile

The default `InMemoryGraphStore` is selected by `make run`, `make mcp`, and the
local Docker command when `HIVEMIND_BACKEND` is unset, blank, or `memory`.
The live profile is selected explicitly with `HIVEMIND_BACKEND=falkordb` plus
`FALKORDB_HOST`, `FALKORDB_PORT`, and `FALKORDB_GRAPH`.

`hivemind.store.FalkorDBStore` implements the same gateway store contract as
the memory backend:

- importing `hivemind` does not import or require the optional `falkordb` client;
- the client is imported only by `FalkorDBStore.connect()` and selects the one
  configured graph;
- domain dataclasses are stored as canonical JSON and reconstructed exactly on
  read, including tuples and nested citation/qualifier mappings;
- node and relationship writes enforce tenant/project binding, immutable
  content, deterministic IDs, idempotency, endpoint existence, and fixed
  allowlists for labels and relationship types;
- reads are bounded and stable-sorted; corrections stay scoped, `READ_*`
  exposure stays separate from support, and draft citations remain exact;
- `run_fixed()` accepts only the trusted parameterized registry in
  `hivemind/queries.py`; there is no raw-Cypher escape hatch in HTTP, MCP, or
  the gateway;
- normal live startup seeds the Juniper fixture without clearing existing
  corrections/drafts, while the live reset path clears only the configured
  HiveMind graph's bound tenant/project data before reseeding;
- `GET /health` runs a bounded fixed server query for the live backend and does
  not fall back to memory when the server becomes unavailable.

The optional client pin is recorded in [`requirements.lock`](requirements.lock):

```bash
# Inside the project-local .venv, for the explicit live profile:
.venv/bin/python -m pip install --require-virtualenv -r requirements.lock
```

The live server image is FalkorDB `6.0.2`. The repository does not install the
server; the isolated local command is:

```bash
docker run -d --name hivemind-falkordb \
  -p 6380:6379 \
  -v hivemind-falkordb-data:/data \
  falkordb/falkordb:6.0.2
```

Run the opt-in live contract suite against that project-specific graph with:

```bash
HIVEMIND_LIVE_TESTS=1 \
PYTHON=.venv/bin/python \
FALKORDB_HOST=127.0.0.1 \
FALKORDB_PORT=6380 \
FALKORDB_GRAPH=hivemind_live_gateway \
make test-live
```

The live suite has been run against the isolated `hivemind-falkordb` container
and covers reset/seed, recall, evidence, exposure-vs-support, immutable scoped
correction, cited draft persistence, health/state, and a new store/gateway
instance. It does not establish product demand, model quality, retention
economics, or superiority over ordinary notes.

## Tests and validation boundaries

The independent offline tests use only the standard library and cover the public
contract, HTTP API, and MCP boundary, including scope isolation, evidence
reachability, immutable duplicate-safe correction, read-versus-support
separation, optional mutation authentication, safe invalid-input errors, and the
cold draft change. `make check` adds Python compilation and JavaScript syntax
validation. The offline suite contains 25 contract tests; the live module adds
seven opt-in tests and is skipped unless `HIVEMIND_LIVE_TESTS=1` is set.

The test fixture is synthetic and deterministic apart from the deliberately
unique session IDs in the compact demo contract. Passing offline tests establish
the memory-mode behavior. Passing `make test-live` establishes the exercised
client/server and persistence paths for the configured synthetic graph, not
product demand, model quality, retention economics, or a benchmark against chat
history.

## AI-assistant disclosure

This implementation and its reproducibility documentation were produced with AI
coding assistance in the OmniRush agent harness. The application itself does not
call an AI model: the local scenario, gateway, HTTP responses, MCP responses,
and tests are deterministic Python code. Synthetic data, optional integrations,
and unvalidated claims are labelled so a human operator can review them before
using the project with real data or an assistant.

## Product boundary

Keep the first slice centered on one user, one capability-planning workflow, one
graph-dependent question, one inspectable evidence path, and one before/after
local draft. Do not expand to broad connectors, a general enterprise-permissions
product, an autonomous swarm, or a large feature list before the cold-read gate
passes. The first gate remains a real write-and-cold-read comparison against
qualified, source-linked notes using identical information and comparable model
budgets. If ordinary notes provide equal useful work with less preparation, the
HiveMind product argument should be rejected.
