# HiveMind — resume point

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
