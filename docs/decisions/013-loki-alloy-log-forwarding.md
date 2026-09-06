# ADR-013: Direct Alloy-to-Loki log forwarding

## Context

ADR-012 established a local Minikube observability namespace containing
Prometheus, Grafana, Tempo, and `opentelemetry-collector-contrib`. The next
requirement is to collect Kubernetes container logs with Grafana Alloy and
forward them directly to Loki. This expands the Kubernetes observability
topology, so it must be decided before installation.

The target remains the dedicated local Minikube profile `aiconfigurator`; the
shared AWS EKS context must not be changed. The portal runtime and its existing
metrics and trace paths should remain unchanged. The Portal already emits JSON
logs containing `trace_id` and `span_id` whenever an active recording span is
available, so the log pipeline can preserve those fields without changing the
application.

## Options Considered

### A. Alloy DaemonSet directly writes to single-binary Loki (recommended)

Install Loki in small, single-binary/local mode with ephemeral storage. Run
Alloy as a DaemonSet with the required read-only host mounts and Kubernetes
RBAC, discover pod metadata, read `/var/log/pods` container logs, and use
Alloy's `loki.write` component to push directly to Loki's HTTP push endpoint.
Add Loki as a data source to the existing Grafana release.

This is the smallest topology that satisfies the direct-forwarding request,
does not require application changes, and keeps logs independent from the
OTel trace pipeline. It is appropriate for a local demo, not durable or
high-availability logging.

### B. Alloy forwards logs through the OTel Collector

Have Alloy send OTLP logs to the existing Collector and configure the
Collector to export to Loki. This reuses an existing component, but adds a
network hop and another buffering/failure boundary. It also does not satisfy
the requested direct Alloy-to-Loki path as clearly as Option A.

### C. Production-oriented Loki and Kubernetes observability bundle

Use a distributed Loki topology and a broader Kubernetes discovery/operator
bundle. This provides stronger scaling, retention, and lifecycle primitives,
but adds CRDs, resources, configuration surface, and operational assumptions
that are out of scope for the local assignment environment.

## Decision

**Proposed decision:** choose Option A.

- Install official Grafana Helm charts for Loki and Alloy into the existing
  `observability` namespace, with chart versions pinned at installation time.
- Run Loki in single-binary/local mode with development-only ephemeral storage;
  do not add HA, durable volumes, Ingress, LoadBalancer, TLS, or authentication.
- Run Alloy as a DaemonSet so each Minikube node can read its local container
  log files. Grant only the RBAC and read-only host mounts required for pod
  metadata and `/var/log/pods` (and `/var/log/containers` if required by the
  selected chart/configuration).
- Configure Alloy's `loki.write` to push directly to
  `http://loki.observability.svc.cluster.local/loki/api/v1/push`.
- Parse the Portal JSON log fields `trace_id` and `span_id` in Alloy and attach
  them to each Loki entry as structured metadata. Keep the fields in the JSON
  log line as well so Grafana's Loki derived field can create a reverse link to
  Tempo. Logs without tracing context remain valid and simply omit these
  metadata fields.
- Use bounded Loki labels such as namespace, pod, container, and application;
  do not promote request IDs, trace IDs, span IDs, or other unbounded values to
  labels. Query `trace_id` and `span_id` as structured metadata instead.
- Add Loki as a Grafana data source and keep the Loki and Tempo data sources
  editable in the Grafana UI. Provision the initial correlation defaults while
  allowing UI changes:
  - Tempo `Trace to logs` points to Loki, uses `service.name` -> `service_name`,
    `namespace` -> `namespace`, and `pod` -> `pod`, with a `-2s`/`+2s` time
    shift and trace-ID and span-ID filtering enabled.
  - Loki has a `TraceID` derived field matching the JSON `trace_id` value and
    linking internally to Tempo with `${__value.raw}`.
  Keep the existing Prometheus data source and the Portal's OTel trace path
  unchanged.
- Before every apply, verify the active context is the dedicated `aiconfigurator`
  Minikube context. Verify Alloy targets, Loki readiness, Grafana datasource
  health, and bidirectional trace/log correlation after installation.

## Trade-offs and Failure Modes

- Host-path collection is coupled to Kubernetes/container-runtime log layout;
  rotation or a chart change can require configuration updates.
- A DaemonSet adds local CPU and memory overhead and can duplicate entries if
  multiple file paths are collected for the same container stream.
- Trace and span metadata is available only for application log records emitted
  inside an active recording span; startup, worker bootstrap, and unrelated
  Kubernetes logs may not contain either ID.
- Grafana correlation requires the Tempo trace IDs and the IDs in Loki to be
  identical and requires low-cardinality context labels to match. A mismatch
  silently results in an empty log view or a missing link.
- Loki data is lost when the local pod or Minikube profile is deleted.
- If Loki is unavailable, Alloy retries and may build backpressure or lose
  entries according to its queue and retry limits; application requests must
  not depend on log delivery.
- This topology has no production-grade multi-tenancy, access control, HA, or
  retention policy.

## What Would Change My Mind

Use the Collector path when a single centralized telemetry pipeline, common
processing, or OTLP log ingestion becomes a requirement. Use distributed Loki,
durable storage, and stronger access controls when logs must survive cluster
deletion, support multiple teams, or meet production retention requirements.

## Status

**Proposed — architecture owner approval required before installation.**
