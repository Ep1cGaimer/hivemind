Showing 1 of 10 activities (limited to 1)

**Concept A — Mantle: sole-attestor succession memory**

- **Target user:** An engineering manager preparing one engineer's role change or departure.
- **Painful workflow (hypothesis):** Onboarding hands over files, not decision authority. Current method: handover doc + wiki search + asking around. It fails because flat search lists what the person *touched*, not which still-live decisions lose their only validating voice.
- **Nodes/edges:** Person, Role, Decision, Attestation, Document, Project, Service, AgentSession; `ATTESTED_BY`, `SUPERSEDES`, `DEPENDS_ON`, `OWNED_BY`, `COLLABORATED_WITH`, `AUTHORIZED_TO_ATTEST`.
- **Graph-dependent operation / removal failure:** From the departing Person, traverse attestations to Decisions, keep those reaching a live Project/Service **without any alternative attestation path**, rank by dependent count, pick successor via co-attestation proximity. Remove relationships (retain all records) and this implementation falls back to "documents she wrote" — the absence-of-alternative-path inference, the risk ranking, and the authority-transfer edge disappear. Same-LLM SQL/BFS parity is acknowledged; the claim is loss in this implementation, not mathematical uniqueness.
- **Agent decision/action + approval:** Rank at-risk decisions, propose successor, draft per-decision handoff packets (rationale, sources, dependents). Manager approval gate before `AUTHORIZED_TO_ATTEST` is written to shared memory; a later cold-start session then answers "why Kafka?" from the transferred packet.
- **Data:** Explicitly synthetic org fixture (~30 people, ~40 decisions, ~10 projects); optional public OSS ADR/git-author supplement. Role/source scopes enforced; source text cannot instruct memory tools.
- **30-second demo:** Departure announced → baseline lists 12 documents; Mantle surfaces 3 sole-attestor decisions, flags 2 active dependents, proposes a successor and approval-gated transfer; new session answers with rationale path where baseline says "no source."
- **Fair before/after:** Same sources, LLM, tool budget, updates; isolated agent and flat/vector shared memory baselines. Measure hidden sole-attestor recall, false-risk on covered decisions, unsupported claims on cold-start Q&A, missed transfers.
- **Closest substitute:** MERIDIAN expert discovery, GraphMem handoffs, Notion handover templates. **Differentiation:** computes *missing* coverage and re-points write authority — absence-of-path, not who-knows-what lookup.
- **Four-day MVP:** One fixture, one coverage Cypher template + successor heuristic, one approval-gated write, two sessions.
- **Biggest rejection reason:** The core query is deterministic; the LLM role may look cosmetic.
- **Falsifiable success test:** Seed 4 sole-attestor + 6 covered decisions, blind labels; graph version recalls ≥3/4 with ≤1 false risk and beats flat/vector on cold-start unsupported claims. If a flat ownership-table + grep ties, reject A.
- **Novelty:** Materially new workflow (role transition/succession) and mechanism (negative/coverage path) relative to ideas.md; adjacent to R-06 and MERIDIAN handoff/expertise.

**Concept B — CommitLedger: commitment-shadowed outbound memory gate**

- **Target user:** A customer success manager approving agent-drafted customer responses.
- **Painful workflow (hypothesis):** Agents draft replies from the current thread only; commitments live in contracts, deal notes, and prior messages. Current method: rep re-reads thread + CRM. It fails because a fresh draft re-promises dates/scope contradicting commitments never mentioned in the thread.
- **Nodes/edges:** Commitment, Customer, Account, Deal, Feature, Statement, Agent, Source, Decision; `COMMITTED_TO`, `CONSTRAINS`, `EVIDENCED_BY`, `SUPERSEDES`, `EXPIRES`, `OWNED_BY`, `REQUIRES_APPROVAL`.
- **Graph-dependent operation / removal failure:** Ground draft claims to entities, then traverse claim entities → active Commitments constraining them for that account, including commitments superseded-but-still-active. Remove relationships and only textually similar commitments surface — the intersecting-constraint path to an unmentioned commitment disappears.
- **Agent decision/action + approval:** Release, edit, or hold the draft with a contradiction report carrying paths; only approval writes a new Commitment node.
- **Data:** Explicitly synthetic CRM/contract fixtures; no real personal data; no external sending (simulated release only).
- **30-second demo:** Draft says "SSO ships in March"; graph flags an active Deal→Feature commitment scoping SSO to enterprise tier with Q4 delivery; baseline happily releases.
- **Fair before/after:** Same commitment records as text for baselines; seed 5 hidden contradictions among 10 drafts. Measure contradiction recall, false-block rate, unsupported claims.
- **Closest substitute:** CRM reminder rules, R-09 Ripple (told-audience on fact change), R-08 Honest Memory (write gate). **Differentiation:** pre-action constraint check over a commitment graph — no fact change, no inbound propagation.
- **Four-day MVP:** One account, 10 commitments, claim-extraction step, one Cypher constraint check, approval queue.
- **Biggest rejection reason:** Claim-to-entity matching is fragile; it risks looking like a rules engine.
- **Falsifiable success test:** Flag ≥4/5 hidden contradictions with ≤1 false block, beating same-LLM flat retrieval; else reject.
- **Novelty:** New workflow; mechanism **reference-adjacent** to R-09/R-08 (labeled, not a rename).

**Six positions**

1. **Preferred:** Concept A.
2. **Strongest support:** A makes a *negative* graph inference (missing attestation coverage) that flat/vector memory cannot express, then converts it into a durable authority-transfer that demonstrably changes a later session's answer — hitting Track 2 memory handoff and Track 3 company brain with one wow moment.
3. **Strongest counter:** Its query is a deterministic graph script; an LLM-free tool plus a flat ownership table might tie, making the agent cosmetic (SQL-parity risk).
4. **Dependent assumption:** Synthetic fixtures can encode attestations and supersession plausibly, and judges value absence-of-path discovery over prettier retrieval; successor choice needs enough co-work signal to be non-arbitrary.
5. **What changes mind:** A cheap flat baseline recovering the same at-risk set *and* successor on seeded data kills A; if B's hidden-commitment reveal proves equally memorable with less parity risk, I would prefer B, and the chair's cheapest experiment is running both seeded tests before scoring.
6. **Response to strongest objection:** Parity only holds if the agent's job is the traversal. It is not: deterministic code owns the coverage/constraint queries, limits, and allowlists, while the LLM grounds draft/handoff text into entities, decides supersession-benign vs at-risk using provenance, composes per-decision packets, and proposes approval-gated actions. A same-LLM control given raw records must perform that grounding and the absence-of-path reasoning itself; that is where we predict it fails, measured by hidden-set recall and unsupported claims rather than asserted.
