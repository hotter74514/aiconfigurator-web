# ADR-005: Bounded concurrency and CPU protection

## Context

Ten simultaneous sweeps can saturate CPU and starve health endpoints. The portal must reject excess work predictably and give Kubernetes realistic resource settings.

## Options Considered

- Unbounded process creation: highest apparent throughput, but risks CPU death and probe failures.
- Bounded workers plus bounded pending queue: predictable resource use and clear backpressure.
- External queue: stronger durability and scale, but outside the take-home’s minimal architecture.

## Decision

Start with one or two worker processes and a pending queue of ten. When capacity is exhausted, reject new submissions with `429` or `503`. Keep liveness independent of worker load; readiness checks service initialization and writable artifact storage, not idleness.

Set Kubernetes CPU requests/limits from measured container behavior and document CFS-throttling trade-offs rather than guessing silently.

## What Would Change My Mind

Adopt a durable queue and independently scaled workers when queue depth or run latency requires horizontal capacity.

## Status

**Accepted — architecture owner approval recorded on 2026-09-05.**
