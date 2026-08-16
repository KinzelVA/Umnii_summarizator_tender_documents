from fastapi import FastAPI
from app.api.routes.summarize import router as summarize_router
from app.api.routes.health import router as health_router
from app.core.config import get_settings

settings = get_settings()

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description=settings.app_description,
)

app.include_router(health_router)
app.include_router(summarize_router)
