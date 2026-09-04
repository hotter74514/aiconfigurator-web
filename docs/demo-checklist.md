# Demo Checklist

This is the acceptance path for the 15-minute live demo. Keep it runnable from a clean checkout and record the exact commands in `README.md`.

## Before the call

- [ ] Build the container successfully on the target machine.
- [ ] Start the local Kubernetes deployment.
- [ ] Confirm the support-matrix example or another documented smoke input.
- [ ] Confirm liveness, readiness, and metrics endpoints.
- [ ] Confirm logs are structured and useful for one failed run.
- [ ] Confirm artifacts survive long enough to download during the demo.

## Demo path

1. Open the portal and submit model, GPU system/type, GPU count, TTFT, and TPOT.
2. Show the returned run ID and status transition.
3. Show the ranked result table with predicted throughput and latency.
4. Download one generated deployment artifact and inspect its contents.
5. Show health/readiness and the basic metrics surface.
6. Explain the estimate warning and the most important known limitation.

## Recovery plan

Keep a recorded run, a local fallback command, and a short explanation of what is mocked versus real. A fallback must not hide whether the real AIConfigurator path works.
