# TASK-062: AIConfigurator Support-Matrix Selectors

The portal now exposes `GET /api/support`, which reads the support-matrix CSV
files shipped by the installed AIConfigurator wheel. Because the portal runs
the default CLI mode without a backend override, the endpoint exposes only
`trtllm` rows with `PASS` or `HYBRID_PASS` status. Duplicate model/system rows
are collapsed, preferring `PASS` over `HYBRID_PASS`.

The form replaces free-text Model and GPU system fields with native HTML
`select` controls. The browser loads the current matrix at page startup and
filters GPU systems to those supported by the selected model. A minimal
Qwen/H200 fallback remains available for local API/UI development when the
Linux-only AIConfigurator dependency is not installed.

The selectable data is versioned by the container's dependency, currently
`aiconfigurator==0.11.0`; it is not a universal guarantee that every backend,
mode, or future wheel version supports every pair. AIConfigurator estimates
still require representative benchmark validation.

## Verification

```sh
./.venv/bin/pytest -q tests/test_support_matrix.py tests/test_support_api.py tests/test_pages.py
kubectl exec deployment/aiconfigurator-portal -- python -c 'import aiconfigurator; print(aiconfigurator.__file__)'
curl -fsS http://127.0.0.1:8000/api/support
```

The deployed `0.11.0` wheel currently reports 60 selectable TRT-LLM models
across 9 GPU systems (PASS or HYBRID_PASS rows). The exact pair list is served
by the endpoint rather than duplicated in the frontend.
