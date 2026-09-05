# TASK-017: Artifact Allow-list and Download

TASK-017 connects the accepted ephemeral artifact decision to the worker and API. Each run receives a directory below `AICONFIGURATOR_ARTIFACT_ROOT/{run_id}` and AIConfigurator receives that path through `--save-dir`. The default local root is `.tmp/runs`; a container deployment should set it to `/app/data/runs`.

After a successful subprocess exits, the worker locates the generated aggregate/disaggregate result root, parses ranked results using TASK-016, and records the safe relative artifact names on the completed run. `GET /api/runs/{id}` returns `results` and `artifacts` for completed runs. `GET /api/runs/{id}/artifacts/{path}` serves only these allow-listed files.

The allow-list includes the observed CSV, YAML, JSON, PNG, `bench_run.sh`, and numbered `run_N.sh` files. The service rejects unknown filenames, `.`/`..` path components, backslashes, missing files, symlink escapes, incomplete runs, and paths outside the run directory. It never executes generated scripts. UUID-named run directories older than 24 hours are removed during service startup; active runs are not swept during submission.

Verification:

```sh
make check                         # 28 tests passed
python3 -m compileall -q app tests
git diff --check
```

The real verification used the existing `aiconfigurator-web:local` image with `linux/amd64`, mounted the current app and artifact volume, and submitted `Qwen/Qwen3-32B-FP8` on `h200_sxm` with 32 GPUs and TTFT/TPOT `2000/30`:

```text
status=completed
exit_code=0
duration_ms=10411
results=8
artifacts=95
first_artifact=.../agg/best_config_topn.csv (1406 bytes)
```

Artifact loss on process/pod restart remains an explicit take-home limitation; durable storage is a future production evolution.
