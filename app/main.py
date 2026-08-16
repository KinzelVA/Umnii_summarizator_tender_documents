from fastapi import FastAPI

from app.api.routes.health import router as health_router
from app.api.routes.summarize import router as summarize_router
from app.core.config import get_settings
from app.core.logging import configure_logging
from app.core.rate_limit import InMemoryRateLimiter
from app.core.request_logging import log_request

settings = get_settings()
configure_logging(settings.log_level)

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description=settings.app_description,
)

rate_limiter = InMemoryRateLimiter(
    max_requests=settings.rate_limit_requests,
    window_seconds=settings.rate_limit_window_seconds,
)

app.middleware("http")(rate_limiter)
app.middleware("http")(log_request)

app.include_router(health_router)
app.include_router(summarize_router)
