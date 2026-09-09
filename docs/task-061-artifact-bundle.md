# BONUS-006: One-click artifact bundle

ADR-016 adds `GET /api/runs/{run_id}/artifacts.zip` while preserving the
ephemeral local artifact boundary from ADR-004. A completed run with a non-empty,
fully available artifact set receives a ZIP attachment named
`aiconfigurator-run-{run_id}-artifacts.zip`. The artifact panel keeps its
individual links and adds a **Download all artifacts** action only when the
complete set is available.

Bundle creation uses a temporary file on the existing artifact volume instead
of holding the whole archive in memory or persisting a second run artifact. It
compares the current allow-listed files with the run's completion-time set,
resolves every path through `ArtifactStore`, preserves relative paths such as
`agg/top1/k8s_deploy.yaml`, and deletes the ZIP after the response. Queued,
failed, empty, expired, incomplete, traversal, and escaping-symlink cases fail
closed. Generated scripts remain data and are never executed or transformed.

The ranked table remains metrics-only. The observed AIConfigurator 0.11.0 CSV
contract identifies the source mode/file but does not provide a stable
candidate-to-`topN` artifact identity after global cross-mode ranking. A row
link would therefore guess, which ADR-016 explicitly rejects.

## Verification

- `.venv/bin/python -m pytest tests/test_artifacts.py
  tests/test_artifact_api.py tests/test_pages.py -q` passes all 18 focused
  tests. They cover ZIP contents, duplicate basenames, allow-list enforcement,
  missing files, nonterminal and failed runs, empty sets, archive-generation
  errors, response headers, cleanup, and the UI contract.
- `.venv/bin/python -m compileall -q app tests` passes.
- `make check` passes all 66 tests. The 630 warnings are the existing FastAPI
  `asyncio.iscoroutinefunction` deprecation warnings under local Python 3.14.
- `make k8s-render` produces a non-empty manifest, and `git diff --check`
  passes.
- Playwright MCP browser validation was attempted against an isolated fake
  runner, but the configured MCP browser profile was already locked by another
  `playwright-mcp` process. The MCP returned `Browser is already in use ... use
  --isolated`; no substitute browser tool was used.

This verification does not rerun the real Linux/amd64 AIConfigurator smoke
path. The bundle operates only on output already produced by the existing
worker contract, and the estimates still require representative benchmarks.
