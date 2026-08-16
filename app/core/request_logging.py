import logging
from collections.abc import Awaitable, Callable
from time import perf_counter

from fastapi import Request, Response


logger = logging.getLogger("app.request")

RequestHandler = Callable[[Request], Awaitable[Response]]


async def log_request(
    request: Request,
    call_next: RequestHandler,
) -> Response:
    started_at = perf_counter()

    try:
        response = await call_next(request)
    except Exception:
        duration_ms = round(
            (perf_counter() - started_at) * 1000,
            2,
        )

        logger.exception(
            "Request failed",
            extra={
                "method": request.method,
                "path": request.url.path,
                "status_code": 500,
                "duration_ms": duration_ms,
            },
        )
        raise

    duration_ms = round(
        (perf_counter() - started_at) * 1000,
        2,
    )

    logger.info(
        "Request completed",
        extra={
            "method": request.method,
            "path": request.url.path,
            "status_code": response.status_code,
            "duration_ms": duration_ms,
        },
    )

    return response