# Simulated first-time onboarding — 2026-10-18

This is one independent agent simulation, not human research or evidence of demand. It tests a fresh Python virtual environment on an existing Windows host, **not a fresh OS**. No implementation source, private answer fixtures, writer transcripts, STATUS file, or earlier reports were inspected. Initial material was README.md and goal.md B/I/J1; a bounded goal read accidentally included adjacent C and J rows. Those rows contained gate definitions, not implementation or expected fixture answers. No author coaching was used.

## Outcome

Fresh-environment dependencies installed and an isolated ephemeral server returned HTTP 200. Durable startup was blocked by the unavailable Docker Linux engine. The supplied CUA browser surface was also unavailable, preventing the documented login → create project → Connect agent/token flow. Consequently repository connection, useful recall, handoff, native trust, and rendered UI are **unproven**, not passes. No models were called. No existing containers, services, data, global client configuration, or OpenTelemetry files were changed.

README orientation was immediate: HiveMind serves teams using coding assistants that need accepted conventions, Git-sensitive findings, and resumable task checkpoints across conversations. This is a simulated README-level J1 positive observation, not a timed rendered-product test. From the README, a new finding belongs to its originating branch; inheritance needs observed publication/integration with matching sources. Same-branch WIP can appear with snapshot mismatch labels. Accepted conventions retain source conditions. I could explain these rules from prose but could not demonstrate recognizing real UI states (I1–I11).

## Environment and elapsed effort

- Host: Windows, PowerShell; workspace `C:/Vivek_projects/hivemind`.
- First recorded time: `2026-10-18T12:56:24.2715310+05:30`; substantive checks finished `2026-10-18T12:58:16.7390427+05:30` (~1m52s, plus report and cleanup).
- Python `3.11.0`; Git `2.47.1.windows.2`; OpenCode `2.0.29` already installed. OpenCode installation on a clean machine was not tested.
- Docker client `28.5.1`, context `desktop-linux`; server unavailable. CUA inventory returned `{"apps":[],"browsers":[]}`.
- Isolated files: `.local/usability/fresh-onboarding-20261018-1256/`; service port `8027`; attempted isolated Compose project `hivemind-fresh-onboarding-20261018-1256`, database port `6397`, graph `hivemind_fresh_onboarding_20261018_1256`.
- Pip used the host's existing wheel cache. Installed: falkordb 1.2.0, redis 5.3.1, python-dateutil 2.9.0.post0, six 1.17.0, PyJWT 2.15.1, async-timeout 5.0.1. This is dependency installation proof with cached artifacts, not cold-network installation proof.

## Exact attempted commands and results

Commands below ran from the HiveMind checkout except the explicitly marked target-repository checks. PowerShell environment changes were confined to the individual command processes. `python` in the README was mapped to the installed `py -3.11` for venv creation and the venv executable thereafter.

```powershell
py -3.11 --version
git --version
docker version --format '{{json .}}'
opencode --version
docker ps --format '{{.Names}} {{.Ports}}'
docker compose config
```

Docker version and ps failed: `open //./pipe/dockerDesktopLinuxEngine: The system cannot find the file specified.` Compose config rendered the pinned 6.0.2 image, loopback 6380 port, AOF settings and `/var/lib/falkordb/data` named-volume mount. No daemon was started or repaired.

```powershell
New-Item -ItemType Directory -Force -Path .local/usability/fresh-onboarding-20261018-1256
py -3.11 -m venv .local/usability/fresh-onboarding-20261018-1256/venv
.local/usability/fresh-onboarding-20261018-1256/venv/Scripts/python.exe -m pip install --require-virtualenv -r requirements.lock
$env:FALKORDB_PORT='6397'
docker compose -p hivemind-fresh-onboarding-20261018-1256 up -d --wait
```

Venv creation and requirements installation succeeded without fixes. Compose failed before startup with the same missing Docker pipe while obtaining the pinned image. The alternate port follows the README; the Compose project name is tester isolation, not a documented product prerequisite.

```powershell
.local/usability/fresh-onboarding-20261018-1256/venv/Scripts/python.exe -m hivemind.api --port 8027
(Invoke-WebRequest -UseBasicParsing http://127.0.0.1:8027).StatusCode
```

The offline server stayed running and returned 200. This was transport availability only; HTML was not inspected as a substitute for UI testing. CUA actions were exactly `await cua.getState()` and then `await cua.createBrowserTab("iab", "http://127.0.0.1:8027", { visible: true })`. The latter returned `Browser is not available: iab`. No alternate UI automation or native-trust bypass was used.

```powershell
$env:HIVEMIND_BACKEND='falkordb'
$env:FALKORDB_HOST='127.0.0.1'
$env:FALKORDB_PORT='6397'
$env:FALKORDB_GRAPH='hivemind_fresh_onboarding_20261018_1256'
.local/usability/fresh-onboarding-20261018-1256/venv/Scripts/python.exe -m hivemind.api --port 8028
```

Exited 1 with `HiveMind backend error [BACKEND_UNAVAILABLE]: Configured FalkorDB backend could not start safely: Could not construct the configured FalkorDB client: Timeout connecting to server; no fallback to memory was performed`. This honestly identifies the failing backend, although it does not tell a novice how to start/check Docker.

```powershell
.local/usability/fresh-onboarding-20261018-1256/venv/Scripts/python.exe -m hivemind --help
.local/usability/fresh-onboarding-20261018-1256/venv/Scripts/python.exe -m hivemind connect --help
New-Item -ItemType Directory -Force -Path .local/usability/fresh-onboarding-20261018-1256/tiny-repo/nested
Set-Content -LiteralPath .local/usability/fresh-onboarding-20261018-1256/tiny-repo/worker.py -Value 'def clamp_size(value):
    return max(1, value)'
git -C .local/usability/fresh-onboarding-20261018-1256/tiny-repo init -b main
git -C .local/usability/fresh-onboarding-20261018-1256/tiny-repo add worker.py
git -C .local/usability/fresh-onboarding-20261018-1256/tiny-repo -c user.name='Simulated Onboarding Tester' -c user.email='simulated-onboarding@example.invalid' commit -m 'Create tiny onboarding repository'
Remove-Item Env:HIVEMIND_AGENT_TOKEN -ErrorAction SilentlyContinue
.local/usability/fresh-onboarding-20261018-1256/venv/Scripts/python.exe -m hivemind connect --repo .local/usability/fresh-onboarding-20261018-1256/tiny-repo --url http://127.0.0.1:8027 --project project:SIMULATED_ONBOARDING --client opencode
```

The tiny repository committed as `134494b` on main. `project:SIMULATED_ONBOARDING` is explicitly a placeholder because project/token creation was blocked. Connect exited 1 with `{"ok": false, "error": "Set HIVEMIND_AGENT_TOKEN or reconnect with a project token"}`. Repeating connect with `$env:HIVEMIND_AGENT_TOKEN='simulated-invalid-token'` exited 1 with `{"ok": false, "error": "AUTH_REQUIRED: Sign in or provide a valid agent bearer token"}`. No valid connection or plugin installation is claimed. Top-level `--help` only advertises the API server options, while `connect --help` provides the documented connection options; subcommands are not discoverable from top-level help.

From **each** of the tiny repository root and its `nested` directory, ran:

```powershell
& 'C:/Vivek_projects/hivemind/.local/usability/fresh-onboarding-20261018-1256/venv/Scripts/python.exe' -m hivemind status
```

Both exited 1 with `No module named hivemind`. Installing requirements does not install the HiveMind module into this fresh venv. Running from the HiveMind checkout works, but the README does not clearly state the required working directory for subsequent CLI commands or provide a package-install step. I did not repair this using PYTHONPATH/editable install or inspect packaging source. This is concrete onboarding friction for B3; intended repository identity could not be assessed without a connection.

## Gate assessment and missing instructions

| Gate | Observed result |
| --- | --- |
| B1 | Partial: fresh venv dependencies/offline server succeed; supported durable profile blocked by host Docker engine. No fresh-OS pass. |
| B2 | Unproven: no token/connection/context; no claim of useful context within ten minutes. Test was blocked before generation, not a measured model-speed failure. |
| B3 | CLI from root/nested fails import in fresh venv; actual repository detection unproven. |
| B4–B7 | Unproven: no authenticated connection or client installation. |
| B8 | Missing/invalid token and unavailable backend errors are explicit. Docker-start recovery, unsupported OpenCode versions, missing Git and actual native-trust failures were not exercised. |
| I1–I11 | Blocked by missing CUA browser. No rendered, visual, keyboard, inspection, promotion, applicability, or handoff pass. |
| J1 | README explains audience/problem promptly to this simulated tester; rendered walkthrough unproven. |

Specific documentation gaps: clarify checkout/installation and CLI working directory; make subcommands discoverable from help; include Windows Docker engine readiness and recovery checks; explain how to install the required OpenCode 2 client rather than merely saying to install it. An unavailable testing browser is an environment/tool limitation, not itself an application defect. No undocumented repair was performed. No broad unit suite was used as onboarding evidence.

Cleanup: stopped only this test's service session with Ctrl-C. `Get-NetTCPConnection -LocalPort 8027 -State Listen -ErrorAction SilentlyContinue` showed no listener. Final report/cleanup check was around `2026-10-18T12:59:18+05:30` (~2m54s after the first timestamp). Isolated venv/repository artifacts remain for review; no database or Compose volume was created.

## Coached installation regression retest

This separate follow-up began `2026-10-18T13:00:23.8390457+05:30`. The author identified a new package-install step and later an error-message fix; I reread the updated README and reran only public CLI/HTTP checks. This is **coached regression verification**, not a fresh uncoached usability pass. The original failures above remain the original observations. No production source was inspected and no model requests, UI substitutes, or broad unit tests were used.

Updated README explicitly documents editable installation from the HiveMind checkout, the Python environment to use in other repositories, source-only working-directory requirements, and `docker desktop start` for the missing Windows engine pipe. Docker had already been restored by the parent task; I did not run that recovery command myself. `docker ps` now succeeded. I used only a new Compose project on 6397 and did not touch the existing database on 6380.

```powershell
# From HiveMind checkout; original fresh venv:
.local/usability/fresh-onboarding-20261018-1256/venv/Scripts/python.exe -m pip install --require-virtualenv -e .

# From each of tiny-repo and tiny-repo/nested:
& 'C:/Vivek_projects/hivemind/.local/usability/fresh-onboarding-20261018-1256/venv/Scripts/python.exe' -m hivemind --help
& 'C:/Vivek_projects/hivemind/.local/usability/fresh-onboarding-20261018-1256/venv/Scripts/python.exe' -m hivemind status
```

Editable `hivemind-git-memory 0.2.0` built and installed successfully. Both locations now import HiveMind. Help now lists `connect, run, sync, status, mcp` and points to connection/launcher help. The first retest of unconnected `status` still returned raw `[Errno 2]` for the **same** tiny-repo `.git/hivemind/config.json` in both locations. I reported that failure, then the author announced a further fix. Both root and nested rechecks then exited 1 with:

```text
This repository is not connected. Run hivemind connect --repo C:\Vivek_projects\hivemind\.local\usability\fresh-onboarding-20261018-1256\tiny-repo --url SERVICE_URL --project PROJECT_ID --client opencode using a project token. See hivemind connect --help.
```

Thus module discovery and actionable unconnected recovery are repaired in the current editable checkout; both locations select the intended target repository. No connected-memory identity behavior is inferred from this unconnected check.

For a regular, noneditable installation, created a **second fresh venv** and ran:

```powershell
# From HiveMind checkout:
py -3.11 -m venv .local/usability/fresh-onboarding-20261018-1256/package-venv
.local/usability/fresh-onboarding-20261018-1256/package-venv/Scripts/python.exe -m pip install --require-virtualenv .

# From tiny-repo/nested (outside the HiveMind checkout working directory):
& 'C:/Vivek_projects/hivemind/.local/usability/fresh-onboarding-20261018-1256/package-venv/Scripts/python.exe' -m hivemind.api --port 8037
$page = Invoke-WebRequest -UseBasicParsing http://127.0.0.1:8037/
$script = Invoke-WebRequest -UseBasicParsing http://127.0.0.1:8037/web/app.js
```

Pip built/installed a regular `hivemind_git_memory-0.2.0-py3-none-any.whl` (113,549 bytes; reported SHA-256 `071f1fc49675c83eadc1dab936888a8b97230a2046892ce506223e17a9651a02`). No requirements install was needed for the explicit memory-mode HTTP check. `/` returned 200, `text/html; charset=utf-8`, 10,253 bytes. `/web/app.js` returned 200, `text/javascript; charset=utf-8`, 28,497 bytes. Content was not inspected to simulate UI; this establishes packaged HTTP asset availability, not rendering or full package isolation from an inaccessible source tree. This package was built before the later unconnected-error repair; that repair was retested through the editable install.

With Docker running, ran the isolated documented durable profile:

```powershell
# From HiveMind checkout:
$env:FALKORDB_PORT='6397'
docker compose -p hivemind-fresh-onboarding-20261018-1256 up -d --wait
$env:HIVEMIND_BACKEND='falkordb'
$env:FALKORDB_HOST='127.0.0.1'
$env:FALKORDB_PORT='6397'
$env:FALKORDB_GRAPH='hivemind_fresh_onboarding_20261018_1256'
.local/usability/fresh-onboarding-20261018-1256/venv/Scripts/python.exe -m hivemind.api --port 8028
(Invoke-WebRequest -UseBasicParsing http://127.0.0.1:8028/).StatusCode
docker ps --filter name=hivemind-fresh-onboarding-20261018-1256 --format '{{.Names}} {{.Status}} {{.Ports}}'
```

Compose created only `hivemind-fresh-onboarding-20261018-1256-falkordb-1`, its project network and named memory-data volume. The container became healthy on `127.0.0.1:6397->6379/tcp`; live HiveMind startup succeeded and HTTP returned 200. This repairs the earlier environment blocker once the documented prerequisite runs. Persistence across writes/restarts, login, project/token creation, connection, and UI remain untested here.

Controlled missing-Git check used absolute Python and cleared PATH **only in a child process**, without uninstalling Git:

```powershell
# From tiny-repo:
$env:PATH=''
$env:HIVEMIND_AGENT_TOKEN='simulated-invalid-token'
& 'C:/Vivek_projects/hivemind/.local/usability/fresh-onboarding-20261018-1256/venv/Scripts/python.exe' -m hivemind connect --repo . --url http://127.0.0.1:8028 --project project:SIMULATED_ONBOARDING --client opencode
```

Exited 1 with `Git is missing. Install Git, ensure it is on PATH, and retry the HiveMind command.` This is an actionable simulated missing-Git failure; it is not a clean-machine prerequisite installation test. Substantive regression checks ended `2026-10-18T13:02:01.8845685+05:30` (~1m38s plus report/cleanup). No UI or native permission claim changed.

Regression cleanup: stopped only this test's two server sessions (ports 8028/8037) and ran `docker compose -p hivemind-fresh-onboarding-20261018-1256 stop` with `FALKORDB_PORT=6397`. No listeners remained on 8028/8037; the test container showed `Exited (0)`. Its container/network/volume and isolated Python/repository artifacts remain for review; existing services and volumes were untouched.
