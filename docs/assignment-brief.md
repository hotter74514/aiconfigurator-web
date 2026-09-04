# Assignment Brief

## Product Goal

Build a self-service Serving Configuration Portal on top of AIConfigurator. An ML engineer should be able to submit model and serving constraints without installing AIConfigurator or reading its documentation, then receive ranked estimates and deployment artifacts.

## Must-Have Outcomes

- Form inputs: model, GPU type/system, total GPU count, TTFT target, and TPOT target.
- A submitted run invokes the real AIConfigurator dependency.
- The user can observe run status and retrieve failures or results.
- Results show ranked configurations with predicted throughput and latency.
- Generated deployment artifacts are downloadable.
- The system runs in a container, deploys to a local Kubernetes cluster, and exposes health/readiness, structured logs, and basic metrics.

## Runtime Constraints

AIConfigurator wheels are Linux x86-64 only. On macOS, use Docker with `linux/amd64`; do not install it natively. Verify a basic end-to-end run before building the portal. Check the support matrix before selecting model/GPU/backend combinations. The reference smoke command is:

Support matrix: <https://ai-dynamo.github.io/aiconfigurator/support-matrix/>

```sh
aiconfigurator cli default \
  --model Qwen/Qwen3-32B-FP8 \
  --total-gpus 32 \
  --system h200_sxm
```

## Scope Guard

Finish must-have behavior before optional Pareto visualization, aggregated/disaggregated comparison, caching, run history, or multi-user awareness. Authentication, TLS, secrets management, and high availability are out of scope for this take-home, but their extension points and limitations must be documented. Do not modify AIConfigurator itself.

## Evaluation Signals

Prioritize explainable trade-offs, sound Kubernetes resources and probes, serving/runtime awareness, testable code, useful observability, and an honest statement that AIConfigurator outputs are estimates requiring real benchmark validation.
