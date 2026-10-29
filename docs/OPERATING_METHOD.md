# Medad Operating Method v0.2

## Objective

Medad is a reusable commercial decision system. Products are replaceable inputs; the durable asset is the method for capturing claims, evaluating evidence, modeling economics, deciding the next action, and recording what happened.

## Operating cycle: RIV

1. **Research** — state the question and applicability boundary; gather dated sources, quote artifacts, observations and counterevidence. Separate a seller claim from an independently verified fact.
2. **Implement** — encode only the decision logic justified by the evidence and contract. Keep model assumptions explicit and avoid hidden defaults that can make an unknown cost look like zero.
3. **Verify** — test expected behavior, edge cases, negative paths, duplicate/idempotent replay and data mutations. Record the exact code revision, evidence snapshot and run.
4. **Decide** — advance only when required gates pass. Otherwise keep the task open with a named next discriminating test.
5. **Revalidate** — refresh any time-bounded evidence and check whether the earlier decision is still applicable.

A green test proves the tested contract for that revision; it does not establish market truth, supplier legitimacy, or production readiness.

## Epistemic labels

Claims use these labels consistently:

| Label | Meaning | Decision treatment |
|---|---|---|
| ESTABLISHED | Accepted as established under the project's source and review standard | Requires at least two independent, non-assumption supporting records in the current kernel |
| EXPERIMENTALLY_SUPPORTED | Supported by a documented experiment or measured cohort | Requires an experimental artifact, method reference, positive sample size, and no unresolved contradiction |
| USER_REPORTED | Reported by the user or an operator | Keep attribution visible; do not recast as independently verified |
| INFERENCE | A conclusion derived from one or more observations | Preserve the link to premises; unresolved contradictions make it OPEN |
| HYPOTHESIS | A proposition to test | Does not become fact just because it is repeated |
| CONTRADICTED | The linked evidence contradicts the proposition | Revisit prior decisions that depended on it |
| UNKNOWN | Evidence is absent or insufficient to decide | Never translate unknown into zero, false, or pass |
| OPEN | A conflict, applicability question, or decision remains unresolved | Identify the next discriminating test and owner |

These statuses are decision-support labels, not a universal theory of truth. They must be interpreted within the claim's scope, date, population and operating conditions.

## Evidence contract

Each evidence record must have a stable identity, source kind, evidence label, polarity (supports, contradicts, context), observation date, and an independence key. URL records require HTTPS; non-URL records require a stable artifact reference. Observed records declare sample size. Experiment records declare both a method reference and a positive sample size.

Important restrictions:

- Source existence is not source correctness.
- Two URLs that reproduce the same seller or dataset are not necessarily independent. Reuse one independence key when their information shares a root.
- A screenshot or artifact reference is traceability, not proof of authenticity by itself.
- Freshness is evaluated from observation dates; a manually entered recent age must not make old source material fresh.
- Contradictory evidence remains visible. Support and contradiction together produce OPEN, not an average confidence score.
- Data-quality scores are heuristic completeness/freshness indicators; they are not probabilities of truth, demand, or profit.

## Unit economics

The unit-economics engine calculates expected placed, delivered, failed, returned and retained orders; contribution before ads; cost allocation; profit; margin; CAC per placed and retained order; and break-even thresholds.

It does not infer values that were not supplied. A positive arithmetic result with missing, stale, or low-coverage evidence is UNVERIFIED_ECONOMICS. A TEST_CANDIDATE status requires HIGH evidence quality and acceptable delivery/return thresholds; it only permits a bounded test, not inventory scale-up.

The separate sensitivity engine performs one-factor-at-a-time shocks and bracketed threshold search. It reports which inputs drive the modeled outcome under explicit shock bounds. It does not learn probabilities, capture all interactions, or upgrade evidence quality. Re-run a small factorial or multi-factor test when input interactions are material.

## Decision gate contract

Every gate is one of PASS, FAIL, UNKNOWN, NOT_APPLICABLE and carries evidence references. Only explicit PASS satisfies a required gate, and only when each referenced record exists in the supplied evidence registry and passes its evidence contract. PASS also requires reviewed_by, a valid reviewed_at date, and a reason. NOT_APPLICABLE requires a reviewer, date and rationale; FAIL requires a reason. A PASS without evidence, review metadata, or valid evidence references is treated as UNKNOWN. Unknown and failed gates block the stage transition.

A generic eligibility result is not an authorization. The person or role empowered to decide must record the decision, owner, reason, review date, accepted risks, and rollback/stop condition.

For product sourcing, the stronger specialized stage gate additionally checks:
- exact SKU and dated inspected sample;
- two current quotes from distinct verified sellers, matching the same SKU and quantity/currency terms;
- a reconciled landed-cost breakdown tied to quote artifacts;
- current seller-specific courier terms, destination coverage and cash-remittance timing;
- a bounded campaign with a traceable spend/creative/attribution record;
- order cohorts reconciled so delivered plus failed equals placed and retained equals delivered minus returned;
- two distinct recent reconciled cohorts before human scale review.

## Instant event protocol

Event shape follows:

(Context, Trigger, Automatic Action, State Delta, Observations, Invariants, Recovery, Propagation)

- **Context:** subject ID, scenario/revision, actor or system, and applicability.
- **Trigger:** deterministic rule and threshold that fired.
- **Automatic Action:** a reversible, safe recommendation or allowed state transition. A financial commitment is never automatic by default.
- **State Delta:** explicit event or decision state change, including before/after state where applicable.
- **Observations:** source, timestamps, evidence references, snapshot hash and measured values.
- **Invariants:** idempotency, unique event identity, traceability, no false stage promotion, and no mutation of prior evidence.
- **Recovery:** acknowledge, resolve, dismiss, reopen or re-run; transitions append audit records rather than silently overwrite history.
- **Propagation:** downstream task/decision references updated only through authorized interfaces; external systems need idempotent adapters.

The Python Instant engine can derive alerts from one evaluated economics snapshot and persist them to a local JSONL journal. The journal uses per-process locking, append and fsync, plus idempotency checks. It is a prototype/local store—not a multi-host transactional database, and not a live feed. The browser Instant panel derives local alerts from manually entered inputs, keeps a session-only event journal, and exports JSON; it does not synchronize with the Python journal or send external notifications.

Production requires a transactional store, access controls, authenticated actors, backup/recovery, schema migration and operational monitoring.

## Continuation frontier contract

At every substantial handoff, record:
- task/goal and applicability boundary;
- current repository, branch, commit/ref and state snapshot;
- last verified commit and exact green test/run;
- established findings, assumptions, unknowns and contradictions;
- killed/failing tests and negative results;
- open gates and dependencies;
- next discriminating test, owner and stop conditions.

This prevents restarting from recollection or treating an old green run as proof about newer code.

## Verification contract

Run all Python tests from the engine directory:

    cd engine
    python -m unittest -v
    python engine.py
    python opportunity.py

CI must test the exact current head revision. Confirm that all expected test modules were discovered; do not equate a green older commit with the current code.

For engine changes, include:
- normal case;
- zero/missing/invalid input;
- boundary values;
- evidence missing or stale;
- contradiction/negative path;
- replay/idempotency;
- mutation test that removes the guard expected to block a bad decision;
- exact regression test for each previously found failure.

## Local CLI examples

Input files are local JSON and must be reviewed before sharing. From the engine directory:

- `python cli.py economics --input inputs.json` — calculate unit economics and evidence-aware decision status.
- `python cli.py sensitivity --input inputs.json` — compare explicit shocks; no probability estimates are generated.
- `python cli.py instant --input inputs.json --journal .medad/instant-events.jsonl` — append deduplicated local alerts; no external notifications are sent.
- `python cli.py claim --input claim-and-evidence.json` — validate a claim against linked records.
- `python cli.py gates --input gates-and-evidence.json` — require a supplied evidence registry plus reviewer, date and reason for PASS.
- `python cli.py continuation --input continuation.json` — check a handoff contract.
- `python cli.py opportunity-audit --snapshot ../data/research_snapshot_2026-10-29.json` — inspect the dated sourcing registry.

The event journal directory `.medad/` is ignored by version control. It is a local development store, not a secure shared database.

## Current implementation boundary

Implemented as standard-library Python modules:
- engine.py: unit economics and evidence-aware decision status;
- sensitivity.py: deterministic sensitivity and threshold calculations;
- decision_kernel.py: evidence/claim validation, generic gates and continuation contract;
- opportunity.py: product-specific source checks and stage gates;
- instant.py: rule-generated alerts and local append-only journal.

Not yet implemented: API/database service, multi-user authorization, synchronized event delivery, persistent evidence/artifact storage, external marketplace/supplier/courier/ad adapters, authenticated partner actions, real-time notification transport, model calibration from historical cohorts, and production deployment. Those boundaries must remain explicit in the UI.
