# TASK-032: Liveness and Readiness Probes

TASK-032 adds separate FastAPI endpoints for deployment health checks:

- `GET /live` returns `200 {"status":"ok"}` and checks only that the process can serve a request.
- `GET /ready` returns `200 {"status":"ready"}` after worker initialization and a writable artifact root are confirmed.
- `/ready` returns `503` with a safe detail when workers are not initialized, artifact storage is unavailable, or shutdown has started.

Readiness does not invoke AIConfigurator, require an idle worker, or inspect queue depth. A CPU-heavy active run therefore remains ready, while queue saturation continues to return `429` at submission. `/live` remains healthy after manager shutdown to preserve the distinction between process liveness and service readiness.

The artifact check creates and removes a temporary file below the configured artifact root. It does not create a run or mutate existing artifacts. The probe router is dependency-injected with the same `RunManager` used by the API.

Verification:

```sh
make check                         # 41 tests passed
python3 -m compileall -q app tests
git diff --check
```

Regression coverage verifies healthy probes, missing workers, unwritable storage, busy workers, and shutdown behavior. Metrics, structured logs, and Kubernetes manifests remain later tasks.
