# ClosePilot - Autonomous Finance Controller

**Models investigate. Rules authorize. Evidence proves.**

ClosePilot is an AI Finance Controller for **Razorpay Buildathon 2026 (Track 04)**. It ingests controlled synthetic financial data, reconciles payments / settlements / bank transactions / invoices / fees / taxes / refunds / adjustments, investigates difficult discrepancies with an AI investigator, verifies every tax line against the expected tax, and forecasts forward cash (7/14/30 days) from the same records. It safely auto-closes only cases that satisfy deterministic evidence and policy controls.

---

## Core principle

**LLM ≠ authority.**

The LLM may investigate, interpret, explain, rank evidence, and propose an action. It must **never** directly mutate financial records or decide authorization.

Required flow:

```
LLM → typed proposal → schema validation → policy engine → authorized service → database
```

- Every case goes through **rule-based validation** before any auto-close.
- All actions are recorded in an **append-only audit / evidence ledger**.
- An **evaluation lab** benchmarks the deterministic engine against simple baselines.

---

## Architecture

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

---

## Repository structure

```text
closepilot/
  apps/
    api/          # FastAPI backend (Python 3.12+, LangChain+Groq, in-memory store)
    web/          # Next.js frontend (Next 15, TS, Tailwind, Recharts, React Flow)
  packages/
    shared/       # Shared types
  data/           # Local data (gitignored)
  docker/         # Docker helpers
  docs/           # Architecture, AI-safety, evaluation, demo guides
  docker-compose.yml
  .env.example
  README.md
```

Backend tests live in `apps/api/tests` (pytest); frontend component tests live in `apps/web/components/__tests__` (vitest).

---

## Quick start (Docker — recommended)

The easiest way to run the whole stack.

### 1. Clone & configure

```bash
git clone https://github.com/Priyanshu-CODERX/ai-finance-controller.git
cd ai-finance-controller

# Create env file from template
cp .env.example .env
```

### 2. (Optional) Add credentials

Edit `.env` and set the optional Groq key (the app runs fine without it; the AI investigator simply degrades to `HUMAN_REVIEW`):

```env
# AI Investigator (enables the LLM; otherwise cases degrade to HUMAN_REVIEW)
GROQ_API_KEY=gsk_xxxxxxxxxxxxxxxxxxxxxxxx
```

> **Security note:** secrets live only in `.env` (gitignored). Keys are never exposed to the frontend, logs, the LLM, or the audit ledger.

### 3. Build and run

```bash
docker compose up --build
```

This starts:

| Service   | URL                    | Notes                  |
|-----------|------------------------|------------------------|
| Frontend  | http://localhost:3000  | Next.js UI             |
| API       | http://localhost:8000  | FastAPI (Swagger at `/docs`) |

The API keeps all data in an **in-memory store** (populated from the synthetic generator). No database is needed; data resets when the API restarts.

Wait for all containers to be **healthy**, then open **http://localhost:3000**.

### 4. Stop

```bash
docker compose down
```

---

## Running locally (no Docker)

No external services are required — the backend uses an in-memory store.

### Backend

```bash
cd apps/api
python -m venv .venv
source .venv/bin/activate (Linux) or .venv\Scripts\Activate.ps1 (for windows)
pip install -r requirements.txt

# copy .env to set credentials (see env section below)
cp ../../.env.example ../../.env

uvicorn app.main:app --reload            # http://localhost:8000
```

### Frontend

```bash
cd apps/web
npm install
npm run dev                              # http://localhost:3000
```

---

## Environment variables

Copy `.env.example` to `.env` at the repo root. All values are optional except the connection defaults shown.

| Variable                | Default                    | Purpose                                            |
|-------------------------|----------------------------|----------------------------------------------------|
| `GROQ_API_KEY`          | *(empty)*                  | Enables the AI investigator                        |
| `GROQ_MODEL`            | `openai/gpt-oss-120b`     | LLM model                                         |
| `GROQ_TEMPERATURE`      | `0`                        | Deterministic output                              |
| `CORS_ORIGINS`          | `http://localhost:3000`    | Allowed CORS origins                              |

---

## Data source

ClosePilot operates entirely on **controlled synthetic data** generated by an internal scenario generator. It produces payments, settlements, bank transactions, invoices and tax records across **22 reconciliation scenarios** (exact matches, splits, refunds, duplicates, fee/tax discrepancies, verified & mismatched tax lines, conflicting candidates, suspicious activity, and more) along with **hidden ground truth** used only by the evaluation lab — never exposed to the LLM.

Because the generator is deterministic, ClosePilot never pretends to be live when it isn't.

### Storage

The API persists everything in an **in-memory store** (records, cases, runs, evidence, audit events, policy config, datasets, tax matches, agent events). It lives only for the process lifetime, so on restart you regenerate data from **Sources** — which makes the demo flow repeatable and needs no external database.

---

## Using the app

1. **Landing** (`/`) — public landing page with live metrics; the assistant is hidden here.
2. **Command Center** (`/explore`) — live dashboard metrics (the old `/`).
3. **Sources** (`/sources`) — generate synthetic data (choose case count and seed); view generated datasets.
4. **Reconciliation** (`/reconciliation`) — run reconciliation over ingested data; view cases.
5. **Exceptions** (`/exceptions`) — prioritized unresolved cases.
6. **Exception Investigator** (`/exceptions/[caseId]`) — AI investigation + policy decision + approve / reject / keep-as-exception.
7. **Cash Forecast** (`/forecast`) — deterministic 7/14/30-day forward cash projection (optimistic path + risk holdback + confidence band); AI commentary only restates the computed figures.
8. **Tax-Line Matcher** (`/tax`) — verifies recorded tax against expected tax (`expected = taxable × rate`, or `gross − settlement − fee`) per line; classifies VERIFIED / EXCEPTION / HUMAN_REVIEW and writes to cases, evidence and audit.
9. **Evidence** (`/evidence`) — provenance graph (React Flow).
10. **Evaluation** (`/evaluation`) — benchmark ClosePilot vs `exact_id`, `amount_date`, `fuzzy` baselines.
11. **Audit** (`/audit`) — immutable, append-only event timeline.

A typical demo flow: **Sources → generate ~100 cases → Reconciliation → run → Exceptions → investigate → Cash Forecast → Tax-Line Matcher → Evidence → Evaluation → Audit**.

---

## Testing

### Backend (pytest)

```bash
cd apps/api
source .venv/bin/activate
python -m pytest            # 93 tests (unit + integration)
```

Integration tests run against the in-memory store and always run (no external database).

### Frontend (vitest + ESLint + typecheck)

```bash
cd apps/web
npm run lint                # ESLint
npm run typecheck           # tsc --noEmit
npm test                    # Vitest
npm run build               # production build
```

---

## Documentation

See `docs/` for detailed guides:

- `architecture.md` — system design and data flow
- `ai-safety.md` — how LLM authority is constrained
- `evaluation.md` — evaluation-lab methodology
- `demo.md` — end-to-end demo script

---

## License

Private / course project — see repository owner.