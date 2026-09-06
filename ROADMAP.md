# Roadmap

The roadmap follows assignment risk, not feature breadth. Do not begin Bonus work until every P0–P5 item is complete.

## P0 — Feasibility spike

- [x] Dockerize AIConfigurator for Linux/amd64
- [x] Run a supported smoke configuration
- [x] Inspect CLI output and generated artifacts

## P1 — Core execution

- [ ] Accept and record architecture ADRs
- [ ] Define the async run/status/artifact contracts
- [ ] Implement the API, bounded worker, subprocess adapter, parser, and download path

## P2 — Minimal user journey

- [ ] Submit model, GPU system/type, GPU count, TTFT, and TPOT
- [ ] Poll status and show failure states
- [ ] Show ranked throughput/latency results and estimate warning

## P3 — Platform behavior

- [ ] Add bounded queue/backpressure and subprocess timeout/cleanup
- [ ] Add distinct liveness/readiness probes
- [x] Add structured logs
- [x] Add focused OpenTelemetry metrics and traces
- [ ] Test failure modes and CPU contention assumptions

## P4 — Container and Kubernetes

- [x] Build the portal and AIConfigurator runtime image
- [x] Add local Kubernetes Deployment and Service manifests
- [x] Measure CPU behavior and set requests/limits
- [x] Verify rolling-update and pod-restart limitations

## P5 — Submission quality

- [x] Complete README: clean checkout, architecture, API, decisions, limitations, production evolution
- [ ] Verify the complete demo path
- [ ] Preserve incremental, reviewable Conventional Commits

## Bonus — Deferred

- [ ] Pareto frontier visualization
- [ ] Aggregated vs disaggregated comparison
- [ ] Deterministic cache
- [ ] Run history
- [ ] Multi-user awareness
