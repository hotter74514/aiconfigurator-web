# BONUS-004 Bounded Process-Local Run History

## Scope

The Portal retains the most recent completed and failed runs in a bounded,
process-local history index. `GET /api/runs` returns those records newest-first,
including the original request, terminal status, result data, failure detail,
and only currently available allow-listed artifact links.

The existing `GET /api/runs/{id}` and artifact download contracts remain
unchanged. History eviction removes only in-memory run metadata; it does not
delete a run directory or change the accepted 24-hour artifact cleanup policy.
The page labels the feature as recent local history, can reload completed
results, and reports expired artifact links as unavailable.

## Trade-offs

The default history limit is 20 terminal records and can be overridden through
the `RunManager(history_size=...)` constructor for tests or embedding. The
history is intentionally not durable, shared between replicas, authenticated,
or multi-tenant. Process or Pod restart clears the index along with existing
in-memory run state and ephemeral artifacts.

## Verification

```sh
uv run pytest tests/test_runs_api.py tests/test_worker.py tests/test_pages.py
sed -n '/<script>/,/<\/script>/p' templates/form.html | sed '1d;$d' | node --check
uv run pytest
make check
make container-check
uv run python -m compileall -q app tests
git diff --check
```

The focused history/API/worker/page tests cover newest-first ordering, bounded
eviction without artifact deletion, active-run exclusion, empty history,
expired artifacts, and the UI contract. The full suite and container checks
must still be run before the milestone commit.
