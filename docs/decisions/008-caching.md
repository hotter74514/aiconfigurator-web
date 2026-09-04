# ADR-008: Defer result caching

## Context

Default AIConfigurator results are deterministic for identical inputs, but caching adds invalidation and artifact lifecycle concerns.

## Proposed Decision

Do not implement caching before the must-have path. If added later, key entries by a canonical request plus AIConfigurator version, data/model version, and runner image digest. Invalidate on any of those changes.

## Alternatives and Trade-offs

Immediate caching reduces repeated CPU work but can return stale estimates. Deferring it keeps the take-home smaller and makes determinism a documented future optimization.

## What Would Change My Mind

Repeated identical requests or measured CPU saturation that materially harms user experience would justify a cache.

## Status

**Proposed — architecture owner approval required.**
