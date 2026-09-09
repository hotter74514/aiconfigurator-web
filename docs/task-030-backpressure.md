# TASK-030: Queue Backpressure

TASK-030 makes the accepted ADR-005 admission boundary explicit. `RunManager` keeps one or two active worker slots and a bounded pending queue (default: ten pending runs). `Queue.put_nowait()` rejects a submission immediately when every pending slot is occupied; it never blocks an HTTP handler and never starts an unbounded subprocess.

The API maps queue saturation to HTTP `429 Too Many Requests` with the stable body `{ "detail": "Run queue is full" }` and advisory `Retry-After: 1`. A `503` is not used for this condition because the service is alive and the queue is functioning; it remains an appropriate response for a future unavailable dependency or failed readiness state. Liveness/readiness semantics remain TASK-032 scope.

The regression coverage verifies both a stopped-worker queue filling completely and the live boundary where one worker is running plus the pending queue is full. The active run is not counted as a pending slot, so the configured queue size remains an explicit pending-work limit.

Verification:

```sh
make check                         # 31 tests passed
python3 -m compileall -q app tests
git diff --check
```

Timeouts, cancellation, subprocess cleanup, probes, metrics, and deployment packaging remain outside TASK-030.
