# ADR-004: Ephemeral local artifacts

## Context

AIConfigurator produces a directory of manifests, CSVs, and plots. The assignment needs downloadable artifacts without requiring external infrastructure.

## Options Considered

- Container filesystem: simplest, but lifecycle is unclear and data is lost on restart.
- `emptyDir`/local application volume: explicit per-run directories and easy serving in a single-pod demo.
- PVC or object storage: durable, but introduces infrastructure and credentials beyond the assignment scope.

## Proposed Decision

Store each run under `/app/data/runs/{run_id}/` with request metadata and allow-listed artifacts. Apply a 24-hour TTL cleanup policy. Clearly warn that pod replacement removes artifacts.

## What Would Change My Mind

Use object storage plus a metadata database when users need bookmarked results, multi-replica access, or retention beyond the pod lifecycle.

## Status

**Proposed — architecture owner approval required.**
