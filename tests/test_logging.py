import json
import logging

import pytest
from fastapi.testclient import TestClient

from app.core.logging import JsonFormatter
from app.main import app

client = TestClient(app)


def test_json_formatter_includes_structured_http_fields() -> None:
    record = logging.LogRecord(
        name="app.request",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg="Request completed",
        args=(),
        exc_info=None,
    )

    record.method = "POST"
    record.path = "/api/v1/summarize"
    record.status_code = 200
    record.duration_ms = 123.45

    payload = json.loads(JsonFormatter().format(record))

    assert payload["level"] == "INFO"
    assert payload["logger"] == "app.request"
    assert payload["message"] == "Request completed"
    assert payload["method"] == "POST"
    assert payload["path"] == "/api/v1/summarize"
    assert payload["status_code"] == 200
    assert payload["duration_ms"] == 123.45
    assert "timestamp" in payload


def test_request_logging_middleware_logs_completed_request(
    caplog: pytest.LogCaptureFixture,
) -> None:
    caplog.set_level(
        logging.INFO,
        logger="app.request",
    )

    response = client.get("/health")

    assert response.status_code == 200

    records = [
        record
        for record in caplog.records
        if record.name == "app.request" and record.getMessage() == "Request completed"
    ]

    assert records

    record = records[-1]

    assert record.method == "GET"
    assert record.path == "/health"
    assert record.status_code == 200
    assert record.duration_ms >= 0
