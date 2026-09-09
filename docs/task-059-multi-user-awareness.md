# BONUS-005: Multi-user awareness

## Scope

ADR-009 is accepted with the smallest defensible take-home boundary: the
Portal is a single-user, controlled-demo deployment. The current process-local
history, run status, artifact download, queue, and cache behavior remains
unchanged.

The Portal does not accept client-supplied `user_id`, `tenant_id`, or identity
headers. A UUID run ID is an identifier, not an authorization mechanism. Any
caller that can reach the current service may access the same process-local
history and a run addressed by a known ID.

## Future extension point

Before shared or untrusted access, add a trusted principal boundary, persist
owner or tenant metadata, enforce ownership on submission/history/status/artifact
operations, scope queue quotas and audit events by tenant, and review cache and
artifact sharing semantics.

## Verification

- `docs/decisions/009-multi-tenancy.md` records the accepted alternatives,
  trade-offs, and change triggers.
- `docs/DESIGN_DECISIONS.md`, `README.md`, `TASKS.md`, and `ROADMAP.md` identify
  the accepted single-user boundary and its limitations.
- `git diff --check` passes.
- No application code, dependency, API contract, or infrastructure was added
  for this milestone.
