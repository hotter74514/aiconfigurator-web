# ADR-007: Minimal operational observability

## Context

The assignment asks for structured logging and a basic metrics surface, not a full observability stack.

## Proposed Decision

Emit structured logs with run ID, status, duration, and subprocess outcome. Expose HTTP request counts, runs by status, active/queued runs, run duration, subprocess exit codes, and artifact bytes. Keep `/metrics` cheap and independent of the sweep worker.

## Alternatives and Trade-offs

- **Dependency-free Prometheus exposition**: keep counters/gauges/histogram buckets in the service and render a small text endpoint. This is reversible, easy to test, and adds no runtime dependency, but lacks aggregation across replicas.
- **`prometheus_client` registry**: standard exposition and instrumentation helpers with a small dependency. It reduces formatting risk but still requires deliberate label/cardinality design and does not solve multi-replica aggregation.
- **OpenTelemetry plus Prometheus/Loki/Grafana**: richer traces, logs, and dashboards, but consumes take-home time and adds deployment dependencies before the single-replica path needs them.

The smallest defensible option is dependency-free Prometheus exposition with stable low-cardinality labels only. Use route templates rather than raw URLs or run IDs. Keep the initial surface to request count, run count by status, active/queued gauges, run-duration buckets, subprocess outcomes, and artifact bytes. `/metrics` must not invoke AIConfigurator or wait on the worker.

Structured logs remain a separate concern for TASK-034; metrics should not become a second unstructured logging channel.

## Failure Modes and Operational Trade-offs

In-memory metrics reset on process restart and are not aggregated across replicas, which is acceptable for the single-replica take-home and must be documented. An incorrectly labelled endpoint could create unbounded cardinality, so request paths and model names are excluded from labels. Metrics collection must stay cheap even while the worker is saturated.

## What Would Change My Mind

Add distributed tracing or a metrics backend when the service becomes multi-replica or debugging crosses process/service boundaries.

## Status

**Proposed — architecture owner approval required.**
