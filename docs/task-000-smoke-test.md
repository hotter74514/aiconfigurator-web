# TASK-000: Dockerized AIConfigurator Smoke Test

## Scope

This task adds only the external AIConfigurator runtime container and a repeatable smoke runner. It does not select a web framework, add portal code, or accept any architecture decision.

## Container

- Base: `python:3.11-slim-bookworm`
- Target platform: `linux/amd64`
- Dependency: `aiconfigurator==0.11.0`
- Compatibility pin: `plotext==5.3.2`
- Entrypoint: `aiconfigurator`
- Host assumption: macOS/Apple Silicon uses Docker amd64 emulation; no host GPU is required for this offline smoke test.

The AIConfigurator package pin is based on the newest version available from the configured PyPI index during setup. The explicit `plotext` pin is required because AIConfigurator `0.11.0` calls `plotext.plot_size`, which is absent from `plotext==6.0.0`. AIConfigurator documents Linux x86-64 wheel requirements and the CLI reference flow in its [official repository](https://github.com/ai-dynamo/aiconfigurator).

## Exact Commands

The canonical command is:

```sh
make smoke-configurator
```

The runner records these expanded commands in `.tmp/task-000/commands.txt`:

```sh
docker build --platform linux/amd64 --load -t aiconfigurator-web:local .
docker run --rm --platform linux/amd64 aiconfigurator-web:local cli default --model Qwen/Qwen3-32B-FP8 --total-gpus 32 --system h200_sxm
docker run --rm --platform linux/amd64 --mount type=bind,src=<repo>/.tmp/task-000/artifacts,dst=/tmp/aiconfigurator-run aiconfigurator-web:local cli default --model Qwen/Qwen3-32B-FP8 --total-gpus 32 --system h200_sxm --save-dir /tmp/aiconfigurator-run
```

## Execution Evidence

Validated successfully on 2026-09-05 from an `arm64` macOS host. Docker built and ran the image as `linux/amd64`:

| Operation | Exit status | Runtime | Result |
|---|---:|---:|---|
| Docker image build | `0` | `83,885 ms` | Image loaded successfully |
| Reference container run | `0` | `13,643 ms` | Assignment command passed |
| Artifact container run | `0` | `10,601 ms` | `--save-dir` passed |
| `make smoke-configurator` | `0` | wrapper | Passed |

Image evidence:

```text
OS: linux
Architecture: amd64
Image: sha256:1be1795dc867d141791570ac37674c457ebe72c859cf85cc806a147006e482e
aiconfigurator: 0.11.0
plotext: 5.3.2
plotext.plot_size: available
```

The first post-fix run exposed an actual dependency incompatibility: `plotext==6.0.0` caused `AttributeError: module 'plotext' has no attribute 'plot_size'` after the experiments completed. Pinning `plotext==5.3.2`, rebuilding, and rerunning resolved it. No AIConfigurator output was fabricated.

Successful output evidence:

```text
.tmp/task-000/
├── build-exit-status.txt        # 0
├── build-runtime-ms.txt         # 83885
├── reference-exit-status.txt   # 0
├── reference-runtime-ms.txt    # 13643
├── artifact-exit-status.txt     # 0
├── artifact-runtime-ms.txt     # 10601
├── reference.stdout.log         # 8752 bytes
├── reference.stderr.log         # empty
├── artifact.stdout.log          # 12313 bytes
├── artifact.stderr.log          # empty
├── commands.txt
├── artifact-files.txt
└── artifacts/                   # 95 files, 315867 bytes
```

## Captured Files and Expected Artifacts

The runner writes disposable evidence under `.tmp/task-000/`:

- `commands.txt`, `build.log`, `build-exit-status.txt`, `build-runtime-ms.txt`
- `reference.stdout.log`, `reference.stderr.log`, `reference-exit-status.txt`, `reference-runtime-ms.txt`
- `artifact.stdout.log`, `artifact.stderr.log`, `artifact-exit-status.txt`, `artifact-runtime-ms.txt`
- `artifacts/` and `artifact-files.txt`

The successful output contains `AIConfigurator Final Results`, `Overall Best Configuration`, aggregate and disaggregate ranked tables, deployment details, and `All experiments completed`. Both stdout files have zero stderr bytes.

The generated artifact tree is:

```text
artifacts/Qwen/Qwen3-32B-FP8_h200_sxm_trtllm_isl4000_osl1000_ttft2000_tpot30_718285/
├── pareto_frontier.png
├── agg/
│   ├── best_config_topn.csv
│   ├── exp_config.yaml
│   ├── pareto.csv
│   └── top1/ ... top4/  # each: 11 files; config YAML, K8s YAML, JSON, and shell runners
└── disagg/
    ├── best_config_topn.csv
    ├── exp_config.yaml
    ├── pareto.csv
    └── top1/ ... top4/  # each: 11 files; prefill/decode config, K8s YAML, and shell runners
```

File types observed: 4 CSV, 46 YAML, 40 shell scripts, 4 JSON, and 1 PNG. The observed CLI and artifact contract is documented in [TASK-001](task-001-cli-artifacts.md); parser and ranking implementation remain later tasks.

## Reproduction

Run with Docker Desktop available:

```sh
make smoke-configurator
```
