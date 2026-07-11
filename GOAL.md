# FlatWatch Goal

## Product

FlatWatch is an accountable financial-transparency and operations product for
residential communities. It turns fragmented receipts, transactions,
explanations, challenges, and approvals into a shared, auditable workflow while
keeping sensitive resident and payment evidence private.

## Product promise

> Every community expense understandable, challengeable, and accountable.

## Primary customers

- Residents who need understandable evidence for community expenses.
- Treasurers, committee members, and managers who need efficient, auditable
  operations.
- Auditors or reviewers who need traceable source evidence and decisions.

## Customer jobs

1. See where community money came from and where it went.
2. Match transactions, invoices, receipts, approvals, and service periods.
3. Ask questions in ordinary language and receive evidence-linked answers.
4. Flag missing, duplicate, unusual, or inconsistent expenses.
5. Challenge a transaction and track response, evidence, and resolution.
6. Delegate routine reconciliation to AI without allowing silent financial
   writes.
7. Prove who approved consequential actions without exposing identity evidence.

## Owned capabilities

- transaction and receipt ingestion, normalization, matching, and reconciliation;
- dashboards and evidence-linked financial explanations;
- challenge, response, correction, and resolution workflows;
- resident, committee, reviewer, and auditor roles;
- AI-assisted anomaly detection, summarization, and workflow preparation;
- dual-control approval for sensitive actions;
- immutable or independently verifiable action-receipt commitments;
- private evidence access, retention, deletion, and audit controls.

## Relationship to AadhaarChain

FlatWatch retains its application-local resident and administrator model.
AadhaarChain provides step-up assurance and AgentGuard authorization only when
an elevated workflow needs it.

- FlatWatch receives minimal claims, never Aadhaar/PAN documents.
- An AI agent receives only purpose- and resource-bound authority.
- Protected actions re-check current trust, policy, approval, and revocation.
- The shared receipt proves authorization; detailed financial evidence remains
  private in FlatWatch.

## Hard rules

- AI may identify anomalies and propose actions; it cannot declare fraud or
  liability without human review.
- Financial writes, payout changes, evidence deletion, and final challenge
  decisions require authenticated roles and appropriate approval thresholds.
- Every answer distinguishes source evidence, deterministic calculation, and AI
  inference.
- Missing or contradictory evidence remains visible; the system does not invent
  reconciliation.
- Receipt and transaction access follows least privilege and produces an audit
  event.
- Challenges support correction, appeal, and supersession rather than silent
  history rewriting.
- Community financial and resident data stays off-chain.
- Demo auth, mock ingestion, and mock OCR cannot be presented as production
  assurance.

## Phase-one outcome

Deliver one evidence-complete community-expense journey:

1. Ingest a signed or clearly labeled fixture transaction and receipt.
2. Match them and show the calculation and source evidence.
3. Let a resident ask an evidence-linked question.
4. Detect and explain a discrepancy without asserting guilt.
5. Open a challenge and assign the correct accountable role.
6. Have an AI agent prepare, but not finalize, the response.
7. Require dual approval for a consequential correction or payment proposal.
8. Record an independently verifiable authorization receipt.
9. Show correction, resolution, and audit history to permitted users.

## Success measures

- Every displayed total traces to source transactions and evidence.
- Users can distinguish fact, calculation, and AI inference.
- Challenges have visible owner, state, evidence, and resolution time.
- Zero protected financial writes from UI-only authorization.
- No private evidence appears in shared/on-chain receipts.
- AI reduces reconciliation and response time without increasing false claims.
- Resident comprehension and trust improve in pilot interviews.

## Non-goals

- Replacing banks, payment processors, statutory auditors, or legal adjudication.
- Publicly labeling residents, vendors, or committee members as fraudulent.
- A universal resident reputation score.
- Autonomous payments or irreversible corrections by an AI agent.
- Publishing receipts, resident data, or transaction details on-chain.
- Claiming production readiness while ingestion, OCR, auth, and storage are mock
  or local-only.

## Source of truth

This file owns the FlatWatch product goal. `README.md` owns development and
runtime instructions. Workspace integration status remains in the root
`AGENTS.md` and `PRODUCTION-READINESS.md`.
