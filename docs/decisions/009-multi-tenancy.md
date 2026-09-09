# ADR-009: Explicit single-user take-home boundary

## Context

The assignment makes authentication optional, but result visibility and future
quotas still need an explicit boundary. The current Portal keeps run metadata,
recent history, cache entries, and artifacts inside one process and one local
artifact root. It has no trusted identity provider, ownership field, or
authorization middleware. In particular, `GET /api/runs` exposes the recent
terminal history of the process and artifact downloads are addressed by run ID.

Adding a client-supplied user or tenant header would not establish identity:
the caller could choose any value. It could therefore create the appearance of
multi-user isolation without protecting results or queue capacity.

## Options Considered

### A. Keep an explicit single-user demo boundary (recommended)

Treat the deployment as one controlled demo principal, document that all runs
and artifacts are visible within that process, and keep authentication,
ownership, quotas, and tenant isolation out of the take-home implementation.
Describe the future insertion points in the API and metadata model without
accepting untrusted identity headers.

This is the smallest reversible choice and matches the assignment scope. It
does not protect results from other callers, so the deployment must not be
internet-facing or presented as production authorization.

### B. Add a process-local or gateway-injected stub identity

Add an identity abstraction and optionally read a value injected by a trusted
gateway, while leaving authentication and durable ownership out of scope.
This gives the future API a seam, but it adds code and test surface while
remaining unsafe if the service is reachable without a gateway that strips and
replaces the identity. A header supplied directly by a browser is not a valid
security boundary.

### C. Implement authentication and tenant-aware authorization now

Use an OIDC/JWT or API-key integration, persist an owner/tenant identifier with
each run, filter status/history/artifact access, and enforce per-tenant queue
quotas. This is the correct direction for a shared service, but requires an
identity provider or secret lifecycle, durable metadata semantics, access
control tests, and a decision about cache and artifact isolation. It would
substantially expand the take-home and risk distracting from the real
AIConfigurator execution path.

## Proposed Decision

Choose Option A for the take-home.

- Declare the current deployment explicitly single-user and controlled-demo
  only; do not claim that UUID run IDs provide authorization.
- Do not add a client-controlled `user_id`, `tenant_id`, or identity header to
  the current API. A stub identity may be used in documentation to describe
  the single demo principal, but it must not be treated as authentication.
- Keep the existing process-local history, cache, queue, and artifact behavior
  unchanged. The current `GET /api/runs`, run status, and artifact endpoints
  therefore remain globally visible to callers of the same process.
- Before enabling shared or untrusted access, introduce a trusted principal
  boundary and add ownership checks to submission, history, status, and
  artifact download. Store `owner_id`/`tenant_id` with run metadata, scope
  queue quotas and audit events by tenant, and review whether cache entries
  and artifact URLs may be shared.
- Document that authentication, authorization, tenant ownership, quotas, TLS,
  and high availability are intentionally absent from this deployment.

## Alternatives and Trade-offs

Option A minimizes scope and false security claims, but any caller who can
reach the service can inspect the same local history and attempt to access a
known run ID. Option B can prepare a clean integration seam, but is only safe
behind a separately trusted gateway and still does not solve durable ownership
or quota enforcement. Option C provides the strongest boundary, but couples
the take-home to external identity and persistence decisions that are not
required by the assignment.

## What Would Change My Mind

Real shared users, untrusted network access, bookmarked results, multiple
replicas, or tenant-specific capacity guarantees would require Option C (or a
superseding ADR): trusted authentication, per-run ownership checks, tenant
quotas, audit events, and storage/queue access controls before exposing the
service beyond the controlled demo.

## Status

**Accepted — architecture owner approval recorded on 2026-09-06.**
