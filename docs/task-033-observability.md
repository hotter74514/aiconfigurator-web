# TASK-033: OpenTelemetry observability

TASK-033 implements the accepted ADR-007 decision with focused OpenTelemetry traces and metrics. Structured logs remain TASK-034 scope.

## Implementation

- `FastAPIInstrumentor` creates HTTP server spans and standard HTTP metrics.
- `GET /metrics` renders the OpenTelemetry Prometheus reader through the existing FastAPI process.
- Run spans cover admission, queue wait, dequeue, subprocess execution, and terminal status.
- Low-cardinality metrics cover terminal runs by status, active runs, queue depth, run duration, subprocess outcomes, and completed artifact bytes.
- Queue depth, capacity, and saturation ratio are numeric span attributes/events. Run IDs, model names, and command details stay on spans and never become metric labels.
- The executor starts a portal-owned `app.services.subprocess_bootstrap` wrapper. It extracts `TRACEPARENT`/`TRACESTATE`, creates an `aiconfigurator.cli` child span, reinjects the child context for the unmodified CLI, and preserves stdout/stderr/exit status.
- Optional asynchronous OTLP HTTP trace/metric exporters use standard `OTEL_*` configuration. Without OTLP settings, local Prometheus metrics still work and runs do not depend on a collector.

## Validation

```sh
make test
git diff --check
```

The focused suite verifies `/metrics`, queue-depth visibility without run-ID labels, artifact byte accounting, and W3C trace carrier propagation through the subprocess wrapper. The full suite completed with 44 passing tests on Python 3.14.

## Operational notes

The OpenTelemetry providers are process-local and initialized once. Prometheus state resets on restart. Exporter failures must not fail a run; configure an OTLP endpoint only when a compatible HTTP/protobuf collector or backend is available. The wrapper adds a short startup allowance to the subprocess deadline because it imports the telemetry SDK before launching AIConfigurator.
