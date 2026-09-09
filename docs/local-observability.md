# Local observability stack

The repository includes a local Minikube stack for the portal:

- Prometheus `29.27.1` / Prometheus `v3.14.0`
- Tempo `1.24.4` / Tempo `2.9.0`
- Grafana `10.5.15` / Grafana `12.3.1`
- OpenTelemetry Collector Helm chart `0.172.1` / contrib image `0.159.0`
- Loki `7.3.0` / Loki image `3.6.11`
- Alloy `1.12.1` / Alloy `v1.19.2`

## Start or recreate the local cluster

The commands below use a dedicated profile. Confirm the context before applying
anything; the repository must never be applied to a shared EKS context.

```sh
brew install minikube
minikube start -p aiconfigurator \
  --driver=docker \
  --container-runtime=containerd \
  --cpus=4 \
  --memory=6144 \
  --disk-size=20g
kubectl config use-context aiconfigurator
kubectl config current-context
```

## Install observability components

```sh
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm repo add grafana https://grafana.github.io/helm-charts
helm repo add open-telemetry https://open-telemetry.github.io/opentelemetry-helm-charts
helm repo update

kubectl create namespace observability --dry-run=client -o yaml | kubectl apply -f -
GRAFANA_PASSWORD=$(openssl rand -hex 16)
kubectl -n observability create secret generic grafana-admin \
  --from-literal=admin-user=admin \
  --from-literal=admin-password="$GRAFANA_PASSWORD" \
  --dry-run=client -o yaml | kubectl apply -f -

helm upgrade --install prometheus prometheus-community/prometheus \
  --version 29.27.1 --namespace observability \
  --values k8s/observability/prometheus-values.yaml --wait
helm upgrade --install tempo grafana/tempo \
  --version 1.24.4 --namespace observability \
  --values k8s/observability/tempo-values.yaml --wait
helm upgrade --install otel-collector open-telemetry/opentelemetry-collector \
  --version 0.172.1 --namespace observability \
  --values k8s/observability/collector-values.yaml --wait
helm upgrade --install loki grafana/loki \
  --version 7.3.0 --namespace observability \
  --values k8s/observability/loki-values.yaml --wait
helm upgrade --install alloy grafana/alloy \
  --version 1.12.1 --namespace observability \
  --values k8s/observability/alloy-values.yaml --wait
helm upgrade --install grafana grafana/grafana \
  --version 10.5.15 --namespace observability \
  --values k8s/observability/grafana-values.yaml --wait
```

## Build and deploy the portal

AIConfigurator is Linux/x86-64 only. On Apple silicon the image remains
`linux/amd64`; `make minikube-load-image` imports that image directly into the
Minikube containerd store because the Minikube node itself is arm64.

```sh
make minikube-load-image
kubectl apply -k k8s
kubectl rollout status deployment/aiconfigurator-portal --timeout=180s
```

The portal sends OTLP/HTTP traces to `otel-collector` and Prometheus scrapes
the portal's `/metrics` endpoint. Alloy reads Pod logs from the Minikube node
and writes directly to Loki. Portal `trace_id` and `span_id` fields are copied
to Loki structured metadata. Grafana is provisioned with Prometheus, Tempo,
and Loki; Tempo trace-to-logs and Loki TraceID derived-field correlation are
editable from the Grafana UI.

Prometheus exemplar storage is enabled with a bounded local limit of 10,000.
The Portal exposes OpenMetrics and attaches the sampled run span's `trace_id`
to the `portal_trace_run_duration_seconds` histogram as exemplar metadata.
Grafana's Prometheus datasource maps the `trace_id` exemplar to the Tempo
datasource, so a completed run's metric point can open its Tempo trace without
turning trace IDs into high-cardinality time-series labels.

Tempo is tuned for the single-node local cluster: liveness uses a TCP check on
port 3200 while `/ready` is reserved for readiness, so temporary query latency
does not restart a healthy process. Readiness allows six consecutive 10-second
checks to fail, and Tempo query concurrency is bounded to four querier queries
and eight search jobs. Tempo requests `250m` CPU/`512Mi` memory and limits at
`1000m` CPU/`1Gi` memory. These are local-demo safeguards, not benchmarked
production capacity numbers.

## Access and verification

Use separate terminals for the port-forwards:

```sh
kubectl port-forward service/aiconfigurator-portal 8000:8000
kubectl port-forward -n observability service/prometheus-server 9090:80
kubectl port-forward -n observability service/grafana 3000:80
kubectl port-forward -n observability service/tempo 3200:3200
kubectl port-forward -n observability service/loki 3100:3100
```

- Portal: <http://127.0.0.1:8000>
- Prometheus: <http://127.0.0.1:9090>
- Grafana: <http://127.0.0.1:3000>, user `admin`, password from
  `kubectl get secret -n observability grafana-admin -o jsonpath='{.data.admin-password}' | base64 --decode`
- Tempo API: <http://127.0.0.1:3200>
- Loki API: <http://127.0.0.1:3100>

Useful checks:

```sh
kubectl wait --for=condition=ready pod --all -n observability --timeout=120s
curl -fsS http://127.0.0.1:8000/live
curl -fsS http://127.0.0.1:8000/ready
curl -fsS 'http://127.0.0.1:9090/api/v1/query?query=up%7Bjob%3D%22aiconfigurator-portal%22%7D'
GRAFANA_PASSWORD=$(kubectl get secret -n observability grafana-admin -o jsonpath='{.data.admin-password}' | base64 --decode)
curl -fsS -u "admin:$GRAFANA_PASSWORD" -X POST \
  http://127.0.0.1:3000/api/datasources/uid/prometheus/health
curl -fsS -u "admin:$GRAFANA_PASSWORD" -X POST \
  http://127.0.0.1:3000/api/datasources/uid/tempo/health
curl -fsS -u "admin:$GRAFANA_PASSWORD" -X POST \
  http://127.0.0.1:3000/api/datasources/uid/loki/health
curl -fsS 'http://127.0.0.1:3200/api/search?tags=service.name%3Daiconfigurator-portal'
# After one real Portal request, query logs by its trace ID:
curl -G -fsS http://127.0.0.1:3100/loki/api/v1/query \
  --data-urlencode 'query={service_name="aiconfigurator-portal"} | trace_id="<TRACE_ID>"'
# After one completed Portal run, query Prometheus exemplars:
curl -G -fsS http://127.0.0.1:9090/api/v1/query_exemplars \
  --data-urlencode 'query=portal_trace_run_duration_seconds_bucket{status="completed"}'
```

All storage is ephemeral. `minikube delete -p aiconfigurator` removes the
cluster and telemetry data. The stack is for local development only and has no
TLS, authentication beyond Grafana's local login, HA, or durable retention.

The Prometheus, Tempo, Grafana, and OTel Collector installation was verified on
2026-09-05. Loki and Alloy were verified on 2026-09-06 in Minikube context
`aiconfigurator`: Loki `2/2` and Alloy `2/2` were Ready, Grafana Loki and Tempo
datasource health returned `OK`, and real Portal run
`c68b01dc-0b0d-4603-95dd-21c38f31118a` completed successfully. Loki returned
the Portal log records for trace ID
`cbff4846d714411f1ff600d580e4b882` and span ID `30c30577c46ad423` through
structured-metadata filters; the corresponding Tempo trace returned 9 spans,
including the matching span. The Grafana datasource API reports
`readOnly: false`, Tempo `tracesToLogsV2` enabled with trace/span filtering, and
the Loki `TraceID` derived field linked to Tempo. In the Grafana UI, open
Explore with Tempo to use the span's Logs for this span link, or Explore with
Loki to use the TraceID link on a matching log line.

Prometheus exemplar correlation was additionally verified on 2026-09-06: the
Portal returned OpenMetrics with a `trace_id` exemplar for a real completed
run, Prometheus reported the Portal target `up`, and
`/api/v1/query_exemplars` returned the matching trace ID from the
`portal_trace_run_duration_seconds_bucket` series. In Grafana, open Explore
with Prometheus and select the exemplar marker to follow the link to Tempo.
