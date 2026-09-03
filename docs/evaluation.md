# Evaluation Methodology

## Approach

ClosePilot is evaluated against controlled synthetic datasets with hidden ground truth. The AI and reconciliation runtime never see ground truth during evaluation.

## Ground truth

Each synthetic case stores:

```text
case_id
expected_relationships
expected_outcome
expected_auto_or_human
root_cause
related_record_ids
```

Ground truth is stored in a separate MongoDB collection (never exposed to AI).

## Metrics

### Precision

```text
correct automatic matches / all automatic matches
```

### Recall

```text
correct matches / all actual matches
```

### False auto-match rate

```text
incorrect automatic matches / all automatic matches
```

This is the critical safety metric.

### Exception rate

```text
unresolved cases / total cases
```

### Auto-resolution rate

```text
automatically resolved cases / total cases
```

### Throughput

```text
records / elapsed seconds
```

Also: average AI investigation latency, deterministic processing latency, total pipeline latency.

## Baselines

1. exact ID/reference
2. amount + date
3. fuzzy matching
4. ClosePilot

All methods run against the same hidden ground-truth dataset.

## Adversarial cases

- duplicate IDs
- near-equal amounts
- dates just outside tolerance
- misleading descriptions
- multiple valid-looking candidates
- missing records
- conflicting evidence
- partial settlement
- split settlement
- refund/chargeback
- fee/tax confusion

## Deterministic repeatability

Same seed + configuration → stable deterministic results.

## No fake metrics

Every metric shown in the UI is computed from stored evaluation output.
