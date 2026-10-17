# Chair's independent concepts — before reading new peer ideas

## CH-A: EchoLedger — prevent circular corroboration in the company brain

User: company operations lead relying on support/sales/planning agents to reuse internal knowledge. Workflow: agents turn a tentative claim into summaries, handoffs and plans, then later mistake the copies for several confirming sources. Current approach/hypothesis: shared chat/vector memory and citations can repeat the same root claim; actual frequency/usefulness needs validation.

Graph: Claim(scope,qualifiers,status), SourceArtifact(immutable origin/version), AgentRun, MemoryUse, Decision, ActionProposal; DERIVED_FROM, CITES, SUPPORTS/CONTRADICTS (proposed semantic assessment), USED_CLAIM, DEPENDS_ON, REVIEWED_BY. Exact operation: follow support/derivation ancestry across agents to original observed artifacts, preserving unknown roots/cycles; enumerate decisions that consumed the claim. Three cited summaries sharing one underlying source are not three independent observations. Root separation does not prove truth/statistical independence.

Agent interprets whether source text actually supports the qualified claim; retrieves lineage; asks the authoritative owner for review rather than promoting an unsupported assertion; drafts a revised plan after source correction. Only internal fixture review requests/drafts, no actual messages. Deterministic code records memory-read receipts, immutable derivations and permissions; LLM cannot certify truth. No automatic trust from a source count.

Data: 12 synthetic source/derived artifacts, two agent-role sessions, two claims and one downstream commitment. Raw artifact provenance generated during actual fixture agent reads/writes rather than pre-storing SHOULD_REJECT edges.

Demo: three agents appear to agree a feature is approved; graph reveals every supporting document descends from one old tentative note, so a later cold-start agent refuses to turn it into a customer commitment and asks for authoritative evidence. Add a genuine scoped approval; new session updates the plan with a witness. Same model+same facts against flat/vector and relationship-aware SQL controls; measure valid root attribution, unsupported promotion, appropriate clarification, correction recall and exact downstream consumers. No scripted baseline error.

Substitutes: provenance-aware memory, Graphiti, Honest Memory, citation validation and manual original-source review. Differentiation hypothesis: treating *echoed agent memory as dependence*, not independent evidence, with downstream action receipts. New relative to reference in precise circular-corroboration workflow/mechanism, while sharing provenance components with Honest Memory/ResearchOS; competitive novelty unverified.

Four-day MVP: immutable artifact/claim graph, two role sessions, fixed ancestry/consumer queries, one review/draft loop, 3 source controls, evidence view. Reject if it collapses into trivial citation de-duplication, source lineage is invented by the model, or there is no meaningful user problem. Falsifier: same root under different quotations/aliases must not count as independent evidence; genuinely distinct roots must not be merged merely because wording matches. Unknown derivation must stay unknown. SQL parity acceptable.

## CH-B: PrecedentRelay — transfer a company's past solution without transferring its hidden exceptions

User: operations manager delegating a repeat customer-onboarding exception to a fresh agent. Workflow: prior agent succeeded under an explicit region, product version, approval and temporary concession; the next agent retrieves the successful playbook and wrongly assumes it applies. Current substitutes: runbooks, memory search, ticket/history review and rule/approval engines.

Graph: Episode, ProcedureVersion, QualifiedConstraint, ExceptionApproval, Evidence, CurrentCase, Owner; USED_PROCEDURE, REQUIRED, VALID_FOR, APPROVED_BY, OBSERVED_IN, EXPIRED_AT/SUPERSEDES. Operation: match source-qualified preconditions and approval scope from the successful episode to the new case, exposing missing facts, incompatible versions or expired exception. Removing relations loses why the old procedure was valid, not just its prose.

Agent reads raw episode/source passages, proposes candidate precedent, investigates missing case qualifiers and drafts an adapted checklist or owner clarification; deterministic rules govern exact approved scope/expiry and no external execution. Episode prose is not permission. Data: synthetic two customer cases, one playbook, one exception and four source notes. No real customer/company data.

Demo: agent A resolves sandbox case; clear session; B finds the same playbook but traverses its expiring exemption and declines to reuse the restricted step for the new region, proposing the allowed alternative. Flat/vector with same notes, same-LLM SQL and configured policy/rule controls; measure invalid precedent reuse, evidence-grounded clarification and useful transfer.

Four-day MVP: one case vocabulary, one procedural memory, two role sessions, precondition/exception queries and review queue. Biggest rejection risk: policy engine plus search already solves it; manual preconditions may encode the answer. Kill test: independently authored wording and irrelevant exception decoy; fail if safe adaptation depends on hidden issue tags or all useful checks are precomputed. Reference-adjacent, not counted new by default: ResearchOS already includes procedural memory and DecisionPulse temporal qualification.

## Position

Initially favor CH-A as a testable new memory failure, not as an established winner. Support: copying knowledge changes perceived corroboration across agents and the ancestry is genuinely connected. Counter: citation/provenance infrastructure may already solve it and actual company pain is unvalidated. Assumption: real agents consume derived output without retaining reliable root provenance. Change mind if official systems already expose the same runtime dependence gate cheaply, or source/support judgments are too unreliable to make a useful decision. Strongest anticipated objection: a root-ID set may solve it without a graph; answer is not database exclusivity—need runtime branching derivation/consumer paths and qualified semantic interpretation to earn product value. If only root-ID de-duplication is needed, reject this concept.
