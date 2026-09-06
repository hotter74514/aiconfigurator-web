# Tasks

Work strictly in priority order. Architect tasks produce accepted ADRs; Builder tasks implement only accepted decisions. Keep each completed task as an inspectable commit.

## P0 — Feasibility

- [x] **TASK-000** — Dockerized AIConfigurator smoke test *(see [test report](docs/task-000-smoke-test.md))*
- [x] **TASK-001** — Understand CLI output and artifact directory structure *(see [contract](docs/task-001-cli-artifacts.md))*

## P1 — Architecture and core execution

- [x] **TASK-010** — Accept execution-model and concurrency ADRs
- [x] **TASK-011** — Accept async API ADR
- [x] **TASK-012** — Accept CLI-subprocess integration ADR
- [x] **TASK-013** — Implement `POST /api/runs`
- [x] **TASK-014** — Implement `GET /api/runs/{id}` and status transitions
- [x] **TASK-015** — Implement bounded worker execution and failure capture *(see [worker report](docs/task-015-worker.md))*
- [x] **TASK-016** — Parse and rank AIConfigurator results *(see [results report](docs/task-016-results.md))*
- [x] **TASK-017** — Implement artifact allow-list and download *(see [artifact report](docs/task-017-artifacts.md))

## P2 — Minimal user experience

- [x] **TASK-020** — Build the plain HTML/Jinja2 form *(see [form report](docs/task-020-form.md))
- [x] **TASK-021** — Poll run status and render loading/error states *(see [polling report](docs/task-021-polling.md))
- [x] **TASK-022** — Render ranked results and estimate warning *(see [results report](docs/task-022-results.md))

## P3 — Operations and failure modes

- [x] **TASK-030** — Enforce bounded queue and return `429`/`503` under saturation *(see [backpressure report](docs/task-030-backpressure.md))
- [x] **TASK-031** — Add timeout, cancellation, subprocess cleanup, and regression tests *(see [timeout report](docs/task-031-timeout-cancellation.md))
- [x] **TASK-032** — Implement distinct `/live` and `/ready` probes *(see [probe report](docs/task-032-probes.md))
- [x] **TASK-033** — Add OpenTelemetry traces and focused metrics *(see [observability report](docs/task-033-observability.md))
- [x] **TASK-034** — Add structured logs with run correlation *(see [logging report](docs/task-034-logging.md))

## P4 — Packaging and deployment

- [x] **TASK-040** — Build reproducible Linux/amd64 Docker image *(see [container report](docs/task-040-container.md))*
- [x] **TASK-041** — Add local Kubernetes Deployment and Service *(see [Kubernetes report](docs/task-041-kubernetes.md))*
- [x] **TASK-042** — Measure and set AIConfigurator Portal CPU/memory requests/limits *(see [Portal resource report](docs/task-042-portal-resources.md))*
- [x] **TASK-043** — Configure AIConfigurator Portal probe thresholds and rolling-update behavior *(see [Portal rollout report](docs/task-043-portal-rollout.md))*
- [x] **TASK-044** — Integrate Prometheus exemplars with Tempo trace correlation *(see [exemplar report](docs/task-044-prometheus-exemplars.md))*
- [x] **TASK-045** — Harden Tempo against probe-induced restarts *(see [Tempo hardening report](docs/task-045-tempo-hardening.md))*

## P5 — Submission and defense

- [x] **TASK-050** — Document architecture and accepted ADR summaries in README
- [x] **TASK-051** — Document known limitations and production evolution
- [x] **TASK-052** — Verify from a clean checkout *(see [clean-checkout report](docs/task-052-clean-checkout.md))*
- [x] **TASK-053** — Rehearse the demo checklist *(see [demo rehearsal report](docs/task-053-demo-rehearsal.md))*
- [x] **TASK-054** — Prepare incremental commit history for review *(see [commit-history report](docs/task-054-commit-history.md))*

## Bonus — Only after P0–P5

- [x] **BONUS-001** — Pareto frontier visualization *(see [bonus report](docs/task-055-pareto.md))*
- [x] **BONUS-002** — Aggregated vs disaggregated comparison *(see [bonus report](docs/task-056-mode-comparison.md))*
- [x] **BONUS-003** — Deterministic result cache *(see [bonus report](docs/task-057-cache.md))*
- [x] **BONUS-004** — Bounded process-local run history *(see [bonus report](docs/task-058-run-history.md))*
- [ ] Multi-user awareness
