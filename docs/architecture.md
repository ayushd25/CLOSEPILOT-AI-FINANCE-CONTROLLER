# ClosePilot Architecture

## High-level architecture

```text
Razorpay Test Mode APIs ─────┐
                             ├→ Integration Layer
Synthetic Generator ─────────┘
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
    integrations/
      razorpay/
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

- Razorpay credentials: backend only
- AI receives only scoped case/evidence data
- No arbitrary tool execution
- Financial domain logic never lives in frontend
- Audit events are append-only
