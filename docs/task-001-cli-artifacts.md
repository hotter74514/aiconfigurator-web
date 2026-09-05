# TASK-001: CLI Output and Artifact Contract

## Observed Run

This contract is based on the successful `linux/amd64` run recorded by TASK-000:

```text
aiconfigurator cli default \
  --model Qwen/Qwen3-32B-FP8 \
  --total-gpus 32 \
  --system h200_sxm \
  --save-dir /tmp/aiconfigurator-run
```

Image: `aiconfigurator==0.11.0`, `plotext==5.3.2`. The invocation applies default workload/SLA values of `ISL=4000`, `OSL=1000`, `TTFT=2000ms`, and `TPOT=30ms`; a future API must pass these explicitly rather than rely on CLI defaults.

## CLI Output

Successful stdout contains timestamped diagnostic lines followed by a human-readable report:

1. Effective model, system, backend, database mode, and SLA parameters.
2. Experiment progress and result counts (`agg` and `disagg`).
3. `AIConfigurator Final Results` and the selected experiment.
4. Overall throughput, per-GPU/per-user throughput, request rate, TTFT, TPOT, and request latency.
5. Pareto text plot, deployment notes, and ranked `agg`/`disagg` tables.
6. Completion timing (`All experiments completed ...`).

Successful stderr was empty. stdout is useful for logs and a raw result transcript, but its formatting should not be the portal's primary parsing contract.

## Artifact Layout

The observed root is named with input parameters and an opaque suffix:

```text
artifacts/Qwen/<model>_<system>_<backend>_isl4000_osl1000_ttft2000_tpot30_<id>/
├── pareto_frontier.png
├── agg/
│   ├── best_config_topn.csv       # 4 rows, 43 columns in this run
│   ├── pareto.csv                 # 42 rows, 43 columns in this run
│   ├── exp_config.yaml            # effective experiment configuration
│   └── top1/ ... top4/
└── disagg/
    ├── best_config_topn.csv       # 4 rows, 62 columns in this run
    ├── pareto.csv                 # 17 rows, 62 columns in this run
    ├── exp_config.yaml
    └── top1/ ... top4/
```

Each aggregate top directory contains engine config, generator config, Kubernetes deployment/benchmark YAML, `per_ops_source.json`, `sflow.yaml`, `bench_run.sh`, and `run_0.sh` through `run_3.sh`. Each disaggregated top directory contains the equivalent files plus separate `prefill_config.yaml` and `decode_config.yaml`.

The CSVs are the primary structured result candidates. Aggregate rows include throughput, latency, batching, GPU parallelism, quantization, backend, version, and system fields. Disaggregated rows additionally include prefill/decode workers, batch sizes, parallelism, and per-stage fields. Preserve raw CSV/YAML/JSON files; do not infer a universal schema from one model or version.

## Integration Constraints

- Treat the generated root suffix as opaque; it is not the portal run ID.
- Parse CSVs from the selected `agg`/`disagg` directories instead of scraping pretty tables.
- Serve artifacts only relative to a run directory and never execute generated shell scripts.
- Keep the original files for download and debugging; normalize a separate result model later.
- Version/package and input metadata must travel with normalized results because output fields can change.

The parser and ranker are implemented in `TASK-016`; artifact storage and serving remain `TASK-017`.
