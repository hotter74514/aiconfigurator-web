# Review a Change

Review the current working tree or specified diff for `aiconfigurator-web`.

Read `docs/assignment-brief.md`, `AGENTS.md`, `ARCHITECTURE.md`, `docs/DESIGN_DECISIONS.md`, and the relevant task before reviewing. Prioritize correctness, broken behavior, security/privacy, accessibility, data loss, API compatibility, missing tests, documentation drift, and assignment scope. Treat formatting issues as secondary unless they hide a functional problem.

Check specifically that the review covers the real AIConfigurator invocation, async status behavior, artifact lifecycle, CPU contention, cache determinism, CLI/SDK choice, probes, metrics, multi-user visibility, estimate warnings, containerization, Kubernetes resources, and the live-demo path.

For every finding, provide:

- Severity: blocking, important, or minor.
- File and line.
- Concrete explanation of the failure or risk.
- A minimal recommended fix.

Do not modify files during review unless explicitly requested. End with checks run, limitations, and a clear statement when no findings remain.
