# Demo Checklist

This is the acceptance path for the 15-minute live demo. Keep it runnable from a clean checkout and record the exact commands in `README.md`.

## Before the call

- [x] Build the container successfully on the target machine.
- [x] Start the local Kubernetes deployment.
- [x] Confirm the support-matrix example or another documented smoke input.
- [x] Confirm liveness, readiness, and metrics endpoints.
- [x] Confirm logs are structured and useful for one failed run.
- [x] Confirm artifacts survive long enough to download during the demo.

## Demo path

1. [x] Open the portal and submit model, GPU system/type, GPU count, TTFT, and TPOT.
2. [x] Show the returned run ID and status transition.
3. [x] Show the ranked result table with predicted throughput and latency.
4. [x] Download one generated deployment artifact and inspect its contents.
5. [x] Show health/readiness and the basic metrics surface.
6. [x] Explain the estimate warning and the most important known limitation.

## Recovery plan

Keep the recorded run IDs and fallback commands in [`docs/task-053-demo-rehearsal.md`](task-053-demo-rehearsal.md). The rehearsal uses the real AIConfigurator CLI; test doubles remain isolated to automated tests and are not part of the production path.
