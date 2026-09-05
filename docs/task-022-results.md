# TASK-022: Ranked Results and Estimate Warning

TASK-022 connects the completed `GET /api/runs/{id}` response to the existing plain HTML/Jinja2 page. Completed runs now render the API's deterministic candidate order in an accessible table with rank, mode, backend/system, GPU count, predicted throughput, request latency, TTFT, TPOT, and SLA outcome.

The page also renders allow-listed artifact names as download links under the same run ID. Artifact path segments are encoded before building the URL, and all response text is inserted with DOM text nodes rather than HTML interpolation. Empty candidates, invalid artifact paths, and malformed result data become the existing user-facing error state.

The estimate warning appears both at the top of the form and beside the ranked results: AIConfigurator predictions must be validated with representative real benchmarks before deployment. This is an interpretation warning only; the portal does not alter ranking or claim production capacity.

Verification:

```sh
make check                         # 30 tests passed
python3 -m compileall -q app tests
git diff --check
```

Playwright MCP verified a completed response with two candidates and two artifacts. It observed the ranked table headings, `Meets SLA`/`Outside SLA` labels, correctly encoded artifact links, two visible estimate warnings, and no browser console errors. No frontend framework or optional visualization was added.
