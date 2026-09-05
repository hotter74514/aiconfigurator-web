# TASK-020: Plain HTML/Jinja2 Form

TASK-020 adds the first browser entry point at `/`. It uses FastAPI's Jinja2 integration and a single server-rendered template; no frontend framework or build pipeline is introduced.

The form exposes the five assignment inputs:

- model
- GPU system/type
- total GPU count
- TTFT target in milliseconds
- TPOT target in milliseconds

Inputs have browser-level required/minimum validation and supported smoke-test defaults. The page displays the estimate warning before submission. A small inline bridge converts the form values to JSON and submits them to `POST /api/runs`, then displays the queued run ID or a safe API error. Polling, loading transitions, ranked-result rendering, and artifact links remain TASK-021/TASK-022.

Verification:

```sh
.venv/bin/python -m pip install -e '.[test]'
make check                         # 30 tests passed
python3 -m compileall -q app tests
git diff --check
```

The page deliberately remains useful without a JavaScript framework and keeps the server-side API contract as the source of truth. The inline submit bridge is the smallest browser integration needed before adding polling.
