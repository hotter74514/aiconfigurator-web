# TASK-043 AIConfigurator Portal probe and rollout report

## Scope

TASK-043 configures Kubernetes lifecycle behavior for the
`aiconfigurator-portal` Deployment. It does not change Tempo probes or query
concurrency.

## Probe policy

The Portal follows accepted ADR-006:

- liveness calls `/live`, which checks only process liveness
- readiness calls `/ready`, which checks worker initialization and writable
  artifact storage
- neither probe invokes AIConfigurator, waits for the worker, or requires the
  queue to be idle

The configured thresholds allow startup and short CPU contention without
turning a healthy AIConfigurator process into a restart loop:

- liveness: initial delay 30s, 10s period, 3s timeout, 6 failures
- readiness: initial delay 10s, 5s period, 3s timeout, 3 failures

## Rollout policy

The single-replica Deployment uses a conservative rolling update:

- `maxSurge: 1` permits one replacement Pod during rollout
- `maxUnavailable: 0` keeps the existing ready Pod until its replacement is
  ready
- `minReadySeconds: 5` requires stable readiness before rollout progress
- `progressDeadlineSeconds: 300` gives the Linux/amd64 image time to start

This improves local service availability during image updates. The mounted
`emptyDir` remains ephemeral, so replacing the Pod still loses in-flight runs
and generated artifacts as documented by the assignment architecture.

## Verification

```sh
kubectl config current-context
kubectl kustomize k8s
kubectl apply -k k8s
kubectl rollout status deployment/aiconfigurator-portal --timeout=180s
kubectl get deployment aiconfigurator-portal \
  -o jsonpath='{.spec.strategy}{"\n"}'
kubectl get pod -l app.kubernetes.io/name=aiconfigurator-portal
```

The checks are scoped to the dedicated `aiconfigurator` Minikube context.
