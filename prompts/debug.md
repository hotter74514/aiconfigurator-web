# Debug a Failure

Investigate a failing command or test in `aiconfigurator-web`.

Read `docs/assignment-brief.md`, `AGENTS.md`, the relevant task, and the affected implementation and tests. Reproduce the failure with the narrowest available command, capture the exact error, identify whether it is environmental or caused by the change, and make the smallest safe fix. For AIConfigurator failures, first confirm the Linux x86-64 container, image architecture, support-matrix entry, and exact CLI/SDK inputs.

After each fix, rerun the reproducing check and then the broader relevant checks, including container or Kubernetes checks when applicable. Add or update a regression test when the failure represents a missing behavior. Do not hide failures, weaken assertions, disable checks, or make unrelated refactors.

If three materially different fixes fail, stop and report the attempts, exact errors, likely root cause, and two or three alternative approaches for the user to choose from.
