# Design Decisions

This index tracks the decisions that must be defensible in the interview. The detailed records live under [`docs/decisions/`](decisions/). A record is **Proposed** until the architecture owner approves it; Builder mode may implement only **Accepted** decisions.

| ADR | Topic | Status |
|---|---|---|
| [001](decisions/001-execution-model.md) | Bounded local execution | Accepted |
| [002](decisions/002-api-model.md) | Async job API and polling | Accepted |
| [003](decisions/003-aiconfigurator-integration.md) | CLI subprocess boundary | Accepted |
| [004](decisions/004-artifact-storage.md) | Ephemeral artifact lifecycle | Accepted |
| [005](decisions/005-concurrency.md) | Queue and CPU contention | Accepted |
| [006](decisions/006-probes.md) | Probe semantics and lifecycle | Accepted |
| [007](decisions/007-observability.md) | Metrics and structured logs | Accepted |
| [008](decisions/008-caching.md) | Determinism and caching | Accepted |
| [009](decisions/009-multi-tenancy.md) | Result visibility and quotas | Accepted |
| [010](decisions/010-output-trust.md) | Estimate warnings and validation | Proposed |
| [011](decisions/011-timeout-cancellation.md) | Timeout, cancellation, and subprocess cleanup | Accepted |
| [012](decisions/012-local-observability-stack.md) | Minikube local observability stack | Accepted |
| [013](decisions/013-loki-alloy-log-forwarding.md) | Direct Alloy-to-Loki log forwarding | Accepted |
| [014](decisions/014-run-history.md) | Bounded process-local run history | Accepted |
| [015](decisions/015-frontend-ui-refresh.md) | Frontend UI refresh without a new runtime stack | Accepted |
| [016](decisions/016-artifact-bundle-and-ranked-downloads.md) | One-click artifact bundle and ranked download links | Accepted |

README summaries should link to the ADRs rather than duplicate them.

## Bonus implementation notes

BONUS-001 keeps the Pareto visualization in the browser and reuses the existing
ranked result contract. It compares predicted request latency (minimize) with
predicted throughput (maximize), highlights non-dominated candidates, and keeps
the ranked table as the source for SLA ordering and complete candidate details.
This adds no API, persistence, execution, or dependency changes. The chart is
an explanation aid for model-based estimates, not a benchmark or deployment
recommendation.

BONUS-002 keeps the aggregate/disaggregated comparison in the browser and
reuses the existing `mode` field in the ranked result contract. It summarizes
each mode's candidate count, SLA-feasible count, highest predicted throughput,
and lowest predicted request latency, scoped to candidates meeting both
requested targets. Missing modes and no-SLA-feasible cases are shown explicitly.
This adds no API, persistence, execution, or dependency changes; the summary is
an explanation aid for model-based estimates, not a deployment recommendation.

ADR-008 is accepted for the deterministic cache milestone. The cache remains
local to one Portal process, bounded by entry count, and ephemeral across
restarts; its key includes the canonical request, AIConfigurator version, result
model version, and runner image identity.

ADR-014 is accepted for the run history milestone. Recent completed and failed
runs are retained in a bounded process-local index and exposed newest-first by
`GET /api/runs`; history and artifact availability are not durable across
process or Pod restarts.

ADR-009 is accepted for the multi-user awareness milestone. The Portal remains
an explicitly single-user, controlled-demo deployment; it does not accept
client-supplied identity headers or claim that run IDs provide authorization.
Authentication, ownership checks, tenant quotas, and audit events remain
required before exposing the service to shared or untrusted users.

## Approval protocol

The architecture owner reviews each record and either marks it **Accepted** or requests changes. If implementation evidence invalidates a decision, stop, explain the new alternatives, and create a superseding ADR. Never silently change an accepted choice.
