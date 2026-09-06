# BONUS-003 Deterministic Result Cache

## Scope

The Portal now caches successful normalized AIConfigurator output within one
process. A cache entry contains the `RankedResults` response and only the
allow-listed artifact bytes needed for download. The cache is a bounded LRU with
16 entries by default and is discarded on process restart.

Cache keys are SHA-256 digests of a canonical JSON payload containing:

- normalized run request fields;
- AIConfigurator version;
- Portal result-model version; and
- runner image identity/digest.

Changing any of these values produces a miss. The default runner identity is
`local-unversioned`; deployments should set `AICONFIGURATOR_RUNNER_IMAGE_DIGEST`
to the actual image digest when release-level invalidation is required.

## Runtime behavior

Cache hits still enter the existing bounded async queue and return a new run ID.
The worker restores cached artifacts into that run's ephemeral directory,
marks the run completed, and does not invoke AIConfigurator. Cache misses run
the normal subprocess path; only successful parsing and artifact snapshotting
populate the cache. Failures, timeouts, cancellations, and parse errors are
never cached.

Cache hits and misses are recorded as bounded `portal.cache.outcomes` metrics
and `run_cache_hit` structured log events. The cache deliberately does not
provide cross-replica deduplication, persistence, TTL retention, or request
coalescing.

## Verification

```sh
uv run pytest tests/test_cache.py tests/test_worker.py
uv run pytest
make check
make container-check
git diff --check
```

The focused cache/worker tests pass, including canonical-key invalidation,
bounded LRU eviction, artifact restoration under a new run ID, and the rule
that failed runs are not cached. The full suite passes with 53 tests, project
checks pass, and `make container-check` validates the Linux/amd64 runtime image
and probes. The real AIConfigurator path remains available on the normal miss
path; cache results remain estimates and require representative benchmark
validation.
