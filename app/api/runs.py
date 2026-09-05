from uuid import UUID

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import FileResponse

from app.domain.runs import RunAcceptedResponse, RunRequest, RunStatusResponse
from app.services.artifacts import ArtifactNotFoundError
from app.services.submissions import QueueCapacityError, RunManager, RunNotFoundError


def build_runs_router(service: RunManager) -> APIRouter:
    router = APIRouter()

    @router.post(
        "/api/runs",
        response_model=RunAcceptedResponse,
        status_code=status.HTTP_202_ACCEPTED,
    )
    def submit_run(request: RunRequest) -> RunAcceptedResponse:
        try:
            run = service.submit(request)
        except QueueCapacityError as exc:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=str(exc),
                headers={"Retry-After": "1"},
            ) from exc
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
        return RunStatusResponse(
            id=run.id,
            status=run.status,
            error=run.error,
            results=run.results,
            artifacts=run.artifacts or None,
        )

    @router.get("/api/runs/{run_id}/artifacts/{artifact_name:path}")
    def download_artifact(run_id: UUID, artifact_name: str) -> FileResponse:
        try:
            path = service.artifact_path(run_id, artifact_name)
        except (ArtifactNotFoundError, RunNotFoundError) as exc:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Artifact not found",
            ) from exc
        return FileResponse(path, filename=path.name)

    return router
