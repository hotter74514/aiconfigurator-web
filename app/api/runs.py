from fastapi import APIRouter, status

from app.domain.runs import RunAcceptedResponse, RunRequest
from app.services.submissions import InMemoryRunSubmissionService


def build_runs_router(service: InMemoryRunSubmissionService) -> APIRouter:
    router = APIRouter()

    @router.post(
        "/api/runs",
        response_model=RunAcceptedResponse,
        status_code=status.HTTP_202_ACCEPTED,
    )
    def submit_run(request: RunRequest) -> RunAcceptedResponse:
        run = service.submit(request)
        return RunAcceptedResponse(id=run.id, status=run.status)

    return router
