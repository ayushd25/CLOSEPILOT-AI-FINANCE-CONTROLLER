# AI Safety and Governance

## Core principle

> Models investigate. Rules authorize. Evidence proves.

The AI investigator is not an authority. It can inspect data and propose an action, but cannot directly close cases, write to MongoDB, execute arbitrary SQL or Mongo queries, or approve money movement.

## Required flow

```
LLM → typed proposal → schema validation → policy engine → authorized service → database
```

## AI responsibilities

- inspect case data
- inspect related financial records
- reason over discrepancies
- identify root cause
- rank evidence
- explain matches/non-matches
- propose action, confidence, risk
- identify missing evidence

## AI must NOT

- write to MongoDB
- execute arbitrary SQL
- execute arbitrary Mongo queries
- call unrestricted tools
- approve money movement
- directly close cases
- fabricate evidence
- see ground truth during evaluation

## Read-only tools

Narrowly scoped:

```text
get_case
get_payment
get_order
get_settlement
get_bank_transaction
get_related_records
get_evidence
get_reconciliation_candidates
get_policy
```

Every tool validates IDs and returns bounded data.

## Structured output

The model returns `InvestigationProposal`:

```text
case_id
conclusion
root_cause
confidence
risk_level
proposed_action
evidence_ids[]
reason_codes[]
unresolved_questions[]
```

Validated with Pydantic.

## Evidence requirement

AI cannot claim a conclusion without citing evidence IDs. If evidence is insufficient:

```text
conclusion = INSUFFICIENT_EVIDENCE
proposed_action = KEEP_EXCEPTION
```

## Failure handling

If Groq is unavailable:

- deterministic reconciliation continues
- case becomes HUMAN_REVIEW or EXCEPTION
- system does not fake an AI response

## Policy authorization

The only code allowed to close a case is an authorized service that receives a validated policy decision.

Supported human actions:

- approve & close
- reject proposal
- keep exception
- request investigation

Every action creates an audit event.

## AI boundaries in analytics

The deterministic analytic services do not outsource decisions to the LLM:

- **Cash forecast**: the projection is computed entirely from records (bank cash, scheduled settlements, receivables, refunds, adjustments, risk holdback). The AI may only *commentate* by restating the computed figures — it cannot change the numbers `app/forecast/service.py`.
- **Tax-line matcher**: the expected tax is derived from the record (taxable × rate, or gross − settlement − fee), never guessed by the model. AI analysis of an exception runs *after* the deterministic VERIFIED / EXCEPTION classification and may suggest a reason to a human reviewer, but it never changes the classification `app/reconciliation/tax_matcher.py`.
- **Human review overrides**: a human may override a tax-line status via the review endpoint; the action is gated by the `X-User-Role` header and recorded as `TAX_MATCH_REVIEWED` in the audit trail.
