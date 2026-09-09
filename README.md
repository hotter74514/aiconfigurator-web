# aiconfigurator-web

Serving Configuration Portal take-home assignment: a self-service web experience over NVIDIA Dynamo AIConfigurator.

## Project workflow

Start with [`docs/assignment-brief.md`](docs/assignment-brief.md), then read [`AGENTS.md`](AGENTS.md), [`ARCHITECTURE.md`](ARCHITECTURE.md), [`ROADMAP.md`](ROADMAP.md), and [`TASKS.md`](TASKS.md). Codex prompts are in [`prompts/`](prompts/), and the interview acceptance path is [`docs/demo-checklist.md`](docs/demo-checklist.md).

Use two deliberate Codex modes: [`prompts/architect.md`](prompts/architect.md) proposes and records ADRs without coding; [`prompts/builder.md`](prompts/builder.md) implements only decisions marked **Accepted**. Keep the commit history incremental and reviewable; do not squash the submission into one commit.

The task-by-task history audit and commit naming policy are recorded in [`docs/task-054-commit-history.md`](docs/task-054-commit-history.md).

TASK-000 provides and verifies a minimal Linux/amd64 AIConfigurator image and smoke runner. TASK-001 documents the observed CLI and artifact contract in [`docs/task-001-cli-artifacts.md`](docs/task-001-cli-artifacts.md). The portal now covers the P1–P4 execution, user-journey, operations, container, and local Kubernetes milestones; P5 focuses on documentation and final verification.

TASK-013 now exposes the validated asynchronous submission boundary at `POST /api/runs`, TASK-014 exposes `GET /api/runs/{id}` with queued/running/completed/failed transitions, and TASK-015 runs jobs through a bounded local worker with an isolated AIConfigurator subprocess. TASK-016 adds a structured CSV parser and deterministic SLA-aware ranking. TASK-017 now persists each run's generated output in an ephemeral per-run directory, returns ranked results and allow-listed artifact names on completion, and serves safe downloads. TASK-020 adds the plain HTML/Jinja2 form at `/`; TASK-021 adds two-second status polling with loading and error states; TASK-022 renders ranked estimates, SLA outcomes, and artifact links; TASK-023 refreshes the page as a responsive serving-decision console without adding a frontend runtime or remote assets; TASK-030 rejects a full pending queue with HTTP `429` and `Retry-After: 1`; TASK-031 adds configurable subprocess deadlines, process-group cleanup, and shutdown cancellation; TASK-032 adds separate `/live` and `/ready` probes; TASK-033 adds OpenTelemetry traces, Prometheus metrics at `/metrics`, optional OTLP export, queue saturation attributes, and subprocess trace propagation; TASK-034 adds JSON lifecycle logs with run and trace correlation; TASK-062 loads model/GPU dropdown choices from the installed AIConfigurator support matrix. BONUS-004 adds bounded newest-first recent local history through `GET /api/runs`; BONUS-006 adds an on-demand ZIP of the complete allow-listed artifact set. Verification is documented in [`docs/task-034-logging.md`](docs/task-034-logging.md), [`docs/task-058-run-history.md`](docs/task-058-run-history.md), [`docs/task-060-ui-refresh.md`](docs/task-060-ui-refresh.md), [`docs/task-061-artifact-bundle.md`](docs/task-061-artifact-bundle.md), and [`docs/task-062-support-selectors.md`](docs/task-062-support-selectors.md).

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
  ├── in-memory run metadata/status and bounded result cache
  └── ephemeral per-run artifacts under /app/data/runs/{run_id}/
```

The web process admits work and returns a run ID immediately. A bounded local worker executes the real CLI in an isolated subprocess, parses its generated CSV output, ranks configurations against the requested SLA, and records safe failure details. Successful normalized results and allow-listed artifacts are retained in a bounded process-local deterministic cache; a cache hit still follows the async run lifecycle but skips the CLI and restores artifacts into the new run directory. Recent completed and failed runs are retained in a separate bounded process-local history index and are exposed newest-first through `GET /api/runs`; eviction removes only metadata, while expired artifact links are reported unavailable. The browser polls until the run is `completed` or `failed`. AIConfigurator output is an estimate and still requires real serving benchmarks before production decisions.

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

With the Python test dependencies installed, `make dev` starts the server for API/UI-only checks. On macOS, use the Docker or Kubernetes demo path below for real AIConfigurator runs:

```sh
curl -X POST http://127.0.0.1:8000/api/runs \
  -H 'content-type: application/json' \
  -d '{"model":"Qwen/Qwen3-32B-FP8","system":"h200_sxm","total_gpus":32,"ttft":2000,"tpot":30}'
```

Open `http://127.0.0.1:8000/` for the form. It loads the installed AIConfigurator support matrix through `GET /api/support`, presenting native Model and GPU system dropdowns with the system choices filtered for the selected model. It submits the five constraints to the async API, polls status every two seconds, and reports loading, completion, or safe error states. Completed runs render ranked estimates with SLA outcomes, an aggregate-versus-disaggregated comparison, a throughput-versus-latency Pareto frontier, individual allow-listed artifact links, and a **Download all artifacts** action. The page also shows bounded recent local history and can reload a completed record or failure message. Identical requests may be served from the bounded deterministic cache after a successful run; cache hits still return a new run ID and restore downloadable artifacts. The mode comparison is scoped to candidates meeting both targets and reports missing modes explicitly; it does not replace benchmark validation. The service exposes `/live` for process liveness, `/ready` for worker/storage readiness, and `/metrics` for Prometheus text. Application lifecycle events are JSON logs with `event`, `run_id`, `trace_id`, and `span_id`; set `PORTAL_LOG_LEVEL` to adjust verbosity. OpenTelemetry uses `OTEL_SERVICE_NAME` and can add asynchronous OTLP HTTP trace/metric export with `OTEL_EXPORTER_OTLP_ENDPOINT` or signal-specific endpoint/exporter variables; no collector is required for local metrics. The API returns HTTP `202` with `{ "id": "...", "status": "queued" }`; `GET /api/runs` returns newest-first completed/failed local history; when all pending queue slots are occupied, it returns `429` with `Retry-After: 1`, and a service shutting down returns `503`. Completed runs include ranked `results` and allow-listed `artifacts`. Individual files use `GET /api/runs/{id}/artifacts/{path}`; `GET /api/runs/{id}/artifacts.zip` creates a transient ZIP only when the complete recorded artifact set is still available. The worker uses `AICONFIGURATOR_ARTIFACT_ROOT` (default `.tmp/runs`; use `/app/data/runs` in the container), `AICONFIGURATOR_TIMEOUT_SECONDS` (default 900 seconds), and removes UUID run directories older than 24 hours. Native macOS execution is not supported because the AIConfigurator dependency is Linux x86-64 only.

## Demo rehearsal

The verified demo uses the dedicated `aiconfigurator` Minikube context and a local port-forward. Run the setup in one terminal:

```sh
make minikube-load-image
kubectl config current-context  # must print: aiconfigurator
kubectl apply -k k8s
kubectl rollout status deployment/aiconfigurator-portal --timeout=180s
kubectl port-forward service/aiconfigurator-portal 8000:8000
```

In a second terminal, open the portal at `http://127.0.0.1:8000/`, then submit the support-matrix example and poll the returned ID:

```sh
curl http://127.0.0.1:8000/live
curl http://127.0.0.1:8000/ready
curl -X POST http://127.0.0.1:8000/api/runs \
  -H 'content-type: application/json' \
  -d '{"model":"Qwen/Qwen3-32B-FP8","system":"h200_sxm","total_gpus":32,"ttft":2000,"tpot":30}'
curl http://127.0.0.1:8000/api/runs/<RUN_ID>
curl -OJ http://127.0.0.1:8000/api/runs/<RUN_ID>/artifacts/<ARTIFACT_PATH>
curl -OJ http://127.0.0.1:8000/api/runs/<RUN_ID>/artifacts.zip
curl http://127.0.0.1:8000/metrics
kubectl logs deployment/aiconfigurator-portal
```

The exact successful run IDs, ranked output, downloaded artifact, failure recovery, and observed metrics/logs are recorded in [`docs/task-053-demo-rehearsal.md`](docs/task-053-demo-rehearsal.md).

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
| [008 — Deterministic caching](docs/decisions/008-caching.md) | Successful normalized results and allow-listed artifacts use a bounded process-local LRU cache keyed by request and runtime identity. |
| [014 — Bounded run history](docs/decisions/014-run-history.md) | Recent completed and failed runs use a bounded process-local index exposed by `GET /api/runs`; eviction does not delete artifacts. |
| [009 — Single-user boundary](docs/decisions/009-multi-tenancy.md) | The deployment is explicitly single-user and controlled-demo only; it does not accept client-supplied identity headers or provide authorization. |
| [011 — Timeout and cancellation](docs/decisions/011-timeout-cancellation.md) | Configurable subprocess deadlines (900 seconds by default), process-group cleanup, and shutdown cancellation prevent hung work from occupying workers forever. |
| [012 — Local observability stack](docs/decisions/012-local-observability-stack.md) | A dedicated Minikube profile runs small, separate Helm releases for Prometheus, Tempo, Grafana, and the OTel Collector. |
| [013 — Direct Alloy-to-Loki forwarding](docs/decisions/013-loki-alloy-log-forwarding.md) | Alloy collects Kubernetes container logs and writes directly to local Loki while preserving trace/span correlation metadata. |
| [015 — Frontend UI refresh](docs/decisions/015-frontend-ui-refresh.md) | Use frontend-design guidance at authoring time while keeping the deployed page as self-contained Jinja2, CSS, and JavaScript. |
| [016 — Artifact bundle and ranked downloads](docs/decisions/016-artifact-bundle-and-ranked-downloads.md) | Generate a complete allow-listed ZIP on demand; do not guess a ranked-row artifact link without a stable candidate identity. |

ADR-010 (output-trust policy) remains **Proposed** and is not an expansion point for the current take-home. ADR-009 is accepted only as an explicit single-user boundary; it does not add authentication or multi-tenant authorization. The UI's estimate warning is still shown because benchmark validation is required.

## Known Limitations

These are deliberate take-home boundaries rather than hidden production guarantees:

- **Estimate accuracy:** AIConfigurator predicts serving behavior; every result needs a real benchmark on the target model, GPU system, backend, and workload before it is used for capacity or deployment decisions. The recorded CPU/memory measurement is a local Minikube observation, not a production capacity benchmark.
- **Execution and durability:** run metadata and the bounded cache are in memory, there is one local worker by default, and the pending queue is capped at ten. A process or Pod restart loses queued/in-flight runs, cache entries, and their status.
- **Artifact lifecycle:** artifacts are stored locally with a 24-hour cleanup policy and Kubernetes uses `emptyDir`. They are lost on restart; bounded recent history is also lost on restart, and an evicted history record does not delete its still-live artifact directory. Only explicit allow-listed filenames can be downloaded. The bundle is a transient local ZIP, not a persisted artifact, and fails if the recorded set is incomplete. Ranked rows have no direct download because the observed output does not expose a stable candidate-to-directory identity. Generated scripts are never executed by the portal.
- **Platform and supply chain:** AIConfigurator is supported only in the Linux x86-64 container contract, so macOS development requires Docker with `linux/amd64`. The base image and direct AIConfigurator dependencies are pinned, but transitive project dependencies are not yet hash-locked.
- **User and network security:** authentication, authorization, tenant ownership, quotas, TLS, ingress, secret management, and high availability are intentionally absent. The local deployment is for a controlled demo and must not be treated as an internet-facing service.
- **Cancellation and operations:** there is no public per-run cancellation endpoint; cancellation is currently limited to service shutdown and timeout cleanup. Metrics and traces are process-local unless an OTLP backend is configured, and Prometheus state resets on restart. The local Loki/Alloy setup is ephemeral and requires privileged read-only access to Kubernetes node log paths.
- **Caching:** cache identity defaults to the pinned AIConfigurator version, the portal result-model version, and a local-unversioned runner identity. Set `AICONFIGURATOR_RUNNER_IMAGE_DIGEST` to the deployed image digest for release-grade invalidation; the cache is process-local, bounded, and not shared across replicas.
- **Frontend surface:** the Portal UI remains one self-contained Jinja2 template with native CSS and JavaScript. It has no shared component system or frontend build pipeline; introduce one only when multiple pages or repeated interactive components justify the added boundary.

## Production evolution

Add the following capabilities only when the corresponding requirement becomes real:

| Trigger | Production change |
|---|---|
| Runs must survive Pod replacement or results need bookmarks | Store run metadata in a durable database; use a durable queue with retry/idempotency semantics; put artifacts in object storage with lifecycle rules and controlled download URLs. |
| Multiple replicas or sustained queue pressure | Separate the stateless API from independently scaled workers; use shared durable state, admission quotas, rate limiting, and worker autoscaling based on queue depth and run latency. |
| Multiple teams or untrusted users | Add authentication, per-run ownership checks, team-level quotas, tenant isolation, audit events, and authorization before exposing metadata, queue access, or artifacts. |
| Internet or enterprise deployment | Add TLS termination, ingress/API gateway policy, secret-manager integration, network policies, image signing/scanning, and a documented backup/restore process. |
| Production availability requirements | Run multiple API replicas, durable worker infrastructure, PodDisruptionBudgets, upgrade/rollback procedures, and recovery objectives appropriate to the service. |
| Capacity decisions need evidence | Add a repeatable benchmark harness, versioned model/GPU/backend inputs, actual-vs-predicted result tracking, and a validation gate before accepting an estimate for deployment. |
| Cross-service observability and retention | Route telemetry through a managed or production collector, use durable metrics/traces/log storage, define retention and access controls, and add alerts/SLOs without promoting run IDs or trace IDs to high-cardinality labels. |
| Reproducible releases are required | Generate a complete dependency lock with hashes, publish an SBOM, scan the image and dependencies, and verify provenance in CI. |

The current single-service shape is intentionally a reversible starting point. Each evolution should preserve the explicit CLI boundary and safe artifact handling while adding only the durability, isolation, or operational control justified by its trigger.
