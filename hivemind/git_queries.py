"""Repository queries. No repository-wide generic node/edge dump is used."""

RETURN_NODE = "n.id, n.node_type, n.tenant_id, n.project_id, n.data_json"
SCOPED = "n.tenant_id = $tenant_id AND n.project_id = $project_id AND n.workspace_project_id = $workspace_project_id"

GIT_QUERIES = {
    "git_list": f"""MATCH (n:GitRecord) WHERE {SCOPED}
      AND ($repo_id = '' OR n.repo_id = $repo_id) AND ($kind = '' OR n.kind = $kind)
      AND n.id > $cursor RETURN {RETURN_NODE} ORDER BY n.id LIMIT $limit""",
    "git_path": """MATCH (h:GitRecord {id:$head_id}), (c:GitRecord {id:$commit_id})
      WITH shortestPath((h)-[:PARENT*0..256]->(c)) AS p
      WHERE p IS NOT NULL AND all(n IN nodes(p) WHERE n.tenant_id=$tenant_id AND n.project_id=$project_id
        AND n.repo_id=$repo_id AND n.workspace_project_id=$workspace_project_id)
      RETURN [n IN nodes(p) | n.id] LIMIT 1""",
    "git_links": """MATCH (a:GitRecord)-[r]->(b:GitRecord)
      WHERE a.tenant_id=$tenant_id AND a.project_id=$project_id
        AND a.workspace_project_id=$workspace_project_id AND a.repo_id=$repo_id
        AND b.tenant_id=$tenant_id AND b.project_id=$project_id
        AND b.workspace_project_id=$workspace_project_id AND b.repo_id=$repo_id
        AND ($from_id='' OR a.id=$from_id) AND ($to_id='' OR b.id=$to_id)
        AND type(r)=$edge_type
      RETURN a.id, b.id, r.properties_json LIMIT $limit""",
    "git_candidates": """MATCH (h:GitRecord {id:$head_id}), (n:GitRecord)
      WHERE n.tenant_id=$tenant_id AND n.project_id=$project_id
        AND n.workspace_project_id=$workspace_project_id AND n.repo_id=$repo_id
        AND n.kind IN ['finding','checkpoint']
      OPTIONAL MATCH (b:GitRecord {id:$branch_id})-[:BRANCH_MEMORY]->(n)
      OPTIONAL MATCH (a:GitRecord {kind:'accepted_promotion'})-[:ACCEPTS]->(n)
      OPTIONAL MATCH (c:GitRecord)-[:PUBLISHES]->(n)
      WITH h, n, b, a, c, CASE WHEN c IS NULL THEN NULL
        ELSE shortestPath((h)-[:PARENT*0..256]->(c)) END AS p
      WITH n, b, a, max(CASE WHEN p IS NOT NULL AND all(x IN nodes(p)
        WHERE x.tenant_id=$tenant_id AND x.project_id=$project_id
          AND x.workspace_project_id=$workspace_project_id AND x.repo_id=$repo_id)
        THEN 1 ELSE 0 END) AS publications
      WHERE b IS NOT NULL OR publications > 0 OR a IS NOT NULL
      RETURN n.id, n.node_type, n.tenant_id, n.project_id, n.data_json,
        0 AS source_count, 0 AS matched_sources,
        publications, count(DISTINCT a), count(DISTINCT b)
      ORDER BY n.id LIMIT $limit""",
    "git_revisions": """MATCH (a:GitRecord)-[:REVISES]->(b:GitRecord)
      WHERE a.tenant_id=$tenant_id AND a.project_id=$project_id
        AND a.workspace_project_id=$workspace_project_id AND a.repo_id=$repo_id
        AND a.id IN $applicable_ids AND b.id IN $applicable_ids
      RETURN a.id, b.id LIMIT $limit""",
    "git_applicability": """MATCH (m:GitRecord)
      WHERE m.tenant_id=$tenant_id AND m.project_id=$project_id
        AND m.workspace_project_id=$workspace_project_id AND m.repo_id=$repo_id
        AND m.id IN $candidate_ids
      OPTIONAL MATCH (m)-[:SUPPORTED_BY]->(s:GitRecord)
      OPTIONAL MATCH (snap:GitRecord {id:$snapshot_id})-[:HAS_SOURCE]->(s)
      RETURN m.id, count(DISTINCT s), count(DISTINCT CASE WHEN snap IS NOT NULL THEN s ELSE NULL END)
      LIMIT $limit""",
    "git_explain": """MATCH (h:GitRecord {id:$head_id}), (c:GitRecord)-[:PUBLISHES]->(m:GitRecord {id:$memory_id})
      WITH m, shortestPath((h)-[:PARENT*0..256]->(c)) AS p
      WHERE m.tenant_id=$tenant_id AND m.project_id=$project_id
        AND m.workspace_project_id=$workspace_project_id AND m.repo_id=$repo_id
        AND p IS NOT NULL AND all(n IN nodes(p) WHERE n.tenant_id=$tenant_id AND n.project_id=$project_id
        AND n.workspace_project_id=$workspace_project_id AND n.repo_id=$repo_id)
      RETURN [n IN nodes(p) | n.id] + [m.id] LIMIT 1""",
    "git_excluded": """MATCH (m:GitRecord)
      WHERE m.tenant_id=$tenant_id AND m.project_id=$project_id
        AND m.workspace_project_id=$workspace_project_id AND m.repo_id=$repo_id
        AND m.kind IN ['finding','checkpoint'] AND NOT m.id IN $candidate_ids
      RETURN m.id LIMIT $limit""",
}
