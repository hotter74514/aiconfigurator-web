# TASK-016: Parse and Rank Results

TASK-016 adds a small adapter around AIConfigurator's structured CSV output. It reads only `agg/best_config_topn.csv` and `disagg/best_config_topn.csv`; it does not scrape the human-readable stdout report or execute generated scripts.

The normalized result keeps the stable portal fields needed for the eventual API/UI: mode, source file, SLA feasibility, predicted tokens/s, tokens/s/GPU, TTFT, TPOT, request latency, GPU count, concurrency, backend, and system. Every original CSV column is retained in `raw` so model- or version-specific deployment fields are not discarded.

Ranking is deterministic and explainable:

1. Candidates meeting both requested TTFT and TPOT targets rank first.
2. Higher predicted `tokens/s` ranks ahead.
3. Lower request latency, lower GPU count, mode, source path, and row order break ties.

The observed disaggregated schema uses `(p)backend`/`(d)backend` and `(p)system`/`(d)system`, while aggregate output uses `backend`/`system`; the adapter handles both forms. Missing columns, malformed numbers, non-finite values, mixed models, and empty results fail with `ResultParseError`.

Verification:

```sh
make check                         # 22 tests passed
python3 -m compileall -q app tests
git diff --check
```

Parsing the recorded Linux/amd64 smoke artifacts produced 8 candidates, all 8 SLA-feasible. The top candidate was disaggregated with 51,726.08 predicted tokens/s, 537.827ms TTFT, and 29.911ms TPOT. TASK-017 will provide the run directory and allow-listed artifact lifecycle; this task deliberately does not choose artifact storage or download behavior.
