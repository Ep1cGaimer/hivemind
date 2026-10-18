"""Small local identity and coding-agent token service.

This is intentionally not an enterprise identity provider.  It gives the
local workspace a useful identity boundary without adding dependencies:
people sign in with configured local credentials, and each person can mint a
signed bearer token for a coding agent.  Tokens can be verified by a separate
MCP process when it receives the same ``HIVEMIND_AUTH_SECRET``.
"""

from __future__ import annotations

import base64
from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import hmac
import json
import os
import secrets
import threading
from typing import Any, Mapping
from .domain import GitRecord
from .store import ImmutableConflictError


DEFAULT_AUTH_SECRET = "local-hivemind-secret-change-me"


@dataclass(frozen=True)
class Identity:
    user_id: str
    display_name: str
    role: str = "member"

    def public(self) -> dict[str, str]:
        return {"user_id": self.user_id, "display_name": self.display_name, "role": self.role}


@dataclass(frozen=True)
class AgentTokenRecord:
    token_id: str
    user_id: str
    label: str
    created_at: str
    token_preview: str
    project_id: str | None = None

    def public(self) -> dict[str, str]:
        return {
            "token_id": self.token_id,
            "user_id": self.user_id,
            "label": self.label,
            "created_at": self.created_at,
            "token_preview": self.token_preview,
            "project_id": self.project_id,
        }


class AuthManager:
    """Authenticate local users and sign agent bearer tokens."""

    SESSION_COOKIE = "hivemind_session"
    AUTH_HEADER = "Authorization"

    def __init__(self, environ: Mapping[str, str] | None = None, store: Any = None) -> None:
        source = os.environ if environ is None else environ
        self.store = store
        configured_secret = source.get('HIVEMIND_AUTH_SECRET')
        if not configured_secret or configured_secret == DEFAULT_AUTH_SECRET:
            key = 'auth:signing-secret'
            prior = store.get_node(key) if store is not None else None
            configured_secret = prior.data['secret'] if isinstance(prior, GitRecord) else secrets.token_urlsafe(48)
            if store is not None and prior is None:
                try:
                    store.add_node(GitRecord(key, store.tenant_id, store.project_id, '', '', 'signing_secret', key,
                        '', '', '', '', '', self._now(), {'secret': configured_secret}))
                except ImmutableConflictError:
                    winner = store.get_node(key)
                    if not isinstance(winner, GitRecord) or winner.kind != 'signing_secret':
                        raise
                    configured_secret = winner.data['secret']
        self.secret = configured_secret.encode('utf-8')
        self._users = self._load_users(source)
        self._sessions: dict[str, Identity] = {}
        self._agent_tokens: dict[str, AgentTokenRecord] = {}
        self._revoked: set[str] = set()
        self._lock = threading.RLock()

    def _persist(self, key: str, kind: str, data: dict, project: str = '') -> None:
        if self.store is not None:
            old = self.store.get_node(key)
            self.store.add_node(GitRecord(key, self.store.tenant_id, self.store.project_id,
                project, '', kind, key, '', '', '', '', '', old.created_at if old else self._now(), data))

    def revoke(self, identity: Identity, token_id: str, project_id: str) -> bool:
        record = self._token_record(token_id)
        if not record or record.project_id != project_id:
            return False
        self._persist('auth:revoked:' + token_id, 'revoked_token', {'token_id': token_id}, project_id)
        with self._lock:
            self._revoked.add(token_id)
        return True

    def _token_record(self, token_id: str) -> AgentTokenRecord | None:
        if self.store is not None:
            n = self.store.get_node('auth:token:' + token_id)
            return AgentTokenRecord(**n.data) if isinstance(n, GitRecord) and n.kind == 'agent_token' else None
        return self._agent_tokens.get(token_id)

    @staticmethod
    def _load_users(source: Mapping[str, str]) -> dict[str, tuple[str, Identity]]:
        configured = source.get("HIVEMIND_USERS", "").strip()
        entries = [item.strip() for item in configured.split(",") if item.strip()] if configured else []
        users: dict[str, tuple[str, Identity]] = {}
        if not entries:
            password = source.get("HIVEMIND_OPERATOR_PASSWORD", "operator")
            users["operator"] = (password, Identity("operator", "Operator", "operator"))
            return users
        for entry in entries:
            username, separator, password = entry.partition("=")
            username = username.strip()
            if not separator or not username or not password:
                continue
            role = "operator" if username == "operator" else "member"
            users[username] = (password, Identity(username, username, role))
        if not users:
            raise ValueError("HIVEMIND_USERS must contain entries in username=password format")
        return users

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")

    @staticmethod
    def _encode(value: Mapping[str, Any]) -> str:
        raw = json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")
        return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")

    @staticmethod
    def _decode(value: str) -> dict[str, Any] | None:
        try:
            padded = value + "=" * (-len(value) % 4)
            decoded = json.loads(base64.urlsafe_b64decode(padded.encode("ascii")).decode("utf-8"))
        except (ValueError, UnicodeDecodeError, json.JSONDecodeError):
            return None
        return decoded if isinstance(decoded, dict) else None

    def _signature(self, payload: str) -> str:
        return hmac.new(self.secret, payload.encode("ascii"), hashlib.sha256).hexdigest()

    def login(self, username: Any, password: Any) -> tuple[str, Identity] | None:
        if not isinstance(username, str) or not isinstance(password, str):
            return None
        entry = self._users.get(username.strip())
        if entry is None:
            return None
        expected_password, identity = entry
        if not hmac.compare_digest(password, expected_password):
            return None
        session = "hm_session_" + secrets.token_urlsafe(24)
        with self._lock:
            self._sessions[session] = identity
        return session, identity

    def logout(self, session: str | None) -> None:
        if isinstance(session, str):
            with self._lock:
                self._sessions.pop(session, None)

    def create_agent_token(
        self,
        identity: Identity,
        label: Any,
        project_id: str | None = None,
    ) -> tuple[str, AgentTokenRecord]:
        clean_label = label.strip() if isinstance(label, str) else ""
        if not clean_label or len(clean_label) > 80:
            raise ValueError("label must be a non-empty string of at most 80 characters")
        token_id = secrets.token_hex(8)
        payload = self._encode(
            {
                "token_id": token_id,
                "user_id": identity.user_id,
                "display_name": identity.display_name,
                "role": identity.role,
                "label": clean_label,
                "project_id": project_id,
            }
        )
        token = f"hm_agent_{payload}.{self._signature(payload)}"
        record = AgentTokenRecord(token_id, identity.user_id, clean_label, self._now(), token[:18] + "…", project_id)
        with self._lock:
            self._agent_tokens[token_id] = record
        self._persist('auth:token:' + token_id, 'agent_token', record.public(), project_id or '')
        return token, record

    def authenticate_agent_token(self, token: Any) -> Identity | None:
        context = self.authenticate_agent_context(token)
        return context[0] if context else None

    def authenticate_agent_context(self, token: Any) -> tuple[Identity, str | None] | None:
        if not isinstance(token, str) or not token.startswith("hm_agent_"):
            return None
        raw = token[len("hm_agent_"):]
        if "." not in raw:
            return None
        payload, signature = raw.rsplit(".", 1)
        expected = self._signature(payload)
        if not hmac.compare_digest(signature, expected):
            return None
        decoded = self._decode(payload)
        if decoded is None:
            return None
        user_id = decoded.get("user_id")
        token_id = decoded.get('token_id')
        if not isinstance(token_id, str) or token_id in self._revoked:
            return None
        if self.store is not None and self.store.get_node('auth:revoked:' + token_id) is not None:
            return None
        record = self._token_record(token_id)
        if record is None or record.user_id != user_id or not record.project_id or record.project_id != decoded.get('project_id'):
            return None
        entry = self._users.get(user_id) if isinstance(user_id, str) else None
        return (entry[1], decoded.get("project_id") if isinstance(decoded.get("project_id"), str) else None) if entry else None

    def known_users(self) -> list[Identity]:
        return [identity for _, identity in self._users.values()]

    def authenticate(self, authorization: str | None = None, cookie_header: str | None = None) -> Identity | None:
        context = self.authenticate_context(authorization, cookie_header)
        return context[0] if context else None

    def authenticate_context(
        self,
        authorization: str | None = None,
        cookie_header: str | None = None,
    ) -> tuple[Identity, str | None] | None:
        if isinstance(authorization, str) and authorization.lower().startswith("bearer "):
            return self.authenticate_agent_context(authorization[7:].strip())
        cookies: dict[str, str] = {}
        for item in (cookie_header or "").split(";"):
            key, separator, value = item.strip().partition("=")
            if separator:
                cookies[key] = value
        session = cookies.get(self.SESSION_COOKIE)
        with self._lock:
            identity = self._sessions.get(session) if session else None
        return (identity, None) if identity else None

    def agent_records_for(self, identity: Identity, project_id: str | None = None) -> list[AgentTokenRecord]:
        with self._lock:
            if self.store is not None:
                from .git_graph import RepositoryGraph
                nodes, _ = RepositoryGraph(self.store, project_id or '', '').list('agent_token')
                records = [AgentTokenRecord(**n.data) for n in nodes]
            else:
                records = list(self._agent_tokens.values())
            return [record for record in records if record.user_id == identity.user_id]
