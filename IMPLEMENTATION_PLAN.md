## Stage 1: Define the Pareto view contract
**Goal**: Define the frontend-only visualization contract over the existing ranked candidates.
**Success Criteria**: The chart compares predicted throughput against request latency, identifies non-dominated candidates, and does not change the API or execution path.
**Tests**: Add page contract assertions for the chart, legend, and frontier summary.
**Status**: Complete

## Stage 2: Implement the accessible SVG visualization
**Goal**: Render all candidates and highlight the Pareto frontier in the existing results view.
**Success Criteria**: Completed runs show an SVG scatter plot, axis labels, a legend, point details, and a frontier summary; invalid or empty data fails safely.
**Tests**: Existing page tests plus JavaScript syntax validation.
**Status**: Complete

## Stage 3: Document and verify the bonus
**Goal**: Record the definition, limitations, and verification of the Pareto visualization.
**Success Criteria**: Roadmap/tasks and bonus report are updated; focused tests, full checks, and diff review pass.
**Tests**: `pytest`, `make check`, `git diff --check`.
**Status**: Complete
