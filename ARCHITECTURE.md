# Architecture

## Status

The repository now contains the TASK-013/014 API boundary, TASK-015 bounded worker execution, TASK-016 structured-result parser/ranker, TASK-017 ephemeral artifact serving, the TASK-020 plain HTML/Jinja2 form, TASK-021 status polling, TASK-022 ranked-result/artifact presentation, TASK-030 queue backpressure, and TASK-031 timeout/cancellation cleanup; operational endpoints remain unimplemented. The following is the deliberately small candidate architecture for the assignment. Each material choice must be accepted in the corresponding ADR before implementation.

## Candidate Shape

```text
Browser
   │ POST /api/runs; poll; download
   ▼
FastAPI + plain HTML/Jinja2 (single service)
   │
   ├── bounded local job manager (1–2 workers, bounded queue)
   │       └── isolated subprocess → AIConfigurator CLI
   │
   ├── run metadata/status → local store
   └── /app/data/runs/{run_id}/ → generated artifacts (24h TTL)
```

The portal is a platform wrapper, not a serving runtime. AIConfigurator remains the computation engine and its output remains an estimate.

## API Candidate

- `POST /api/runs` validates model, GPU system/type, total GPUs, TTFT, and TPOT, then returns `{id, status: "queued"}`.
- A full pending queue rejects `POST /api/runs` with HTTP `429` and `Retry-After: 1`; readiness remains independent of worker idleness.
- A service that is shutting down rejects new `POST /api/runs` requests with HTTP `503`.
- `GET /api/runs/{id}` returns status, failure information, or ranked configurations when complete.
- `GET /api/runs/{id}/artifacts/{name}` downloads an allow-listed generated artifact.
- `GET /live` checks only that the process is alive.
- `GET /ready` checks worker initialization and writable artifact storage; a busy worker remains ready, while a full queue is handled by `429`/`503` at submission.
- `GET /metrics` exposes a small operational metrics surface.

Polling at roughly two seconds is the default candidate. SSE/WebSockets and a Kubernetes Job per request are alternatives to discuss, not to add by default.

## Operational Defaults to Validate

Use ephemeral local artifacts with a 24-hour cleanup policy for the take-home. Bound execution concurrency and pending work so CPU-heavy sweeps cannot starve probes. Prefer a single replica for demo clarity; document that restart loses in-flight jobs and local artifacts.

Keep metrics focused: HTTP requests, runs by status, active/queued runs, run duration, subprocess exit codes, and artifact bytes. Do not add Kafka, Redis, PostgreSQL, S3/MinIO, a durable queue, or a full observability stack without an accepted ADR and time justification.

## Production Evolution

If scale or durability becomes a requirement, evolve toward a multi-replica API, durable queue, worker Deployment or Jobs, metadata database, object storage, per-user authorization/quotas, and production observability. Document the trigger for each addition instead of pre-building it.
