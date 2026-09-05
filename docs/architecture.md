# ClosePilot Architecture

## High-level architecture

```text
Synthetic Generator ─────► Integration Layer
                           ↓
                  Canonical Financial Model
                           ↓
                  Normalization / Validation
                           ↓
                  Candidate Generation
                           ↓
               Deterministic Reconciliation
                     ↙              ↘
               matched           ambiguous
                  ↓                  ↓
            evidence              AI Investigator
                    ↓                  ↓
                 policy ← typed proposal
                    ↓
          ┌─────────┴─────────┐
          ↓                   ↓
      Auto-close          Human Review
          └─────────┬─────────┘
                    ↓
             Audit / Evidence Ledger
                    ↓
              Evaluation Engine
```

## Core principle

**LLM ≠ authority.**

The LLM may investigate, interpret, explain, rank evidence, and propose an action. It must never directly mutate financial records or decide authorization.

Required flow:

```
LLM → typed proposal → schema validation → policy engine → authorized service → database
```

## Backend

- Python 3.12+
- FastAPI
- Pydantic
- MongoDB (motor async driver)
- pytest
- structured logging

## AI

- LangChain
- `langchain-groq`
- Groq API (configurable model via env)
- isolated behind application service

## Frontend

- Next.js
- TypeScript
- Tailwind CSS
- shadcn/ui components
- Recharts (trends)
- React Flow (evidence graph)

## Repository structure

```text
closepilot/
  apps/
    api/
    web/
  packages/
    shared/
  data/
  docs/
  tests/
  docker/
  docker-compose.yml
  .env.example
  README.md
```

## Backend logical structure

```text
apps/api/
  app/
    main.py
    config.py
    db/
    api/
    domain/
    services/
    reconciliation/
    ai/
    evidence/
    policy/
    audit/
    evaluation/
    synthetic/
    security/
```

## Security model

- Credentials: backend only
- AI receives only scoped case/evidence data
- No arbitrary tool execution
- Financial domain logic never lives in frontend
- Audit events are append-only

## Analytic services

Two deterministic surfaces sit on top of the same canonical financial model — the AI is advisory only:

- **Forward Cash Forecast** — `app/forecast/service.py` computes a 7/14/30-day projection from current bank cash, scheduled settlements, receivables, refunds/adjustments/chargebacks, and a risk holdback scaled from open cases; a confidence band reflects data quality. `app/api/forecast.py` exposes `GET /forecast`. The optional AI commentary (`ai=true`) may only restate the computed figures.
- **Tax-Line Matcher** — `app/reconciliation/tax_matcher.py` groups records per reference and derives the expected tax (rate-based `round(taxable × rate / 100)` or legacy `gross − settlement − fee`), classifies each line VERIFIED / EXCEPTION / HUMAN_REVIEW within tolerance, and links discrepancies into cases with evidence and audit events. `app/api/tax_lines.py` exposes run/list/metrics/detail/review under `/reconciliation/tax-lines`. AI explanation (if configured) runs only after deterministic classification and never alters it.
