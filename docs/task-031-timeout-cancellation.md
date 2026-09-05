# TASK-031: Timeout, Cancellation, and Subprocess Cleanup

TASK-031 implements accepted ADR-011 inside the existing bounded worker. The AIConfigurator CLI now runs in its own POSIX process group through `Popen`, captures stdout/stderr, and enforces `AICONFIGURATOR_TIMEOUT_SECONDS` (default: 900 seconds). On timeout it sends `SIGTERM`, waits five seconds, then escalates to `SIGKILL` if the process group remains alive.

`RunManager` gives each active run a cancellation event. During shutdown it stops new work, rejects new submissions with HTTP `503`, marks queued runs failed, signals active real runners, waits for cleanup, and removes incomplete run directories. Timeout and shutdown failures preserve captured diagnostic output in memory but do not expose partial artifacts. There is intentionally no public cancellation endpoint; individual-run cancellation is a future product decision.

Injected runners remain test doubles with the explicit three-argument contract `(request, save_dir, cancel_event)`. The production guarantee applies to the real CLI adapter, which can terminate the third-party process group rather than relying on cooperative code.

Verification:

```sh
make check                         # 36 tests passed
python3 -m compileall -q app tests
git diff --check
```

Regression coverage verifies normal worker behavior, timeout cleanup, active-run shutdown cancellation, process-group termination, and the existing queue/API contracts. TASK-032 probes, TASK-033 metrics, and TASK-034 structured logs remain out of scope.
