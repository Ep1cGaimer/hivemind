# HiveMind memory contract

Status: The deterministic local gateway, HTTP/MCP adapters, fixture, and tests
implement this contract in memory. FalkorDB v6.0.2 remains the proposed shared
server pin, but no live server/client compatibility check or executed FalkorDB
query has been validated. No APOC, arbitrary procedures, or unrestricted
model-generated Cypher is assumed.

## Product boundary

One operations/account-planning lead wants a later role agent to reuse a qualified company learning without reopening the old chat or turning a summary into a broader assertion. One memory gateway, one bounded company capability, two company scopes, two genuinely cold role sessions; at most eight source/memory items per visible case. A small third memory can show a derivation chain, not a swarm. Source text, uncertain agent interpretation and reviewed memory are deliberately distinguishable. UI headline: what we learned, why, where it applies, and what still needs checking. Technical support states stay in the evidence details.

A generic write/recall API, MCP exposure, permissions or temporal graph is existing infrastructure, not novelty. The proposed differentiating job is source-and-scope-sensitive shared learning that shapes the next role's investigation/draft. Evidence/lineage preparation versus reuse benefit is unvalidated.

## Labels, properties and identity

Every node is server-bound to tenant_id/project_id and immutable logical ID. Labels:
- CompanyEntity: canonical_id, kind (project/account/system/capability), explicit source-backed aliases. Identical display names never merge tenants/scopes.
- Scope: entity_ids, stage/environment, qualifiers, valid_from/valid_to when supplied; missing qualifier stays unknown rather than defaulting broad.
- SourcePassage: artifact_id/version/content_hash, span offsets, text, source_uri, observed_at and source-stated time if known. Immutable raw data, no model permission to rewrite it.
- AgentRun: role, session_id, input_manifest_hash, started_at, tool/context coverage flag. No claim that a gateway observes unproxied model context or actual cognitive influence.
- MemoryVersion: qualified_text, created_at, writer_run_id, version, proposed/current/superseded marker, scope_id and source references. It can preserve uncertainty without being deleted.
- Claim: qualified proposition, entity/scope candidates, exact supporting quote references, status as a proposal/reviewed assertion/disputed/unknown. These are workflow states, not a truth/confidence score.
- SupportProposal: claim_id, exact memory/source span IDs, relation kind (supports/qualifies/contradicts), proposing_run_id, rationale, created_at. May cite several passages; missing/ambiguous support remains explicit.
- Review: proposal/version/scope hash, accepted/rejected/needs_evidence, reviewer identity/role, allowed review scope, accepted_at, cited sources. Review records who accepted a qualified interpretation, never truth or action authorization.
- MemoryUse: requesting_run_id, returned_version_ids, source/scope manifest_hash, created_at, tool coverage. Retrieval receipt only; it does not prove a draft relied semantically on every returned item.
- Draft: owner_run_id, requested_scope_hash, cited memory/source versions, created_at, review_status, allowed_local_action. No external send or automatic business commitment.

Identity resolution is deterministic for source/artifact/hash/run IDs. The LLM proposes entity/scope matches using quoted evidence; ambiguous matches cannot silently become canonical edges. Content hashes detect exact duplicates; identical wording does not establish identical original observations. Different run IDs are distinct recorded events, not proof of statistical independence.

## Directed edges and their meanings

- AgentRun-READ_PASSAGE->SourcePassage and AgentRun-READ_MEMORY->MemoryVersion: observed tool/context exposure only, with full/partial coverage metadata.
- AgentRun-WROTE->MemoryVersion; MemoryVersion-ASSERTS->Claim; Claim-ABOUT->CompanyEntity; Claim-IN_SCOPE->Scope.
- Claim-HAS_PROPOSAL->SupportProposal; SupportProposal-CITES_PASSAGE->SourcePassage or CITES_MEMORY->MemoryVersion. This is declared/proposed justification; citation existence does not prove semantic entailment.
- Review-REVIEWS->SupportProposal or MemoryVersion; Review-APPLIES_IN->Scope. Current reviewed support is a validated join of explicit approved proposal+scope, never an automatic READ-to-SUPPORTS conversion.
- MemoryVersion-SUPERSEDES->MemoryVersion, scoped by explicit review/correction; an update for one account/stage does not invalidate unrelated scopes globally.
- MemoryUse-RETURNED->MemoryVersion and AgentRun-HAS_MEMORY_USE->MemoryUse. Draft-CITES_VERSION->MemoryVersion and Draft-CITES_PASSAGE->SourcePassage record declared draft citations, not every retrieved item as a semantic dependency.
- Optional source-origin links require a source-declared or reviewed identity/provenance relation. A reviewer-accepted copied passage can retain a derivation link to its earlier artifact; generic shared context cannot create this link automatically.

Critical investigation path: cold AgentRun -> MemoryUse -> returned MemoryVersion -> Claim -> SupportProposal -> cited earlier MemoryVersion -> its Claim/SupportProposal -> original SourcePassage, with applicable Review/Scope at every promoted step. Separate READ paths remain visible as exposure evidence, not supporting proof. Consumer path: reviewed/corrected MemoryVersion <- cited version - Draft, plus historical retrievals labeled as potentially affected, not proved influenced.

## Seven realistic graph operations (proposed fixed tools)

| User question | Traversal | Result shape | Agent use | Why flat/vector-only retrieval is insufficient |
|---|---|---|---|---|
| 1. What do we already know for this company context? | Scope/entity seeds -> Claims -> current applicable MemoryVersions with provenance/reviews | Memory text/version, explicit qualifiers, review status, source refs, ambiguity/null fields | Select relevant learning or ask entity/stage clarification | Similarity can seed candidates but does not establish exact applicability/current version. Full relational logic can reproduce. |
| 2. Why does this memory say that? | Memory -> Claim -> SupportProposal -> cited memories/passages, bounded recursive expansion | Explicit declared/reviewed support paths, exact spans, missing links, cycle/cap markers | Read actual support and compare it to the qualified question | Surface citations alone omit transitive agent restatements; equivalent recursive SQL is a control. |
| 3. Is repeated wording supported by the same recorded observation? | Support paths to source-declared observation/artifact identities; READ paths separately | Shared cited roots, distinct recorded observation IDs, unknown provenance; no truth/independence number | Investigate broadening/qualifier loss, never count votes or automatically collapse observations | Vector similarity does not distinguish copied evidence from separate observations or context exposure. ID-set/provenance controls remain capable. |
| 4. What evidence is missing for this situation? | Proposed claim/scope -> support path -> reviewed scope qualifiers/source versions | Candidate mismatch/gap with exact passages and unresolved scope, not a pre-stored verdict | Interpret raw condition, ask one targeted question or draft a bounded statement | Similarity cannot by itself validate scoped support. The LLM interpretation remains necessary work; deterministic code only returns facts/paths. |
| 5. May this correction change this memory? | Review -> exact proposal/version/scope plus current hashes -> proposed replacement MemoryVersion | Approved/rejected/stale binding; new immutable scoped version or unresolved proposal | Propose qualified correction; explain disputed/partial state | Latest text is not blanket supersession; flat histories do not enforce scope/hash applicability. Deterministic relational code can. |
| 6. Which later work should be re-examined? | Corrected version <- explicitly citing Draft; separately MemoryUse-returned versions | Actual declared citation consumers vs merely exposed runs; scope/currentness; unknown influence flagged | Draft a local review/revision queue, not claim every reader was misled | Retrieval similarity cannot enumerate version-specific consumers; READ receipt is not causal evidence. |
| 7. What should a fresh role use now? | New independent AgentRun -> scoped recall -> current/reviewed/source paths, excluding incompatible correction scope | A provenance manifest and raw qualifiers identical to retrievable source facts, plus stale conflicts | Answer/draft using persistent learning without old chat; preserve uncertainty; cite exact version | A raw conversation dump obscures current scoped validity. Complete SQL+same LLM may tie. |

All enumerations preserve missing expected items independently of positive traversal; cap+1 means incomplete, not 'no more sources'. Bounded cycle detection returns an unresolved frontier. No absence of reachable recorded support is proof no real support exists. No maximum-depth/cap result can be promoted to complete lineage. No arbitrary model Cypher or destructive query tools.

## Temporal updates, deletion and isolation

Immutable source/memory versions with observed time; source-stated validity time kept separately. Correcting a source creates a new version and a proposed scoped supersession. Existing drafts' citations are traceable to old versions, while later recall retrieves applicable versions or explicit conflicts. A current review hash includes source, claim, scope and content version; changed evidence invalidates reuse of that approval.

P0 tenant isolation uses server-selected graph keys and scoped tools, not user/model-supplied graph names. Source visibility enforced before retrieval; derived memory is not exposed to a principal lacking required sources. P0 may conservatively require source visibility and refuse regeneration rather than implementing a general security/declassification engine. No public paraphrase declassifies restricted memory; hidden counts/existence must not leak.

Only synthetic/source-permitted content. Tombstones/corrections and scope-specific retirement preserve audit references; any eventual physical deletion/reset is a deterministic local operation on explicitly selected fixture resources. No production erasure/compliance claim. Source passages are untrusted data and cannot instruct tool calls, alter tenant or grant reviewer privileges.

## Deterministic versus model responsibilities and approval

Deterministic service controls identities, permissions, receipt capture, source/version/hash bindings, graph query limits, current scoped review status, idempotency and local writes. The model interprets source support/qualifiers, proposes merges/supersession with quotes, chooses a safe retrieval/evidence tool, asks a useful clarification and drafts the next role's response. It cannot turn an observation or review into universal truth or authorize business actions. Human review is a bounded assertion/clarification action; sending messages, changing contracts, deployments, HR or source permissions is outside this extra concept's MVP.

Highest-risk experiment: same raw passages/corrections/model/budget through complete primary-source memory, origin-ID/provenance tables, configured Graphiti/Glean-like workflow and this graph gateway. Measure unsafe scope reuse, unknown/support confusion, correct cold-session action/citations, reviewer/preparation effort. Paper cases can expose logical flaws; only later actual agent/graph runs and user walkthroughs can establish implementation behavior/usefulness. An equal-usefulness lower-preparation substitute rejects the product argument; SQL representational parity alone does not.
