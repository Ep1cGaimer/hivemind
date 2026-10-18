"""Fixed, parameterized Cypher used by the optional FalkorDB backend.

The gateway never accepts Cypher.  Store methods select one of the query names
in this module and pass values separately as parameters.  Labels and
relationship types are literals from the internal registries below; they are
never interpolated from a request, source passage, or model output.
"""

from __future__ import annotations

from types import MappingProxyType
from typing import Mapping


# These are the only labels the HiveMind adapter creates.  The subtype label
# makes the persisted graph inspectable while HiveMindNode gives safe, fixed
# lookup queries a common label.
NODE_LABELS: Mapping[str, str] = MappingProxyType(
    {
        "CompanyEntity": "CompanyEntity",
        "Scope": "Scope",
        "SourcePassage": "SourcePassage",
        "AgentRun": "AgentRun",
        "Claim": "Claim",
        "SupportProposal": "SupportProposal",
        "Review": "Review",
        "MemoryVersion": "MemoryVersion",
        "MemoryUse": "MemoryUse",
        "Draft": "Draft",
        "WorkspaceMemory": "WorkspaceMemory",
        "WorkspaceProject": "WorkspaceProject",
        "ProjectMember": "ProjectMember",
        "GitRecord": "GitRecord",
    }
)

EDGE_TYPES: tuple[str, ...] = (
    "ABOUT",
    "IN_SCOPE",
    "WROTE",
    "ASSERTS",
    "HAS_PROPOSAL",
    "CITES_PASSAGE",
    "CITES_MEMORY",
    "REVIEWS",
    "APPLIES_IN",
    "READ_PASSAGE",
    "READ_MEMORY",
    "HAS_MEMORY_USE",
    "RETURNED",
    "SUPERSEDES",
    "CREATED_DRAFT",
    "CITES_VERSION",
    "PARENT", "BRANCH_MEMORY", "PUBLISHES", "SUPPORTED_BY", "HAS_SOURCE",
    "OBSERVED", "AT_COMMIT", "REVISES", "ACCEPTS", "TRANSFERRED_FROM",
)


def _node_upsert_query(label: str) -> str:
    """Build one trusted query from an internal, hard-coded label."""

    return f"""
MERGE (n:HiveMindNode:{label} {{id: $id}})
ON CREATE SET n.tenant_id = $tenant_id,
  n.project_id = $project_id,
  n.node_type = '{label}',
  n.data_json = $data_json,
  n.scope_id = $scope_id,
  n.status = $status,
  n.kind = $kind,
  n.company_id = $company_id,
  n.memory_version_id = $memory_version_id,
  n.reviewed_target_id = $reviewed_target_id,
  n.created_at = $created_at,
  n.workspace_project_id = $workspace_project_id, n.repo_id = $repo_id,
  n.branch_id = $branch_id, n.key = $key, n.head = $head
RETURN n.id AS id, n.node_type AS node_type, n.tenant_id AS tenant_id,
  n.project_id AS project_id, n.data_json AS data_json
""".strip()


def _edge_upsert_query(edge_type: str) -> str:
    """Build one trusted query from an internal, hard-coded relationship type."""

    return f"""
MATCH (a:HiveMindNode {{id: $from_id}}), (b:HiveMindNode {{id: $to_id}})
WHERE a.tenant_id = $tenant_id AND a.project_id = $project_id
  AND b.tenant_id = $tenant_id AND b.project_id = $project_id
MERGE (a)-[r:{edge_type} {{id: $edge_id}}]->(b)
ON CREATE SET r.tenant_id = $tenant_id,
  r.project_id = $project_id,
  r.edge_type = '{edge_type}',
  r.properties_json = $properties_json
RETURN r.id AS id, type(r) AS edge_type, a.id AS from_id, b.id AS to_id,
  r.tenant_id AS tenant_id, r.project_id AS project_id,
  r.properties_json AS properties_json
""".strip()


RECALL_CONTEXT_QUERY = """
MATCH (s:Scope {id: $scope_id})<-[:IN_SCOPE]-(c:Claim)<-[:ASSERTS]-(m:MemoryVersion)
WHERE s.tenant_id = $tenant_id AND s.project_id = $project_id
  AND c.tenant_id = $tenant_id AND c.project_id = $project_id
  AND m.tenant_id = $tenant_id AND m.project_id = $project_id
  AND m.scope_id = $scope_id AND m.status IN ['reviewed', 'reviewed_correction']
RETURN m, c, s
ORDER BY m.created_at DESC
LIMIT $memory_limit
""".strip()

INSPECT_EVIDENCE_QUERY = """
MATCH p=(m:MemoryVersion {id: $memory_id})-[:ASSERTS|HAS_PROPOSAL|CITES_MEMORY|CITES_PASSAGE*0..4]->(e)
WHERE m.tenant_id = $tenant_id AND m.project_id = $project_id
  AND all(node IN nodes(p) WHERE node.tenant_id = $tenant_id AND node.project_id = $project_id)
RETURN p
LIMIT $path_limit
""".strip()

CREATE_CORRECTION_QUERY = """
MATCH (base:MemoryVersion {id: $base_memory_id}), (scope:Scope {id: $scope_id})
WHERE base.tenant_id = $tenant_id AND base.project_id = $project_id
  AND scope.tenant_id = $tenant_id AND scope.project_id = $project_id
MERGE (correction:MemoryVersion {id: $correction_id})
ON CREATE SET correction.scope_id = $scope_id,
  correction.supersedes_memory_id = $base_memory_id,
  correction.content_hash = $content_hash,
  correction.tenant_id = $tenant_id,
  correction.project_id = $project_id,
  correction.status = 'reviewed_correction',
  correction.immutable = true
MERGE (correction)-[:SUPERSEDES {scope_id: $scope_id}]->(base)
RETURN correction, base, scope
""".strip()

SAVE_DRAFT_QUERY = """
MATCH (scope:Scope {id: $scope_id})
WHERE scope.tenant_id = $tenant_id AND scope.project_id = $project_id
MERGE (draft:Draft {id: $draft_id})
ON CREATE SET draft.scope_id = $scope_id,
  draft.requested_scope_hash = $requested_scope_hash,
  draft.content_hash = $content_hash,
  draft.tenant_id = $tenant_id,
  draft.project_id = $project_id,
  draft.review_status = 'local-draft'
WITH draft
UNWIND $citation_ids AS citation_id
MATCH (memory:MemoryVersion {id: citation_id, scope_id: $scope_id})
WHERE memory.tenant_id = $tenant_id AND memory.project_id = $project_id
MERGE (draft)-[:CITES_VERSION {scope_id: $scope_id}]->(memory)
RETURN draft
""".strip()

STATE_QUERY = """
MATCH (n:HiveMindNode)
WHERE n.tenant_id = $tenant_id AND n.project_id = $project_id
RETURN labels(n) AS labels, n.id AS id, n.node_type AS node_type,
  n.data_json AS data_json
ORDER BY n.id
LIMIT $node_limit
""".strip()

HEALTH_QUERY = "RETURN 1 AS ok LIMIT 1"

NODE_LOOKUP_ANY_QUERY = """
MATCH (n:HiveMindNode {id: $id})
RETURN n.id AS id, n.node_type AS node_type, n.tenant_id AS tenant_id,
  n.project_id AS project_id, n.data_json AS data_json
LIMIT 1
""".strip()

NODE_LOOKUP_QUERY = """
MATCH (n:HiveMindNode {id: $id})
WHERE n.tenant_id = $tenant_id AND n.project_id = $project_id
RETURN n.id AS id, n.node_type AS node_type, n.tenant_id AS tenant_id,
  n.project_id AS project_id, n.data_json AS data_json
LIMIT 1
""".strip()

NODE_LIST_QUERY = """
MATCH (n:HiveMindNode)
WHERE n.tenant_id = $tenant_id AND n.project_id = $project_id
  AND ($node_type = '' OR n.node_type = $node_type)
RETURN n.id AS id, n.node_type AS node_type, n.tenant_id AS tenant_id,
  n.project_id AS project_id, n.data_json AS data_json
ORDER BY n.id
LIMIT $node_limit
""".strip()

EDGE_LOOKUP_QUERY = """
MATCH (a:HiveMindNode)-[r]->(b:HiveMindNode)
WHERE r.id = $edge_id
RETURN r.id AS id, type(r) AS edge_type, a.id AS from_id, b.id AS to_id,
  r.tenant_id AS tenant_id, r.project_id AS project_id,
  r.properties_json AS properties_json
LIMIT 1
""".strip()

EDGE_LIST_QUERY = f"""
MATCH (a:HiveMindNode)-[r]->(b:HiveMindNode)
WHERE a.tenant_id = $tenant_id AND a.project_id = $project_id
  AND b.tenant_id = $tenant_id AND b.project_id = $project_id
  AND type(r) IN [{', '.join(repr(edge_type) for edge_type in EDGE_TYPES)}]
  AND ($edge_type = '' OR type(r) = $edge_type)
  AND ($from_id = '' OR a.id = $from_id)
  AND ($to_id = '' OR b.id = $to_id)
RETURN r.id AS id, type(r) AS edge_type, a.id AS from_id, b.id AS to_id,
  r.tenant_id AS tenant_id, r.project_id AS project_id,
  r.properties_json AS properties_json
ORDER BY r.id
LIMIT $edge_limit
""".strip()

CLEAR_GRAPH_QUERY = """
MATCH (n:HiveMindNode)
WHERE n.tenant_id = $tenant_id AND n.project_id = $project_id
DETACH DELETE n
""".strip()


_registry: dict[str, str] = {
    "recall_context": RECALL_CONTEXT_QUERY,
    "inspect_evidence": INSPECT_EVIDENCE_QUERY,
    "create_correction": CREATE_CORRECTION_QUERY,
    "save_draft": SAVE_DRAFT_QUERY,
    "state": STATE_QUERY,
    "health": HEALTH_QUERY,
    "node_lookup_any": NODE_LOOKUP_ANY_QUERY,
    "node_lookup": NODE_LOOKUP_QUERY,
    "node_list": NODE_LIST_QUERY,
    "edge_lookup": EDGE_LOOKUP_QUERY,
    "edge_list": EDGE_LIST_QUERY,
    "clear_graph": CLEAR_GRAPH_QUERY,
}
for _node_label in NODE_LABELS.values():
    _registry[f"node_upsert_{_node_label}"] = _node_upsert_query(_node_label)
from .git_queries import GIT_QUERIES
_registry.update(GIT_QUERIES)
for _edge_type in EDGE_TYPES:
    _registry[f"edge_upsert_{_edge_type}"] = _edge_upsert_query(_edge_type)

FIXED_QUERY_REGISTRY: Mapping[str, str] = MappingProxyType(_registry)
NODE_UPSERT_QUERY_NAMES: Mapping[str, str] = MappingProxyType(
    {node_type: f"node_upsert_{label}" for node_type, label in NODE_LABELS.items()}
)
EDGE_UPSERT_QUERY_NAMES: Mapping[str, str] = MappingProxyType(
    {edge_type: f"edge_upsert_{edge_type}" for edge_type in EDGE_TYPES}
)


def get_fixed_query(name: str) -> str:
    """Return a registered query or raise a safe, explicit error."""

    if not isinstance(name, str):
        raise TypeError("Fixed query name must be a string")
    try:
        return FIXED_QUERY_REGISTRY[name]
    except KeyError as exc:
        raise KeyError(f"Unknown fixed HiveMind query: {name}") from exc
