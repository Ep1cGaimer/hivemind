Showing 1 of 78 activities (limited to 1)

## Attacks, in order: weakness / what works without a graph / mature substitute / data problem / overclaim / demo break / one repair / cheapest kill test

**H11 (institutional echo)**
- **Weakness:** A mandatory owner-source check stops the launch-approval example without finding any echo.
- **Without a graph:** A citation-ID set deduplicates shallow echoes, and "always cite a primary source" is cheap.
- **Substitutes:** V6 covers the mechanism. Graphiti, Glean and MAP-style provenance are capable controls.
- **Data:** Read receipts show what a run saw, not what supports a claim. Shared background context can falsely merge separate observations.
- **Overclaim:** Treating common roots as non-independence, or independent roots as truth.
- **Demo break:** The owner approves in the scenario anyway.
- **Repair:** Use a cross-team capability claim with no single approving record. The gateway stores *available* evidence (reads), *claimed* support (LLM-proposed, with quotes) and *reviewed* support separately. Only reviewed support counts. Root counts never authorize action.
- **Kill:** A "primary-source-or-owner-approval" control with the same agent gives the same questions and the same cold-session action across blind cases.

**H03 (knowledge handover)**
- **Weakness:** Recorded paths cannot expose tacit knowledge. If the fixture stores a decision without a rationale, the target was curated.
- **Without a graph:** A generic handover prompt with the same notes and question budget may ask the same questions.
- **Substitutes:** Bus-factor tools, service catalogs, wikis.
- **Data:** Attestation edges are partial. Co-work is not expertise or permission.
- **Overclaim:** Calling a person the "sole knower."
- **Demo break:** The leaver is scripted, so the answers are authored.
- **Repair:** Choose interview targets only from observed artifact-to-dependent paths and unanswered thread questions, with no SHOULD_ASK labels. State plainly that the answers are scripted.
- **Kill:** A generic prompt over the same notes and budget picks the same questions, and the cold successor answers identically.

**H06 (two-sided handoff)**
- **Weakness:** If scope edges are hand-authored, ingestion did the interpretation.
- **Without a graph:** A signed-off checklist plus the same agent.
- **Substitutes:** Gong, Gainsight, checklists (V8).
- **Data:** A missing ACCEPTED edge may be stale or incomplete records, not refusal.
- **Overclaim:** "Not delivered," or any legal conclusion.
- **Demo break:** "Migration" becomes a contrived wording puzzle.
- **Repair:** Ingest raw sales and delivery passages with no scope vocabulary. Edges are proposed with quotes, and the recipient's reviewed clarification persists to the next role.
- **Kill:** A checklist plus the same agent reaches the same include, exclude or ask outcome on six paraphrase packets.

## Position

- **Preferred, conditionally: H11 in the repaired form. Exact change:** I leave H03 as the minority card.
  - **What changed it:** The attack on H03 holds. The tiny fixture lets a generic prompt read the same notes and ask the same questions, and the interviewee is scripted. That leaves H03's graph role the weakest of the three.
  - **Why H11:** It is the only one whose provenance can come from the memory layer itself. A gateway records reads and writes while real agent runs execute, instead of an importer hand-authoring them. That answers the "ingestion did the interpretation" objection. It also fits your ask most directly: agents learn from one another's summaries, and a cold role changes its action.
- **Strongest support:** Echo is a hive-mind-specific failure. Three role summaries that agree can trace to one tentative remark.
- **Strongest counter:**
  - V6 and the V3–V5 systems occupy the mechanism, so the claim is only a product hypothesis.
  - A "cite a primary source or get owner approval" rule may produce the same action with less preparation, which is a real kill condition.
  - LLM-proposed support is not semantic proof.
- **Assumption:** The gateway-recorded lineage plus reviewed support proposals gives a cold role a different, justified action than citation-dedupe does.
- **Evidence changing my mind:**
  - The kill test above passing for the control.
  - A mature tool recording claim-level support with review.
  - A blind packet where reviewed claim support is unavailable or unreliable. Then I move to H03 or reject.
- **Response to the strongest objection (authority check):** I accept it. The repair removes the single-owner approval from the scenario and does not hide authority records from the baseline. Read receipts are labelled "available," never "supports."

**Verdict:** Unresolved, with the demand and incumbent gaps open for the owner. I see no H11 variant that justifies dropping H03 as the minority card.
