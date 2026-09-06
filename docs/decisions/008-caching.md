# ADR-008: Defer result caching

## Context

Default AIConfigurator results are deterministic for identical inputs, but caching adds invalidation and artifact lifecycle concerns.

## Decision

Implement a bounded in-memory LRU cache inside the existing Portal service. Cache
only successful normalized results and the allow-listed artifact bytes needed to
serve a completed run. On a cache hit, keep the existing asynchronous queue and
status contract, restore the cached artifacts into the new ephemeral run
directory, and complete the new run without invoking AIConfigurator.

Key entries by a canonical request plus AIConfigurator version, portal result
model version, and runner image identity/digest. Changing any key component
automatically misses older entries. Keep the cache bounded by entry count and
discard it on process restart; do not introduce a shared cache or persistent
storage for this take-home.

## Alternatives and Trade-offs

Immediate caching reduces repeated CPU work but can return stale estimates. Deferring it keeps the take-home smaller and makes determinism a documented future optimization.

## What Would Change My Mind

Repeated identical requests or measured CPU saturation that materially harms user experience would justify a cache.

## Status

**Accepted — architecture owner approval recorded on 2026-09-06.**
