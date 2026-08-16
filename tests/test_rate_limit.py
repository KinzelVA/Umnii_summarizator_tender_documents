from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.rate_limit import InMemoryRateLimiter


def _build_client(
    *,
    max_requests: int = 2,
    window_seconds: int = 60,
) -> TestClient:
    app = FastAPI()

    limiter = InMemoryRateLimiter(
        max_requests=max_requests,
        window_seconds=window_seconds,
    )

    app.middleware("http")(limiter)

    @app.post("/api/v1/summarize")
    async def summarize() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    return TestClient(app)


def test_rate_limiter_allows_requests_within_limit() -> None:
    client = _build_client(max_requests=2)

    first = client.post("/api/v1/summarize")
    second = client.post("/api/v1/summarize")

    assert first.status_code == 200
    assert second.status_code == 200


def test_rate_limiter_returns_429_after_limit_is_exceeded() -> None:
    client = _build_client(max_requests=2)

    client.post("/api/v1/summarize")
    client.post("/api/v1/summarize")
    response = client.post("/api/v1/summarize")

    assert response.status_code == 429
    assert response.json() == {
        "detail": (
            "Too many summarization requests. "
            "Please retry later."
        )
    }


def test_rate_limiter_sets_retry_after_header() -> None:
    client = _build_client(
        max_requests=1,
        window_seconds=60,
    )

    client.post("/api/v1/summarize")
    response = client.post("/api/v1/summarize")

    retry_after = int(response.headers["Retry-After"])

    assert 1 <= retry_after <= 60


def test_rate_limiter_does_not_limit_unrelated_routes() -> None:
    client = _build_client(max_requests=1)

    first = client.get("/health")
    second = client.get("/health")
    third = client.get("/health")

    assert first.status_code == 200
    assert second.status_code == 200
    assert third.status_code == 200