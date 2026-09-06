# aiconfigurator-web

Serving Configuration Portal take-home assignment: a self-service web experience over NVIDIA Dynamo AIConfigurator.

## Project workflow

Start with [`docs/assignment-brief.md`](docs/assignment-brief.md), then read [`AGENTS.md`](AGENTS.md), [`ARCHITECTURE.md`](ARCHITECTURE.md), [`ROADMAP.md`](ROADMAP.md), and [`TASKS.md`](TASKS.md). Codex prompts are in [`prompts/`](prompts/), and the interview acceptance path is [`docs/demo-checklist.md`](docs/demo-checklist.md).

Use two deliberate Codex modes: [`prompts/architect.md`](prompts/architect.md) proposes and records ADRs without coding; [`prompts/builder.md`](prompts/builder.md) implements only decisions marked **Accepted**. Keep the commit history incremental and reviewable; do not squash the submission into one commit.

TASK-000 provides and verifies a minimal Linux/amd64 AIConfigurator image and smoke runner. TASK-001 documents the observed CLI and artifact contract in [`docs/task-001-cli-artifacts.md`](docs/task-001-cli-artifacts.md). The portal now covers the P1–P4 execution, user-journey, operations, container, and local Kubernetes milestones; P5 focuses on documentation and final verification.

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

## Architecture

The portal is intentionally a single-service wrapper around AIConfigurator:

```text
Browser
  │ POST /api/runs; poll; download
  ▼
FastAPI + Jinja2
  │
  ├── bounded local worker and pending queue
  │       └── isolated Linux/amd64 subprocess → AIConfigurator CLI
  ├── in-memory run metadata and status
  └── ephemeral per-run artifacts under /app/data/runs/{run_id}/
```

The web process admits work and returns a run ID immediately. A bounded local worker executes the real CLI in an isolated subprocess, parses its generated CSV output, ranks configurations against the requested SLA, and records safe failure details. The browser polls until the run is `completed` or `failed`. AIConfigurator output is an estimate and still requires real serving benchmarks before production decisions.

The container contract is `linux/amd64` because AIConfigurator's wheels are Linux x86-64 only. The local Kubernetes deployment has one Portal replica, a ClusterIP Service, an `emptyDir` artifact volume, and non-root execution. It requests 1 CPU/1 GiB and is limited to 2 CPU/2 GiB based on the recorded local measurement; rolling updates use `maxUnavailable: 0` and `maxSurge: 1`. The Portal is not a serving runtime.

For local observability, the Portal exposes Prometheus text at `/metrics`, emits OpenTelemetry traces, and writes correlated JSON lifecycle logs. The optional Minikube stack uses Prometheus, Tempo, Grafana, and the OTel Collector for traces; Alloy forwards Kubernetes logs directly to Loki. These components use local, ephemeral storage and are documented in [`docs/local-observability.md`](docs/local-observability.md).

## Local Kubernetes

The local manifests are in [`k8s/`](k8s/). For the complete Minikube plus Prometheus, Tempo, OTel Collector Contrib, Loki, Alloy, and Grafana setup, follow [`docs/local-observability.md`](docs/local-observability.md). Alloy forwards Kubernetes Pod logs directly to Loki and preserves Portal `trace_id`/`span_id` as structured metadata for Grafana trace/log correlation. The short portal-only path is:

```sh
make minikube-load-image
kubectl kustomize k8s
kubectl apply -k k8s
kubectl rollout status deployment/aiconfigurator-portal
kubectl port-forward service/aiconfigurator-portal 8000:8000
```

The Deployment uses measured CPU/memory requests and limits and tuned liveness/readiness thresholds. Pod replacement still loses in-flight runs, run metadata, and generated artifacts because the service is intentionally single-replica and ephemeral.

## Current API

With the Python test dependencies installed, start the development server with `make dev` and submit a run:

```sh
curl -X POST http://127.0.0.1:8000/api/runs \
  -H 'content-type: application/json' \
  -d '{"model":"Qwen/Qwen3-32B-FP8","system":"h200_sxm","total_gpus":32,"ttft":2000,"tpot":30}'
```

Open `http://127.0.0.1:8000/` for the form. It submits the five constraints to the async API, polls status every two seconds, and reports loading, completion, or safe error states. Completed runs render ranked estimates with SLA outcomes and allow-listed artifact links. The service exposes `/live` for process liveness, `/ready` for worker/storage readiness, and `/metrics` for Prometheus text. Application lifecycle events are JSON logs with `event`, `run_id`, `trace_id`, and `span_id`; set `PORTAL_LOG_LEVEL` to adjust verbosity. OpenTelemetry uses `OTEL_SERVICE_NAME` and can add asynchronous OTLP HTTP trace/metric export with `OTEL_EXPORTER_OTLP_ENDPOINT` or signal-specific endpoint/exporter variables; no collector is required for local metrics. The API returns HTTP `202` with `{ "id": "...", "status": "queued" }`; when all pending queue slots are occupied, it returns `429` with `Retry-After: 1`, and a service shutting down returns `503`. Completed runs include ranked `results` and allow-listed `artifacts`, which can be downloaded with `GET /api/runs/{id}/artifacts/{path}`. The worker uses `AICONFIGURATOR_ARTIFACT_ROOT` (default `.tmp/runs`; use `/app/data/runs` in the container), `AICONFIGURATOR_TIMEOUT_SECONDS` (default 900 seconds), and removes UUID run directories older than 24 hours. Native macOS execution is not supported because the AIConfigurator dependency is Linux x86-64 only.

## Accepted design decisions

The detailed records in [`docs/DESIGN_DECISIONS.md`](docs/DESIGN_DECISIONS.md) are the source of truth. Each ADR records alternatives, trade-offs, failure modes, and what would change the decision. The current implementation is governed by these accepted choices:

| ADR | Decision used by the portal |
|---|---|
| [001 — Bounded local execution](docs/decisions/001-execution-model.md) | One or two local worker processes keep CPU-heavy sweeps out of the HTTP request path. Pod restart may lose in-flight work. |
| [002 — Asynchronous job API](docs/decisions/002-api-model.md) | `POST /api/runs` returns `202` and a run ID; clients poll `GET /api/runs/{id}` about every two seconds. |
| [003 — CLI subprocess integration](docs/decisions/003-aiconfigurator-integration.md) | The bounded worker invokes the unmodified AIConfigurator CLI and normalizes its output behind an adapter. |
| [004 — Ephemeral local artifacts](docs/decisions/004-artifact-storage.md) | Per-run artifacts live under the local run root for up to 24 hours and are served only through an allow-list. |
| [005 — Bounded concurrency](docs/decisions/005-concurrency.md) | One or two workers and a pending queue of ten provide predictable CPU use; saturation returns `429` with `Retry-After: 1`. |
| [006 — Separate probes](docs/decisions/006-probes.md) | `/live` checks process liveness; `/ready` checks initialization and writable artifact storage, not worker idleness. |
| [007 — Focused observability](docs/decisions/007-observability.md) | OpenTelemetry traces, Prometheus metrics, and correlated structured logs cover HTTP, queue, runs, subprocesses, and artifact bytes. |
| [011 — Timeout and cancellation](docs/decisions/011-timeout-cancellation.md) | Configurable subprocess deadlines (900 seconds by default), process-group cleanup, and shutdown cancellation prevent hung work from occupying workers forever. |
| [012 — Local observability stack](docs/decisions/012-local-observability-stack.md) | A dedicated Minikube profile runs small, separate Helm releases for Prometheus, Tempo, Grafana, and the OTel Collector. |
| [013 — Direct Alloy-to-Loki forwarding](docs/decisions/013-loki-alloy-log-forwarding.md) | Alloy collects Kubernetes container logs and writes directly to local Loki while preserving trace/span correlation metadata. |

ADR-008 (caching), ADR-009 (multi-tenancy), and ADR-010 (output-trust policy) remain **Proposed** and are not expansion points for the current take-home. The UI's estimate warning is still shown because benchmark validation is required.

## Known Limitations

The form is intentionally plain HTML/Jinja2 with a small inline submit/polling/result bridge and no frontend framework. There is no public per-run cancellation endpoint; shutdown cancellation is lifecycle protection only. Metrics, traces, and logs are process-local unless an OTLP backend or external log collector is configured; in-memory metric state resets on restart. The local Minikube observability stack uses ephemeral storage and is not production-ready; Grafana Loki/Alloy collection requires privileged read-only access to the node's `/var/log` path. Artifacts are ephemeral and are lost on process/pod restart; only explicit generated filenames are downloadable, and generated scripts are never executed by the portal. The Docker image pins the base image digest and direct AIConfigurator dependencies, but does not yet hash-lock every transitive Python dependency. Authentication, TLS, secrets management, and high availability are intentionally out of scope for the take-home; the eventual submission must state what would be added for production.
