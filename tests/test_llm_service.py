import asyncio
import json
from types import SimpleNamespace
from httpx import TimeoutException
import pytest

from app.services.llm import (
    LlmConnectionError,
    LlmInvalidResponseError,
    LlmTimeoutError,
    build_analysis_prompt,
    summarize_tender,
)


class FakeLlmClient:
    def __init__(
        self,
        response_content: str | None = None,
        error: Exception | None = None,
    ) -> None:
        self.response_content = response_content
        self.error = error
        self.last_request: dict | None = None

    async def chat(
        self,
        *,
        model: str,
        messages: list[dict[str, str]],
        format: dict,
        options: dict[str, float],
    ) -> object:
        self.last_request = {
            "model": model,
            "messages": messages,
            "format": format,
            "options": options,
        }

        if self.error is not None:
            raise self.error

        return SimpleNamespace(
            message=SimpleNamespace(
                content=self.response_content,
            )
        )


def test_build_analysis_prompt_contains_document() -> None:
    prompt = build_analysis_prompt(
        "Contract amount: 1 000 000 RUB"
    )

    assert "<document>" in prompt
    assert "Contract amount: 1 000 000 RUB" in prompt
    assert "</document>" in prompt


def test_summarize_tender_returns_validated_summary() -> None:
    response = json.dumps(
        {
            "contract_amount": "1 000 000 RUB",
            "execution_deadlines": "30 days",
            "contractor_requirements": [
                "Valid license",
            ],
            "penalties": [
                "0.1% per day of delay",
            ],
        }
    )

    client = FakeLlmClient(response_content=response)

    summary = asyncio.run(
        summarize_tender(
            "Tender document text",
            base_url="http://localhost:11434",
            model="gpt-oss:20b",
            timeout_seconds=120,
            client=client,
        )
    )

    assert summary.contract_amount == "1 000 000 RUB"
    assert summary.execution_deadlines == "30 days"
    assert summary.contractor_requirements == [
        "Valid license"
    ]
    assert summary.penalties == [
        "0.1% per day of delay"
    ]

    assert client.last_request is not None
    assert client.last_request["model"] == "gpt-oss:20b"
    assert client.last_request["options"] == {
        "temperature": 0
    }


def test_summarize_tender_rejects_empty_text() -> None:
    with pytest.raises(
        ValueError,
        match="document_text must not be empty",
    ):
        asyncio.run(
            summarize_tender(
                "   ",
                base_url="http://localhost:11434",
                model="gpt-oss:20b",
                timeout_seconds=120,
                client=FakeLlmClient(),
            )
        )


def test_summarize_tender_rejects_empty_llm_response() -> None:
    client = FakeLlmClient(response_content="")

    with pytest.raises(
        LlmInvalidResponseError,
        match="empty response",
    ):
        asyncio.run(
            summarize_tender(
                "Tender document text",
                base_url="http://localhost:11434",
                model="gpt-oss:20b",
                timeout_seconds=120,
                client=client,
            )
        )


def test_summarize_tender_rejects_invalid_json() -> None:
    client = FakeLlmClient(
        response_content="This is not valid JSON"
    )

    with pytest.raises(
        LlmInvalidResponseError,
        match="expected schema",
    ):
        asyncio.run(
            summarize_tender(
                "Tender document text",
                base_url="http://localhost:11434",
                model="gpt-oss:20b",
                timeout_seconds=120,
                client=client,
            )
        )


def test_summarize_tender_handles_connection_error() -> None:
    client = FakeLlmClient(
        error=ConnectionError("Connection refused")
    )

    with pytest.raises(
        LlmConnectionError,
        match="Could not connect",
    ):
        asyncio.run(
            summarize_tender(
                "Tender document text",
                base_url="http://localhost:11434",
                model="gpt-oss:20b",
                timeout_seconds=120,
                client=client,
            )
        )

def test_summarize_tender_handles_timeout() -> None:
    client = FakeLlmClient(
        error=TimeoutException("Request timed out")
    )

    with pytest.raises(
        LlmTimeoutError,
        match="request timed out",
    ):
        asyncio.run(
            summarize_tender(
                "Tender document text",
                base_url="http://localhost:11434",
                model="gpt-oss:20b",
                timeout_seconds=120,
                client=client,
            )
        )