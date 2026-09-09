# TASK-021: Status Polling and Error States

TASK-021 extends the plain form with a bounded client polling loop. After `POST /api/runs` returns a run ID, the page requests `GET /api/runs/{id}` every two seconds using recursive `setTimeout`; this avoids overlapping status requests that an unrestricted `setInterval` could create.

The status region exposes accessible loading state via `aria-busy` and handles:

- `queued` and `running`: keep the submit button disabled and show progress text.
- `completed`: stop polling and show that results are ready; ranked rows remain TASK-022.
- `failed`: stop polling and show the API's safe error detail.
- HTTP, malformed JSON, and network errors: stop polling and show a user-facing error.

Submitting again cancels the previous timer and uses a generation token so an older response cannot overwrite the current run. No SSE/WebSocket, frontend framework, result table, or artifact link was added.

Verification:

```sh
make check                         # 30 tests passed
python3 -m compileall -q app tests
git diff --check
```

Playwright MCP verification loaded `/`, clicked the submit button, observed `POST /api/runs` with `202 Accepted`, and observed `GET /api/runs/{id}` with `200 OK`. Against the local host without an AIConfigurator runtime, the real request reached the failed state with `AIConfigurator process could not start` and no console errors. A route-intercepted browser scenario then returned `queued` followed by `completed`; the page made two status requests, waited for the two-second interval, stopped polling, and displayed `Results are ready.` The next UI task will consume the completed response and render ranked results.
