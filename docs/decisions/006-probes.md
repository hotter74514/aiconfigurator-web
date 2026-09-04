# ADR-006: Separate liveness and readiness

## Context

CPU-heavy runs and worker saturation must not cause Kubernetes to mistake a healthy process for a dead one.

## Proposed Decision

`/live` checks only process liveness. `/ready` checks worker initialization and writable artifact storage. A busy worker stays ready; a full queue applies backpressure at submission instead of failing readiness.

## Alternatives and Trade-offs

One combined health check is simpler but causes unnecessary restarts. Deep readiness checks provide more signal but can become expensive or couple probes to AIConfigurator availability.

## What Would Change My Mind

Use dependency-aware readiness only when the portal has durable external dependencies whose unavailability truly means it cannot serve requests.

## Status

**Proposed — architecture owner approval required.**
