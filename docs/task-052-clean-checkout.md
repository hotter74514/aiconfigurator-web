# TASK-052 Clean Checkout Verification

## Scope

Verify that the committed Portal source can be checked out into a clean
worktree, install its declared test dependencies, render its Kubernetes
manifests, and build/run the Linux/amd64 container without relying on the
developer worktree's virtual environment or ignored files.

## Environment

- Host: macOS arm64
- Python: 3.14.5
- Docker: 29.4.0
- Kubernetes client: v1.37.0 / kustomize v5.8.1
- Commit verified: `96584cc` (`docs: record limitations and production evolution`)

AIConfigurator was exercised previously through the real Linux/amd64 smoke
test documented in [`docs/task-000-smoke-test.md`](task-000-smoke-test.md).
This task verifies the clean-checkout build and runtime contract; it does not
repeat that potentially long AIConfigurator sweep.

## Verification commands

The clean checkout was created without copying ignored or untracked files:

```sh
git worktree add --detach /tmp/aiconfigurator-clean-checkout.UvMrXd HEAD
git status --porcelain=v1 --branch
```

The clean status was:

```text
## HEAD (no branch)
```

The first `make check` correctly reported that a fresh checkout had no test
dependencies (`No module named pytest`). After installing only the declared
test extra in the temporary worktree, verification succeeded:

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -e '.[test]'
make check
.venv/bin/python -m compileall -q app tests
make k8s-render
make container-check
```

## Results

- `make check`: **46 passed**
- `compileall`: passed
- `make k8s-render`: passed; Deployment and ClusterIP Service rendered
- `make container-check`: passed
  - image platform: `linux/amd64`
  - liveness: `{"status":"ok"}`
  - readiness: `{"status":"ready"}`
  - metrics: Prometheus text endpoint responded successfully
- The clean checkout remained free of tracked changes throughout verification.

## Limitations

The project does not yet commit a complete dependency lock with hashes, so the
fresh installation resolves the declared version ranges at verification time.
The full submit → poll → ranked results → artifact download rehearsal remains
TASK-053, and a local Kubernetes cluster deployment is not repeated here.
