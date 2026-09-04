# ADR-009: Explicit single-user take-home boundary

## Context

The assignment makes authentication optional, but result visibility and future quotas still need an explicit boundary.

## Proposed Decision

Use a stub identity and document that the single deployment is not multi-tenant. Do not expose this design as production authorization. Future per-user/team ownership, access checks, and quotas belong in the API and metadata store, before object storage or queue access.

## Alternatives and Trade-offs

Adding authentication now expands scope and creates false confidence. Ignoring the issue entirely makes the security boundary unclear.

## What Would Change My Mind

Real users, shared environments, or persisted results would require authentication, ownership checks, and per-user/team quotas.

## Status

**Proposed — architecture owner approval required.**
