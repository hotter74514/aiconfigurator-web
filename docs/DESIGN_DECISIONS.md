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
| [008](decisions/008-caching.md) | Determinism and caching | Proposed |
| [009](decisions/009-multi-tenancy.md) | Result visibility and quotas | Proposed |
| [010](decisions/010-output-trust.md) | Estimate warnings and validation | Proposed |
| [011](decisions/011-timeout-cancellation.md) | Timeout, cancellation, and subprocess cleanup | Proposed |
| [012](decisions/012-local-observability-stack.md) | Minikube local observability stack | Accepted |

README summaries should link to the ADRs rather than duplicate them.

## Approval protocol

The architecture owner reviews each record and either marks it **Accepted** or requests changes. If implementation evidence invalidates a decision, stop, explain the new alternatives, and create a superseding ADR. Never silently change an accepted choice.
