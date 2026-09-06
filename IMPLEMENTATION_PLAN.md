## Stage 1: Define the mode comparison contract
**Goal**: Define a frontend-only comparison over the existing `agg` and `disagg` ranked candidates.
**Success Criteria**: The completed results view reports candidate counts, SLA-feasible counts, and SLA-scoped throughput/latency summaries for each available mode without changing the API or execution path.
**Tests**: Add page contract assertions for the comparison cards and rendering function.
**Status**: Complete

## Stage 2: Implement the accessible comparison view
**Goal**: Render aggregate and disaggregated summaries beside the existing ranked table and Pareto chart.
**Success Criteria**: Both modes are compared when present; missing modes and no-SLA-feasible cases produce explicit text; a new submission clears the previous comparison.
**Tests**: Existing page tests plus JavaScript syntax validation.
**Status**: Complete

## Stage 3: Document and verify the bonus
**Goal**: Record the comparison definition, limitations, and verification results.
**Success Criteria**: Roadmap/tasks, architecture notes, README, and the bonus report are updated; focused tests, full checks, and diff review pass.
**Tests**: `pytest`, `make check`, `git diff --check`.
**Status**: Complete
