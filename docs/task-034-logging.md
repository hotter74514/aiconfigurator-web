# TASK-034: Structured logs with run correlation

TASK-034 adds structured application logs on top of the accepted ADR-007 trace model. It does not add an OpenTelemetry Logs exporter or a centralized logging service.

## Implementation

- Portal-owned loggers emit one JSON object per event through the standard library logging package.
- Every record includes UTC timestamp, severity, logger, event name, `run_id` when available, and current `trace_id`/`span_id` when a recording span is active.
- RunManager logs admission, queueing, start, rejection, and terminal status events.
- The executor logs subprocess outcome, exit code, and duration without logging model inputs or raw command arguments.
- The subprocess bootstrap logs start and child completion while preserving the parent trace context and run ID environment value.
- `PORTAL_LOG_LEVEL` controls the portal logger threshold and defaults to `INFO`.

## Validation

```sh
make check
git diff --check
```

The regression suite verifies JSON shape and trace/span/run correlation; the complete suite passes with 45 tests on Python 3.14.

## Limitations

Logs are written to stderr and remain local to the process/container. TASK-040+ packaging and Kubernetes work must choose the final collection and retention path. Raw AIConfigurator stdout/stderr remain execution diagnostics and are not duplicated into structured log fields.
