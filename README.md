# aiconfigurator-web

Serving Configuration Portal take-home assignment: a self-service web experience over NVIDIA Dynamo AIConfigurator.

## Project workflow

Start with [`docs/assignment-brief.md`](docs/assignment-brief.md), then read [`AGENTS.md`](AGENTS.md), [`ARCHITECTURE.md`](ARCHITECTURE.md), [`ROADMAP.md`](ROADMAP.md), and [`TASKS.md`](TASKS.md). Codex prompts are in [`prompts/`](prompts/), and the interview acceptance path is [`docs/demo-checklist.md`](docs/demo-checklist.md).

Use two deliberate Codex modes: [`prompts/architect.md`](prompts/architect.md) proposes and records ADRs without coding; [`prompts/builder.md`](prompts/builder.md) implements only decisions marked **Accepted**. Keep the commit history incremental and reviewable; do not squash the submission into one commit.

TASK-000 now provides and verifies a minimal Linux/amd64 AIConfigurator image and smoke runner. The successful run, captured commands, runtimes, and artifact structure are documented in [`docs/task-000-smoke-test.md`](docs/task-000-smoke-test.md). The portal stack remains intentionally unselected.

## Quick start

```sh
codex
make check
```

Use Docker on macOS; AIConfigurator's published wheels are not supported natively on macOS or Windows. Do not commit credentials or local environment files.

Run the TASK-000 smoke test after Docker Desktop access is available:

```sh
make smoke-configurator
```

The runner stores disposable evidence under `.tmp/task-000/` and does not add application code.

## Design Decisions

Document the execution model, asynchronous API, artifact lifecycle, concurrency, caching, CLI vs SDK choice, probes, observability, multi-tenancy, and output-trust warning in [`docs/DESIGN_DECISIONS.md`](docs/DESIGN_DECISIONS.md). Explain both the selected approach and the alternative rejected. Each detailed ADR must record trade-offs, failure modes, and what would change the decision.

## Known Limitations

The framework, package manager, API, storage, Kubernetes manifests, and application code are not implemented yet. Authentication, TLS, secrets management, and high availability are intentionally out of scope for the take-home; the eventual submission must state what would be added for production.
