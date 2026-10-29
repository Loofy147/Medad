# Medad Transactional Store Contract v0.1

## Purpose and boundary

This contract is the persistence seam between Medad's decision engines and future adapters. It prevents the current local journals from becoming the implicit universal storage API. Implementations may change; record identity, revision checks, authorization decisions, and audit semantics must remain stable.

The engine/store.py module defines TransactionalStore and implements it as SQLiteStore. The backend is intended for local and single-host use. It is not a shared multi-host database service and is not currently wired to a live API or the browser UI.

## Stored record categories

| Collection | Intended contents | Write authority |
|---|---|---|
| evidence | Evidence contract records, metadata, source references | Analyst |
| runs | Reproducible decision-run packets | Analyst |
| tasks | Tasks, owners, states, due dates and dependencies | Analyst |
| artifacts | Artifact references, content digests and metadata | Analyst |
| decisions | Immutable evidence reviews, stage decisions and risk-acceptance records | Reviewer or approver, according to decision type |

The store validates evidence records through the existing decision-kernel contract, checks decision-run identity/hashes and analysis-only status, and requires artifact records to carry a reference or a valid SHA-256 digest. A reference or digest is not proof that external bytes are authentic; provenance verification and retained artifact bytes still need a trusted adapter.

## Transaction and revision contract

- Each successful record write and its audit event commit in the same SQLite transaction.
- New records start at revision 1. Updating an existing record requires its exact expected_revision; stale writes fail with StoreConflict. Blind overwrites are rejected.
- Decision records are append-only: reusing a decision ID fails, and generic record updates cannot modify the decisions collection.
- Unsupported collections, unknown decision fields, non-JSON values, NaN and Infinity are rejected.
- SQLite uses BEGIN IMMEDIATE, a busy timeout and WAL/FULL synchronous mode for file-backed databases. This is still a single-host persistence design; deployments needing multiple hosts should implement the same protocol on a server database with migrations and transactional concurrency tests.

## Identity and access policy

Roles are reader, analyst, reviewer, approver, auditor and admin. The policy defaults to deny:

- Analysts can create/update evidence, runs, tasks and artifacts, but cannot record review/approval decisions.
- Reviewers can record EVIDENCE_REVIEW decisions only.
- Approvers can record STAGE_DECISION and RISK_ACCEPTANCE decisions only.
- Auditors can inspect and verify the audit chain; they cannot mutate business records.
- Admin can perform all actions inside this local policy. Admin is not a substitute for a production identity governance process.

**Important security boundary:** Actor is an identity value object, not authentication. The library does not verify passwords, sessions, JWTs, signatures, group membership or identity-provider claims. A trusted adapter must authenticate the caller and only then construct the Actor with verified issuer, subject and roles. Until that adapter exists, this is a tested domain-level authorization mechanism, not multi-user production security.

## Decision-record requirements

Evidence review outcomes are PASS, FAIL or UNKNOWN and must cite existing evidence record IDs. Stage outcomes are ADVANCE, HOLD or REJECT; ADVANCE requires evidence references, rationale, stop condition and rollback plan. Risk acceptance outcomes are ACCEPT or DECLINE; ACCEPT additionally requires named accepted risks, a stop condition and rollback plan.

Each decision automatically captures the exact evidence revision and content hash it reviewed. A STAGE_DECISION with ADVANCE is rejected unless every cited record has a PASS EVIDENCE_REVIEW for the same current revision and hash, and the stage decision timestamp does not precede that review. Updating evidence therefore invalidates the old review for future advancement until the new revision is reviewed.

These records document a human decision; they do not execute a business action or grant financial authorization. The current workflow remains analysis-only with authorization_granted=false.

## Audit contract

Successful writes, decision records and authorization denials create audit events. Each event records actor subject, issuer, role claims at the time, authentication timestamp/method, action, result and reason. Events are chained with SHA-256 hashes; database triggers block ordinary update/delete operations on audit events and decision records. Verification detects altered or re-ordered events when the relevant chain is present.

This is tamper-evident, not tamper-proof. A database owner can disable triggers, replace the database or truncate the end of the chain. Production must anchor checkpoints outside the database, restrict filesystem/DB administration, back up and test restoration, and monitor audit verification.

## Migration and recovery gates before external integration

1. Connect a real authentication adapter and test role claims/tenant boundaries; never accept client-supplied roles as proof.
2. Keep extending persistence validation for task-state transitions, tenant-scoped references and verification of retained artifact bytes; evidence, decision-run envelope and basic artifact identity validation are already enforced.
3. Test migrations from every supported schema version and concurrent writer behavior on the target database.
4. Add external audit checkpoints, backups, restore drills and retention policies.
5. Build API/connector adapters against TransactionalStore; do not let the UI write directly to the database.
6. Keep external effects behind separately authorized, idempotent commands. Recording ADVANCE must not automatically buy stock, spend money, message a supplier or dispatch a task.
7. Re-run the complete regression suite and security-focused negative tests before enabling any real integrations.
