# Roadmap

The roadmap follows assignment risk, not feature breadth. Do not begin Bonus work until every P0–P5 item is complete.

## P0 — Feasibility spike

- [x] Dockerize AIConfigurator for Linux/amd64
- [x] Run a supported smoke configuration
- [x] Inspect CLI output and generated artifacts

## P1 — Core execution

- [x] Accept and record architecture ADRs
- [x] Define the async run/status/artifact contracts
- [x] Implement the API, bounded worker, subprocess adapter, parser, and download path

## P2 — Minimal user journey

- [x] Submit model, GPU system/type, GPU count, TTFT, and TPOT
- [x] Poll status and show failure states
- [x] Show ranked throughput/latency results and estimate warning

## P3 — Platform behavior

- [x] Add bounded queue/backpressure and subprocess timeout/cleanup
- [x] Add distinct liveness/readiness probes
- [x] Add structured logs
- [x] Add focused OpenTelemetry metrics and traces
- [x] Test failure modes and CPU contention assumptions

## P4 — Container and Kubernetes

- [x] Build the portal and AIConfigurator runtime image
- [x] Add local Kubernetes Deployment and Service manifests
- [x] Measure CPU behavior and set requests/limits
- [x] Verify rolling-update and pod-restart limitations

## P5 — Submission quality

- [x] Complete README: clean checkout, architecture, API, decisions, limitations, production evolution
- [x] Verify the complete demo path
- [x] Preserve incremental, reviewable Conventional Commits

## Bonus — In progress

- [x] Pareto frontier visualization
- [x] Aggregated vs disaggregated comparison
- [x] Deterministic cache
- [ ] Run history
- [ ] Multi-user awareness
