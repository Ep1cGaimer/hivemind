"""Prepare and verify an isolated, persistent OpenTelemetry HiveMind trial.

Run with Python 3.11 from any directory. No third-party host packages required.
Credentials stay in the git-ignored .local/opentelemetry-test directory.
"""

from __future__ import annotations

import argparse
import http.cookiejar
import json
from pathlib import Path
import secrets
import subprocess
import time
import urllib.request
import urllib.error


ROOT = Path(__file__).resolve().parents[2]
SUPPORT = Path(__file__).resolve().parent
REPO = ROOT / ".local" / "opentelemetry.io"
STATE = ROOT / ".local" / "opentelemetry-test"
CONTAINER = "hivemind-otel-test"
GRAPH = "hivemind_opentelemetry_trial"
BASE = "http://127.0.0.1:8772"
MCP_COMMAND = ["docker", "exec", "-i", CONTAINER, "python", "/test-support/mcp_bridge.py"]


def run(*args: str, **kwargs):
    return subprocess.run(list(args), check=True, text=True, **kwargs)


def request(path, payload=None, *, opener=None, token=None):
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = "Bearer " + token
    req = urllib.request.Request(
        BASE + path,
        data=None if payload is None else json.dumps(payload).encode(),
        headers=headers,
    )
    with (opener or urllib.request.build_opener()).open(req, timeout=30) as response:
        result = json.load(response)
    if result.get("ok") is not True:
        raise RuntimeError(result.get("error", "Request failed"))
    return result


def wait_ready():
    for attempt in range(60):
        try:
            health = request("/health")
            if health["backend"] != "falkordb":
                raise RuntimeError("Trial must use persistent FalkorDB")
            return health
        except (OSError, ValueError):
            if attempt == 59:
                raise
            time.sleep(1)


def rpc(requests):
    result = run(*MCP_COMMAND, input="".join(json.dumps(item) + "\n" for item in requests),
                 capture_output=True, timeout=60)
    replies = [json.loads(line) for line in result.stdout.splitlines() if line.strip()]
    for reply in replies:
        if "error" in reply or reply.get("result", {}).get("isError"):
            raise RuntimeError(reply)
    return {reply["id"]: reply.get("result", {}) for reply in replies}


def tool(request_id, name, arguments):
    return {"jsonrpc": "2.0", "id": request_id, "method": "tools/call",
            "params": {"name": name, "arguments": arguments}}


def initialize():
    return {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {
        "protocolVersion": "2024-11-05", "capabilities": {},
        "clientInfo": {"name": "hivemind-real-repo-trial", "version": "1"}}}


def seed_memories(connection):
    commit = run("git", "-C", str(REPO), "rev-parse", "HEAD", capture_output=True).stdout.strip()
    notes = [
        ("Repository map and source authority", "Read AGENTS.md first. It identifies content/en/site/ "
         "as the primary source for site build, testing, and implementation guidance. "
         "This is the documentation website repository, not a language SDK implementation.",
         ["AGENTS.md", "README.md", "content/en/site/build/_index.md"]),
        ("Install and build scope", "package.json pins dependency versions through package-lock.json. "
         "Use npm run install:safe: lock-exact npm ci --ignore-scripts, then ci:prepare. "
         "Optional dependencies are needed for platform binaries. Do not use bare npx. "
         "The default build is lean when BUILD_KIND is unset; production builds differ in draft/future handling.",
         ["package.json", ".npmrc", "content/en/site/build/dependencies.md", "content/en/site/build/_index.md"]),
        ("Documentation validation boundaries", "The site uses Hugo/Goldmark and Docsy. "
         "Consult the style guide for alert syntax and blank lines. test:public reads generated public/ "
         "and can skip when it is absent; a skipped public test does not establish a successful build. "
         "Windows builds are not the primary supported environment; this trial runs site commands in Linux Docker.",
         ["content/en/docs/contributing/style-guide.md", "content/en/site/testing/_index.md",
          "content/en/docs/contributing/development.md"]),
    ]
    endpoint = f"/api/projects/{connection['project_id']}/memories"
    existing = request(endpoint, token=connection["token"])["memories"]
    for title, body, sources in notes:
        if any(item["title"] == title for item in existing):
            continue
        paths = "\n".join(f"- {source}" for source in sources)
        body += f"\n\nSource checkout: {commit}\nSource files:\n{paths}\n\n"
        body += "Scope: this checkout's website tooling. Revalidate against current files before use. "
        body += "These are manually source-checked workspace notes, not automatically verified evidence claims."
        request(endpoint, {"title": title, "body": body, "tags": ["bootstrap", "source-linked", "opentelemetry"]},
                token=connection["token"])
    return commit


def setup():
    if not (REPO / ".git").is_dir():
        raise RuntimeError(f"Clone the repository to {REPO} first")
    STATE.mkdir(parents=True, exist_ok=True)
    env_path = STATE / "runtime.env"
    if not env_path.exists():
        values = {
            "HIVEMIND_BACKEND": "falkordb", "FALKORDB_HOST": "host.docker.internal",
            "FALKORDB_PORT": "6380", "FALKORDB_GRAPH": GRAPH,
            "HIVEMIND_OPERATOR_PASSWORD": secrets.token_urlsafe(24),
            "HIVEMIND_AUTH_SECRET": secrets.token_urlsafe(48),
            "HIVEMIND_API_KEY": secrets.token_urlsafe(32),
        }
        env_path.write_text("".join(f"{key}={value}\n" for key, value in values.items()), encoding="utf-8")
    values = dict(line.split("=", 1) for line in env_path.read_text().splitlines() if line)
    names = run("docker", "ps", "-a", "--format", "{{.Names}}", capture_output=True).stdout.splitlines()
    if CONTAINER in names:
        run("docker", "start", CONTAINER, capture_output=True)
    else:
        run("docker", "run", "-d", "--name", CONTAINER, "--restart", "unless-stopped",
            "--env-file", str(env_path), "-p", "127.0.0.1:8772:8000",
            "--mount", f"type=bind,source={ROOT / 'hivemind'},target=/app/hivemind,readonly",
            "--mount", f"type=bind,source={ROOT / 'web'},target=/app/web,readonly",
            "--mount", f"type=bind,source={SUPPORT},target=/test-support,readonly",
            "--mount", f"type=bind,source={STATE},target=/test-state,readonly",
            "hivemind:live", capture_output=True)
    wait_ready()
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
    request("/api/auth/login", {"username": "operator", "password": values["HIVEMIND_OPERATOR_PASSWORD"]}, opener=opener)
    connection_path = STATE / "connection.json"
    if connection_path.exists():
        connection = json.loads(connection_path.read_text())
    else:
        projects = request("/api/projects", opener=opener)["projects"]
        project = next((item for item in projects if item["name"] == "OpenTelemetry website trial"), None)
        if project is None:
            project = request("/api/projects", {"name": "OpenTelemetry website trial",
                "description": "Real-repo two-session shared-memory evaluation"}, opener=opener)["project"]
        connection = request(f"/api/projects/{project['id']}/agents", {"label": "Codex real-repo trial"}, opener=opener)
        connection_path.write_text(json.dumps(connection, indent=2), encoding="utf-8")
    commit = seed_memories(connection)
    exclude_path = REPO / ".git" / "info" / "exclude"
    exclude = exclude_path.read_text(encoding="utf-8")
    for entry in ["/.codex/config.toml", "/.hivemind/"]:
        if entry not in exclude.splitlines():
            exclude += "\n" + entry + "\n"
    exclude_path.write_text(exclude, encoding="utf-8")
    codex_path = REPO / ".codex" / "config.toml"
    codex_path.parent.mkdir(exist_ok=True)
    config = ('[mcp_servers.hivemind_otel]\ncommand = "docker"\n'
              'args = ["exec", "-i", "hivemind-otel-test", "python", "/test-support/mcp_bridge.py"]\n'
              'startup_timeout_sec = 60\ntool_timeout_sec = 60\n'
              'enabled_tools = ["list_memories", "create_memory", "edit_memory"]\n')
    if codex_path.exists() and codex_path.read_text() != config:
        raise RuntimeError("Refusing to overwrite a different project MCP configuration")
    codex_path.write_text(config, encoding="utf-8")
    prompts_path = REPO / ".hivemind"
    prompts_path.mkdir(exist_ok=True)
    for source in SUPPORT.glob("session-*.txt"):
        (prompts_path / source.name).write_text(source.read_text(encoding="utf-8"), encoding="utf-8")
    (STATE / "metadata.json").write_text(json.dumps({"repo": str(REPO), "commit": commit,
        "project_id": connection["project_id"], "url": BASE, "graph": GRAPH}, indent=2), encoding="utf-8")
    print(f"Ready: {BASE}; project {connection['project_id']}; repo {REPO}")
    print("Credentials are in .local/opentelemetry-test/runtime.env (not printed).")


def smoke():
    wait_ready()
    connection = json.loads((STATE / "connection.json").read_text())
    first = rpc([initialize(), {"jsonrpc": "2.0", "method": "notifications/initialized"},
                 {"jsonrpc": "2.0", "id": 2, "method": "tools/list"},
                 tool(3, "list_memories", {})])
    assert len(first[2]["tools"]) == 8, "Unexpected tool registry"
    bootstrap = first[3]["structuredContent"]["memories"]
    assert len(bootstrap) >= 3
    old = next((item for item in bootstrap if item["title"] == "MCP persistence probe"), None)
    marker = "probe-" + secrets.token_hex(8)
    body = "Infrastructure-only probe, not domain evidence. Marker: " + marker
    write = tool(2, "edit_memory", {"memory_id": old["id"], "body": body}) if old else tool(
        2, "create_memory", {"title": "MCP persistence probe", "body": body, "tags": ["smoke-test"]})
    created = rpc([initialize(), write])[2]["structuredContent"]["memory"]
    # rpc() starts a NEW docker exec / Python MCP process for each call.
    second = rpc([initialize(), tool(2, "list_memories", {})])[2]["structuredContent"]
    recalled = next(item for item in second["memories"] if item["memory_key"] == created["memory_key"])
    assert marker in recalled["body"]
    via_http = request(f"/api/projects/{connection['project_id']}/memories", token=connection["token"])
    assert any(item["id"] == recalled["id"] for item in via_http["memories"])
    try:
        request("/api/projects/project:default/memories", token=connection["token"])
        raise AssertionError("Project token unexpectedly accessed another project")
    except urllib.error.HTTPError as exc:
        assert exc.code == 403
    edit = rpc([initialize(), tool(2, "edit_memory", {"memory_id": recalled["id"],
        "body": body + "\nVersioned edit verified."})])[2]["structuredContent"]["memory"]
    assert edit["version"] == recalled["version"] + 1
    report = {"ok": True, "checks": ["live HTTP health", "MCP initialize", "eight advertised tools",
        "project notes returned", "MCP write", "new-process MCP recall", "HTTP sees MCP write",
        "immutable version increment", "cross-project HTTP access rejected"],
        "project_id": connection["project_id"], "backend": "falkordb"}
    (STATE / "smoke-result.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["setup", "smoke", "status"])
    action = parser.parse_args().action
    if action == "setup":
        setup()
    elif action == "smoke":
        smoke()
    else:
        print(json.dumps(request("/health"), indent=2))
        print((STATE / "metadata.json").read_text())
