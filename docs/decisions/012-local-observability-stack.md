# ADR-012: Minikube local observability stack

## Context

The portal already exposes Prometheus text at `/metrics` and can export traces
through OTLP/HTTP, but the repository does not yet define a local backend for
those signals. The requested development environment needs Minikube,
Prometheus, Tempo, Grafana, and `opentelemetry-collector-contrib` without touching the
currently selected shared AWS EKS context.

The host is macOS on Apple silicon. AIConfigurator remains a Linux/x86-64
dependency, so the portal image must continue to be built and run as
`linux/amd64` under container emulation.

## Options Considered

### A. Minikube plus small, separate Helm releases (recommended)

Create a dedicated Minikube Docker-driver profile and an `observability`
namespace. Install the standalone Prometheus and Grafana charts, Tempo in
monolithic/local mode, and the OpenTelemetry Collector contrib chart. Configure
the portal to send traces over OTLP/HTTP to the Collector; Prometheus scrapes
the portal's `/metrics` endpoint. Provision Grafana with Prometheus and Tempo
data sources. Use local ephemeral storage and port-forwarding only.

This keeps the requested components explicit, avoids installing the additional
Alertmanager and operator CRDs from a monitoring bundle, and matches the
assignment's deliberately small architecture. The trade-off is a few Helm
values files and no durable retention or HA.

### B. Minikube plus `kube-prometheus-stack`, Tempo, and Collector

Use the Prometheus Operator bundle, which includes Grafana, for discovery, rules,
and dashboards, then add Tempo and the Collector. This offers more
Kubernetes-native monitoring features, but also installs Alertmanager, CRDs,
and substantially more resources than this local demo needs.

### C. Hand-written Kubernetes manifests

Pin images and define Deployments, Services, ConfigMaps, and scrape settings in
the repository directly. This minimizes Helm client state, but makes upgrades,
configuration validation, and chart defaults the project's maintenance burden.

## Decision

**Decision:** choose Option A.

- Install Minikube with Homebrew and use the Docker driver in a dedicated
  profile named `aiconfigurator`.
- Do not change or apply to the existing AWS EKS context. Use explicit
  `minikube -p aiconfigurator` and verify the active context before every apply.
- Deploy Prometheus, Grafana, Tempo, and the Collector into namespace
  `observability` with
  Helm releases and development-only local storage.
- Wire portal traces to the Collector's OTLP/HTTP receiver and Tempo's OTLP
  HTTP ingestion. Keep Prometheus scraping the portal `/metrics` endpoint to
  avoid duplicate metric streams from the app's existing Prometheus reader.
- Provision Grafana's Prometheus and Tempo data sources and verify both from
  the Grafana UI. Do not add a dashboard suite unless needed to demonstrate
  the portal's request, run, queue, and subprocess metrics.
- Generate the local Grafana admin credential into a Kubernetes Secret during
  installation; do not commit credentials or expose Grafana through an
  Ingress or LoadBalancer.
- Keep all access local through `kubectl port-forward`; do not add an Ingress,
  LoadBalancer, authentication, TLS, or production retention configuration.
- Use explicit chart versions resolved at install time and record the resolved
  versions and verification output in the task report.

## Trade-offs and Failure Modes

- Minikube and Docker emulation add local CPU and memory overhead; this is not a
  performance benchmark environment.
- Pod or profile deletion loses local telemetry data.
- A stopped Collector must not make portal runs fail; the portal's telemetry
  exporters are optional and asynchronous.
- Chart upgrades can change values and service names, so rendered manifests and
  rollout status must be checked after installation.
- Grafana provisioning may fail if Prometheus or Tempo service names change;
  datasource health must be checked explicitly.
- The existing AWS EKS context is a safety hazard; accidental context changes
  must be treated as a hard stop rather than silently corrected.

## What Would Change My Mind

Use `kube-prometheus-stack` when Kubernetes service discovery, alerting rules,
Grafana dashboards, or operator-managed ServiceMonitors become requirements.
Use durable volumes or a production collector topology when telemetry must
survive local-cluster deletion, support HA, or serve multiple teams.

## Status

**Accepted — architecture owner approval recorded on 2026-09-05.**
