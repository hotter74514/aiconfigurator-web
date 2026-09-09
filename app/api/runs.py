from uuid import UUID

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import FileResponse
from starlette.background import BackgroundTask

from app.domain.runs import (
    RunAcceptedResponse,
    RunHistoryItem,
    RunRequest,
    RunStatusResponse,
)
from app.services.artifacts import ArtifactNotFoundError, ArtifactStoreError
from app.services.submissions import (
    QueueCapacityError,
    RunManager,
    RunManagerUnavailableError,
    RunNotFoundError,
)


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
        except RunManagerUnavailableError as exc:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=str(exc),
            ) from exc
        except QueueCapacityError as exc:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=str(exc),
                headers={"Retry-After": "1"},
            ) from exc
        return RunAcceptedResponse(id=run.id, status=run.status)

    @router.get(
        "/api/runs",
        response_model=list[RunHistoryItem],
        response_model_exclude_none=True,
    )
    def list_runs() -> list[RunHistoryItem]:
        return service.history()

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

    @router.get("/api/runs/{run_id}/artifacts.zip")
    def download_artifact_bundle(run_id: UUID) -> FileResponse:
        try:
            path = service.artifact_bundle_path(run_id)
        except (ArtifactNotFoundError, RunNotFoundError) as exc:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Artifact bundle not available",
            ) from exc
        except ArtifactStoreError as exc:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Artifact bundle could not be created",
            ) from exc
        return FileResponse(
            path,
            media_type="application/zip",
            filename=f"aiconfigurator-run-{run_id}-artifacts.zip",
            background=BackgroundTask(path.unlink, missing_ok=True),
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
