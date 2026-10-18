# Implementation and evidence disclosure

HiveMind extends the existing Python service, web workspace, MCP integration and
Juniper evidence regression in this repository. The Git bridge, immutable Git
memory model, publication/revision queries, recovery queue, project authorization
changes, OpenCode adapter and acceptance tools were developed here with AI coding
assistance. Independent AI subagents authored adversarial tests and synthetic
outcome fixtures. This is simulated review/testing, not human user research.

Reused components:

- Python's standard library supplies HTTP, SQLite, hashing and subprocess support.
- Git supplies object identities, clean-filter normalization, ancestry and patch
  identities. A connector observation records provenance; it is not independent
  proof that a model's interpretation is correct.
- FalkorDB 6.0.2 and its Python client 1.2.0 execute the central graph operations.
  Redis persistence and the Docker volume determine database crash durability.
- OpenCode's native version 2 plugin/session/tool/event APIs drive automatic recall
  and capture. The assistant's existing model selects memories. HiveMind does not
  implement a model, train one, or introduce a server-side summarizer.
- The workspace uses HTML, CSS and JavaScript. Syntax checks do not establish
  browser rendering, accessibility or usability.

Evaluation fixtures are small synthetic programs generated for this project.
Their independent expected outcomes stay outside the tested checkout. The capable
source-linked notes control retains the same actual facts, immutable revisions,
source identities and publication metadata; its independent provenance index is
a legitimate alternative. It is allowed to tie or outperform HiveMind.

The separately retained OpenTelemetry trial uses an upstream repository under its
own license. Local checkout data and the existing uncommitted patch remain
separate from product source. The historical Juniper scenario remains a synthetic
regression. Neither establishes a production deployment or real team adoption.

The acceptance ledger distinguishes deterministic checks, actual OpenCode/Zen
runs, simulated users, failures and missing evidence. Other native client adapters
are outside current end-to-end verification. No hackathon result, human adoption,
general model superiority, or untested integration is guaranteed.
