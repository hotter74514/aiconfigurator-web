# Local observability stack

The repository includes a local Minikube stack for the portal:

- Prometheus `29.27.1` / Prometheus `v3.14.0`
- Tempo `1.24.4` / Tempo `2.9.0`
- Grafana `10.5.15` / Grafana `12.3.1`
- OpenTelemetry Collector Helm chart `0.172.1` / contrib image `0.159.0`

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
the portal's `/metrics` endpoint. Grafana is provisioned with both backends.

## Access and verification

Use separate terminals for the port-forwards:

```sh
kubectl port-forward service/aiconfigurator-portal 8000:8000
kubectl port-forward -n observability service/prometheus-server 9090:80
kubectl port-forward -n observability service/grafana 3000:80
kubectl port-forward -n observability service/tempo 3200:3200
```

- Portal: <http://127.0.0.1:8000>
- Prometheus: <http://127.0.0.1:9090>
- Grafana: <http://127.0.0.1:3000>, user `admin`, password from
  `kubectl get secret -n observability grafana-admin -o jsonpath='{.data.admin-password}' | base64 --decode`
- Tempo API: <http://127.0.0.1:3200>

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
curl -fsS 'http://127.0.0.1:3200/api/search?tags=service.name%3Daiconfigurator-portal'
```

All storage is ephemeral. `minikube delete -p aiconfigurator` removes the
cluster and telemetry data. The stack is for local development only and has no
TLS, authentication beyond Grafana's local login, HA, or durable retention.

The installation was verified on 2026-09-05 with all four observability pods
Ready, Portal probe responses `200`, Prometheus portal target `up=1`, Grafana
Prometheus and Tempo datasource health `OK`, and Tempo returning Portal traces.
