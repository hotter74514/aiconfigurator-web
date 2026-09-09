# TASK-044: Prometheus exemplars and Tempo correlation

## Implementation

- Enabled Prometheus `exemplar-storage` with a bounded local limit of 10,000
  exemplars.
- Configured Grafana's Prometheus datasource to resolve the `trace_id` exemplar
  label through the existing Tempo datasource UID.
- Changed the Portal `/metrics` endpoint to expose OpenMetrics, which is the
  scrape format required to carry exemplars.
- Added the low-cardinality
  `portal_trace_run_duration_seconds` histogram. Completed runs attach the
  sampled run span's `trace_id` as an exemplar without promoting it to a
  Prometheus label.
- Added a regression test that verifies the OpenMetrics response contains a
  32-character trace ID exemplar.

## Validation

Local checks passed:

```text
make check
46 passed

helm template prometheus prometheus-community/prometheus --version 29.27.1 ...
Prometheus render passed

helm template grafana grafana/grafana --version 10.5.15 ...
Grafana render passed
```

The image was rebuilt for `linux/amd64`, loaded into the dedicated Minikube
profile `aiconfigurator`, and the Portal, Prometheus, and Grafana releases were
rolled out successfully. Prometheus reported the Portal scrape target as
`up`. A real Portal run completed successfully, and Prometheus returned its
exemplar through:

```text
/api/v1/query_exemplars?query=portal_trace_run_duration_seconds_bucket{status="completed"}
trace_id=8f64c3c54b1dba89a4a38b93bc6451db
```

The trace ID is stored only in exemplar metadata; it is not a time-series
label. This remains a local, ephemeral setup, so exemplars disappear when the
Prometheus pod or Minikube profile is deleted.
