# Tasks

Work strictly in priority order. Architect tasks produce accepted ADRs; Builder tasks implement only accepted decisions. Keep each completed task as an inspectable commit.

## P0 — Feasibility

- [x] **TASK-000** — Dockerized AIConfigurator smoke test *(see [test report](docs/task-000-smoke-test.md))*
- [x] **TASK-001** — Understand CLI output and artifact directory structure *(see [contract](docs/task-001-cli-artifacts.md))*

## P1 — Architecture and core execution

- [x] **TASK-010** — Accept execution-model and concurrency ADRs
- [x] **TASK-011** — Accept async API ADR
- [x] **TASK-012** — Accept CLI-subprocess integration ADR
- [ ] **TASK-013** — Implement `POST /api/runs`
- [ ] **TASK-014** — Implement `GET /api/runs/{id}` and status transitions
- [ ] **TASK-015** — Implement bounded worker execution and failure capture
- [ ] **TASK-016** — Parse and rank AIConfigurator results
- [ ] **TASK-017** — Implement artifact allow-list and download

## P2 — Minimal user experience

- [ ] **TASK-020** — Build the plain HTML/Jinja2 form
- [ ] **TASK-021** — Poll run status and render loading/error states
- [ ] **TASK-022** — Render ranked results and estimate warning

## P3 — Operations and failure modes

- [ ] **TASK-030** — Enforce bounded queue and return `429`/`503` under saturation
- [ ] **TASK-031** — Add timeout, cancellation, subprocess cleanup, and regression tests
- [ ] **TASK-032** — Implement distinct `/live` and `/ready` probes
- [ ] **TASK-033** — Add focused metrics
- [ ] **TASK-034** — Add structured logs with run correlation

## P4 — Packaging and deployment

- [ ] **TASK-040** — Build reproducible Linux/amd64 Docker image
- [ ] **TASK-041** — Add local Kubernetes Deployment and Service
- [ ] **TASK-042** — Measure and set CPU requests/limits
- [ ] **TASK-043** — Configure probe thresholds and rolling-update behavior

## P5 — Submission and defense

- [ ] **TASK-050** — Document architecture and accepted ADR summaries in README
- [ ] **TASK-051** — Document known limitations and production evolution
- [ ] **TASK-052** — Verify from a clean checkout
- [ ] **TASK-053** — Rehearse the demo checklist
- [ ] **TASK-054** — Prepare incremental commit history for review

## Bonus — Only after P0–P5

- [ ] Pareto frontier visualization
- [ ] Aggregated vs disaggregated comparison
- [ ] Deterministic result cache
- [ ] Run history
- [ ] Multi-user awareness
