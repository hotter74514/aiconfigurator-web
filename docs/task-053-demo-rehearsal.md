# TASK-053 Demo Rehearsal

## Scope

Rehearse the 15-minute acceptance path from [`docs/demo-checklist.md`](demo-checklist.md)
against both the Linux/amd64 Docker runtime and the dedicated local Minikube
deployment. The successful runs use the real AIConfigurator CLI; the failure
case uses the same real CLI with an intentionally invalid system value.

## Inputs

```json
{
  "model": "Qwen/Qwen3-32B-FP8",
  "system": "h200_sxm",
  "total_gpus": 32,
  "ttft": 2000,
  "tpot": 30
}
```

This is the documented support-matrix example with the portal's TTFT/TPOT
constraints included.

## Docker runtime rehearsal

Commands:

```sh
make docker-build
docker run --detach --rm --name aiconfigurator-demo-task053 \
  --platform linux/amd64 \
  --publish 127.0.0.1:18001:8000 \
  aiconfigurator-portal:local
curl http://127.0.0.1:18001/live
curl http://127.0.0.1:18001/ready
curl http://127.0.0.1:18001/
curl -X POST http://127.0.0.1:18001/api/runs \
  -H 'content-type: application/json' \
  -d '{"model":"Qwen/Qwen3-32B-FP8","system":"h200_sxm","total_gpus":32,"ttft":2000,"tpot":30}'
curl http://127.0.0.1:18001/api/runs/659ebb56-4ab4-4aab-9527-b78ef692a1a6
curl http://127.0.0.1:18001/api/runs/659ebb56-4ab4-4aab-9527-b78ef692a1a6/artifacts/Qwen/Qwen3-32B-FP8_h200_sxm_trtllm_isl4000_osl1000_ttft2000_tpot30_767559/agg/top1/k8s_deploy.yaml
curl http://127.0.0.1:18001/metrics
docker logs aiconfigurator-demo-task053
docker rm --force aiconfigurator-demo-task053
```

Results:

- The form was present at `/` and returned the default model value.
- Run `659ebb56-4ab4-4aab-9527-b78ef692a1a6` was accepted as `queued` and
  completed through the real subprocess in 12,392 ms.
- The result contained 8 ranked candidates. The top candidate was `disagg`
  with 32 GPUs, 51,726.08 predicted tokens/s, 537.827 ms predicted TTFT,
  29.911 ms predicted TPOT, and `meets_sla: true`.
- The allow-listed `k8s_deploy.yaml` download returned HTTP 200 with
  `content-disposition: attachment` and a 3,608-byte YAML artifact.
- Metrics recorded one successful subprocess, one completed run, and
  315,867 artifact bytes. Logs recorded `run_queued`, `run_started`,
  `subprocess_completed`, and `run_terminal` with matching run and trace IDs.

Failure recovery used this additional request:

```sh
curl -X POST http://127.0.0.1:18001/api/runs \
  -H 'content-type: application/json' \
  -d '{"model":"Qwen/Qwen3-32B-FP8","system":"not-a-real-system","total_gpus":1,"ttft":2000,"tpot":30}'
curl http://127.0.0.1:18001/api/runs/f4f132a8-2670-4bd9-b5d9-03b4aa32f7fc
```

The invalid run became `failed` in 2,798 ms with the safe message
`AIConfigurator exited with status 1`. Its structured lifecycle logs recorded
the subprocess `error` outcome and the terminal `failed` status; no partial
artifacts were exposed.

## Kubernetes rehearsal

The active context was checked before applying resources:

```sh
kubectl config current-context
minikube profile list
make minikube-load-image
kubectl apply -k k8s
kubectl rollout status deployment/aiconfigurator-portal --timeout=180s
kubectl get pods -l app.kubernetes.io/name=aiconfigurator-portal -o wide
kubectl port-forward service/aiconfigurator-portal 18002:8000
```

Observed context and rollout:

```text
context: aiconfigurator
profile: aiconfigurator / docker / OK / 1 node
pod: 1/1 Running, 0 restarts
```

Through the port-forward, run `8b939040-be46-48d4-b5e1-93a185119ad5` completed
through the real subprocess in 13,592 ms. It produced 8 candidates with the
same top estimate and 95 allow-listed artifacts. The downloaded
`agg/best_config_topn.csv` returned HTTP 200, `text/csv`, and 1,406 bytes.
`/live` returned `{"status":"ok"}`, `/ready` returned `{"status":"ready"}`,
and `/metrics` exposed completed-run, successful-subprocess, and artifact-byte
metrics. Pod logs contained the four expected lifecycle events with matching
run and trace IDs.

## Recovery and limitations

- The Docker runtime is the fast local fallback when port-forwarding or
  Minikube is unavailable; both paths still use the real AIConfigurator CLI.
- The run IDs and output values above are recorded evidence, not durable run
  history. Restarting the Pod removes the local metadata and artifacts.
- The estimate warning remains part of the demo: predicted values require
  benchmark validation on the target serving stack.
