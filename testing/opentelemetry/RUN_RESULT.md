# Real-repository handoff result — 18 October 2026

**The functional writer-to-fresh-consumer handoff passed.** Two independent,
ephemeral Codex CLI sessions used the configured HiveMind MCP server against the
persistent OpenTelemetry trial project. No model or provider override was added.

The test used local Git branch `hivemind/memory-trial` at base commit
`5c42532e37db75bdd0ffbf158ff088fb774f4492`. The four-line result remains local
and uncommitted; no push, PR, or publication occurred.

## Observed sequence

1. The writer retrieved the bootstrap notes, inspected the repository's tooling
   and contributor guidance, and executed focused checks. It left source files
   unchanged and saved **Writer handoff: contributor setup and validation**
   through MCP `create_memory`.
2. A new consumer thread called MCP `list_memories` before editing and received
   the exact writer note/version. The recorded commands do not access the writer
   transcript, final response, or writer prompt file.
3. The consumer checked the handoff against the current dependency guide and
   package manifests. It added one contributor-setup clarification about retaining
   optional dependencies, including the Sass platform compiler.
4. Its first formatting check failed. It formatted only the target document and
   reran the checks successfully, then saved **Consumer outcome: contributor
   setup clarification** through MCP, citing the writer's exact memory ID/version.
5. The verification helper confirmed both records through the project's HTTP API,
   the distinct completed thread IDs, retrieval before editing, the intended
   single-file diff, and successful direct document checks.

## Persistent records

| Record | ID | Version |
| --- | --- | --- |
| Writer handoff | `memory:workspace:dfe49fe5fcea9a92:v1` | 1 |
| Consumer outcome | `memory:workspace:5747eaaba2352cf2:v1` | 1 |

Project: `project:e3022e4a967eb458`, **OpenTelemetry website trial**.
Open `http://127.0.0.1:8772` to inspect these notes in the workspace.

## Local patch

Only `content/en/docs/contributing/development.md` changed, after its local
dependency-install explanation:

```diff
+    Keep optional dependencies enabled in your npm configuration, and don't use
+    `--omit=optional` or `--no-optional`. They include platform binaries, such
+    as the Sass compiler, that the site build requires.
+
```

The source requirement is documented in
`content/en/site/build/dependencies.md:21-23` of the tested checkout. The consumer
also inspected the optional platform packages in the committed lockfile. No
lockfile, translation, submodule pointer, or unrelated source file changed.

## Validation

- Final Prettier check: passed after correcting the initial wrapping issue.
- Direct Markdown wrapper: one file checked, zero issues, 13 repository custom rules.
- CSpell: one file checked, zero issues.
- Textlint and host `git diff --check`: passed.
- Upstream Markdown CLI: exit 0 but reports zero files in its summary; it is not
  counted as evidence of lint coverage. The direct wrapper supplies that check.
- Writer's tests against the existing generated site: nine passed, none skipped.
- Writer's isolated copy of the public tests without generated output: all three
  suites skipped with a successful exit. This demonstrated the skip trap while
  preserving the original site output.
- No fresh install, site build, or link check was performed by either model
  session. The earlier successful baseline build belongs to the setup report;
  it is not a post-edit build result.
- `py -3.11 testing/opentelemetry/verify-run.py`: all seven recorded handoff checks
  passed. Both saved memory records were retrieved through the live project API.

Raw JSONL events, final messages, memory snapshots, `consumer.patch`, and
`run-result.json` are retained under the Git-ignored
`.local/opentelemetry-test/` directory. Existing batch evidence is not overwritten.

## What this establishes, and what remains absent

This establishes working explicit MCP memory writes, persistence, retrieval in a
fresh agent thread, source verification, a local documentation edit, and an
outcome note referencing the handoff. There was no control run without memory,
so it does not establish a causal usefulness improvement.

**Memory is project-scoped, not Git-branch-scoped.** The test branch isolates
the Git patch. Switching branches does not change the token's project or filter
workspace notes. There is no native branch/commit visibility field in
`WorkspaceMemory`; commit references in note bodies are text. Separate projects
and tokens are a manual isolation option until branch-aware scope is implemented.

**Memory writes are explicit.** These prompts required the assistant to call
`create_memory`. The application has no background transcript capture, Git hooks,
automatic summarization, or automatic source-to-evidence extraction installed.

**This is not a Graph RAG comparison.** The workspace tool lists project notes;
this trial did not exercise vector retrieval or the separate structured evidence
gateway. Notes do not automatically gain claims, reviewed scopes, or transitive
support edges. FalkorDB storage alone does not demonstrate better retrieval than
regular RAG. A fair comparison would need the same facts, source preparation,
model and budget, and an independent task whose outcome depends on those
relationships.
