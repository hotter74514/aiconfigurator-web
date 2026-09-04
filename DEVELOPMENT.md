# Development Workflow

## Start Here

Read `docs/assignment-brief.md`, `AGENTS.md`, `ARCHITECTURE.md`, `docs/DESIGN_DECISIONS.md`, `ROADMAP.md`, and `TASKS.md`. Confirm the working tree and local tools:

```sh
git status
codex --version
docker --version
```

Run Codex from the repository root:

```sh
codex
```

Use `prompts/architect.md` when a task involves an architecture decision; it must stop after producing a Proposed ADR. Use `prompts/builder.md` only after the architecture owner marks the ADR Accepted. `prompts/plan.md` is for non-architecture planning, `prompts/review.md` is for focused diff review, and `prompts/debug.md` is for failures.

## Feasibility First

Complete `TASK-000` and `TASK-001` before building the UI or API. Build/run AIConfigurator in a Linux x86-64 container and verify the chosen model/GPU/backend against the support matrix. On Apple Silicon, include `--platform linux/amd64` for the relevant Docker build/run commands.

## Validation Commands

```sh
make help
make check
make smoke-configurator  # available after Dockerfile/runtime setup
make ci                  # includes the app build once configured
git diff --check
```

The current scaffold has no application package, build system, or test framework, so `make check` validates the harness and reports that app checks are pending. Once the stack is selected, update the Makefile and README with exact install, dev-server, build, format, lint, typecheck, unit, integration, and Kubernetes commands.

## Task Loop

Work from one `TASKS.md` item at a time. Tie implementation and tests to acceptance criteria, record design trade-offs in `docs/DESIGN_DECISIONS.md` and `docs/decisions/`, update `ROADMAP.md`, create focused Conventional Commits at approved milestones, and verify the demo path in `docs/demo-checklist.md` before handoff.

## Safety Boundary

Local repository edits, container builds, tests, and local-cluster operations are allowed. Production deployment, production data, secret handling, IAM changes, and destructive operations require explicit user review.
