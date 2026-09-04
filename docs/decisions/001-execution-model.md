# ADR-001: Bounded local execution

## Context

AIConfigurator sweeps are CPU-bound and may run for seconds or minutes. The portal must keep the HTTP process responsive and make failure behavior explainable within an 8–10 hour take-home.

## Options Considered

- Inline in the request handler: simplest, but ties up HTTP workers and creates timeout risk.
- Background thread/process pool: local and simple; a bounded process pool isolates CPU work.
- Durable queue plus worker or Kubernetes Job per request: more resilient and scalable, but too much infrastructure for this scope.

## Proposed Decision

Use one web/API service with a bounded local process worker. Start with one or two workers and document that pod restart loses in-flight work.

## Trade-offs and Failure Modes

This is easy to demo and keeps the event loop responsive, but it is not durable and does not scale correctly across replicas. A failed child must produce a failed run with captured stderr and exit status.

## What Would Change My Mind

Use a durable queue and worker deployment when runs must survive pod replacement, multiple replicas are required, or sustained concurrency exceeds the local bound.

## Status

**Proposed — architecture owner approval required.**
