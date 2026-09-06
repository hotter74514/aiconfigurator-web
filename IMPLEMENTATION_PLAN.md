## Stage 1: Define the deterministic cache contract
**Goal**: Record the accepted bounded in-memory cache behavior and canonical cache identity.
**Success Criteria**: Cache keys include normalized request inputs and all invalidation dimensions from ADR-008; only successful normalized results and allow-listed artifacts are eligible.
**Tests**: Add cache unit tests for canonical keys, identity invalidation, and bounded eviction.
**Status**: Complete

## Stage 2: Implement cache-aware worker completion
**Goal**: Reuse successful results and artifacts on a cache hit while preserving the async run lifecycle.
**Success Criteria**: Identical requests avoid a second runner invocation; cached artifacts are downloadable under the new run ID; failures are never cached; cache outcomes are observable.
**Tests**: Add worker regression tests for hit, miss/invalidation, artifact restoration, and failed-run behavior.
**Status**: Complete

## Stage 3: Document and verify the bonus
**Goal**: Record cache behavior, limitations, and verification results.
**Success Criteria**: Roadmap/tasks, architecture notes, README, and the bonus report are updated; focused tests, full checks, and diff review pass.
**Tests**: `pytest`, `make check`, `git diff --check`.
**Status**: Complete
