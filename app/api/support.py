from fastapi import APIRouter

from app.domain.runs import SupportMatrixResponse, SupportPairResponse
from app.services.support_matrix import SupportMatrix, load_support_matrix


def build_support_router(matrix: SupportMatrix | None = None) -> APIRouter:
    router = APIRouter()
    support = matrix or load_support_matrix()

    @router.get("/api/support", response_model=SupportMatrixResponse)
    def get_support() -> SupportMatrixResponse:
        return SupportMatrixResponse(
            backend=support.backend,
            source=support.source,
            aiconfigurator_version=support.aiconfigurator_version,
            models=list(support.models),
            systems=list(support.systems),
            pairs=[
                SupportPairResponse(
                    model=pair.model,
                    system=pair.system,
                    status=pair.status,
                )
                for pair in support.pairs
            ],
        )

    return router
