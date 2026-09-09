# TASK-041 Kubernetes Report

## Scope

TASK-041 adds local Kubernetes manifests for the verified `aiconfigurator-portal:local` runtime image. It does not tune resources, configure rollout behavior, or add external storage.

## Workload shape

- `k8s/deployment.yaml`: one replica, port 8000, `IfNotPresent` local image policy, non-root UID/GID 10001, `RuntimeDefault` seccomp profile, and an `emptyDir` mounted at `/app/data/runs`.
- `k8s/service.yaml`: internal `ClusterIP` Service named `aiconfigurator-portal` on port 8000.
- `k8s/kustomization.yaml`: local composition entry point for `kubectl apply -k k8s`.
- Liveness calls `/live`; readiness calls `/ready`. Both use the named `http` container port and do not invoke AIConfigurator.

## Local usage

```sh
make docker-build
kubectl kustomize k8s
kubectl apply -k k8s
kubectl rollout status deployment/aiconfigurator-portal
kubectl port-forward service/aiconfigurator-portal 8000:8000
```

Before `kubectl apply`, verify the current context is a local Kubernetes cluster and that the cluster can access the locally loaded image. Never apply these manifests to a shared or production context.

## Verification

The manifest set was rendered locally with:

```sh
make k8s-render
```

The render completed without a live cluster. A live apply was intentionally not run because the active kubeconfig context was a shared EKS cluster and local AWS credentials were unavailable. No cluster state was changed.

## Follow-up completed

TASK-042 measured the AIConfigurator Portal workload and added resource
requests/limits in [the Portal resource report](task-042-portal-resources.md).
TASK-043 added Portal probe thresholds and conservative rolling-update behavior
in [the Portal rollout report](task-043-portal-rollout.md). The `emptyDir`
volume remains deliberately ephemeral: pod replacement loses active runs and
generated artifacts.
