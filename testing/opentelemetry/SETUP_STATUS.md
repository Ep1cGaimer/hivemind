# Trial setup status — 17 October 2026

Update, 18 October: the actual two-session model trial completed successfully.
See [RUN_RESULT.md](RUN_RESULT.md) for memory IDs, local patch, checks, and limits.

Repository: `open-telemetry/opentelemetry.io`, commit
`5c42532e37db75bdd0ffbf158ff088fb774f4492`.
Local branch: `hivemind/memory-trial`.

## Ready infrastructure

- Local repo and all ten pinned submodules checked out.
- HiveMind test app: `http://127.0.0.1:8772`, container `hivemind-otel-test`.
- Separate graph: `hivemind_opentelemetry_trial` on the existing pinned FalkorDB server.
- User-facing project: `project:e3022e4a967eb458`, **OpenTelemetry website trial**.
- Three source-linked bootstrap memories and one clearly labeled infrastructure probe.
- Private credentials/token files under git-ignored `.local/opentelemetry-test/`.
- Codex project config and writer/consumer launchers installed; CLI is logged in.
- Linux site tooling: container `otel-site-trial`, Node 24.21.0, npm 11.19.0,
  Hugo Extended 0.166.0, pinned root and theme dependencies installed.

## Checks performed

| Check | Result |
| --- | --- |
| Live HiveMind health | Passed; backend is FalkorDB. |
| MCP initialization and tools/list | Passed; eight tools advertised. |
| Project memory listing and write | Passed. |
| Recall through a new MCP process | Passed. |
| HTTP reads the MCP-written note | Passed. |
| Versioned edit | Passed; new version number returned. |
| Another project's HTTP memory endpoint | Correctly denied with HTTP 403. |
| HiveMind app restart and repeated setup | Project and saved memories retained. |
| Codex MCP configuration parsing | Passed; launcher exposes three workspace tools. |
| Target document formatting | Passed with pinned Prettier. |
| Direct Markdown validation | Passed: one file, zero issues, 13 custom rules. |
| Site `npm run build` | Passed with exit code 0, including all 11 languages and final HTML postprocessing. |
| Trial helper syntax | Python and PowerShell parsed successfully. |
| Target source/lock/submodule changes | None after setup and line-ending/index normalization. |

The upstream Markdown CLI exits successfully while reporting zero files in its
summary on this checkout. The direct wrapper in `check-doc.py` verifies the file
is actually linted using the checkout's pinned library, ancestor configuration,
and custom rules. It does not change upstream code or dependency pins.

The pinned upstream npm dependency audit reports five high-severity findings.
The audit output is saved locally in `.local/opentelemetry-test/npm-audit.json`;
no automated dependency upgrade or lockfile rewrite was performed.

Windows checkout preparation required LF shell scripts and Git long-path support.
The cloned sources and submodule commits remain unchanged. Git index metadata was
refreshed after switching between Windows and Linux tools.

## Evidence files and next action

Local machine-readable connection/metadata and smoke results are in
`.local/opentelemetry-test/`. The build log is `site-build.log` in that directory.
They are excluded from Git and from Docker build context.

The actual model-backed two-session trial has now run; its evidence is retained.
For a separate interactive run, start the writer with
`py -3.11 testing/opentelemetry/session.py writer`, then exit that conversation
and start the consumer with `py -3.11 testing/opentelemetry/session.py consumer`.
The prepared prompts handle source checks, memory creation/retrieval, a small
local documentation edit, validation, and a saved consumer outcome.
