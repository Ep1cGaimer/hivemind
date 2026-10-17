Showing 1 of 80 activities (limited to 1)

# Hive mind adversarial stage: Claude Opus 5.5

Each card gets the docket's eight attacks:
1. Weakness
2. What works without a graph
3. Mature substitute
4. Missing or unreliable data
5. Likely overclaim
6. How the demo breaks
7. One repair
8. Cheapest kill test

## H11 Anti-echo institutional decision memory
1. **Weakness:** A record that an agent run *read* a source doesn't show the source supports its claim. The lineage is only as good as what the memory gateway records.
2. **Without a graph:**
   - A mandatory owner-source check stops the launch-approval example outright. I concede that example is killed.
   - A set of origin IDs handles shallow duplication.
3. **Substitutes:** Graphiti provenance (which has a FalkorDB backend), Glean agents with citations, MAP-Graph-style admission checks, and the method published in V6.
4. **Data:** Real agent-summary lineage is rarely captured. Support has to be read from raw text, and a fixture's lineage edges could encode the verdict.
5. **Overclaim:** "Detects echo or independence". A shared root does not prove two claims are dependent, and counting roots says nothing about truth.
6. **Demo break:** The agent misreads what supports what. Or shared background context collapses two genuinely separate observations into one.
7. **Repair:** Ask about a *qualified capability* that has no single authoritative source, instead of launch approval. Example: "Is EU data residency ready for customer X?"
   - Sales, Support and Solutions memories all say yes.
   - The gateway records `READ`. The LLM separately proposes `SUPPORTS` with a quote, and a human reviews it.
   - The graph shows every reviewed support traces to one Engineering note: "EU region ready for *new tenants*, after migration."
   - The agent asks the Engineering owner a question grounded in that note.
   - The reviewed qualified answer is stored. A later cold Sales session then tells customer X "not until migration", where it would otherwise have said "yes".
8. **Kill test:**
   - Give the strongest control a real owner source, plus an origin-ID set and the same LLM. If it produces the same clarification and the same change in the later session, kill.
   - Also kill if two genuinely independent observations that share a background document get collapsed into one.

## H03 Coverage-driven knowledge handover
1. **Weakness:** Coverage gaps reflect recording gaps, and tacit knowledge stays invisible. A fixture with a Decision but no rationale has already curated the interview target.
2. **Without a graph:** A generic prompt, "list your decisions and why", with the same question budget.
3. **Substitutes:** Git bus-factor scripts, Backstage owners, Glean's people graph, wikis.
4. **Data:** Attestation and review records are plausible to obtain. Whether a rationale is actually present has to be read from raw text.
5. **Overclaim:** "Sole knower". The defensible wording is "unattested elsewhere in records."
6. **Demo break:** The targeted question looks obvious, and the generic interview gets the same answer.
7. **Repair:**
   - Ingest only raw docs and observed authorship and review links, with no SHOULD_ASK labels.
   - The graph ranks decisions that have *active dependents* and whose rationale sources are all attested only by the departing person.
   - The LLM reads those sources to judge whether the rationale is actually there.
   - The successor's cold session answers with citations to the approved answer.
8. **Kill test:** Hold a 3-question budget. The generic prompt plus the same LLM with full docs chooses questions, and an independent author judges which ones the successor needs. Kill if they are equal.

## H06 Two-sided acceptance handoff memory
1. **Weakness:** If acceptance-scope edges are hand-authored, the interpretation happens during ingestion. The graph is shallow, about 2 hops.
2. **Without a graph:** A signed checklist.
3. **Substitutes:** Gong (V8), Gainsight, project checklists.
4. **Data:** Synthetic sales wording invites contrived ambiguity.
5. **Overclaim:** "Undelivered" or "refused". A missing acceptance means not recorded, not rejected.
6. **Demo break:** The "migration" puzzle reads as staged.
7. **Repair:** Ingest only raw passages. The agent proposes quoted scope edges and a human reviews them.
8. **Kill test:** The same passages with a prompt plus a checklist tie.

## Minority note
Repaired H11 converges with H10: claim, then reviewed support, then evidence. That suggests the strongest mechanism is support tracing across agents, not a separate card. I'm not reopening H10 independently.

## Position
1. **Preferred:** H11, conditionally, with the qualified-capability repair. H03 is runner-up. H06 is weakest: shallow graph, Gong already covers handoff, and its interpretation sits in ingestion.
2. **Support:** It is truly hive-mind. Role agents write memories, and the graph traces the reviewed support behind them to a shared conditional root that differs from what the requester asked. The owner's clarification then changes a cold later role's action.
3. **Counter:** It may slide into a generic fact-checker. A capable authority-plus-origin-ID control may tie with less preparation.
4. **Assumption:** Company capability questions often lack one authoritative source, and agent summaries drop qualifiers as they propagate.
5. **What would change my mind:** Kill test 8 ties. Or the reviewed-support step needs so much human review that the memory never gets reused.
6. **Direct responses:**
   - **Read receipts:** I accept they are not semantic support. The repair separates `READ` (provenance) from `SUPPORTS` (proposed, then reviewed).
   - **H02:** I reject it on V3/V1 precedent, not on any invented preference.
   - **No-graph controls:** The authority checks, origin-ID set and recursive SQL controls all stay fully capable.
   - **What changed:** I drop the launch-approval demo, because the authority-check control kills it.
