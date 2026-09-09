# ADR-016: One-click artifact bundle and ranked download links

## Context

The Portal already exposes each allow-listed artifact through
`GET /api/runs/{run_id}/artifacts/{artifact_name}`. A real AIConfigurator run
can produce dozens of files, so asking users to download them one by one is
slow and browser-dependent. The UI also shows ranked configurations, but the
current `RankedResult` contract contains only metrics and the source CSV path;
it does not contain a validated reference to the artifact generated for a
specific ranked row.

The existing artifact decision is intentionally ephemeral and local
(ADR-004). Any extension must preserve that boundary, the allow-list, and the
rule that generated scripts are downloadable data only and are never executed
by the Portal.

## Decision points

There are two related but separate decisions:

1. How to provide one-click access to all artifacts for a completed run.
2. Whether a ranked row can safely link to one artifact without guessing from
   its global rank or from an implementation-specific directory name.

## Options considered

### A. Client-side multi-download

Add a button that loops over the existing artifact URLs and triggers one
browser download per file.

- Smallest server change.
- Browser popup/download protections can block or serialize the requests.
- The user receives many files with no single retryable operation.
- It does not solve candidate-to-artifact identity; a row link would still
  require guessing.

### B. On-demand server-generated ZIP (recommended)

Add a bundle endpoint for a completed run. The server enumerates the existing
allow-listed relative paths, validates each path with `ArtifactStore`, and
creates a ZIP on demand. The archive preserves relative paths such as
`agg/top1/agg_config.yaml` so same-named files cannot overwrite one another.
The response is an attachment; the ZIP is not persisted as a second durable
artifact.

- One browser action and one retryable response.
- Reuses the existing artifact security boundary and 24-hour lifecycle.
- Adds bounded CPU and transient memory/disk work at download time.
- A run that has expired or has no complete artifact set cannot produce a
  misleading partial archive.

### C. Persist a ZIP when the run completes

Create and store the archive during worker completion, then serve it like any
other artifact.

- Fast and predictable download latency after completion.
- Duplicates storage, complicates cleanup, and increases completion work.
- Makes the bundle format part of the persisted artifact contract even though
  artifacts are otherwise ephemeral.
- Still does not provide a safe ranked-row mapping by itself.

For ranked-row links, the alternatives are:

- **Infer a path from rank/mode** (for example, `mode/top{rank}`): rejected
  because the current normalized rank is global across modes and the observed
  directory convention is not a formally validated candidate identity.
- **Add an explicit candidate artifact reference** to the normalized result
  contract: preferred only when the AIConfigurator output proves a stable
  candidate-to-directory mapping. The reference must be relative, allow-listed,
  and validated before it reaches the API response.
- **Keep the ranked table metrics-only and use the artifact panel**: the safe
  fallback when no stable mapping exists. Users can still download a complete
  bundle or individual files without presenting a misleading row link.

## Proposed decision

1. Implement an on-demand ZIP endpoint for completed runs, while retaining the
   existing individual-file endpoint. The endpoint must:

   - use the run's existing allow-listed artifact set;
   - preserve relative paths inside the ZIP;
   - reject missing, expired, failed, or incomplete runs rather than returning
     a partial archive;
   - enforce the same traversal, symlink, and filename checks as individual
     downloads;
   - avoid executing or transforming generated scripts; and
   - avoid durable bundle persistence, keeping ADR-004's ephemeral lifecycle.

2. Add a clearly labelled **Download all artifacts** action to the artifact
   panel. The control is disabled or hidden when the run has no available
   artifacts, and the UI continues to expose individual links.

3. Add a **Download artifact** column to the ranked table only after the
   result contract contains an explicit, validated candidate artifact
   reference. Do not derive a link from the displayed rank. If the
   AIConfigurator contract cannot guarantee that mapping, keep the table
   metrics-only and direct users to the artifact panel/bundle instead.

4. Keep the endpoint and result-contract changes covered by tests for archive
   contents, path safety, incomplete/expired runs, duplicate basenames,
   candidate references, and the empty/unavailable UI states.

## Trade-offs and failure modes

- ZIP generation consumes CPU and transient memory or temporary-file space;
  implementation should use a bounded approach and report a clear error when
  the archive cannot be created.
- The bundle is a snapshot at request time. Files disappearing during
  packaging must fail the request rather than silently producing a partial
  archive.
- Relative paths are intentionally retained to avoid collisions between
  `agg/` and `disagg/` files.
- The bundle remains unavailable after the existing 24-hour retention window
  or a process/pod restart, consistent with ADR-004.
- A per-row link is more useful than a global link only if its identity is
  trustworthy; a guessed link would be worse than no link because it could
  download a different candidate's configuration.

## What would change this decision

- Archive sizes large enough to require streaming or dedicated temporary
  storage would justify a follow-up implementation ADR.
- Bookmarked results, multi-replica serving, or retention beyond the pod
  lifecycle would require revisiting ADR-004 and likely adopting object
  storage plus metadata.
- A documented AIConfigurator output contract that gives every ranked row a
  stable artifact directory would justify enabling the ranked-table download
  column.

## Status

**Accepted — architecture owner approval recorded on 2026-09-08.**
