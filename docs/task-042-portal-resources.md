# TASK-042 AIConfigurator Portal resource report

## Scope

TASK-042 measures the CPU and memory envelope of the `aiconfigurator-portal`
Deployment while it runs the real AIConfigurator CLI. The Tempo resource
changes are documented separately in the supplemental Tempo hardening report.

## Measurement

The active context was the dedicated Minikube profile `aiconfigurator`. A
supported `Qwen/Qwen3-32B-FP8` / `h200_sxm` request was submitted through the
Portal API and the Pod cgroup counters were sampled before and after the run.

Observed result:

- elapsed time: approximately 12 seconds
- average CPU usage during the run: approximately 1.11 cores
- memory peak: 808,988,672 bytes (approximately 772 MiB)
- workload: one bounded Portal worker invoking the real AIConfigurator CLI

This is a local Minikube observation, not a production capacity benchmark.
Different models, GPU systems, constraints, and AIConfigurator versions can
produce materially different resource requirements.

## Changes

`k8s/deployment.yaml` now sets:

- requests: `1 CPU`, `1Gi` memory
- limits: `2 CPU`, `2Gi` memory

The request covers the observed steady CPU and memory envelope so the Pod can
be scheduled with predictable resources. The limit leaves headroom for import,
CSV parsing, artifact generation, and model-specific variation while keeping a
single worker bounded on the four-CPU local cluster.

## Verification

```sh
kubectl config current-context
kubectl kustomize k8s
kubectl apply -k k8s
kubectl rollout status deployment/aiconfigurator-portal --timeout=180s
kubectl get deployment aiconfigurator-portal \
  -o jsonpath='{.spec.template.spec.containers[0].resources}'
```

The deployment was applied only to the `aiconfigurator` Minikube context and
the real run completed successfully during measurement.
