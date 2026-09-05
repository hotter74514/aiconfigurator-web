# TASK-015: Bounded Worker Execution

## Implemented Boundary

`RunManager` owns an in-memory run store and a bounded pending queue. It starts one local scheduler worker by default (two is supported), and each queued run invokes AIConfigurator through an isolated child subprocess. The worker captures stdout, stderr, exit code, and elapsed milliseconds before moving the run to `completed` or `failed`.

The queue capacity is ten. A full queue is rejected by `POST /api/runs` with HTTP `429`. Worker exceptions become a safe failure message; raw subprocess stderr remains stored for later diagnostics and is not exposed by the status response.

## Real Container Verification

The worker was exercised against the previously verified `linux/amd64` image rather than a fake runner:

```text
Image: aiconfigurator-web:local
Platform: linux/amd64
Model: Qwen/Qwen3-32B-FP8
System: h200_sxm
Total GPUs: 32
TTFT/TPOT: 2000/30
Status: completed
Exit code: 0
Duration: 10209 ms
stdout: 8726 bytes
stderr: 0 bytes
```

The worker test command mounted the current `app/` package into the container and submitted a `RunRequest` through `RunManager`; AIConfigurator itself was executed by the child process. This verified execution and failure capture only; it did not persist artifacts.

## Tests

The focused suite covers command construction, successful completion, non-zero exit failure, runner exceptions, queue capacity, status transitions, and API `429` behavior. Fresh Python 3.11 validation completed with `16 passed`.

## Deferred Work

Timeout/cancellation, artifact directory allocation, result parsing, structured logs, metrics, and production container packaging remain in later tasks. The worker currently has no timeout so cancellation policy is not silently chosen ahead of TASK-031.
