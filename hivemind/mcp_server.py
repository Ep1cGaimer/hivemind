"""Minimal newline-delimited JSON-RPC MCP server for HiveMind tools."""

from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Any, TextIO

from .auth import AuthManager, Identity
from .backend import BackendSelectionError, create_store
from .gateway import HiveMindGateway
from .workspace import MemoryWorkspace


PROTOCOL_VERSION = "2024-11-05"
SERVER_NAME = "hivemind"
SERVER_VERSION = "0.1.0"
MAX_LINE_BYTES = 1_000_000


def _json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _rpc_error(request_id: Any, code: int, message: str, data: dict[str, Any] | None = None) -> dict[str, Any]:
    error: dict[str, Any] = {"code": code, "message": message}
    if data is not None:
        error["data"] = data
    return {"jsonrpc": "2.0", "id": request_id, "error": error}


class MCPServer:
    """Serve a bounded set of HiveMind gateway operations over stdin/stdout."""

    def __init__(
        self,
        gateway: HiveMindGateway | None = None,
        *,
        auth: AuthManager | None = None,
        agent_token: str | None = None,
    ) -> None:
        self.gateway = gateway if gateway is not None else HiveMindGateway(create_store())
        self.auth = auth or AuthManager()
        self.workspace = MemoryWorkspace(self.gateway.store)
        token_context = self.auth.authenticate_agent_context(agent_token or os.environ.get("HIVEMIND_AGENT_TOKEN"))
        self.identity = token_context[0] if token_context else None
        self.project_id = token_context[1] if token_context else None

    @property
    def backend_name(self) -> str:
        """Return the backend selected for this MCP process."""

        return getattr(self.gateway.store, "backend_name", "unknown")

    @staticmethod
    def tool_definitions() -> list[dict[str, Any]]:
        """Return MCP tool metadata with closed, explicit input shapes."""

        return [
            {
                "name": "recall_context",
                "description": "Recall current evidence-aware memory for one exact scope.",
                "inputSchema": {"type": "object", "properties": {"scope_id": {"type": "string"}}, "required": ["scope_id"], "additionalProperties": False},
            },
            {
                "name": "inspect_evidence",
                "description": "Inspect a bounded declared support path for one memory version.",
                "inputSchema": {"type": "object", "properties": {"memory_id": {"type": "string"}, "max_depth": {"type": "integer", "minimum": 0}}, "required": ["memory_id"], "additionalProperties": False},
            },
            {
                "name": "apply_correction",
                "description": "Create an immutable operator-reviewed correction in one exact scope.",
                "inputSchema": {"type": "object", "properties": {"base_memory_id": {"type": "string"}, "scope_id": {"type": "string"}, "correction_text": {"type": "string"}, "reviewer": {"type": "string"}}, "required": ["base_memory_id", "scope_id"], "additionalProperties": False},
            },
            {
                "name": "record_exposure",
                "description": "Record that an agent saw a memory without treating exposure as support.",
                "inputSchema": {"type": "object", "properties": {"run_id": {"type": "string"}, "memory_id": {"type": "string"}}, "required": ["run_id", "memory_id"], "additionalProperties": False},
            },
            {
                "name": "save_draft",
                "description": "Save a local planning draft with exact same-scope citations.",
                "inputSchema": {"type": "object", "properties": {"scope_id": {"type": "string"}, "title": {"type": "string"}, "body": {"type": "string"}, "citations": {"type": "array"}}, "required": ["scope_id", "title", "body", "citations"], "additionalProperties": False},
            },
            {
                "name": "list_memories",
                "description": "List the shared memories available to the connected user.",
                "inputSchema": {"type": "object", "properties": {}, "additionalProperties": False},
            },
            {
                "name": "create_memory",
                "description": "Create a shared memory for the connected user.",
                "inputSchema": {"type": "object", "properties": {"title": {"type": "string"}, "body": {"type": "string"}, "tags": {"type": "array", "items": {"type": "string"}}}, "required": ["title", "body"], "additionalProperties": False},
            },
            {
                "name": "edit_memory",
                "description": "Edit a shared memory owned by the connected user.",
                "inputSchema": {"type": "object", "properties": {"memory_id": {"type": "string"}, "title": {"type": "string"}, "body": {"type": "string"}, "tags": {"type": "array", "items": {"type": "string"}}}, "required": ["memory_id"], "additionalProperties": False},
            },
        ]

    def _workspace_identity(self) -> Identity | dict[str, Any]:
        if self.identity is None:
            return {"ok": False, "error": {"code": "AUTH_REQUIRED", "message": "Connect this coding agent with HIVEMIND_AGENT_TOKEN"}}
        return self.identity

    def _tool_call(self, name: Any, arguments: Any) -> dict[str, Any]:
        if not isinstance(name, str) or name not in {tool["name"] for tool in self.tool_definitions()}:
            return {"ok": False, "error": {"code": "UNKNOWN_TOOL", "message": "Tool is not in the fixed HiveMind tool registry"}}
        if not isinstance(arguments, dict):
            return {"ok": False, "error": {"code": "INVALID_ARGUMENTS", "message": "tools/call arguments must be a JSON object"}}
        if name == "recall_context":
            return self.gateway.recall_context(arguments.get("scope_id"))
        if name == "inspect_evidence":
            return self.gateway.inspect_evidence(arguments.get("memory_id"), arguments.get("max_depth", 4))
        if name == "apply_correction":
            return self.gateway.apply_correction(
                arguments.get("base_memory_id"),
                arguments.get("scope_id"),
                correction_text=arguments.get("correction_text"),
                reviewer=arguments.get("reviewer", "operator"),
            )
        if name == "record_exposure":
            return self.gateway.record_exposure(arguments.get("run_id"), arguments.get("memory_id"))
        if name == "save_draft":
            return self.gateway.save_draft(arguments.get("scope_id"), arguments.get("title"), arguments.get("body"), arguments.get("citations"))
        if name == "list_memories":
            identity = self._workspace_identity()
            if isinstance(identity, dict):
                return identity
            result = self.workspace.list_memories(self.project_id or "project:default")
            result["user"] = identity.public()
            return result
        if name == "create_memory":
            identity = self._workspace_identity()
            if isinstance(identity, dict):
                return identity
            return self.workspace.create(identity, arguments.get("title"), arguments.get("body"), arguments.get("tags"), self.project_id or "project:default")
        if name == "edit_memory":
            identity = self._workspace_identity()
            if isinstance(identity, dict):
                return identity
            return self.workspace.edit(identity, arguments.get("memory_id"), arguments.get("title"), arguments.get("body"), arguments.get("tags"), self.project_id or "project:default")
        return {"ok": False, "error": {"code": "UNKNOWN_TOOL", "message": "Tool is not in the fixed HiveMind tool registry"}}

    def dispatch(self, request: Any) -> dict[str, Any] | None:
        """Handle one parsed JSON-RPC request without allowing exceptions out."""

        if not isinstance(request, dict):
            return _rpc_error(None, -32600, "Invalid Request", {"ok": False, "error": {"code": "INVALID_REQUEST", "message": "request must be an object"}})
        request_id = request.get("id")
        if request.get("jsonrpc") != "2.0" or "method" not in request:
            return _rpc_error(request_id, -32600, "Invalid Request", {"ok": False, "error": {"code": "INVALID_REQUEST", "message": "jsonrpc 2.0 and method are required"}})
        method = request["method"]
        if not isinstance(method, str) or not method:
            return _rpc_error(request_id, -32600, "Invalid Request", {"ok": False, "error": {"code": "INVALID_METHOD", "message": "method must be a non-empty string"}})
        params = request.get("params", {})
        if "id" not in request:
            return None
        if method == "notifications/initialized" or (method.startswith("notifications/") and "id" not in request):
            return None
        if method == "initialize":
            if not isinstance(params, dict):
                return _rpc_error(request_id, -32602, "Invalid params", {"ok": False, "error": {"code": "INVALID_PARAMS", "message": "initialize params must be an object"}})
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {
                    "protocolVersion": PROTOCOL_VERSION,
                    "capabilities": {"tools": {"listChanged": False}},
                    "serverInfo": {"name": SERVER_NAME, "version": SERVER_VERSION, "backend": self.backend_name},
                },
            }
        if method == "tools/list":
            if not isinstance(params, dict):
                return _rpc_error(request_id, -32602, "Invalid params", {"ok": False, "error": {"code": "INVALID_PARAMS", "message": "tools/list params must be an object"}})
            return {"jsonrpc": "2.0", "id": request_id, "result": {"tools": self.tool_definitions()}}
        if method == "tools/call":
            if not isinstance(params, dict):
                return _rpc_error(request_id, -32602, "Invalid params", {"ok": False, "error": {"code": "INVALID_PARAMS", "message": "tools/call params must be an object"}})
            try:
                result = self._tool_call(params.get("name"), params.get("arguments", {}))
            except Exception as exc:  # safe structured boundary for model clients
                result = {"ok": False, "error": {"code": "TOOL_FAILED", "message": "Tool failed safely"}}
            is_error = result.get("ok") is not True
            content = [{"type": "text", "text": _json(result)}]
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {"content": content, "structuredContent": result, "isError": is_error},
            }
        return _rpc_error(request_id, -32601, "Method not found", {"ok": False, "error": {"code": "METHOD_NOT_FOUND", "message": f"Unsupported method: {method}"}})

    def serve(self, input_stream: TextIO = sys.stdin, output_stream: TextIO = sys.stdout) -> None:
        """Read one JSON request per line and write one response per request."""

        for line in input_stream:
            if not line.strip():
                continue
            if len(line.encode("utf-8")) > MAX_LINE_BYTES:
                response = _rpc_error(None, -32600, "Invalid Request", {"ok": False, "error": {"code": "REQUEST_TOO_LARGE", "message": f"MCP request line must be at most {MAX_LINE_BYTES} bytes"}})
            else:
                try:
                    request = json.loads(line)
                except json.JSONDecodeError as exc:
                    response = _rpc_error(None, -32700, "Parse error", {"ok": False, "error": {"code": "PARSE_ERROR", "message": str(exc)}})
                else:
                    response = self.dispatch(request)
            if response is not None:
                output_stream.write(_json(response) + "\n")
                output_stream.flush()


def main(argv: list[str] | None = None) -> int:
    """CLI entry point for ``python -m hivemind.mcp_server``."""

    parser = argparse.ArgumentParser(description="Run HiveMind's newline-delimited MCP server")
    parser.parse_args(argv)
    try:
        MCPServer().serve()
    except BackendSelectionError as exc:
        print(f"HiveMind backend error [{exc.code}]: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
