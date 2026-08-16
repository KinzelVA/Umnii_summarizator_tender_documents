import asyncio
from collections import deque
from collections.abc import Awaitable, Callable
from math import ceil
from time import monotonic

from fastapi import Request, Response, status
from fastapi.responses import JSONResponse

RequestHandler = Callable[[Request], Awaitable[Response]]


class InMemoryRateLimiter:
    def __init__(
        self,
        *,
        max_requests: int,
        window_seconds: int,
        path: str = "/api/v1/summarize",
        method: str = "POST",
    ) -> None:
        if max_requests <= 0:
            raise ValueError("max_requests must be positive")

        if window_seconds <= 0:
            raise ValueError("window_seconds must be positive")

        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.path = path
        self.method = method.upper()

        self._requests: dict[str, deque[float]] = {}
        self._lock = asyncio.Lock()

    async def __call__(
        self,
        request: Request,
        call_next: RequestHandler,
    ) -> Response:
        if request.method != self.method or request.url.path != self.path:
            return await call_next(request)

        client_host = request.client.host if request.client is not None else "unknown"

        now = monotonic()
        cutoff = now - self.window_seconds

        async with self._lock:
            timestamps = self._requests.setdefault(
                client_host,
                deque(),
            )

            while timestamps and timestamps[0] <= cutoff:
                timestamps.popleft()

            if len(timestamps) >= self.max_requests:
                retry_after = max(
                    1,
                    ceil(self.window_seconds - (now - timestamps[0])),
                )

                return JSONResponse(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    content={
                        "detail": (
                            "Too many summarization requests. Please retry later."
                        )
                    },
                    headers={
                        "Retry-After": str(retry_after),
                    },
                )

            timestamps.append(now)

        return await call_next(request)
