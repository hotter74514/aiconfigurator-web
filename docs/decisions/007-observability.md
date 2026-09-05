# ADR-007: OpenTelemetry traces and focused metrics

## Context

The assignment asks for structured logging and a basic metrics surface, while the execution path crosses an HTTP service, a bounded queue, and a Linux-only AIConfigurator subprocess. A single trace should explain admission, queue wait, subprocess execution, and terminal run status. Queue depth must also be visible without turning a numeric measurement into a high-cardinality metric label.

## Proposed Decision

Use the OpenTelemetry Python SDK with the FastAPI instrumentation library for HTTP spans, manual spans around run admission/queue wait and the AIConfigurator subprocess, and OpenTelemetry metrics for the focused operational surface. Use a Prometheus metric reader for the local `/metrics` endpoint and optional OTLP exporters configured by standard `OTEL_*` environment variables for a collector or backend. Keep exporters asynchronous and never block request handling or the worker.

Record these low-cardinality metrics: HTTP requests by route template and status, runs by terminal status, active runs, queued runs, run duration, subprocess outcomes, and artifact bytes. Record queue depth as a gauge and as a numeric span attribute/event (`queue.depth`, `queue.capacity`, `queue.saturation_ratio`) at admission, dequeue, and saturation; never use the changing queue number as a metric label. Add run ID and subprocess command details to spans only, not metric labels.

For the subprocess boundary, create a parent `aiconfigurator.subprocess` span and manually inject W3C Trace Context into the child environment. The adapter maps the propagator carrier's `traceparent`/`tracestate` values to the wrapper's `TRACEPARENT`/`TRACESTATE` environment variables; the wrapper extracts them, starts a child span, invokes the unmodified `aiconfigurator` CLI, records its exit/timeout outcome, and exports the span. This makes propagation testable without modifying AIConfigurator. If the wrapper cannot initialize telemetry, the parent span remains authoritative and the run must still proceed.

## Alternatives and Trade-offs

- **Dependency-free Prometheus exposition**: small and reversible, but provides no trace model or cross-process context propagation and duplicates telemetry conventions.
- **OpenTelemetry SDK plus FastAPI instrumentation, Prometheus reader, and OTLP exporters**: standard traces/metrics, reusable instrumentation, optional backend integration, and explicit propagation support. It adds dependencies and requires careful provider/exporter lifecycle setup.
- **Full collector/agent and auto-instrumentation deployment**: stronger production routing and less application setup, but adds infrastructure and cannot by itself create a meaningful span inside an uninstrumented third-party CLI.

The recommended smallest option is the OpenTelemetry SDK plus these focused packages: `opentelemetry-api`, `opentelemetry-sdk`, `opentelemetry-instrumentation-fastapi`, `opentelemetry-exporter-prometheus`, and `opentelemetry-exporter-otlp-proto-http`. Do not add a collector deployment in this task; make OTLP optional through environment configuration. `/metrics` must not invoke AIConfigurator or wait on the worker.

Structured logs remain a separate concern for TASK-034; use trace/span IDs in logs there rather than duplicating log content as metric attributes.

## Failure Modes and Operational Trade-offs

Telemetry exporters can be unavailable or slow, so export failures must be isolated and recorded without failing runs. In-memory metric state resets on restart, while an OTLP backend can provide aggregation when configured. An incorrectly labelled endpoint, run ID, model, or queue value could create unbounded cardinality, so only route templates and bounded status/outcome values are metric labels. The child wrapper adds process complexity, but it is the only reliable way to prove propagation into an otherwise uninstrumented CLI process without changing AIConfigurator.

## What Would Change My Mind

Move to a collector/agent when telemetry must be routed, sampled, or aggregated across replicas. Add baggage or richer semantic attributes only when a trusted downstream consumer and data-sensitivity review justify them.

## References

- [OpenTelemetry Python instrumentation](https://opentelemetry.io/docs/languages/python/instrumentation/)
- [OpenTelemetry Python propagation](https://opentelemetry.io/docs/languages/python/propagation/)
- [OpenTelemetry Python exporters](https://opentelemetry.io/docs/languages/python/exporters/)

## Status

**Proposed — architecture owner approval required.**
