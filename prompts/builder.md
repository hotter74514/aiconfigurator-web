# Builder Mode

You are implementing an approved task for the Serving Configuration Portal. Read `docs/assignment-brief.md`, `AGENTS.md`, `ARCHITECTURE.md`, `TASKS.md`, and every relevant ADR. Confirm the ADR status is **Accepted** before writing code. If a required decision is still Proposed or the implementation needs a new decision, stop and switch to Architect mode.

Implement only the approved scope. Prefer one small service, bounded local workers, subprocess isolation, plain HTML, and ephemeral artifacts unless an accepted ADR says otherwise. Do not add Kafka, Redis, PostgreSQL, S3/MinIO, a durable queue, or optional UI features without an accepted ADR and explicit scope justification.

Before finishing:

1. Add meaningful unit/integration/regression tests.
2. Run formatter, linter, type checker, tests, container checks, and `make check` as applicable.
3. Exercise submit → poll → ranked results → artifact download.
4. Verify probes, metrics, structured logs, timeout, backpressure, and failure behavior when applicable.
5. Update `TASKS.md`, `ROADMAP.md`, README, and limitations.
6. Review `git diff` and create one focused Conventional Commit for the approved milestone.

Report changed files, exact checks and results, assumptions, trade-offs implemented, and remaining risks. Never claim the real AIConfigurator path works unless it was actually executed.
