# aiconfigurator-web

Serving Configuration Portal take-home assignment: a self-service web experience over NVIDIA Dynamo AIConfigurator.

## Project workflow

Start with [`docs/assignment-brief.md`](docs/assignment-brief.md), then read [`AGENTS.md`](AGENTS.md), [`ARCHITECTURE.md`](ARCHITECTURE.md), [`ROADMAP.md`](ROADMAP.md), and [`TASKS.md`](TASKS.md). Codex prompts are in [`prompts/`](prompts/), and the interview acceptance path is [`docs/demo-checklist.md`](docs/demo-checklist.md).

Use two deliberate Codex modes: [`prompts/architect.md`](prompts/architect.md) proposes and records ADRs without coding; [`prompts/builder.md`](prompts/builder.md) implements only decisions marked **Accepted**. Keep the commit history incremental and reviewable; do not squash the submission into one commit.

TASK-000 now provides and verifies a minimal Linux/amd64 AIConfigurator image and smoke runner. TASK-001 documents the observed CLI and artifact contract in [`docs/task-001-cli-artifacts.md`](docs/task-001-cli-artifacts.md). The current API shell follows the FastAPI candidate in `ARCHITECTURE.md`; worker execution and UI remain intentionally scoped to later tasks.

TASK-013 now exposes the validated asynchronous submission boundary at `POST /api/runs`, TASK-014 exposes `GET /api/runs/{id}` with queued/running/completed/failed transitions, and TASK-015 runs jobs through a bounded local worker with an isolated AIConfigurator subprocess. TASK-016 adds a structured CSV parser and deterministic SLA-aware ranking. TASK-017 now persists each run's generated output in an ephemeral per-run directory, returns ranked results and allow-listed artifact names on completion, and serves safe downloads. TASK-020 adds the plain HTML/Jinja2 form at `/`; TASK-021 adds two-second status polling with loading and error states; TASK-022 renders ranked estimates, SLA outcomes, and artifact links; TASK-030 rejects a full pending queue with HTTP `429` and `Retry-After: 1`; TASK-031 adds configurable subprocess deadlines, process-group cleanup, and shutdown cancellation; TASK-032 adds separate `/live` and `/ready` probes; TASK-033 adds OpenTelemetry traces, Prometheus metrics at `/metrics`, optional OTLP export, queue saturation attributes, and subprocess trace propagation; TASK-034 adds JSON lifecycle logs with run and trace correlation. Verification is documented in [`docs/task-034-logging.md`](docs/task-034-logging.md).

## Quick start

```sh
codex
python3.11 -m venv .venv
.venv/bin/python -m pip install -e '.[test]'
make check
```

Use Docker on macOS; AIConfigurator's published wheels are not supported natively on macOS or Windows. Do not commit credentials or local environment files.

Run the TASK-000 smoke test after Docker Desktop access is available:

```sh
make smoke-configurator
```

The runner stores disposable evidence under `.tmp/task-000/` and does not add application code.

Build and check the portal image with the same Linux/amd64 contract:

```sh
make docker-build
make container-check
```

The runtime target listens on port `8000`, runs as the non-root `portal` user, and stores ephemeral run artifacts under `/app/data/runs`. The smoke-only image remains available for TASK-000 through `AICONFIGURATOR_DOCKER_TARGET=smoke make smoke-configurator`.

## Current API

With the Python test dependencies installed, start the development server with `make dev` and submit a run:

```sh
curl -X POST http://127.0.0.1:8000/api/runs \
  -H 'content-type: application/json' \
  -d '{"model":"Qwen/Qwen3-32B-FP8","system":"h200_sxm","total_gpus":32,"ttft":2000,"tpot":30}'
```

Open `http://127.0.0.1:8000/` for the form. It submits the five constraints to the async API, polls status every two seconds, and reports loading, completion, or safe error states. Completed runs render ranked estimates with SLA outcomes and allow-listed artifact links. The service exposes `/live` for process liveness, `/ready` for worker/storage readiness, and `/metrics` for Prometheus text. Application lifecycle events are JSON logs with `event`, `run_id`, `trace_id`, and `span_id`; set `PORTAL_LOG_LEVEL` to adjust verbosity. OpenTelemetry uses `OTEL_SERVICE_NAME` and can add asynchronous OTLP HTTP trace/metric export with `OTEL_EXPORTER_OTLP_ENDPOINT` or signal-specific endpoint/exporter variables; no collector is required for local metrics. The API returns HTTP `202` with `{ "id": "...", "status": "queued" }`; when all pending queue slots are occupied, it returns `429` with `Retry-After: 1`, and a service shutting down returns `503`. Completed runs include ranked `results` and allow-listed `artifacts`, which can be downloaded with `GET /api/runs/{id}/artifacts/{path}`. The worker uses `AICONFIGURATOR_ARTIFACT_ROOT` (default `.tmp/runs`; use `/app/data/runs` in the container), `AICONFIGURATOR_TIMEOUT_SECONDS` (default 900 seconds), and removes UUID run directories older than 24 hours. Native macOS execution is not supported because the AIConfigurator dependency is Linux x86-64 only.

## Design Decisions

Document the execution model, asynchronous API, artifact lifecycle, concurrency, caching, CLI vs SDK choice, probes, observability, multi-tenancy, and output-trust warning in [`docs/DESIGN_DECISIONS.md`](docs/DESIGN_DECISIONS.md). Explain both the selected approach and the alternative rejected. Each detailed ADR must record trade-offs, failure modes, and what would change the decision.

## Known Limitations

Kubernetes manifests are not implemented yet. The form is intentionally plain HTML/Jinja2 with a small inline submit/polling/result bridge and no frontend framework. There is no public per-run cancellation endpoint; shutdown cancellation is lifecycle protection only. Metrics, traces, and logs are process-local unless an OTLP backend or external log collector is configured; in-memory metric state resets on restart. Artifacts are ephemeral and are lost on process/pod restart; only explicit generated filenames are downloadable, and generated scripts are never executed by the portal. The Docker image pins the base image digest and direct AIConfigurator dependencies, but does not yet hash-lock every transitive Python dependency. Authentication, TLS, secrets management, and high availability are intentionally out of scope for the take-home; the eventual submission must state what would be added for production.
