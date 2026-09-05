# TASK-040 Container Report

## Scope

TASK-040 packages the existing portal and AIConfigurator smoke contract in a Linux/amd64 Docker image. It does not add Kubernetes resources or change application behavior.

## Build contract

The Dockerfile has three useful targets:

- `smoke`: Python 3.11 plus `aiconfigurator==0.11.0` and `plotext==5.3.2`; entrypoint is `aiconfigurator`.
- `portal`: adds `app/`, `templates/`, the installed project, and `/app/data/runs`.
- `runtime`: starts Uvicorn on port 8000 as the non-root `portal` user.

The Python base image is digest-pinned. The repository commands still pass `--platform linux/amd64` explicitly because AIConfigurator wheels are not supported on macOS arm64.

## Verification

Exact commands run:

```sh
make container-check
docker build --platform linux/amd64 --target smoke --load -t aiconfigurator-web:task-040-smoke .
docker image inspect aiconfigurator-portal:local --format '{{.Os}}/{{.Architecture}} user={{.Config.User}} entrypoint={{json .Config.Entrypoint}}'
docker run --rm --platform linux/amd64 aiconfigurator-web:task-040-smoke --help
```

Observed results:

```text
Portal container check passed
  image: aiconfigurator-portal:local
  platform: linux/amd64
  live: {"status":"ok"}
  ready: {"status":"ready"}
linux/amd64 user=portal entrypoint=["uvicorn","app.main:app","--host","0.0.0.0","--port","8000"]
smoke-help-exit: 0
```

The container check also confirms `/metrics` returns Prometheus text containing `http_server`. Build artifacts are local Docker images; no generated files are persisted in the repository. The runtime image has application code under `/app`, with ephemeral run output under `/app/data/runs`.

## Limitations

The base image and direct AIConfigurator dependencies are pinned, but transitive project dependencies remain version-range resolved because no lockfile or hash-locked requirements set exists yet. Container state and artifacts are ephemeral until a later deployment/storage task.
