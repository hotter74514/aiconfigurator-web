# ADR-011: Timeout, cancellation, and subprocess cleanup

## Context

`run_aiconfigurator()` currently waits without a deadline. A hung AIConfigurator process can occupy a bounded worker indefinitely, and `RunManager.shutdown()` only waits briefly for worker threads; it cannot terminate an active subprocess or clean up a partial run. TASK-031 must make failure and shutdown behavior deterministic without changing the accepted local-worker architecture.

## Options Considered

- **Deadline-aware CLI adapter**: use `Popen` with a configurable timeout, start the child in its own process group, terminate then kill after a short grace period, and capture partial stdout/stderr. This is testable and keeps the existing worker boundary.
- **Cooperative cancellation token**: pass a cancellation event through the runner and ask the adapter to stop. This is simple for portal-owned code, but cannot reliably stop a third-party process or its descendants.
- **External supervisor or Kubernetes Job per run**: delegate timeout and cleanup to a stronger lifecycle manager. This improves isolation, but adds infrastructure and conflicts with the deliberately small take-home architecture.

## Proposed Decision

Use a deadline-aware CLI adapter inside the existing bounded worker. Make the timeout configurable through `AICONFIGURATOR_TIMEOUT_SECONDS`, with a proposed 900-second default and a 5-second termination grace period. On deadline, terminate the AIConfigurator process group, escalate to kill if needed, capture output, and mark the run failed with a safe timeout message.

During service shutdown, stop accepting work, cancel active AIConfigurator process groups, mark affected runs failed with a shutdown-cancellation reason, and remove incomplete per-run artifacts. Do not add a public cancellation endpoint in this task. Keep injected test runners as isolated test doubles; production cancellation guarantees apply to the real CLI adapter.

## Trade-offs and Failure Modes

Process-group cleanup prevents child scripts from surviving the parent, but POSIX process control requires Linux/macOS-specific tests and careful handling of already-exited children. A fixed default protects workers from hangs but may terminate unusually long valid sweeps; the environment override makes the trade-off explicit. Partial stdout/stderr remains available in run diagnostics while incomplete artifacts are not downloadable.

## What Would Change My Mind

Adopt an external supervisor when runs need independent scaling, durable cancellation across pod replacement, or stronger per-run isolation. Add a public cancellation API only when users need to cancel individual runs rather than relying on service lifecycle cancellation.

## Status

**Accepted — architecture owner approval recorded on 2026-09-05.**
