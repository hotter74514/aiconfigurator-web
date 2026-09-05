from fastapi import APIRouter
from fastapi.responses import Response
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

from app.services.telemetry import get_telemetry


def build_metrics_router() -> APIRouter:
    router = APIRouter()

    @router.get("/metrics", include_in_schema=False)
    def metrics() -> Response:
        get_telemetry()
        return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)

    return router
