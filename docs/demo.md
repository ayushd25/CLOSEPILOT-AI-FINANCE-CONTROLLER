# Five-Minute Demo Script

## Goal

Demonstrate a real autonomous finance-control workflow, not a generic AI chatbot.

## Scene 1 — Landing & Command Center

Open the landing page (`/`), then the Command Center (`/explore`). Show live dashboard with real backend metrics:

> ClosePilot is an autonomous finance controller. It reconciles financial records, investigates exceptions, and only closes cases when evidence and policy allow it.

## Scene 2 — Synthetic data source

Open Data Sources. Show:

- the scenario generator (case count + seed)
- generate a fresh dataset and show it appears the generated datasets list

> The demo runs entirely on controlled synthetic financial data with hidden ground-truth labels. The generator is deterministic, so every run is reproducible — we never pretend to be live when we aren't.

## Scene 3 — Reconciliation

Run reconciliation. Show:

- straightforward cases auto-resolved
- ambiguous cases routed to exceptions

> We don't waste an LLM call on every transaction. Deterministic controls handle the obvious cases first.

## Scene 4 — Difficult exception

Open a case with a discrepancy. Show payment, settlement, bank transaction, amount difference, fee/tax, candidates. Run AI investigation.

> The AI investigator is not an authority. It can inspect evidence and propose a conclusion, but it cannot close the case.

## Scene 5 — Cash Forecast

Open Cash Forecast (`/forecast`). Switch horizons 7 / 14 / 30 days. Show current cash, projected curve (optimistic), risk holdback (dashed line), and confidence.

> Every figure is projected deterministically from the loaded records — scheduled settlements, receivables, refunds, adjustments, and a risk holdback pulled from open cases. The AI commentary only explains the numbers; it can't change them.

## Scene 6 — Tax-line matcher

Open Tax-Line Matcher (`/tax`). Run the matcher and show VERIFIED / EXCEPTION / HUMAN_REVIEW split. Open an EXCEPTION row: expected = taxable × rate, recorded, difference, evidence. Change the status via the review panel.

> The matcher derives the expected tax from the record — it never asks the AI to guess it. A human can review and override, and every decision lands in the audit trail as TAX_MATCH_REVIEWED.

## Scene 7 — Evidence graph

Open the graph. Show Payment → Settlement → Bank transaction with supporting fee/tax/invoice/adjustment evidence.

> Every conclusion has a provenance chain.

## Scene 8 — Policy

Show policy decision.

If safe:
> Evidence is sufficient, risk is low, and policy authorizes the action.

If unsafe:
> The system refuses to auto-close and escalates to a human.

## Scene 9 — Audit

Show audit timeline.

> Every investigation, policy decision, and human action is recorded and replayable.

## Scene 10 — Evaluation Lab

Run controlled synthetic benchmark. Show baseline comparison, precision, recall, false auto-match, exception rate, auto-resolution, throughput.

> We don't claim the AI is good because it looks good. We measure it against hidden ground truth.

## Closing line

> ClosePilot doesn't ask AI to be trusted. It makes AI prove its work.

Alternative:

> Models investigate. Rules authorize. Evidence proves.
