# Repository Guidelines

## Mission

Build the take-home assignment: a small, working Serving Configuration Portal over AIConfigurator. Optimize for scope discipline, explainable trade-offs, failure handling, and a demo that works—not visual polish or speculative infrastructure.

## Read First

Before every task, read `docs/assignment-brief.md`, `ARCHITECTURE.md`, the relevant file under `docs/decisions/`, `ROADMAP.md`, and `TASKS.md`. Inspect the relevant code and `git status`. Work on exactly one task at a time in priority order.

## Architecture-Owner Gate

Codex MUST NOT silently make architecture decisions. For any change involving execution model, API synchrony, artifact persistence, concurrency, caching, CLI vs SDK, Kubernetes lifecycle, probes, observability, or multi-tenancy:

1. Identify the decision.
2. List 2–3 viable alternatives.
3. Explain trade-offs and failure modes.
4. Recommend the smallest defensible option.
5. Record it in `docs/decisions/` and STOP until the user approves it.

After an ADR is marked **Accepted** by the user, Builder mode may implement it. Builder mode must not change an accepted architecture; create a new ADR when evidence requires reconsideration.

## Assignment Constraints

- AIConfigurator is an external dependency; never modify it.
- Its wheels are Linux x86-64 only. On macOS, use Docker with `linux/amd64`; never attempt a native install.
- Complete the real AIConfigurator smoke test before building the portal around it.
- Use a deliberately small architecture: one web/API service, a bounded local worker, subprocess isolation, and ephemeral local artifacts unless an accepted ADR says otherwise.
- Finish all must-haves before optional visualization, caching, history, or multi-user work.
- Always present results as estimates that require real benchmark validation.

## Two-Mode Workflow

**Architect mode** reads the assignment and repository, proposes alternatives, writes/updates the relevant ADR, and does not edit application code. **Builder mode** reads only accepted decisions, implements the current task, adds tests, runs checks, updates docs, and reports risks. Use `prompts/architect.md` and `prompts/builder.md` respectively.

## Quality and Safety

Prefer focused modules, explicit contracts, and reversible changes. Never fake AIConfigurator output in the production path. Test doubles must be isolated and documented. Ask before production deployment, credentials, production data, IAM, destructive operations, or any new infrastructure not covered by an accepted ADR.

## Git

Use feature branches (`feat/run-api`, `feat/artifact-download`) and keep an inspectable, incremental history. Create focused Conventional Commits at approved milestones (`feat: add asynchronous run API`, `infra: add kubernetes deployment`, `docs: record design decisions`); do not squash the assignment into one commit or commit directly to `main` unless explicitly requested.

## Completion Gate

Before handoff, run applicable formatter, linter, type checker, unit/integration tests, container/Kubernetes checks, `make check`, and `git diff --check`. Exercise the demo path: submit a run, poll status, inspect ranked results, download an artifact, and show probes/metrics. Report exact commands, results, changed files, assumptions, and known limitations.
