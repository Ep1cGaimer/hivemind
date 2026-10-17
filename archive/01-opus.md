Showing 1 of 70 activities (limited to 1)

# Hive-mind proposals: Claude Opus 5.5

Demand, competitor gaps and the Air Canada reference are unverified hypotheses until a validation phase.

## Card A: PromiseKeeper, a shared memory of commitments with authority checks

- **Novelty:** Materially new. Ripple (R-09) tracks *facts told to people*. This card tracks *obligations created by agents*, checked against who was allowed to make them.
- **User:** The customer-success lead at a B2B SaaS company, where support, sales and CS agents (AI and human) all talk to the same accounts.
- **Workflow (hypothesis):** Before a renewal or escalation, someone has to know what was promised to the account, by whom, whether that person had authority, and whether it can still be delivered.
  - Today this lives in CRM notes and transcripts.
  - A new agent session starts with no memory. Promises sit buried in transcripts, and nobody checks the promiser's authority or slips in the roadmap.
  - The Air Canada chatbot ruling is a recalled reference only. It is unverified in this phase.
- **Graph:**
  - Nodes: `Commitment`, `Account`, `Agent/Person`, `Role`, `AuthorityPolicy{type, cap}`, `RoadmapItem{target_date}`, `Evidence{quote, span}`.
  - Edges: `Commitment-MADE_BY->Agent`, `-OWED_TO->Account`, `-MADE_IN->Evidence`, `-DEPENDS_ON->RoadmapItem`, `-APPROVED_BY->Person`, `-FULFILLED_BY->Ticket`; `Agent-ACTS_AS->Role-GRANTED->AuthorityPolicy`; `Role-DELEGATED_BY->Role`.
- **Operation:** For each open commitment on an account, the graph checks two paths:
  - **Authority path:** maker → role → a delegated policy that covers this type and amount, or an approval from someone whose role covers it.
  - **Dependency path:** commitment → roadmap item, comparing the current target date with the promised date.
  - **Removal failure:** without these relationships there is no "unauthorized promise" witness and no "at-risk promise" witness. The transcripts still contain the words, but not the chains.
- **Agent:**
  - Extracts proposed commitments from new transcripts, with quotes, and deduplicates them.
  - Before another agent makes an offer, checks it for conflicts and authority.
  - Drafts an escalation to the approver with authority. A human approves it, and no external message is sent.
- **Data:** A synthetic company: 3 accounts, 4 agents, 30 transcript snippets, 6 roadmap items, a policy table.
- **30-second demo:** A renewal agent starting cold asks, "Anything on Acme?"
  - **Flat memory:** a summary of tickets.
  - **Graph:** "The support agent promised a 20% credit, but its role caps credits at 10% and there is no approval. Sales promised SSO by September, but that roadmap item slipped to November." The agent then drafts the escalation.
- **Baselines:** isolated agents; vector memory over transcripts; the same LLM with SQL over the same extracted tables.
- **Substitute:** conversation intelligence and CS platforms such as Gong, Gainsight and Salesforce Einstein. Their gaps are unverified.
- **Four-day MVP:** One commitment family (credits and feature dates), three queries, one escalation draft.
- **Biggest rejection reason:** Extraction precision. CRM tools may already log commitments.
- **Falsifiable test:**
  - **Fixture:** 20 seeded transcripts with 8 commitments (3 unauthorized, 2 at risk) and paraphrased decoys such as "we'll look into it".
  - **Pass:** at least 7 of 8 commitments found with quotes, every unauthorized or at-risk one flagged with a valid path, and at most 1 decoy accepted.
  - **Kill:** if the authority check is really one flat table lookup with no delegation chain.

## Card B: TaintTrail, need-to-know reuse of derived agent memory

- **Novelty:** Materially new mechanism: permission inheritance through the lineage of derived memories. Its neighbor, Honest Memory (R-08), decides whether a fact may be *written*. This card governs who may *reuse* a derived memory later.
- **User:** The IT or platform lead running shared company agents (HR, sales, engineering helpers) over one memory.
- **Workflow (hypothesis):** Agents write summaries and conclusions drawn from sources with different permissions, and later agents serving other users reuse them.
  - Search tools enforce access lists at the source level.
  - Derived memories may lose that lineage, which leads either to a leak or to separate silos that duplicate work.
- **Graph:**
  - Nodes: `Source`, `Memory`, `Session`, `User`, `Group`.
  - Edges: `Memory-DERIVED_FROM->Memory|Source` (multi-hop), `Source-READABLE_BY->Group`, `User-MEMBER_OF->Group`, `Memory-WRITTEN_IN->Session-FOR->User`, `Memory-SUPERSEDES->Memory`.
- **Operation:** At read time, the full `DERIVED_FROM` ancestry is traversed, using `all(n IN nodes(p) WHERE …)`.
  - A memory is usable for user U only if U can read every ancestor source.
  - Otherwise the agent finds the permitted sub-ancestry.
  - **Removal failure:** a derived memory becomes plain text, so the system can only leak it or block it entirely. Permission changes made after the memory was derived can't be applied either.
- **Agent:** It chooses one of three moves:
  - use the memory;
  - re-derive the answer from permitted ancestors only, writing a new memory with narrower lineage;
  - or answer partially and say so.
  - It never reveals restricted content. Whether the existence of restricted material may be mentioned is a policy flag. Every write must record its lineage. Reclassifying a source requires admin approval.
- **Data:** A synthetic tenant: 12 sources across HR, finance and engineering, 3 groups, 3 sessions.
- **30-second demo:**
  1. The HR agent writes: "Platform merges into Infra; 2 roles cut." It draws on an HR-restricted doc and the public all-hands.
  2. Later, an engineer asks the engineering agent about the Platform team.
  - **Flat shared memory:** returns "2 roles cut", a leak.
  - **Graph:** the ancestry includes the HR-only doc, so the agent re-derives from the all-hands only: "Platform is merging into Infra (all-hands, Oct 3)."
  3. Then the all-hands is reclassified, and the derived memory is correctly withdrawn.
- **Baselines:** silos; vector shared memory; **the strongest one:** a fair access list computed per memory at write time (the intersection of its sources' groups), plus the same LLM with recursive SQL.
- **Substitute:** permission-aware enterprise search (Glean, Copilot), memory layers (Zep, Mem0), and information-flow-control research. Coverage of derived memories is unverified.
- **Four-day MVP:** One tenant, a two-level derivation chain, a read-time gate, a re-derive tool.
- **Biggest rejection reason:** Write-time label intersection may be enough. The card is also security-adjacent.
- **Falsifiable test:**
  - **Fixture:** 15 questions × 3 users, plus 1 reclassification.
  - **Pass:** zero restricted facts leaked, more useful answers kept than blanket blocking, and correct withdrawal after the reclassification.
  - **Kill:** if write-time access lists plus recompute-on-change tie on everything, including partial re-derivation, with less complexity.

## Position

1. **Current position:** I prefer B, held moderately. It addresses the Track 2 isolation requirement and the Track 3 company brain together, the graph is used at runtime, and the wow is clear: the same memory gives different answers to different users, and a leak is prevented.
2. **Strongest support:** Reuse across roles is the point of a hive mind, and lineage-scoped permissions are what make that reuse safe.
3. **Strongest counter:** A write-time access list plus recompute triggers may be simpler and equally correct.
4. **Assumption:** Derived memories are reused across users, and source permissions change after a memory has been derived.
5. **What would change my mind:**
   - validation showing that permission-aware enterprise search already applies lineage to derived memories; or
   - the write-time control tying on reclassification and partial re-derivation.
6. **Direct response:** Same-LLM SQL parity is acceptable. The value is a re-derivation decision taken at read time, not uniqueness.
