# ADR-006: Separate liveness and readiness

## Context

CPU-heavy runs and worker saturation must not cause Kubernetes to mistake a healthy process for a dead one.

## Proposed Decision

`/live` checks only process liveness. `/ready` checks worker initialization and writable artifact storage. A busy worker stays ready; a full queue applies backpressure at submission instead of failing readiness.

## Alternatives and Trade-offs

- **Separate process and service probes**: `/live` is a cheap process-only check; `/ready` checks initialization and writable artifact storage. This maps cleanly to Kubernetes and avoids restarting a healthy process under load.
- **One combined health endpoint**: simpler for clients, but a storage or initialization fault would also fail liveness and can trigger unnecessary restarts instead of allowing recovery.
- **Dependency-aware readiness**: include AIConfigurator availability, queue idleness, or a subprocess probe. This provides more signal, but is expensive, can fail during normal CPU-heavy work, and couples readiness to the third-party runtime.

The smallest defensible option is separate probes with no AIConfigurator invocation and no queue-idleness requirement. Readiness returns unhealthy only before worker initialization completes or when the configured artifact root is unavailable or not writable. A busy worker remains ready, while submission backpressure remains the queue's responsibility.

## Failure Modes and Operational Trade-offs

The process can be alive while the artifact filesystem is unavailable; `/ready` exposes that distinction to a deployment controller. A process-only `/live` cannot detect an internal deadlock, but adding a deep execution check would turn a health probe into an AIConfigurator workload and risk probe-induced CPU contention.

## What Would Change My Mind

Use dependency-aware readiness only when the portal has durable external dependencies whose unavailability truly means it cannot serve requests.

## Status

**Accepted — architecture owner approval recorded on 2026-09-05.**
