from fastapi import FastAPI
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

from app.api.metrics import build_metrics_router
from app.api.pages import build_pages_router
from app.api.probes import build_probes_router
from app.api.runs import build_runs_router
from app.services.submissions import RunManager
from app.services.telemetry import get_telemetry


def create_app(service: RunManager | None = None) -> FastAPI:
    submission_service = service or RunManager()
    app = FastAPI(title="AIConfigurator Serving Configuration Portal")
    telemetry = get_telemetry()
    FastAPIInstrumentor.instrument_app(
        app,
        tracer_provider=telemetry.providers.tracer_provider,
        meter_provider=telemetry.providers.meter_provider,
    )
    app.include_router(build_pages_router())
    app.include_router(build_metrics_router())
    app.include_router(build_probes_router(submission_service))
    app.include_router(build_runs_router(submission_service))
    app.state.submission_service = submission_service
    app.state.telemetry = telemetry
    return app


app = create_app()
