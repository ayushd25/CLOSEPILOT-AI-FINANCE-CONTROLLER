# Razorpay Test Mode Integration

## Purpose

ClosePilot ingests authentic Razorpay Test Mode financial data to validate the reconciliation engine on real financial records.

## Environment variables

```env
RAZORPAY_MODE=test
RAZORPAY_KEY_ID=
RAZORPAY_KEY_SECRET=
```

The key secret is backend-only and never exposed to the frontend, browser, LLM, logs, audit events, or MongoDB documents.

## Client

`RazorpayClient` in `app/integrations/razorpay/client.py`:

- Uses Basic Auth
- Uses configured Test Mode credentials
- Applies timeout
- Retries transient failures with bounded exponential backoff
- Handles HTTP errors safely
- Never logs secrets

## Modules

```text
apps/api/app/integrations/razorpay/
  __init__.py
  client.py         # HTTP client with retry/backoff
  payments.py
  orders.py
  settlements.py
  settlement_recon.py
  models.py         # Razorpay DTOs
  mapper.py         # mapping to canonical FinancialRecord
  service.py        # orchestration + sync run tracking
```

## Sync run

`SyncRun` model tracks:

- ID, source
- started_at, completed_at
- status
- fetched, inserted, updated, skipped
- errors, duration
- error summaries

## API

```text
GET  /integrations/razorpay/status
POST /integrations/razorpay/sync
GET  /integrations/razorpay/sync-runs
GET  /integrations/razorpay/configuration
```

No credentials are returned.

## Credibility rules

- Do not claim a specific large volume of data from Razorpay Test Mode
- Report the actual fetched count
- Large benchmark sizes use controlled synthetic augmentation
