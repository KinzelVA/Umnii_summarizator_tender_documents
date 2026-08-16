from io import BytesIO
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from pypdf import PdfWriter

import app.api.routes.summarize as summarize_route
from app.main import app
from app.schemas.summary import TenderSummary
from app.services.llm import (
    LlmConnectionError,
    LlmProcessingError,
    LlmTimeoutError,
)

client = TestClient(app)


def _build_pdf_with_text(text: str) -> bytes:
    escaped_text = (
        text.replace("\\", "\\\\")
        .replace("(", "\\(")
        .replace(")", "\\)")
    )

    content = (
        f"BT /F1 12 Tf 72 720 Td ({escaped_text}) Tj ET"
    ).encode("latin-1")

    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        (
            b"<< /Type /Page /Parent 2 0 R "
            b"/MediaBox [0 0 612 792] "
            b"/Resources << /Font << /F1 4 0 R >> >> "
            b"/Contents 5 0 R >>"
        ),
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        (
            b"<< /Length %d >>\nstream\n%s\nendstream"
            % (len(content), content)
        ),
    ]

    pdf = bytearray(b"%PDF-1.4\n")
    offsets = [0]

    for object_number, pdf_object in enumerate(objects, start=1):
        offsets.append(len(pdf))
        pdf.extend(f"{object_number} 0 obj\n".encode())
        pdf.extend(pdf_object)
        pdf.extend(b"\nendobj\n")

    xref_offset = len(pdf)

    pdf.extend(f"xref\n0 {len(objects) + 1}\n".encode())
    pdf.extend(b"0000000000 65535 f \n")

    for offset in offsets[1:]:
        pdf.extend(f"{offset:010d} 00000 n \n".encode())

    pdf.extend(
        (
            f"trailer\n"
            f"<< /Size {len(objects) + 1} /Root 1 0 R >>\n"
            f"startxref\n"
            f"{xref_offset}\n"
            f"%%EOF\n"
        ).encode()
    )

    return bytes(pdf)


def _build_blank_pdf() -> bytes:
    buffer = BytesIO()
    writer = PdfWriter()
    writer.add_blank_page(width=612, height=792)
    writer.write(buffer)

    return buffer.getvalue()


def _settings(
    *,
    max_pdf_size_bytes: int = 20 * 1024 * 1024,
) -> SimpleNamespace:
    return SimpleNamespace(
        max_pdf_size_bytes=max_pdf_size_bytes,
        ollama_base_url="http://localhost:11434",
        ollama_model="gpt-oss:20b",
        ollama_context_length=16384,
        llm_timeout_seconds=120,
    )


def test_summarize_pdf_returns_structured_summary(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def fake_summarize_tender(
        document_text: str,
        *,
        base_url: str,
        model: str,
        context_length: int,
        timeout_seconds: int,
    ) -> TenderSummary:
        assert "Tender amount 1000 RUB" in document_text
        assert base_url == "http://localhost:11434"
        assert model == "gpt-oss:20b"
        assert context_length == 16384
        assert timeout_seconds == 120

        return TenderSummary(
            contract_amount="1000 RUB",
            execution_deadlines="30 days",
            contractor_requirements=["Valid license"],
            penalties=["0.1% per day"],
        )

    monkeypatch.setattr(
        summarize_route,
        "summarize_tender",
        fake_summarize_tender,
    )

    pdf = _build_pdf_with_text("Tender amount 1000 RUB")

    response = client.post(
        "/api/v1/summarize",
        files={
            "file": (
                "tender.pdf",
                pdf,
                "application/pdf",
            )
        },
    )

    assert response.status_code == 200
    assert response.json() == {
        "contract_amount": "1000 RUB",
        "execution_deadlines": "30 days",
        "contractor_requirements": ["Valid license"],
        "penalties": ["0.1% per day"],
    }


def test_summarize_rejects_non_pdf_file() -> None:
    response = client.post(
        "/api/v1/summarize",
        files={
            "file": (
                "tender.txt",
                b"not a pdf",
                "text/plain",
            )
        },
    )

    assert response.status_code == 415
    assert response.json() == {
        "detail": "Only PDF files are supported."
    }


def test_summarize_rejects_oversized_pdf(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        summarize_route,
        "get_settings",
        lambda: _settings(max_pdf_size_bytes=10),
    )

    pdf = _build_pdf_with_text("Tender")

    response = client.post(
        "/api/v1/summarize",
        files={
            "file": (
                "tender.pdf",
                pdf,
                "application/pdf",
            )
        },
    )

    assert response.status_code == 413
    assert "exceeds the maximum size" in response.json()["detail"]


def test_summarize_rejects_corrupted_pdf() -> None:
    response = client.post(
        "/api/v1/summarize",
        files={
            "file": (
                "tender.pdf",
                b"%PDF-1.4\ncorrupted",
                "application/pdf",
            )
        },
    )

    assert response.status_code == 400
    assert "corrupted or cannot be read" in response.json()["detail"]


def test_summarize_rejects_pdf_without_text_layer() -> None:
    response = client.post(
        "/api/v1/summarize",
        files={
            "file": (
                "scan.pdf",
                _build_blank_pdf(),
                "application/pdf",
            )
        },
    )

    assert response.status_code == 400
    assert "No extractable text" in response.json()["detail"]


@pytest.mark.parametrize(
    ("error", "expected_status", "expected_detail"),
    [
        (
            LlmConnectionError("Connection refused"),
            503,
            "The LLM provider is unavailable.",
        ),
        (
            LlmTimeoutError("Timed out"),
            504,
            "The LLM provider request timed out.",
        ),
        (
            LlmProcessingError("Invalid response"),
            502,
            "The LLM provider returned an invalid response.",
        ),
    ],
)
def test_summarize_handles_llm_errors(
    monkeypatch: pytest.MonkeyPatch,
    error: Exception,
    expected_status: int,
    expected_detail: str,
) -> None:
    async def failing_summarize_tender(
        document_text: str,
        *,
        base_url: str,
        model: str,
        context_length: int,
        timeout_seconds: int,
    ) -> TenderSummary:
        raise error

    monkeypatch.setattr(
        summarize_route,
        "summarize_tender",
        failing_summarize_tender,
    )

    pdf = _build_pdf_with_text("Tender amount 1000 RUB")

    response = client.post(
        "/api/v1/summarize",
        files={
            "file": (
                "tender.pdf",
                pdf,
                "application/pdf",
            )
        },
    )

    assert response.status_code == expected_status
    assert response.json() == {
        "detail": expected_detail
    }