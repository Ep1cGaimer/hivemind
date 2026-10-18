"""Storage implementations for the HiveMind vertical slice.

The default store is an in-memory graph with immutable node replacement checks
and idempotent edge insertion.  ``FalkorDBStore`` is a lazy persistent backend:
importing this package does not require the optional ``falkordb`` client, and
only registered parameterized queries may be sent.
"""

from __future__ import annotations

import importlib
import json
import re
import threading
from collections.abc import Mapping as ABCMapping
from dataclasses import MISSING, fields, is_dataclass
from types import UnionType
from typing import Any, Iterable, Mapping, get_args, get_origin, get_type_hints

from .domain import (
    GraphEdge,
    DOMAIN_RECORD_TYPES,
    MemoryVersion,
    Review,
    Scope,
    deterministic_id,
    is_domain_record,
    record_to_dict,
    canonical_json,
)
from .queries import (
    EDGE_TYPES,
    EDGE_UPSERT_QUERY_NAMES,
    NODE_LABELS,
    NODE_UPSERT_QUERY_NAMES,
    get_fixed_query,
)


class StoreError(RuntimeError):
    """Base class for deterministic storage failures."""


class ImmutableConflictError(StoreError):
    """Raised when an existing immutable ID is assigned different content."""


class FalkorDBUnavailableError(StoreError):
    """Raised when the optional client or configured graph is unavailable."""


class InMemoryGraphStore:
    """Thread-safe graph store used by the fixture and local API.

    Nodes are immutable by ID.  Re-adding an identical node is idempotent;
    re-adding a changed node fails rather than silently rewriting audit data.
    Relationships are also idempotent by their deterministic ID.
    """

    backend_name = "memory"

    def __init__(self, tenant_id: str = "tenant:demo", project_id: str = "project:hivemind") -> None:
        self.tenant_id = tenant_id
        self.project_id = project_id
        self._nodes: dict[str, Any] = {}
        self._node_types: dict[str, str] = {}
        self._edges: dict[str, GraphEdge] = {}
        self._lock = threading.RLock()

    def clear(self) -> None:
        """Remove every node and edge from this local store."""

        with self._lock:
            self._nodes.clear()
            self._node_types.clear()
            self._edges.clear()

    def add_node(self, record: Any) -> Any:
        """Insert a domain node idempotently, enforcing immutability."""

        if not is_domain_record(record):
            raise TypeError("Only HiveMind domain records can be stored as nodes")
        record_id = getattr(record, "id", None)
        if not isinstance(record_id, str) or not record_id:
            raise ValueError("Domain records require a non-empty string id")
        record_tenant = getattr(record, "tenant_id", self.tenant_id)
        record_project = getattr(record, "project_id", self.project_id)
        if record_tenant != self.tenant_id or record_project != self.project_id:
            raise StoreError("tenant/project binding does not match this graph store")
        with self._lock:
            existing = self._nodes.get(record_id)
            if existing is not None:
                if record_to_dict(existing) != record_to_dict(record):
                    raise ImmutableConflictError(f"Immutable node already exists with different content: {record_id}")
                return existing
            self._nodes[record_id] = record
            self._node_types[record_id] = type(record).__name__
            return record

    def add_nodes(self, records: Iterable[Any]) -> None:
        """Insert a sequence of nodes."""

        for record in records:
            self.add_node(record)

    def add_edge(
        self,
        edge_type: str,
        from_id: str,
        to_id: str,
        properties: Mapping[str, Any] | None = None,
    ) -> GraphEdge:
        """Insert a typed relationship idempotently.

        Both endpoints must already exist so dangling support cannot be
        accidentally manufactured by a caller.
        """

        if not edge_type or not from_id or not to_id:
            raise ValueError("edge_type, from_id, and to_id are required")
        with self._lock:
            if from_id not in self._nodes or to_id not in self._nodes:
                raise StoreError(f"edge endpoint missing: {from_id} -> {to_id}")
            normalized_properties = dict(properties or {})
            edge_id = deterministic_id("edge", edge_type, from_id, to_id, normalized_properties)
            edge = GraphEdge(edge_id, edge_type, from_id, to_id, normalized_properties)
            existing = self._edges.get(edge_id)
            if existing is not None:
                if record_to_dict(existing) != record_to_dict(edge):
                    raise ImmutableConflictError(f"Immutable edge already exists with different content: {edge_id}")
                return existing
            self._edges[edge_id] = edge
            return edge

    def get_node(self, record_id: str) -> Any | None:
        """Return a node by ID, or ``None``."""

        with self._lock:
            return self._nodes.get(record_id)

    def require_node(self, record_id: str) -> Any:
        """Return a node or raise a clear store error."""

        node = self.get_node(record_id)
        if node is None:
            raise StoreError(f"Unknown graph node: {record_id}")
        return node

    def nodes(self, node_type: str | None = None) -> list[Any]:
        """Return stable-sorted nodes, optionally filtered by type name."""

        with self._lock:
            values = list(self._nodes.values())
            if node_type is not None:
                values = [value for value in values if type(value).__name__ == node_type]
            return sorted(values, key=lambda value: (type(value).__name__, getattr(value, "id", "")))

    def edges(self, edge_type: str | None = None) -> list[GraphEdge]:
        """Return stable-sorted relationships, optionally by type."""

        with self._lock:
            values = list(self._edges.values())
            if edge_type is not None:
                values = [value for value in values if value.edge_type == edge_type]
            return sorted(values, key=lambda value: value.id)

    def edges_from(self, from_id: str, edge_type: str | None = None) -> list[GraphEdge]:
        """Return outgoing relationships in deterministic order."""

        return [edge for edge in self.edges(edge_type) if edge.from_id == from_id]

    def edges_to(self, to_id: str, edge_type: str | None = None) -> list[GraphEdge]:
        """Return incoming relationships in deterministic order."""

        return [edge for edge in self.edges(edge_type) if edge.to_id == to_id]

    def scopes(self) -> list[Scope]:
        """Return all scope nodes."""

        return [node for node in self.nodes("Scope") if isinstance(node, Scope)]

    def memories(self) -> list[MemoryVersion]:
        """Return all memory versions."""

        return [node for node in self.nodes("MemoryVersion") if isinstance(node, MemoryVersion)]

    def reviews_for(self, target_id: str) -> list[Review]:
        """Return reviews bound to an exact proposal or memory version."""

        return [
            node
            for node in self.nodes("Review")
            if isinstance(node, Review)
            and (node.reviewed_target_id == target_id or node.memory_version_id == target_id)
        ]

    def memory_for_scope(self, scope_id: str, limit: int | None = None) -> list[MemoryVersion]:
        """Return current memory versions bound exactly to ``scope_id``.

        A correction supersedes only a base in the correction's explicit scope;
        a correction in another scope can never hide or add a memory here.
        """

        values = [
            memory
            for memory in self.memories()
            if memory.scope_id == scope_id and memory.status in {"reviewed", "reviewed_correction"}
        ]
        values.sort(key=lambda memory: (memory.kind != "correction", -memory.version, memory.id))
        if limit is not None:
            return values[:limit]
        return values

    def memory_candidates_for_scope(self, scope_id: str, limit: int | None = None) -> list[MemoryVersion]:
        """Return exact memories, or related scoped evidence when exact memory is absent.

        A cold planner often asks about a scope that has not been exercised yet.
        In that case the gateway must still surface nearby evidence from the same
        company rather than returning an empty result and hiding the missing
        condition. Exact-scope corrections win over fallback evidence.
        """

        exact = self.memory_for_scope(scope_id, limit=limit)
        if exact:
            return exact
        scope = self.get_node(scope_id)
        company_id = getattr(scope, "company_id", None)
        if not isinstance(company_id, str):
            return []
        values: list[MemoryVersion] = []
        for memory in self.memories():
            if memory.status not in {"reviewed", "reviewed_correction"}:
                continue
            memory_scope = self.get_node(memory.scope_id)
            if getattr(memory_scope, "company_id", None) == company_id:
                values.append(memory)
        values.sort(key=lambda memory: (memory.kind != "base", -memory.version, memory.id))
        if limit is not None:
            return values[:limit]
        return values

    def correction_for(self, base_memory_id: str, scope_id: str) -> MemoryVersion | None:
        """Find an immutable correction for exactly one base/scope pair."""

        matches = [
            memory
            for memory in self.memories()
            if memory.kind == "correction"
            and memory.supersedes_memory_id == base_memory_id
            and memory.scope_id == scope_id
        ]
        return sorted(matches, key=lambda memory: memory.id)[0] if matches else None

    def snapshot(self) -> dict[str, Any]:
        """Return a complete JSON-safe local graph snapshot."""

        with self._lock:
            nodes = [
                {"type": self._node_types[node_id], "data": record_to_dict(record)}
                for node_id, record in sorted(self._nodes.items())
            ]
            edges = [record_to_dict(edge) for edge in sorted(self._edges.values(), key=lambda item: item.id)]
            return {
                "backend": self.backend_name,
                "tenant_id": self.tenant_id,
                "project_id": self.project_id,
                "nodes": nodes,
                "edges": edges,
                "counts": {
                    "nodes": len(nodes),
                    "edges": len(edges),
                    "memories": len(self.memories()),
                    "drafts": len(self.nodes("Draft")),
                },
            }


class FalkorDBStore:
    """Persistent FalkorDB implementation of the gateway's graph-store API.

    Domain records are stored as canonical JSON in a single immutable
    ``data_json`` property.  A fixed subtype label and the common
    ``HiveMindNode`` label make the graph inspectable without ever interpolating
    a caller-controlled label.  Relationships use only the internal allowlist
    in :mod:`hivemind.queries`.

    ``run_fixed`` is intentionally the only method that executes Cypher.  All
    other methods select a trusted query name and pass data as parameters.
    """

    backend_name = "falkordb"
    MAX_NODE_READ = 256
    MAX_EDGE_READ = 512
    _GRAPH_NAME_RE = re.compile(r"^[A-Za-z0-9_.:-]+$")
    _DOMAIN_TYPES = {record_type.__name__: record_type for record_type in DOMAIN_RECORD_TYPES}
    _EDGE_TYPES = frozenset(EDGE_TYPES)

    def __init__(
        self,
        graph_name: str = "hivemind_demo",
        *,
        host: str = "localhost",
        port: int = 6379,
        username: str | None = None,
        password: str | None = None,
        tenant_id: str = "tenant:demo",
        project_id: str = "project:hivemind",
        client: Any | None = None,
        graph: Any | None = None,
    ) -> None:
        if not isinstance(graph_name, str) or not self._GRAPH_NAME_RE.fullmatch(graph_name):
            raise ValueError("graph_name must contain only configured graph-name characters")
        if not isinstance(host, str) or not host.strip() or any(character.isspace() for character in host):
            raise ValueError("host must be a non-empty, whitespace-free configured value")
        if isinstance(port, bool) or not isinstance(port, int) or not 1 <= port <= 65535:
            raise ValueError("port must be an integer between 1 and 65535")
        if not isinstance(tenant_id, str) or not tenant_id or not isinstance(project_id, str) or not project_id:
            raise ValueError("tenant_id and project_id must be non-empty configured values")
        self.graph_name = graph_name
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.tenant_id = tenant_id
        self.project_id = project_id
        self._client = client
        self._graph = graph
        self._server_checked = False

    @property
    def connected(self) -> bool:
        """Whether a graph object was explicitly connected or injected."""

        return self._graph is not None

    def connect(self) -> "FalkorDBStore":
        """Lazily import the official client and select only ``graph_name``."""

        if self._graph is not None:
            return self
        if self._client is None:
            try:
                module = importlib.import_module("falkordb")
            except ImportError as exc:
                raise FalkorDBUnavailableError(
                    "Optional dependency 'falkordb' is not installed; use the memory backend or install requirements.lock"
                ) from exc
            client_type = getattr(module, "FalkorDB", None)
            if client_type is None:
                raise FalkorDBUnavailableError("Installed falkordb client does not expose FalkorDB")
            kwargs: dict[str, Any] = {"host": self.host, "port": self.port,
                                      "socket_connect_timeout": 2, "socket_timeout": 5}
            if self.username is not None:
                kwargs["username"] = self.username
            if self.password is not None:
                kwargs["password"] = self.password
            try:
                self._client = client_type(**kwargs)
            except Exception as exc:  # official client constructor details vary by release
                raise FalkorDBUnavailableError(f"Could not construct the configured FalkorDB client: {exc}") from exc
        select_graph = getattr(self._client, "select_graph", None)
        if not callable(select_graph):
            raise FalkorDBUnavailableError("FalkorDB client does not expose select_graph")
        try:
            self._graph = select_graph(self.graph_name)
        except Exception as exc:
            raise FalkorDBUnavailableError(f"Could not select the configured FalkorDB graph: {exc}") from exc
        return self

    @staticmethod
    def _rows(result: Any) -> list[Any]:
        """Normalize official and small injected graph-client result shapes."""

        rows = getattr(result, "result_set", result)
        if rows is None:
            return []
        if isinstance(rows, Mapping):
            return [rows]
        try:
            return list(rows)
        except TypeError as exc:
            raise FalkorDBUnavailableError("FalkorDB returned an unreadable fixed-query result") from exc

    @staticmethod
    def _value(row: Any, index: int, key: str) -> Any:
        if isinstance(row, Mapping):
            return row.get(key)
        try:
            return row[index]
        except (IndexError, KeyError, TypeError) as exc:
            raise FalkorDBUnavailableError(f"FalkorDB fixed-query result is missing {key}") from exc

    def run_fixed(self, query_name: str, params: Mapping[str, Any]) -> Any:
        """Execute one registered parameterized query; raw Cypher is impossible."""

        query = get_fixed_query(query_name)
        if not isinstance(params, Mapping):
            raise TypeError("params must be a mapping")
        bound_params = dict(params)
        for binding in ("tenant_id", "project_id"):
            if binding in bound_params and bound_params[binding] != getattr(self, binding):
                raise StoreError(f"{binding} is bound to the configured HiveMind graph")
            bound_params[binding] = getattr(self, binding)
        for bounded_key, maximum in (
            ("max_depth", 4),
            ("limit", 1025 if query_name.startswith('git_') else 8),
            ("max_items", 64),
            ("memory_limit", 8),
            ("path_limit", 8),
            ("node_limit", self.MAX_NODE_READ),
            ("edge_limit", self.MAX_EDGE_READ),
        ):
            if bounded_key in bound_params:
                value = bound_params[bounded_key]
                if isinstance(value, bool) or not isinstance(value, int) or value < 0 or value > maximum:
                    raise StoreError(f"{bounded_key} exceeds the fixed HiveMind query bound")
        defaults = {
            "state": {"node_limit": self.MAX_NODE_READ},
            "node_list": {"node_limit": self.MAX_NODE_READ},
            "edge_list": {"edge_limit": self.MAX_EDGE_READ, "edge_type": "", "from_id": "", "to_id": ""},
            "recall_context": {"memory_limit": 8},
            "inspect_evidence": {"path_limit": 8, "node_limit": self.MAX_NODE_READ},
        }
        for key, value in defaults.get(query_name, {}).items():
            bound_params.setdefault(key, value)
        self.connect()
        query_method = getattr(self._graph, "query", None)
        if not callable(query_method):
            raise FalkorDBUnavailableError("Selected FalkorDB graph does not expose query")
        try:
            # The pinned official SDK supports a server-side millisecond timeout.
            # Do not silently retry without it: bounded path depth can still
            # produce expensive traversal in a merge-heavy commit DAG.
            return query_method(query, params=bound_params, timeout=2000)
        except Exception as exc:
            raise FalkorDBUnavailableError(f"Fixed FalkorDB query failed: {exc}") from exc

    @classmethod
    def _record_from_json(cls, data_json: Any, row_type: Any = None) -> Any:
        if not isinstance(data_json, str):
            raise FalkorDBUnavailableError("FalkorDB node data is not stored as JSON")
        try:
            data = json.loads(data_json)
        except (TypeError, json.JSONDecodeError) as exc:
            raise FalkorDBUnavailableError("FalkorDB node data is not valid JSON") from exc
        if not isinstance(data, dict):
            raise FalkorDBUnavailableError("FalkorDB node data must be a JSON object")
        node_type = data.get("node_type")
        if node_type not in cls._DOMAIN_TYPES:
            raise FalkorDBUnavailableError("FalkorDB returned an unknown HiveMind node type")
        if row_type is not None and row_type != node_type:
            raise FalkorDBUnavailableError("FalkorDB node label and serialized node type disagree")
        record_type = cls._DOMAIN_TYPES[node_type]
        type_hints = get_type_hints(record_type)
        kwargs: dict[str, Any] = {}
        for field in fields(record_type):
            if field.name not in data:
                if field.default is not MISSING:
                    kwargs[field.name] = field.default
                    continue
                if field.default_factory is not MISSING:  # type: ignore[comparison-overlap]
                    kwargs[field.name] = field.default_factory()  # type: ignore[misc]
                    continue
                raise FalkorDBUnavailableError(f"FalkorDB node is missing immutable field {field.name}")
            kwargs[field.name] = cls._restore_value(data[field.name], type_hints.get(field.name, field.type))
        try:
            return record_type(**kwargs)
        except (TypeError, ValueError) as exc:
            raise FalkorDBUnavailableError("FalkorDB node could not be reconstructed as a HiveMind record") from exc

    @classmethod
    def _restore_value(cls, value: Any, annotation: Any) -> Any:
        """Restore tuple/mapping containers lost by JSON without changing values."""

        origin = get_origin(annotation)
        args = get_args(annotation)
        if origin in (UnionType,):
            non_none = [item for item in args if item is not type(None)]
            if value is None:
                return None
            return cls._restore_value(value, non_none[0]) if len(non_none) == 1 else value
        if str(origin) == "typing.Union":
            non_none = [item for item in args if item is not type(None)]
            if value is None:
                return None
            return cls._restore_value(value, non_none[0]) if len(non_none) == 1 else value
        if origin is tuple:
            item_type = args[0] if args and args[-1] is Ellipsis else None
            if item_type is None and args:
                return tuple(cls._restore_value(item, item_type) for item, item_type in zip(value, args))
            return tuple(cls._restore_value(item, item_type or Any) for item in value)
        if origin in (dict, ABCMapping):
            value_type = args[1] if len(args) > 1 else Any
            key_type = args[0] if args else Any
            return {
                cls._restore_value(key, key_type): cls._restore_value(item, value_type)
                for key, item in value.items()
            }
        if origin is list:
            item_type = args[0] if args else Any
            return [cls._restore_value(item, item_type) for item in value]
        return value

    def _node_from_row(self, row: Any) -> Any:
        record_id = self._value(row, 0, "id")
        row_type = self._value(row, 1, "node_type")
        tenant_id = self._value(row, 2, "tenant_id")
        project_id = self._value(row, 3, "project_id")
        if tenant_id != self.tenant_id or project_id != self.project_id:
            raise StoreError("tenant/project binding does not match this graph store")
        record = self._record_from_json(self._value(row, 4, "data_json"), row_type)
        if getattr(record, "id", None) != record_id:
            raise FalkorDBUnavailableError("FalkorDB node ID and serialized ID disagree")
        return record

    def _find_node_any(self, record_id: str) -> Any | None:
        rows = self._rows(self.run_fixed("node_lookup_any", {"id": record_id}))
        return self._node_from_row(rows[0]) if rows else None

    @staticmethod
    def _node_upsert_params(record_id: str, expected_data: Mapping[str, Any]) -> dict[str, Any]:
        """Return scalar query metadata alongside the canonical record JSON.

        The JSON payload is the immutable source of truth.  These duplicated
        scalar fields are only query indexes for the fixed recall/state
        templates; empty strings represent absent optional values so the
        properties remain FalkorDB-compatible primitives.
        """

        def text(name: str) -> str:
            value = expected_data.get(name)
            return value if isinstance(value, str) else ""

        return {
            "id": record_id,
            "tenant_id": text("tenant_id"),
            "project_id": text("project_id"),
            "data_json": canonical_json(expected_data),
            "scope_id": text("scope_id"),
            "status": text("status"),
            "kind": text("kind"),
            "company_id": text("company_id"),
            "memory_version_id": text("memory_version_id"),
            "reviewed_target_id": text("reviewed_target_id"),
            "created_at": text("created_at"),
            "workspace_project_id": text("workspace_project_id"),
            "repo_id": text("repo_id"),
            "branch_id": text("branch_id"),
            "key": text("key"),
            "head": text("head"),
        }

    def add_node(self, record: Any) -> Any:
        """Persist one immutable domain record idempotently."""

        if not is_domain_record(record):
            raise TypeError("Only HiveMind domain records can be stored as nodes")
        record_id = getattr(record, "id", None)
        node_type = type(record).__name__
        if not isinstance(record_id, str) or not record_id:
            raise ValueError("Domain records require a non-empty string id")
        if node_type not in NODE_LABELS:
            raise StoreError("Domain record type is not in the fixed HiveMind node allowlist")
        if getattr(record, "tenant_id", self.tenant_id) != self.tenant_id or getattr(record, "project_id", self.project_id) != self.project_id:
            raise StoreError("tenant/project binding does not match this graph store")
        expected_data = record_to_dict(record)
        existing = self._find_node_any(record_id)
        if existing is not None:
            if record_to_dict(existing) != expected_data:
                raise ImmutableConflictError(f"Immutable node already exists with different content: {record_id}")
        result = self.run_fixed(
            NODE_UPSERT_QUERY_NAMES[node_type],
            self._node_upsert_params(record_id, expected_data),
        )
        rows = self._rows(result)
        if not rows:
            raise StoreError(f"FalkorDB did not persist node: {record_id}")
        stored = self._node_from_row(rows[0])
        if record_to_dict(stored) != expected_data:
            raise ImmutableConflictError(f"Immutable node already exists with different content: {record_id}")
        return stored

    def add_nodes(self, records: Iterable[Any]) -> None:
        """Persist a sequence of immutable domain records."""

        for record in records:
            self.add_node(record)

    @staticmethod
    def _properties_json(properties: Mapping[str, Any] | None) -> str:
        if properties is None:
            return "{}"
        if not isinstance(properties, Mapping):
            raise TypeError("edge properties must be a mapping")
        try:
            return canonical_json(dict(properties))
        except TypeError as exc:
            raise ValueError(f"edge properties must be JSON-serializable: {exc}") from exc

    def _edge_from_row(self, row: Any) -> GraphEdge:
        edge_id = self._value(row, 0, "id")
        edge_type = self._value(row, 1, "edge_type")
        from_id = self._value(row, 2, "from_id")
        to_id = self._value(row, 3, "to_id")
        tenant_id = self._value(row, 4, "tenant_id")
        project_id = self._value(row, 5, "project_id")
        if tenant_id != self.tenant_id or project_id != self.project_id:
            raise StoreError("tenant/project binding does not match this graph store")
        if edge_type not in self._EDGE_TYPES:
            raise FalkorDBUnavailableError("FalkorDB returned a relationship outside the HiveMind allowlist")
        properties_json = self._value(row, 6, "properties_json")
        try:
            properties = json.loads(properties_json) if isinstance(properties_json, str) else None
        except json.JSONDecodeError as exc:
            raise FalkorDBUnavailableError("FalkorDB relationship properties are not valid JSON") from exc
        if not isinstance(properties, dict):
            raise FalkorDBUnavailableError("FalkorDB relationship properties must be a JSON object")
        return GraphEdge(str(edge_id), edge_type, str(from_id), str(to_id), properties)

    def _find_edge_any(self, edge_id: str) -> GraphEdge | None:
        rows = self._rows(self.run_fixed("edge_lookup", {"edge_id": edge_id}))
        return self._edge_from_row(rows[0]) if rows else None

    def _validate_edge_type(self, edge_type: str) -> None:
        if not isinstance(edge_type, str) or edge_type not in self._EDGE_TYPES:
            raise StoreError("edge_type is not in the fixed HiveMind relationship allowlist")

    def add_edge(
        self,
        edge_type: str,
        from_id: str,
        to_id: str,
        properties: Mapping[str, Any] | None = None,
    ) -> GraphEdge:
        """Persist one allowlisted, immutable relationship idempotently."""

        self._validate_edge_type(edge_type)
        if not isinstance(from_id, str) or not from_id or not isinstance(to_id, str) or not to_id:
            raise ValueError("edge_type, from_id, and to_id are required")
        properties_json = self._properties_json(properties)
        normalized_properties = json.loads(properties_json)
        edge_id = deterministic_id("edge", edge_type, from_id, to_id, normalized_properties)
        expected = GraphEdge(edge_id, edge_type, from_id, to_id, normalized_properties)
        existing = self._find_edge_any(edge_id)
        if existing is not None:
            if record_to_dict(existing) != record_to_dict(expected):
                raise ImmutableConflictError(f"Immutable edge already exists with different content: {edge_id}")
            return existing
        result = self.run_fixed(
            EDGE_UPSERT_QUERY_NAMES[edge_type],
            {
                "edge_id": edge_id,
                "from_id": from_id,
                "to_id": to_id,
                "properties_json": properties_json,
            },
        )
        rows = self._rows(result)
        if not rows:
            raise StoreError(f"edge endpoint missing or outside the configured tenant/project: {from_id} -> {to_id}")
        stored = self._edge_from_row(rows[0])
        if record_to_dict(stored) != record_to_dict(expected):
            raise ImmutableConflictError(f"Immutable edge already exists with different content: {edge_id}")
        return stored

    def get_node(self, record_id: str) -> Any | None:
        """Return one bound node by ID, or ``None`` without cross-tenant leakage."""

        if not isinstance(record_id, str) or not record_id:
            return None
        rows = self._rows(self.run_fixed("node_lookup", {"id": record_id}))
        return self._node_from_row(rows[0]) if rows else None

    def require_node(self, record_id: str) -> Any:
        """Return a bound node or raise a clear store error."""

        node = self.get_node(record_id)
        if node is None:
            raise StoreError(f"Unknown graph node: {record_id}")
        return node

    def nodes(self, node_type: str | None = None) -> list[Any]:
        """Return bounded, stable-sorted bound nodes."""

        if node_type is not None and node_type not in NODE_LABELS:
            raise StoreError("node_type is not in the fixed HiveMind node allowlist")
        rows = self._rows(self.run_fixed("node_list", {"node_type": node_type or ""}))
        values = [self._node_from_row(row) for row in rows]
        return sorted(values, key=lambda value: (type(value).__name__, getattr(value, "id", "")))

    def edges(self, edge_type: str | None = None) -> list[GraphEdge]:
        """Return bounded, stable-sorted allowlisted relationships."""

        if edge_type is not None:
            self._validate_edge_type(edge_type)
        rows = self._rows(self.run_fixed("edge_list", {"edge_type": edge_type or "", "from_id": "", "to_id": ""}))
        return sorted((self._edge_from_row(row) for row in rows), key=lambda value: value.id)

    def edges_from(self, from_id: str, edge_type: str | None = None) -> list[GraphEdge]:
        """Return bounded outgoing relationships in deterministic order."""

        if not isinstance(from_id, str) or not from_id:
            return []
        if edge_type is not None:
            self._validate_edge_type(edge_type)
        rows = self._rows(self.run_fixed("edge_list", {"edge_type": edge_type or "", "from_id": from_id, "to_id": ""}))
        return sorted((self._edge_from_row(row) for row in rows), key=lambda value: value.id)

    def edges_to(self, to_id: str, edge_type: str | None = None) -> list[GraphEdge]:
        """Return bounded incoming relationships in deterministic order."""

        if not isinstance(to_id, str) or not to_id:
            return []
        if edge_type is not None:
            self._validate_edge_type(edge_type)
        rows = self._rows(self.run_fixed("edge_list", {"edge_type": edge_type or "", "from_id": "", "to_id": to_id}))
        return sorted((self._edge_from_row(row) for row in rows), key=lambda value: value.id)

    def scopes(self) -> list[Scope]:
        """Return all bound scope nodes."""

        return [node for node in self.nodes("Scope") if isinstance(node, Scope)]

    def memories(self) -> list[MemoryVersion]:
        """Return all bound memory versions."""

        return [node for node in self.nodes("MemoryVersion") if isinstance(node, MemoryVersion)]

    def reviews_for(self, target_id: str) -> list[Review]:
        """Return bounded reviews for an exact proposal or memory target."""

        return [
            node
            for node in self.nodes("Review")
            if isinstance(node, Review)
            and (node.reviewed_target_id == target_id or node.memory_version_id == target_id)
        ]

    def memory_for_scope(self, scope_id: str, limit: int | None = None) -> list[MemoryVersion]:
        """Return current reviewed memories bound exactly to one scope."""

        if limit is not None and (isinstance(limit, bool) or not isinstance(limit, int) or limit < 0 or limit > self.MAX_NODE_READ):
            raise StoreError("memory limit exceeds the fixed HiveMind read bound")
        values = [
            memory
            for memory in self.memories()
            if memory.scope_id == scope_id and memory.status in {"reviewed", "reviewed_correction"}
        ]
        values.sort(key=lambda memory: (memory.kind != "correction", -memory.version, memory.id))
        return values[:limit] if limit is not None else values

    def memory_candidates_for_scope(self, scope_id: str, limit: int | None = None) -> list[MemoryVersion]:
        """Return exact memories or bounded same-company nearby evidence."""

        exact = self.memory_for_scope(scope_id, limit=limit)
        if exact:
            return exact
        scope = self.get_node(scope_id)
        company_id = getattr(scope, "company_id", None)
        if not isinstance(company_id, str):
            return []
        values: list[MemoryVersion] = []
        for memory in self.memories():
            if memory.status not in {"reviewed", "reviewed_correction"}:
                continue
            memory_scope = self.get_node(memory.scope_id)
            if getattr(memory_scope, "company_id", None) == company_id:
                values.append(memory)
        values.sort(key=lambda memory: (memory.kind != "base", -memory.version, memory.id))
        return values[:limit] if limit is not None else values

    def correction_for(self, base_memory_id: str, scope_id: str) -> MemoryVersion | None:
        """Find one immutable correction for exactly one base/scope pair."""

        matches = [
            memory
            for memory in self.memories()
            if memory.kind == "correction"
            and memory.supersedes_memory_id == base_memory_id
            and memory.scope_id == scope_id
        ]
        return sorted(matches, key=lambda memory: memory.id)[0] if matches else None

    def clear(self) -> None:
        """Clear only bound HiveMind nodes in this configured graph."""

        self.run_fixed("clear_graph", {})

    def snapshot(self) -> dict[str, Any]:
        """Return a bounded JSON-safe gateway snapshot from persisted graph data."""

        nodes = [
            {"type": type(record).__name__, "data": record_to_dict(record)}
            for record in self.nodes()
        ]
        edges = [record_to_dict(edge) for edge in self.edges()]
        memories = [record for record in self.nodes("MemoryVersion") if isinstance(record, MemoryVersion)]
        drafts = [record for record in self.nodes("Draft")]
        return {
            "backend": self.backend_name,
            "graph_name": self.graph_name,
            "tenant_id": self.tenant_id,
            "project_id": self.project_id,
            "nodes": nodes,
            "edges": edges,
            "counts": {
                "nodes": len(nodes),
                "edges": len(edges),
                "memories": len(memories),
                "drafts": len(drafts),
            },
            "bounded": True,
            "limits": {"nodes": self.MAX_NODE_READ, "edges": self.MAX_EDGE_READ},
        }

    def check_server(self) -> bool:
        """Run a bounded fixed health query and report whether it succeeded."""

        rows = self._rows(self.run_fixed("health", {}))
        healthy = bool(rows) and self._value(rows[0], 0, "ok") == 1
        if not healthy:
            raise FalkorDBUnavailableError("FalkorDB health query returned no successful result")
        self._server_checked = True
        return True

    def state(self) -> dict[str, Any]:
        """Return adapter metadata; gateway state uses :meth:`snapshot`."""

        return {
            "backend": self.backend_name,
            "graph_name": self.graph_name,
            "connected_handle": self.connected,
            "server_checked": self._server_checked,
            "query_registry": sorted(
                name
                for name in (
                    "clear_graph",
                    "edge_list",
                    "health",
                    "node_list",
                    "recall_context",
                    "inspect_evidence",
                    "create_correction",
                    "save_draft",
                    "state",
                )
            ),
        }
