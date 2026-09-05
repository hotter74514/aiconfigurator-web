from uuid import UUID

from fastapi import APIRouter, HTTPException, status

from app.domain.runs import RunAcceptedResponse, RunRequest, RunStatusResponse
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

    @router.get(
        "/api/runs/{run_id}",
        response_model=RunStatusResponse,
        response_model_exclude_none=True,
    )
    def get_run(run_id: UUID) -> RunStatusResponse:
        run = service.get(run_id)
        if run is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Run not found",
            )
        return RunStatusResponse(id=run.id, status=run.status, error=run.error)

    return router
