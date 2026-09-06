## Stage 1: Approve the Loki and Alloy topology
**Goal**: Approve ADR-013 for direct Alloy-to-Loki forwarding and trace/log correlation in local Minikube.
**Success Criteria**: ADR-013 is marked Accepted by the architecture owner, including structured `trace_id`/`span_id` metadata and editable Grafana Tempo/Loki correlation settings.
**Tests**: Review the selected topology, failure modes, metadata cardinality, and target Kubernetes context.
**Status**: In Progress

## Stage 2: Install and configure Loki and Alloy
**Goal**: Install pinned Grafana Helm releases in `observability` and configure Alloy to read Kubernetes container logs, extract `trace_id`/`span_id`, and write directly to Loki.
**Success Criteria**: Loki is Ready; Alloy DaemonSet is Ready; Alloy has healthy write targets; structured trace/span metadata is present; no AWS EKS resources are changed.
**Tests**: Helm render/lint, rollout status, pod readiness, and active-context safety check.
**Status**: Not Started

## Stage 3: Integrate and exercise Grafana log search
**Goal**: Add Loki to Grafana and prove bidirectional trace/log correlation in the UI.
**Success Criteria**: Grafana reports healthy Loki and Tempo data sources; a Tempo span opens matching Loki logs; a Loki log opens the matching Tempo trace; span filtering is verified where a span ID is present.
**Tests**: Generate one real traced Portal request, query its log through Loki/Grafana, verify `trace_id`/`span_id` metadata, and verify labels remain bounded.
**Status**: Not Started

## Stage 4: Document, test, commit, and push
**Goal**: Record setup and verification commands, run repository checks, and publish the approved infrastructure changes.
**Success Criteria**: Documentation is complete, checks pass, a focused Conventional Commit is pushed, and the working tree contains only intentional user changes.
**Tests**: `make check`, applicable Kubernetes checks, `git diff --check`, and review of the commit summary.
**Status**: Not Started
