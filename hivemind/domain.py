"""Domain types and deterministic identity helpers for HiveMind.

The records in this module are intentionally boring dataclasses.  They make
the audit distinctions visible in Python and serialize to ordinary JSON
without requiring an ORM or a graph client.
"""

from __future__ import annotations

from dataclasses import dataclass, fields, is_dataclass
import hashlib
import json
import re
from typing import Any, Mapping, TypeVar


JSONPrimitive = None | bool | int | float | str
JSONValue = JSONPrimitive | list["JSONValue"] | dict[str, "JSONValue"]
T = TypeVar("T")


def canonical_json(value: Any) -> str:
    """Return a stable JSON representation used for hashes and IDs."""

    return json.dumps(
        to_jsonable(value),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )


def content_hash(value: Any) -> str:
    """Hash content deterministically using SHA-256.

    Hashes are duplicate detectors and binding inputs.  They are not a claim
    that two observations are independent or true.
    """

    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def _slug(value: Any) -> str:
    text = str(value).strip().lower()
    text = re.sub(r"[^a-z0-9]+", "-", text).strip("-")
    return text or "item"


def deterministic_id(kind: str, *parts: Any) -> str:
    """Create a stable, project-local ID from a kind and canonical parts.

    The readable prefix is useful in logs while the digest prevents accidental
    collisions from punctuation or ambiguous concatenation.
    """

    normalized = [to_jsonable(part) for part in parts]
    digest = hashlib.sha256(canonical_json(normalized).encode("utf-8")).hexdigest()[:16]
    prefix = _slug(kind)
    return f"{prefix}:{digest}"


def to_jsonable(value: Any) -> JSONValue:
    """Recursively convert supported values to JSON-serializable values."""

    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    if is_dataclass(value):
        return {field.name: to_jsonable(getattr(value, field.name)) for field in fields(value)}
    if isinstance(value, Mapping):
        return {str(key): to_jsonable(item) for key, item in value.items()}
    if isinstance(value, (tuple, list, set, frozenset)):
        return [to_jsonable(item) for item in value]
    raise TypeError(f"Value of type {type(value).__name__} is not JSON serializable")


def record_to_dict(record: Any) -> dict[str, JSONValue]:
    """Serialize one domain record and add its conceptual node type."""

    if not is_dataclass(record):
        raise TypeError("record_to_dict expects a dataclass record")
    result = to_jsonable(record)
    if not isinstance(result, dict):  # pragma: no cover - guarded by dataclass shape
        raise TypeError("domain records must serialize to objects")
    result.setdefault("node_type", type(record).__name__)
    return result


@dataclass(frozen=True)
class CompanyEntity:
    """A tenant/project-qualified company, capability, or other entity."""

    id: str
    canonical_id: str
    kind: str
    name: str
    tenant_id: str
    project_id: str
    aliases: tuple[str, ...] = ()


@dataclass(frozen=True)
class Scope:
    """An exact environment in which a memory may apply."""

    id: str
    tenant_id: str
    project_id: str
    company_id: str
    stage: str
    environment: str
    qualifiers: Mapping[str, str]
    unknowns: tuple[str, ...] = ()
    valid_from: str | None = None
    valid_to: str | None = None


@dataclass(frozen=True)
class SourcePassage:
    """An immutable, source-backed passage with version and span metadata."""

    id: str
    tenant_id: str
    project_id: str
    artifact_id: str
    version: str
    content_hash: str
    span_start: int
    span_end: int
    text: str
    source_uri: str
    observed_at: str
    source_stated_at: str | None = None
    scope_id: str | None = None


@dataclass(frozen=True)
class AgentRun:
    """An observed agent session or deterministic tool-run receipt."""

    id: str
    tenant_id: str
    project_id: str
    role: str
    session_id: str
    input_manifest_hash: str
    started_at: str
    context_coverage: str = "tool-mediated"


@dataclass(frozen=True)
class Claim:
    """A qualified proposition, kept separate from its support proposal."""

    id: str
    tenant_id: str
    project_id: str
    qualified_proposition: str
    entity_id: str
    scope_id: str
    status: str
    exact_quote_refs: tuple[str, ...] = ()


@dataclass(frozen=True)
class SupportProposal:
    """A declared support, qualification, or contradiction relationship."""

    id: str
    tenant_id: str
    project_id: str
    claim_id: str
    relation_kind: str
    cited_memory_ids: tuple[str, ...]
    cited_passage_ids: tuple[str, ...]
    proposing_run_id: str
    rationale: str
    created_at: str
    status: str = "proposed"


@dataclass(frozen=True)
class Review:
    """A bounded review of an exact proposal/version in one scope."""

    id: str
    tenant_id: str
    project_id: str
    reviewed_target_id: str
    proposal_id: str | None
    memory_version_id: str | None
    scope_id: str
    reviewer: str
    state: str
    binding_hash: str
    cited_source_ids: tuple[str, ...]
    accepted_at: str | None = None


@dataclass(frozen=True)
class MemoryVersion:
    """An immutable, scope-bound memory version."""

    id: str
    tenant_id: str
    project_id: str
    qualified_text: str
    created_at: str
    writer_run_id: str
    version: int
    scope_id: str
    source_ids: tuple[str, ...]
    claim_ids: tuple[str, ...]
    unknowns: tuple[str, ...]
    status: str
    content_hash: str
    kind: str = "observation"
    supersedes_memory_id: str | None = None
    review_id: str | None = None
    immutable: bool = True


@dataclass(frozen=True)
class MemoryUse:
    """A retrieval receipt; it is not semantic support or causal influence."""

    id: str
    tenant_id: str
    project_id: str
    requesting_run_id: str
    returned_version_ids: tuple[str, ...]
    source_manifest_hash: str
    scope_id: str
    created_at: str
    tool_coverage: str = "gateway-recall"


@dataclass(frozen=True)
class Draft:
    """A local, cited planning draft with no external side effect."""

    id: str
    tenant_id: str
    project_id: str
    owner_run_id: str
    requested_scope_hash: str
    scope_id: str
    title: str
    body: str
    citations: tuple[Mapping[str, Any], ...]
    created_at: str
    review_status: str
    allowed_local_action: str
    content_hash: str


@dataclass(frozen=True)
class WorkspaceMemory:
    """A human-editable shared memory item.

    The workspace presents one logical memory to people, while the store keeps
    immutable versions underneath.  ``memory_key`` groups those versions and
    ``supersedes_id`` records the previous edit without exposing graph details
    in the primary product flow.
    """

    id: str
    memory_key: str
    tenant_id: str
    project_id: str
    owner_user_id: str
    title: str
    body: str
    tags: tuple[str, ...]
    created_at: str
    updated_at: str
    version: int
    supersedes_id: str | None = None
    archived: bool = False
    workspace_project_id: str = "project:default"


@dataclass(frozen=True)
class WorkspaceProject:
    """A user-facing project that groups memories and people."""

    id: str
    tenant_id: str
    project_id: str
    owner_user_id: str
    name: str
    description: str
    created_at: str
    updated_at: str
    archived: bool = False


@dataclass(frozen=True)
class ProjectMember:
    """A user role inside one user-facing project."""

    id: str
    tenant_id: str
    project_id: str
    workspace_project_id: str
    user_id: str
    role: str
    created_at: str


@dataclass(frozen=True)
class GraphEdge:
    """A typed relationship in the in-memory graph."""

    id: str
    edge_type: str
    from_id: str
    to_id: str
    properties: Mapping[str, Any]


DOMAIN_RECORD_TYPES = (
    CompanyEntity,
    Scope,
    SourcePassage,
    AgentRun,
    Claim,
    SupportProposal,
    Review,
    MemoryVersion,
    MemoryUse,
    Draft,
    WorkspaceMemory,
    WorkspaceProject,
    ProjectMember,
)


def is_domain_record(value: Any) -> bool:
    """Return whether a value is one of the supported graph node records."""

    return isinstance(value, DOMAIN_RECORD_TYPES)
