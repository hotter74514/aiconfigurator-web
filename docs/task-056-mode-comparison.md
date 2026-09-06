# BONUS-002 Aggregate vs. Disaggregated Comparison

## Scope

The completed results view now includes a side-by-side comparison of the two
result modes emitted by AIConfigurator:

- `agg` is presented as Aggregate.
- `disagg` is presented as Disaggregated.

Each card reports the number of returned candidates, the number meeting both
requested TTFT and TPOT targets, the highest predicted throughput among those
SLA-feasible candidates, and the lowest predicted request latency among those
candidates. A run with a missing mode or with no SLA-feasible candidates gets
an explicit explanation instead of an invented comparison.

The ranked table remains authoritative for rank, full candidate details, and
SLA ordering. The comparison is an explanation aid over AIConfigurator's
predictions; it does not prove that either serving mode will perform better in
production and must be checked with representative real benchmarks.

## Implementation

- No API, runtime, persistence, or frontend dependency changes were added.
- The browser groups the existing `results.candidates` array by its `mode`
  field and renders the summaries with DOM text assignment.
- A new submission clears the comparison along with the table, chart, and
  artifact links.
- Missing modes and no-SLA-feasible cases remain visible in the two-card
  layout so an incomplete result cannot look like a complete comparison.

## Verification

```sh
uv run pytest tests/test_pages.py
sed -n '/<script>/,/<\/script>/p' templates/form.html | sed '1d;$d' | node --check
uv run pytest
make check
git diff --check
```

The focused page contract test and full test suite pass. The inline JavaScript
passes `node --check`. No live browser backend was available for an interactive
smoke check in this environment, so visual behavior should still be checked in
the local portal demo.
