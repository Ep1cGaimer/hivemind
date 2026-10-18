# OpenTelemetry website: real-repository HiveMind trial

This setup connects a local checkout of `open-telemetry/opentelemetry.io` to a
dedicated persistent HiveMind project. It prepares two separate Codex sessions:
one records source-linked findings; the next retrieves them and makes a small
documentation change. The launchers support interactive sessions and recorded
batch runs.

The first actual model-backed run completed on 18 October 2026:
[results and limits](RUN_RESULT.md). `verify-run.py` audits its retained evidence.

## Prepared locations

| Item | Location |
| --- | --- |
| Real repository | `../../.local/opentelemetry.io` |
| Local branch | `hivemind/memory-trial` |
| Checkout used for initial setup | `5c42532e37db75bdd0ffbf158ff088fb774f4492` |
| HiveMind UI/API | `http://127.0.0.1:8772` |
| HiveMind container | `hivemind-otel-test` |
| Persistent graph | `hivemind_opentelemetry_trial`, in the existing `hivemind-falkordb` server |
| Site tooling container | `otel-site-trial` |
| Site toolchain | `node:24.21.0-bookworm`, npm 11.19.0, pinned Hugo Extended 0.166.0 |
| Private runtime settings | `../../.local/opentelemetry-test/runtime.env` |
| Agent token and project ID | `../../.local/opentelemetry-test/connection.json` |
| Machine-readable smoke report | `../../.local/opentelemetry-test/smoke-result.json` |

The entire `.local/` tree is ignored by the HiveMind repo. The target repo's local
Git exclude also hides its generated `.codex/config.toml` and `.hivemind/` prompt
copies. The MCP configuration contains a Docker command, not a token. The bridge
reads the token from a private mounted file inside the HiveMind container.

## Start the actual two-session test

Run these commands from the HiveMind repository root, in separate sessions:

```powershell
# Session 1: inspect source and save a handoff through MCP.
py -3.11 testing/opentelemetry/session.py writer
```

After the writer finishes, exit that Codex conversation. Start a fresh one:

```powershell
# Session 2: retrieve the handoff, verify it, make one local doc edit, and validate.
py -3.11 testing/opentelemetry/session.py consumer
```

Alternatively use `start-session.ps1 -Stage writer` or `-Stage consumer`.
Both launchers pass the prepared prompt and MCP settings to the installed Codex
CLI. They preserve native argument quoting on Windows. They do not select a new
model or change your account configuration.

The repo also has a project-scoped `.codex/config.toml`. Opening the checkout in
Codex normally can use it after project trust. The launcher passes explicit MCP
overrides so the test does not depend on that configuration already being trusted.
Official reference: [Codex MCP configuration](https://developers.openai.com/codex/mcp/).

### The task

The writer investigates contributor setup and validation rules, checks sources,
and writes **Writer handoff: contributor setup and validation** to HiveMind.
The consumer must retrieve that note before editing
`content/en/docs/contributing/development.md`, verify it against the current code,
make one useful clarification, and save **Consumer outcome: contributor setup
clarification** with the actual memory ID/version used and check outcomes.

The prompts are [session-1-writer.txt](session-1-writer.txt) and
[session-2-consumer.txt](session-2-consumer.txt). They explicitly keep the work
local. A later independent run can compare the same task against ordinary notes;
this setup alone does not establish an improvement over those alternatives.

### Project scope, branch scope, and memory capture

This branch isolates the Git edit, not the HiveMind memory collection. The current
workspace stores notes by `workspace_project_id`; it does not automatically detect,
filter by, or switch with a Git branch. The trial's token selects one project on
every branch. Commit references in note bodies are useful provenance text, not
enforced branch visibility. Separate projects/tokens can be used as a manual
workaround when separate branch collections are needed.

Memory capture is explicit: the writer prompt instructs the assistant to call
`create_memory`. No Git hook, transcript summarizer, automatic indexing job, or
automatic source-to-evidence extraction is installed. The workspace tool path
lists project notes; this trial does not exercise vector retrieval or the separate
structured evidence gateway and cannot prove a Graph RAG advantage.

For automated runs, `session.py writer --batch` and `session.py consumer --batch`
start separate ephemeral Codex sessions and retain JSONL events/final messages in
the private state directory. Existing evidence files are not overwritten. The
batch runner uses the current configured model/provider and requires the local
execution permissions already authorized for this trial.

## Inspect the memories in the browser

Open `http://127.0.0.1:8772`, sign in as `operator`, and select **OpenTelemetry
website trial**. Its generated local password is available on your computer:

```powershell
# Displays the password locally; do not paste it into a commit or shared report.
(Get-Content .local/opentelemetry-test/runtime.env |
  Where-Object { $_ -like 'HIVEMIND_OPERATOR_PASSWORD=*' }).Split('=', 2)[1]
```

Three bootstrap memories describe the source authority, install/build scope, and
validation boundaries. They cite the actual checkout's files and commit. They
are manually checked workspace notes, not automatic semantic evidence graphs.
The **MCP persistence probe** memory is infrastructure-only and should be ignored
when judging the documentation task.

## Verify or resume the infrastructure

```powershell
py -3.11 testing/opentelemetry/trial.py status
py -3.11 testing/opentelemetry/trial.py smoke
py -3.11 testing/opentelemetry/session.py check
```

The smoke check exercises initialization, eight advertised tools, project-scoped
memory listing, an MCP write, recall in a new MCP process, HTTP visibility of the
same write, and a versioned edit. Repeating it updates the one probe memory and
adds another immutable version. It does not reset the graph or impersonate an
independent model experiment.
It also verifies that the project token is denied access to another project's
HTTP memory endpoint.

The installed Codex configuration enables only the three workspace tools:
`list_memories`, `create_memory`, and `edit_memory`. The other five advertised
tools operate on the synthetic evidence scenario and are outside this trial.

To restart stopped services:

```powershell
docker start hivemind-falkordb hivemind-otel-test otel-site-trial
```

If the graph server was explicitly stopped, start it before running setup:

```powershell
py -3.11 testing/opentelemetry/trial.py setup
```

This setup command reuses its private environment file, project, and token. It
does not rotate the credentials or clear existing memories. It expects the
already available `hivemind:live` app image, FalkorDB on port 6380, and the cloned
repo. On another machine, first build that image with
`docker build --build-arg HIVEMIND_PROFILE=live -t hivemind:live .` and start the
documented isolated FalkorDB server from the project README.

## Run checks on an edit

Site dependencies and checks run inside Linux Docker; host Node/npm are not used.

```powershell
docker exec otel-site-trial npm exec --no -- prettier --check content/en/docs/contributing/development.md
docker exec otel-site-trial npm exec --no -- markdownlint-cli2 content/en/docs/contributing/development.md
py -3.11 testing/opentelemetry/check-doc.py
docker exec otel-site-trial npm run build
```

Report the exit code and substantive output. A check reporting zero linted files
or skipped public tests is not evidence that those files or a build were tested.
The `check-doc.py` wrapper runs Prettier and directly invokes the checkout's pinned
Markdown linter with its ancestor configuration and 13 custom rules, asserting
that the target file is present in the lint results. It covers the observed
zero-file reporting problem without changing the upstream dependencies or config.
Use the baseline recorded in [SETUP_STATUS.md](SETUP_STATUS.md) to distinguish
existing checkout issues from a regression introduced by the test edit.

To serve the website interactively from another terminal:

```powershell
docker exec -it otel-site-trial npm run serve -- --bind 0.0.0.0
```

Then open `http://127.0.0.1:1313`. This is the OpenTelemetry site, separate from
the HiveMind UI at port 8772. The site server runs until you stop that command.

`setup-site.ps1 -Build` can reinstall the pinned site dependencies and build.
For a fresh clone on Windows, clone with `git -c core.autocrlf=false -c
core.longpaths=true clone --depth 1 ...` and initialize submodules with the same
two options: the Linux tooling needs LF shell scripts, and some Java paths exceed
Windows' default Git path limit.

## Score the real trial

| Question | Evidence to retain |
| --- | --- |
| Did the writer persist useful knowledge? | Saved memory ID, version, exact file references, and observed scope. |
| Did the fresh session retrieve it? | MCP `list_memories` call before planning, with the writer's memory returned. |
| Did it affect the work? | A concrete edit decision explained using that note and verified source. |
| Was the result correct? | Focused checks, local diff, and honest baseline/skip reporting. |
| Did the consumer persist an outcome? | Consumer memory cites the writer's exact memory/version and real validation. |

Keep transcripts from the writer and consumer separate. Do not give the consumer
the writer's conversation. Both sessions may inspect the same repository, which
is expected: current source should remain the authority when memory is stale.
No model-backed writer/consumer run is claimed by the infrastructure smoke test.

## Stop the two trial containers

```powershell
docker stop hivemind-otel-test otel-site-trial
```

The graph, named volumes, checkout, and local credentials are preserved. The
existing FalkorDB service also supports other local work, so stopping the trial
does not stop or delete that shared server.
