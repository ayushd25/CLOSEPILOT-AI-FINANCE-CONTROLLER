# Five-Minute Demo Script

## Goal

Demonstrate a real autonomous finance-control workflow, not a generic AI chatbot.

## Scene 1 — Command Center

Show live dashboard with real backend metrics:

> ClosePilot is an autonomous finance controller. It reconciles financial records, investigates exceptions, and only closes cases when evidence and policy allow it.

## Scene 2 — Razorpay Test Mode

Open Data Sources. Show:

- Razorpay Test Mode connected
- actual fetched payment/settlement counts
- last sync

Click Sync Now if appropriate.

> The demo can ingest authentic Razorpay Test Mode data directly. We keep the raw source payload for provenance and normalize it into our internal financial model.

## Scene 3 — Reconciliation

Run reconciliation. Show:

- straightforward cases auto-resolved
- ambiguous cases routed to exceptions

> We don't waste an LLM call on every transaction. Deterministic controls handle the obvious cases first.

## Scene 4 — Difficult exception

Open a case with a discrepancy. Show payment, settlement, bank transaction, amount difference, fee/tax, candidates. Run AI investigation.

> The AI investigator is not an authority. It can inspect evidence and propose a conclusion, but it cannot close the case.

## Scene 5 — Evidence graph

Open the graph. Show Payment → Settlement → Bank transaction with supporting fee/tax/invoice/adjustment evidence.

> Every conclusion has a provenance chain.

## Scene 6 — Policy

Show policy decision.

If safe:
> Evidence is sufficient, risk is low, and policy authorizes the action.

If unsafe:
> The system refuses to auto-close and escalates to a human.

## Scene 7 — Audit

Show audit timeline.

> Every investigation, policy decision, and human action is recorded and replayable.

## Scene 8 — Evaluation Lab

Run controlled synthetic benchmark. Show baseline comparison, precision, recall, false auto-match, exception rate, auto-resolution, throughput.

> We don't claim the AI is good because it looks good. We measure it against hidden ground truth.

## Closing line

> ClosePilot doesn't ask AI to be trusted. It makes AI prove its work.

Alternative:

> Models investigate. Rules authorize. Evidence proves.
