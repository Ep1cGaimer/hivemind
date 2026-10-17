"""Dependency-free HTTP API for the local HiveMind demo."""

from __future__ import annotations

import argparse
import hmac
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import logging
import os
from pathlib import Path
import sys
import threading
from typing import Any, Mapping
from urllib.parse import unquote, urlparse

from . import __version__
from .auth import AuthManager, Identity
from .backend import BackendSelectionError, create_store, select_backend
from .fixture import SHARED_SCOPE_ID
from .gateway import HiveMindGateway
from .workspace import MemoryWorkspace, ProjectWorkspace


MAX_REQUEST_BYTES = 1_000_000
LOGGER = logging.getLogger("hivemind.api")


class HiveMindRuntime:
    """Own the replaceable seeded store used by one local server."""

    def __init__(self, environ: Mapping[str, str] | None = None) -> None:
        self._lock = threading.RLock()
        # Snapshot both selection and connection settings.  A long-running
        # process must not change backend or graph because its parent process
        # environment changes after startup.
        self._environ = dict(os.environ if environ is None else environ)
        self._backend_name = select_backend(self._environ)
        self.store = create_store(self._environ, backend=self._backend_name)
        self.gateway = HiveMindGateway(self.store)
        self.workspace = MemoryWorkspace(self.store)
        self.auth = AuthManager(self._environ)
        self.projects = ProjectWorkspace(self.store, self.auth)

    def reset(self) -> dict[str, Any]:
        """Replace the graph with a fresh deterministic fixture."""

        with self._lock:
            self.store = create_store(self._environ, backend=self._backend_name, reset=True)
            self.gateway = HiveMindGateway(self.store)
            self.workspace = MemoryWorkspace(self.store)
            self.projects = ProjectWorkspace(self.store, self.auth)
            return self.gateway.state()

    def health(self) -> dict[str, Any]:
        """Report process health and verify a live backend with one fixed query."""

        result: dict[str, Any] = {
            "ok": True,
            "service": "hivemind",
            "version": __version__,
            "backend": self.backend_name,
            "falkordb_adapter": {"optional": True, "server_checked": False},
        }
        if self.backend_name != "falkordb":
            return result
        try:
            checker = getattr(self.store, "check_server")
            checker()
        except Exception as exc:  # health must remain a safe JSON boundary
            result["ok"] = False
            result["falkordb_adapter"] = {
                "optional": True,
                "server_checked": True,
                "reachable": False,
                "error": {"code": "FALKORDB_UNAVAILABLE", "message": str(exc)},
            }
            return result
        result["falkordb_adapter"] = {"optional": True, "server_checked": True, "reachable": True}
        return result

    @property
    def backend_name(self) -> str:
        """Return the selected backend reported by the current store."""

        return self._backend_name

    def get_gateway(self) -> HiveMindGateway:
        """Return the current gateway under the runtime lock."""

        with self._lock:
            return self.gateway


class HiveMindHTTPServer(ThreadingHTTPServer):
    """Threading HTTP server carrying a HiveMind runtime."""

    allow_reuse_address = True

    def __init__(self, server_address: tuple[str, int], runtime: HiveMindRuntime | None = None) -> None:
        self.runtime = runtime or HiveMindRuntime()
        super().__init__(server_address, HiveMindRequestHandler)


class HiveMindRequestHandler(BaseHTTPRequestHandler):
    """Route JSON API calls and safe static files from an optional ``web/``."""

    server_version = "HiveMindHTTP/0.1"

    def log_message(self, format: str, *args: Any) -> None:
        """Keep the API quiet by default; callers can inspect response bodies."""

    @property
    def runtime(self) -> HiveMindRuntime:
        return self.server.runtime  # type: ignore[attr-defined]

    @property
    def web_root(self) -> Path:
        return Path(__file__).resolve().parent.parent / "web"

    def _send_json(
        self,
        payload: dict[str, Any],
        status: int = HTTPStatus.OK,
        headers: Mapping[str, str] | None = None,
    ) -> None:
        body = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        for name, value in (headers or {}).items():
            self.send_header(name, value)
        self.end_headers()
        self.wfile.write(body)

    def _send_bytes(self, body: bytes, content_type: str) -> None:
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _error(self, code: str, message: str, status: int = HTTPStatus.BAD_REQUEST, details: dict[str, Any] | None = None) -> None:
        error: dict[str, Any] = {"code": code, "message": message}
        if details:
            error["details"] = details
        self._send_json({"ok": False, "error": error}, status)

    def _status_for_result(self, result: Any) -> int:
        if not isinstance(result, dict) or result.get("ok") is True:
            return HTTPStatus.OK
        code = str(result.get("error", {}).get("code", ""))
        if code.endswith("FAILED") or code in {"STATE_FAILED", "DEMO_FAILED"}:
            return HTTPStatus.INTERNAL_SERVER_ERROR
        return HTTPStatus.BAD_REQUEST

    def _read_json(self) -> dict[str, Any] | None:
        raw_length = self.headers.get("Content-Length", "0")
        try:
            length = int(raw_length)
        except ValueError:
            self._error("INVALID_CONTENT_LENGTH", "Content-Length must be an integer")
            return None
        if length < 0 or length > MAX_REQUEST_BYTES:
            self._error("REQUEST_TOO_LARGE", f"JSON request must be at most {MAX_REQUEST_BYTES} bytes")
            return None
        try:
            raw = self.rfile.read(length)
            payload = json.loads(raw.decode("utf-8") or "{}")
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            self._error("INVALID_JSON", f"Request body is not valid JSON: {exc}")
            return None
        if not isinstance(payload, dict):
            self._error("INVALID_JSON", "Request body must be a JSON object")
            return None
        return payload

    def _authorized_mutation(self, path: str) -> bool:
        """Require an optional local API key for mutating routes.

        Memory-mode local development remains zero-config. Deployments that bind
        beyond loopback can set ``HIVEMIND_API_KEY`` and require callers to send
        ``X-HiveMind-Key`` for writes, corrections, resets, and demo replays.
        """

        if path not in {"/api/reset", "/api/exposure", "/api/correction", "/api/draft", "/api/demo"}:
            return True
        expected = os.environ.get("HIVEMIND_API_KEY", "").strip()
        if not expected:
            return True
        supplied = self.headers.get("X-HiveMind-Key", "")
        if hmac.compare_digest(supplied, expected):
            return True
        self._error("UNAUTHORIZED", "This HiveMind mutation requires an API key", HTTPStatus.UNAUTHORIZED)
        return False

    def _identity(self) -> Identity | None:
        context = self._identity_context()
        return context[0] if context else None

    def _identity_context(self) -> tuple[Identity, str | None] | None:
        return self.runtime.auth.authenticate_context(
            self.headers.get("Authorization"),
            self.headers.get("Cookie"),
        )

    def _require_identity(self) -> Identity | None:
        identity = self._identity()
        if identity is None:
            self._error("AUTH_REQUIRED", "Sign in or provide a valid agent bearer token", HTTPStatus.UNAUTHORIZED)
        return identity

    def _require_human_identity(self) -> Identity | None:
        context = self._identity_context()
        if context is None:
            self._error("AUTH_REQUIRED", "Sign in with a human workspace session", HTTPStatus.UNAUTHORIZED)
            return None
        if context[1] is not None:
            self._error("FORBIDDEN", "This action requires the human project session", HTTPStatus.FORBIDDEN)
            return None
        return context[0]

    def _require_human_project(self, project_id: str, write: bool = False) -> Identity | None:
        identity = self._require_human_identity()
        if identity is None:
            return None
        if not self.runtime.projects.can_access(identity, project_id, write=write):
            self._error("FORBIDDEN", "You do not have access to this project", HTTPStatus.FORBIDDEN)
            return None
        return identity

    def _workspace_path(self, path: str) -> tuple[str, str | None] | None:
        prefix = "/api/memories"
        if path == prefix:
            return "collection", None
        if path.startswith(prefix + "/"):
            memory_id = unquote(path[len(prefix) + 1:])
            return "item", memory_id if memory_id else None
        return None

    def _project_path(self, path: str) -> tuple[str, str | None, str | None] | None:
        """Return collection/item/action and project-relative ID for API paths."""

        prefix = "/api/projects/"
        if not path.startswith(prefix):
            return None
        parts = [unquote(part) for part in path[len(prefix):].split("/") if part]
        if not parts:
            return None
        project_id = parts[0]
        if len(parts) == 1:
            return "project", project_id, None
        if parts[1] == "graph" and len(parts) == 2:
            return "graph", project_id, None
        if parts[1] == "members":
            return "members", project_id, parts[2] if len(parts) > 2 else None
        if parts[1] == "agents":
            return "agents", project_id, parts[2] if len(parts) > 2 else None
        if parts[1] == "memories":
            return "memories", project_id, parts[2] if len(parts) > 2 else None
        return None

    def _require_project(self, project_id: str, write: bool = False) -> Identity | None:
        context = self._identity_context()
        if context is None:
            self._error("AUTH_REQUIRED", "Sign in or provide a valid agent bearer token", HTTPStatus.UNAUTHORIZED)
            return None
        identity, token_project_id = context
        if token_project_id is not None and token_project_id != project_id:
            self._error("FORBIDDEN", "This agent token is scoped to another project", HTTPStatus.FORBIDDEN)
            return None
        if not self.runtime.projects.can_access(identity, project_id, write=write):
            self._error("FORBIDDEN", "You do not have access to this project", HTTPStatus.FORBIDDEN)
            return None
        return identity

    def _serve_static(self, path: str) -> bool:
        root = self.web_root
        if not root.is_dir():
            return False
        relative = unquote(path).lstrip("/")
        if relative == "web":
            relative = ""
        elif relative.startswith("web/"):
            relative = relative[4:]
        if not relative:
            relative = "index.html"
        if ".." in Path(relative).parts:
            self._error("NOT_FOUND", "Static path not found", HTTPStatus.NOT_FOUND)
            return True
        candidate = (root / relative).resolve()
        try:
            candidate.relative_to(root.resolve())
        except ValueError:
            self._error("NOT_FOUND", "Static path not found", HTTPStatus.NOT_FOUND)
            return True
        if not candidate.is_file():
            return False
        content_types = {
            ".html": "text/html; charset=utf-8",
            ".css": "text/css; charset=utf-8",
            ".js": "text/javascript; charset=utf-8",
            ".json": "application/json; charset=utf-8",
            ".svg": "image/svg+xml",
            ".png": "image/png",
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
        }
        self._send_bytes(candidate.read_bytes(), content_types.get(candidate.suffix.lower(), "application/octet-stream"))
        return True

    def do_GET(self) -> None:  # noqa: N802 - stdlib handler API
        parsed = urlparse(self.path)
        path = parsed.path
        if path == "/api/auth/me":
            identity = self._require_identity()
            if identity is not None:
                self._send_json({"ok": True, "user": identity.public()})
            return
        if path == "/api/projects":
            identity = self._require_identity()
            if identity is not None:
                self._send_json(self.runtime.projects.list_projects(identity))
            return
        project_path = self._project_path(path)
        if project_path is not None:
            action, project_id, item_id = project_path
            if action == "project":
                identity = self._require_project(project_id)
                if identity is not None:
                    result = self.runtime.projects.detail(identity, project_id)
                    self._send_json(result, self._status_for_result(result))
                return
            if action == "graph":
                identity = self._require_project(project_id)
                if identity is not None:
                    result = self.runtime.projects.graph(identity, project_id)
                    self._send_json(result, self._status_for_result(result))
                return
            if action == "memories":
                identity = self._require_project(project_id)
                if identity is not None:
                    if item_id:
                        result = self.runtime.workspace.get_memory(item_id, project_id)
                    else:
                        result = self.runtime.workspace.list_memories(project_id)
                    self._send_json(result, self._status_for_result(result))
                return
            if action == "members":
                identity = self._require_project(project_id)
                if identity is not None:
                    result = self.runtime.projects.detail(identity, project_id)
                    if result.get("ok"):
                        self._send_json({"ok": True, "members": result.get("members", [])})
                    else:
                        self._send_json(result, self._status_for_result(result))
                return
            if action == "agents":
                identity = self._require_project(project_id)
                if identity is not None:
                    self._send_json({"ok": True, "agents": [record.public() for record in self.runtime.auth.agent_records_for(identity) if record.project_id == project_id]})
                return
        if path == "/api/workspace":
            identity = self._require_identity()
            if identity is not None:
                result = self.runtime.workspace.list_memories()
                result["user"] = identity.public()
                result["agent"] = {
                    "memory_endpoint": "/api/memories",
                    "mcp_command": "HIVEMIND_AGENT_TOKEN=<token> python -m hivemind.mcp_server",
                }
                self._send_json(result)
            return
        workspace_path = self._workspace_path(path)
        if workspace_path is not None:
            identity = self._require_identity()
            if identity is not None:
                if workspace_path[0] == "collection":
                    self._send_json(self.runtime.workspace.list_memories())
                else:
                    result = self.runtime.workspace.get_memory(workspace_path[1])
                    self._send_json(result, self._status_for_result(result))
            return
        if path == "/api/agents":
            identity = self._require_identity()
            if identity is not None:
                self._send_json({"ok": True, "agents": [record.public() for record in self.runtime.auth.agent_records_for(identity)]})
            return
        if path == "/health":
            health = self.runtime.health()
            self._send_json(health, HTTPStatus.OK if health.get("ok") else HTTPStatus.SERVICE_UNAVAILABLE)
            return
        if path == "/api/state":
            gateway = self.runtime.get_gateway()
            result = gateway.state()
            recall = gateway.recall_context(SHARED_SCOPE_ID)
            if recall.get("ok"):
                result.update(recall)
                result["state"] = gateway.state().get("state", {})
                result["backend"] = self.runtime.backend_name
                memory_versions = recall.get("memory_versions", [])
                if memory_versions:
                    result["evidence"] = gateway.inspect_evidence(memory_versions[0].get("id"), max_depth=4)
                draft_records = [
                    entry.get("data", {})
                    for entry in result["state"].get("nodes", [])
                    if entry.get("type") == "Draft"
                ]
                if draft_records:
                    latest_draft = sorted(draft_records, key=lambda item: item.get("created_at", ""))[-1]
                    result["draft"] = {"draft": latest_draft, "saved": True}
                result["integration"] = {
                    "mcp_server": "python -m hivemind.mcp_server",
                    "http_api": True,
                    "backend": self.runtime.backend_name,
                }
            self._send_json(result, self._status_for_result(result))
            return
        if path == "/" or not path.startswith("/api/"):
            if self._serve_static(path):
                return
        self._error("NOT_FOUND", "Endpoint or static file not found", HTTPStatus.NOT_FOUND, {"path": path})

    def do_POST(self) -> None:  # noqa: N802 - stdlib handler API
        parsed = urlparse(self.path)
        if not self._authorized_mutation(parsed.path):
            return
        payload = self._read_json()
        if payload is None:
            return
        if parsed.path == "/api/auth/login":
            result = self.runtime.auth.login(payload.get("username"), payload.get("password"))
            if result is None:
                self._error("INVALID_CREDENTIALS", "Username or password is incorrect", HTTPStatus.UNAUTHORIZED)
                return
            session, identity = result
            self._send_json(
                {"ok": True, "user": identity.public()},
                headers={
                    "Set-Cookie": f"{self.runtime.auth.SESSION_COOKIE}={session}; HttpOnly; SameSite=Lax; Path=/",
                },
            )
            return
        if parsed.path == "/api/projects":
            identity = self._require_human_identity()
            if identity is None:
                return
            result = self.runtime.projects.create_project(identity, payload.get("name"), payload.get("description", ""))
            self._send_json(result, self._status_for_result(result))
            return
        project_path = self._project_path(parsed.path)
        if project_path is not None:
            action, project_id, item_id = project_path
            if action == "memories" and item_id is None:
                identity = self._require_project(project_id, write=True)
                if identity is None:
                    return
                result = self.runtime.workspace.create(
                    identity,
                    payload.get("title"),
                    payload.get("body"),
                    payload.get("tags"),
                    project_id,
                )
                self._send_json(result, self._status_for_result(result))
                return
            if action == "members" and item_id is None:
                identity = self._require_human_project(project_id, write=True)
                if identity is None:
                    return
                result = self.runtime.projects.add_member(identity, project_id, payload.get("user_id"), payload.get("role", "editor"))
                self._send_json(result, self._status_for_result(result))
                return
            if action == "agents" and item_id is None:
                identity = self._require_human_project(project_id, write=True)
                if identity is None:
                    return
                try:
                    token, record = self.runtime.auth.create_agent_token(identity, payload.get("label"), project_id)
                except ValueError as exc:
                    self._send_json({"ok": False, "error": {"code": "INVALID_AGENT_LABEL", "message": str(exc)}}, HTTPStatus.BAD_REQUEST)
                    return
                self._send_json({"ok": True, "token": token, "agent": record.public(), "project_id": project_id})
                return
        if parsed.path == "/api/auth/logout":
            identity = self._require_identity()
            if identity is None:
                return
            self.runtime.auth.logout(self._session_cookie())
            self._send_json(
                {"ok": True},
                headers={
                    "Set-Cookie": f"{self.runtime.auth.SESSION_COOKIE}=; Max-Age=0; HttpOnly; SameSite=Lax; Path=/",
                },
            )
            return
        if parsed.path == "/api/agents":
            identity = self._require_identity()
            if identity is None:
                return
            try:
                token, record = self.runtime.auth.create_agent_token(identity, payload.get("label"))
            except ValueError as exc:
                self._send_json({"ok": False, "error": {"code": "INVALID_AGENT_LABEL", "message": str(exc)}}, HTTPStatus.BAD_REQUEST)
                return
            self._send_json(
                {
                    "ok": True,
                    "token": token,
                    "agent": record.public(),
                    "endpoint": "/api/memories",
                    "mcp_command": "HIVEMIND_AGENT_TOKEN=<token> python -m hivemind.mcp_server",
                }
            )
            return
        if parsed.path == "/api/memories":
            identity = self._require_identity()
            if identity is None:
                return
            result = self.runtime.workspace.create(identity, payload.get("title"), payload.get("body"), payload.get("tags"))
            self._send_json(result, self._status_for_result(result))
            return
        gateway = self.runtime.get_gateway()
        try:
            if parsed.path == "/api/reset":
                result = self.runtime.reset()
            elif parsed.path == "/api/recall":
                result = gateway.recall_context(payload.get("scope_id"))
            elif parsed.path == "/api/evidence":
                result = gateway.inspect_evidence(payload.get("memory_id"), payload.get("max_depth", 4))
            elif parsed.path == "/api/exposure":
                result = gateway.record_exposure(payload.get("run_id"), payload.get("memory_id"))
            elif parsed.path == "/api/correction":
                result = gateway.apply_correction(
                    payload.get("base_memory_id"),
                    payload.get("scope_id"),
                    correction_text=payload.get("correction_text"),
                    reviewer=payload.get("reviewer", "operator"),
                )
            elif parsed.path == "/api/draft":
                result = gateway.save_draft(payload.get("scope_id"), payload.get("title"), payload.get("body"), payload.get("citations"))
            elif parsed.path == "/api/demo":
                result = gateway.run_demo()
            else:
                self._error("NOT_FOUND", "POST endpoint not found", HTTPStatus.NOT_FOUND, {"path": parsed.path})
                return
        except Exception as exc:  # the boundary must never dump a traceback to a model client
            LOGGER.exception("HiveMind request failed: %s", exc)
            self._error("INTERNAL_ERROR", "Request failed safely", HTTPStatus.INTERNAL_SERVER_ERROR)
            return
        self._send_json(result, self._status_for_result(result))

    def _session_cookie(self) -> str | None:
        for item in self.headers.get("Cookie", "").split(";"):
            key, separator, value = item.strip().partition("=")
            if separator and key == self.runtime.auth.SESSION_COOKIE:
                return value
        return None

    def do_PATCH(self) -> None:  # noqa: N802 - stdlib handler API
        parsed = urlparse(self.path)
        project_path = self._project_path(parsed.path)
        if project_path is not None and project_path[0] == "memories" and project_path[2] is not None:
            project_id = project_path[1]
            identity = self._require_project(project_id, write=True)
            if identity is None:
                return
            payload = self._read_json()
            if payload is None:
                return
            result = self.runtime.workspace.edit(
                identity,
                project_path[2],
                payload.get("title"),
                payload.get("body"),
                payload.get("tags"),
                project_id,
            )
            self._send_json(result, self._status_for_result(result))
            return
        workspace_path = self._workspace_path(parsed.path)
        if workspace_path is None or workspace_path[0] != "item":
            self._error("NOT_FOUND", "PATCH endpoint not found", HTTPStatus.NOT_FOUND, {"path": parsed.path})
            return
        identity = self._require_identity()
        if identity is None:
            return
        payload = self._read_json()
        if payload is None:
            return
        result = self.runtime.workspace.edit(
            identity,
            workspace_path[1],
            payload.get("title"),
            payload.get("body"),
            payload.get("tags"),
        )
        self._send_json(result, self._status_for_result(result))


def serve(host: str = "127.0.0.1", port: int = 8000) -> None:
    """Run the local API until interrupted."""

    server = HiveMindHTTPServer((host, port))
    print(f"HiveMind API listening on http://{host}:{port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


def main(argv: list[str] | None = None) -> int:
    """CLI entry point for ``python -m hivemind.api``."""

    parser = argparse.ArgumentParser(description="Run the local HiveMind API")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args(argv)
    try:
        serve(args.host, args.port)
    except BackendSelectionError as exc:
        print(f"HiveMind backend error [{exc.code}]: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
