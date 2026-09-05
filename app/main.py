from fastapi import FastAPI

from app.api.pages import build_pages_router
from app.api.runs import build_runs_router
from app.services.submissions import RunManager


def create_app(service: RunManager | None = None) -> FastAPI:
    submission_service = service or RunManager()
    app = FastAPI(title="AIConfigurator Serving Configuration Portal")
    app.include_router(build_pages_router())
    app.include_router(build_runs_router(submission_service))
    app.state.submission_service = submission_service
    return app


app = create_app()
