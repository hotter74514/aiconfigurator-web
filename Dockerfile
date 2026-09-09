# TASK-040 provides the portal runtime by default and keeps a TASK-000 smoke
# target for the external AIConfigurator-only contract.
ARG PYTHON_IMAGE=python:3.11-slim-bookworm@sha256:528257d48c1da0dcecc2e725d1ae34498d60c965f1241e39cd6a85a8859bdf84
FROM ${PYTHON_IMAGE} AS aiconfigurator

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# 0.11.0 is the newest release currently available from the configured PyPI
# index. Its report code calls plotext.plot_size, which was removed in plotext
# 6.x, so keep the compatible 5.3.2 pin explicit and reproducible.
RUN python -m pip install --no-cache-dir \
    "aiconfigurator==0.11.0" \
    "plotext==5.3.2"

FROM aiconfigurator AS portal

WORKDIR /app
COPY pyproject.toml ./
COPY app ./app
COPY templates ./templates

RUN python -m pip install --no-cache-dir . \
    && useradd --create-home --uid 10001 --shell /usr/sbin/nologin portal \
    && mkdir -p /app/data/runs \
    && chown -R portal:portal /app

ENV AICONFIGURATOR_ARTIFACT_ROOT=/app/data/runs
EXPOSE 8000

FROM aiconfigurator AS smoke
ENTRYPOINT ["aiconfigurator"]

FROM portal AS runtime
USER portal
ENTRYPOINT ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
