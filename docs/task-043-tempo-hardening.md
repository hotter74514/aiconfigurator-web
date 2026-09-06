# Tempo restart hardening report

## Finding

`observability/tempo-0` was restarted twice because its liveness probe queried
`/ready`. Kubernetes recorded both HTTP 503 responses and five-second request
timeouts, followed by `Container tempo failed liveness probe, will be
restarted`. The previous container exited with code 137, but its termination
reason was `Error`, not `OOMKilled`; the previous Tempo log also recorded a
SIGTERM/SIGINT shutdown. This identifies the restart mechanism as kubelet probe
failure rather than a Tempo panic or confirmed node OOM.

The incident-time CPU and memory peak could not be measured because the
Minikube Metrics API is not installed. A current node snapshot showed no
MemoryPressure and approximately 5.1 GiB available memory. The most likely
trigger was transient query/resource contention from repeated Grafana Tempo
correlation searches on the single-node local cluster.

## Changes

- Changed Tempo liveness from `/ready` HTTP to a TCP check on port 3200.
- Kept `/ready` for readiness and increased its timeout to 10 seconds with a
  six-failure threshold.
- Increased Tempo resources from `100m/256Mi` request and `500m/512Mi` limit to
  `250m/512Mi` request and `1000m/1Gi` limit.
- Bounded Tempo query concurrency to four querier queries and eight search jobs.
- Documented that these are local-demo safeguards and not production capacity
  benchmarks.

## Verification

The change was applied only after confirming the active context was
`aiconfigurator`:

```text
helm upgrade --install tempo grafana/tempo --version 1.24.4 \
  --namespace observability --values k8s/observability/tempo-values.yaml \
  --wait --timeout 180s
```

The resulting StatefulSet and pod showed:

- `livenessProbe.tcpSocket.port=3200` with no HTTP handler
- readiness `GET /ready`, timeout 10 seconds, failure threshold 6
- resources `requests: 250m/512Mi`, `limits: 1000m/1Gi`
- rendered `max_concurrent_queries=4` and `search.concurrent_jobs=8`
- rollout complete, pod `1/1 Running`, `restartCount=0`

An in-pod smoke test sent 20 concurrent Tempo search requests. `/ready`
returned `ready` before and after the load, and the pod remained Ready with
`restartCount=0`.

This verifies the intended local failure mode, but does not establish a
production throughput or retention capacity target.
