from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates


TEMPLATES_DIR = Path(__file__).resolve().parents[2] / "templates"
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))


def build_pages_router() -> APIRouter:
    router = APIRouter()

    @router.get("/", response_class=HTMLResponse)
    def index(request: Request) -> HTMLResponse:
        return templates.TemplateResponse(
            request=request,
            name="form.html",
            context={
                "defaults": {
                    "model": "Qwen/Qwen3-32B-FP8",
                    "system": "h200_sxm",
                    "total_gpus": 32,
                    "ttft": 2000,
                    "tpot": 30,
                }
            },
        )

    return router
