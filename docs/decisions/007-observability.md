# ADR-007: Minimal operational observability

## Context

The assignment asks for structured logging and a basic metrics surface, not a full observability stack.

## Proposed Decision

Emit structured logs with run ID, status, duration, and subprocess outcome. Expose HTTP request counts, runs by status, active/queued runs, run duration, subprocess exit codes, and artifact bytes. Keep `/metrics` cheap and independent of the sweep worker.

## Alternatives and Trade-offs

OpenTelemetry plus Prometheus/Loki/Grafana provides richer operations but consumes time and adds deployment dependencies. Plain logs only are insufficient for queue and latency questions.

## What Would Change My Mind

Add distributed tracing or a metrics backend when the service becomes multi-replica or debugging crosses process/service boundaries.

## Status

**Proposed — architecture owner approval required.**
