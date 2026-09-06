# ADR-014: Bounded process-local run history

## Context

The next optional feature is run history. The current Portal keeps run
metadata in memory and keeps generated artifacts in ephemeral per-run
directories with a 24-hour cleanup policy. A history view must not imply that
results or downloads survive a process or Pod restart, and it must not silently
change the accepted artifact lifecycle or single-user boundary.

## Options Considered

### A. Bounded process-local history (recommended)

Retain the most recent completed and failed `StoredRun` records in the existing
`RunManager`, expose a read-only recent-runs API, and render those records in
the existing page. Keep the current per-run artifact directories unchanged.
Apply a fixed entry limit so history cannot grow without bound. A history item
whose artifact directory has expired remains visible with status/results but no
working download links.

This is the smallest reversible option and reuses the current in-memory store,
async lifecycle, and single-service shape. It is useful for a same-process demo
but is intentionally lost on restart and is not shared across replicas.

### B. Local SQLite history

Persist run metadata and normalized results in SQLite, add schema/versioning and
startup recovery, and continue storing artifacts under the current local root.
This survives a process restart when the database volume survives, but adds
storage locking, migration, backup, and container-volume behavior that the
take-home does not otherwise need. With Kubernetes `emptyDir`, it still would
not survive Pod replacement without another storage decision.

### C. Durable database plus object storage

Store history in a shared database and artifacts in object storage with
ownership-aware download URLs. This supports bookmarks, multiple replicas,
retention, and future users, but requires new infrastructure, credentials,
authorization, lifecycle policies, and a superseding artifact-storage decision.

## Proposed Decision

Choose Option A. Add a bounded read-only recent-runs contract over the existing
process-local metadata. Preserve the existing `GET /api/runs/{id}` and artifact
download contracts. Do not retain additional artifact copies, change the
24-hour cleanup policy, or expose history as durable or multi-tenant storage.

The history limit should be configurable for tests and default to a small fixed
value suitable for the demo. Eviction removes only metadata from the history
index; it does not delete an active run directory or alter the artifact store's
TTL cleanup behavior. The UI should label the feature as recent, local history
and show unavailable downloads explicitly.

## Trade-offs and Failure Modes

- Process restart loses the history index, run metadata, cache entries, and
  ephemeral artifacts together.
- A bounded history can evict older records while their artifact directory is
  still present; the existing artifact allow-list remains the security boundary.
- Expired or deleted artifact directories must not make the history endpoint
  fail; download links should be treated as unavailable.
- This feature does not establish authentication, ownership, quotas, or
  multi-user isolation. Those remain governed by the proposed ADR-009.

## What Would Change My Mind

Use SQLite when same-process history is insufficient and a restart-surviving
single-replica store is explicitly required. Use a durable database and object
storage when users need bookmarks, multiple replicas, retention guarantees, or
cross-team access.

## Status

**Accepted — architecture owner approval recorded on 2026-09-06.**
