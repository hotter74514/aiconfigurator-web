from fastapi import FastAPI

from app.api.runs import build_runs_router
from app.services.submissions import InMemoryRunSubmissionService


def create_app(service: InMemoryRunSubmissionService | None = None) -> FastAPI:
    submission_service = service or InMemoryRunSubmissionService()
    app = FastAPI(title="AIConfigurator Serving Configuration Portal")
    app.include_router(build_runs_router(submission_service))
    app.state.submission_service = submission_service
    return app


app = create_app()
