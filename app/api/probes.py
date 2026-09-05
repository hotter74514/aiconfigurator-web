from fastapi import APIRouter, HTTPException, status

from app.services.submissions import RunManager


def build_probes_router(service: RunManager) -> APIRouter:
    router = APIRouter()

    @router.get("/live")
    def liveness() -> dict[str, str]:
        return {"status": "ok"}

    @router.get("/ready")
    def readiness() -> dict[str, str]:
        error = service.readiness_error()
        if error is not None:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=error,
            )
        return {"status": "ready"}

    return router
