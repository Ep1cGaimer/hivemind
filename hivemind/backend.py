"""Runtime backend selection for HiveMind entry points.

Memory mode remains the dependency-free default.  An explicit FalkorDB
selection constructs a live, graph-specific store, verifies it with a bounded
query, and idempotently seeds the deterministic Juniper fixture.  Failures are
reported instead of silently changing the selected backend to memory.
"""

from __future__ import annotations

import os
from typing import Mapping

from .fixture import seed_demo_store
from .store import FalkorDBStore, StoreError


DEFAULT_BACKEND = "memory"
FALKORDB_BACKEND = "falkordb"
FALKORDB_ENV_KEYS = (
    "FALKORDB_HOST",
    "FALKORDB_PORT",
    "FALKORDB_GRAPH",
    "FALKORDB_USERNAME",
    "FALKORDB_PASSWORD",
)


class BackendSelectionError(RuntimeError):
    """Raised when the configured backend cannot serve the runtime."""

    def __init__(self, code: str, message: str) -> None:
        self.code = code
        super().__init__(message)


def _normalize_backend(value: object) -> str:
    """Normalize one backend setting or raise a stable configuration error."""

    if value is None:
        return DEFAULT_BACKEND
    if not isinstance(value, str):
        raise BackendSelectionError("INVALID_BACKEND", "HIVEMIND_BACKEND must be a string")
    return value.strip().lower() or DEFAULT_BACKEND


def select_backend(environ: Mapping[str, str] | None = None) -> str:
    """Return the normalized backend selected by ``HIVEMIND_BACKEND``."""

    source = os.environ if environ is None else environ
    return _normalize_backend(source.get("HIVEMIND_BACKEND", DEFAULT_BACKEND))


def _required_live_value(source: Mapping[str, str], key: str) -> str:
    value = source.get(key)
    if not isinstance(value, str) or not value.strip():
        raise BackendSelectionError(
            "INVALID_FALKORDB_CONFIG",
            "HIVEMIND_BACKEND=falkordb requires explicit "
            "FALKORDB_HOST, FALKORDB_PORT, and FALKORDB_GRAPH settings; "
            "no fallback to memory was performed",
        )
    return value.strip()


def _live_store_config(source: Mapping[str, str]) -> dict[str, object]:
    """Parse the live profile without allowing malformed values to reach Redis."""

    host = _required_live_value(source, "FALKORDB_HOST")
    graph = _required_live_value(source, "FALKORDB_GRAPH")
    raw_port = _required_live_value(source, "FALKORDB_PORT")
    try:
        port = int(raw_port, 10)
    except ValueError as exc:
        raise BackendSelectionError("INVALID_FALKORDB_CONFIG", "FALKORDB_PORT must be a decimal integer") from exc
    if not 1 <= port <= 65535:
        raise BackendSelectionError("INVALID_FALKORDB_CONFIG", "FALKORDB_PORT must be between 1 and 65535")
    return {
        "host": host,
        "port": port,
        "graph_name": graph,
        "username": source.get("FALKORDB_USERNAME") or None,
        "password": source.get("FALKORDB_PASSWORD") or None,
    }


def create_store(
    environ: Mapping[str, str] | None = None,
    *,
    backend: str | None = None,
    reset: bool = False,
):
    """Create and seed the selected store.

    ``reset=True`` is reserved for the HTTP runtime reset path: it clears only
    the configured tenant/project data in the configured graph before seeding.
    Normal live construction never clears the graph, so a new store/gateway
    instance sees persisted corrections and drafts.
    """

    source = os.environ if environ is None else environ
    selected = _normalize_backend(backend) if backend is not None else select_backend(source)
    if selected == DEFAULT_BACKEND:
        return seed_demo_store()
    if selected == FALKORDB_BACKEND:
        config = _live_store_config(source)
        try:
            store = FalkorDBStore(**config)
            store.connect()
            store.check_server()
            seed_demo_store(store, clear=reset)
            return store
        except BackendSelectionError:
            raise
        except (StoreError, TypeError, ValueError) as exc:
            raise BackendSelectionError(
                "BACKEND_UNAVAILABLE",
                f"Configured FalkorDB backend could not start safely: {exc}; no fallback to memory was performed",
            ) from exc
    raise BackendSelectionError(
        "INVALID_BACKEND",
        f"Unsupported HIVEMIND_BACKEND={selected!r}; available runtime backends are "
        f"{DEFAULT_BACKEND!r} and {FALKORDB_BACKEND!r}",
    )
