# TASK-000 deliberately contains only the external AIConfigurator runtime.
FROM --platform=linux/amd64 python:3.11-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# 0.11.0 is the newest release currently available from the configured PyPI
# index. Its report code calls plotext.plot_size, which was removed in plotext
# 6.x, so keep the compatible 5.3.2 pin explicit and reproducible.
RUN python -m pip install --no-cache-dir \
    "aiconfigurator==0.11.0" \
    "plotext==5.3.2"

ENTRYPOINT ["aiconfigurator"]
