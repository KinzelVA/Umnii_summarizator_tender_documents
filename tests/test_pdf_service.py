from io import BytesIO

import pytest
from pypdf import PdfWriter

from app.services.pdf import (
    InvalidPdfError,
    PdfTextNotFoundError,
    PdfTooLargeError,
    extract_pdf,
    normalize_text,
)


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


def test_normalize_text() -> None:
    text = "Contract    amount\n\n  1 000 RUB\t"

    assert normalize_text(text) == "Contract amount\n1 000 RUB"


def test_extract_pdf_returns_text_and_page_count() -> None:
    pdf = _build_pdf_with_text("Tender amount 1000 RUB")

    result = extract_pdf(
        BytesIO(pdf),
        max_size_bytes=1024 * 1024,
    )

    assert result.page_count == 1
    assert result.text == "Tender amount 1000 RUB"


def test_extract_pdf_rejects_non_pdf_file() -> None:
    with pytest.raises(
        InvalidPdfError,
        match="valid PDF signature",
    ):
        extract_pdf(
            BytesIO(b"This is not a PDF"),
            max_size_bytes=1024,
        )


def test_extract_pdf_rejects_oversized_file() -> None:
    pdf = _build_pdf_with_text("Tender")

    with pytest.raises(
        PdfTooLargeError,
        match="exceeds the maximum size",
    ):
        extract_pdf(
            BytesIO(pdf),
            max_size_bytes=10,
        )


def test_extract_pdf_rejects_pdf_without_text_layer() -> None:
    pdf = _build_blank_pdf()

    with pytest.raises(
        PdfTextNotFoundError,
        match="No extractable text",
    ):
        extract_pdf(
            BytesIO(pdf),
            max_size_bytes=1024 * 1024,
        )

def test_extract_pdf_rejects_empty_file() -> None:
    with pytest.raises(
        InvalidPdfError,
        match="PDF file is empty",
    ):
        extract_pdf(
            BytesIO(b""),
            max_size_bytes=1024,
        )


def test_extract_pdf_rejects_corrupted_pdf() -> None:
    corrupted_pdf = b"%PDF-1.4\nThis is corrupted PDF content"

    with pytest.raises(
        InvalidPdfError,
        match="corrupted or cannot be read",
    ):
        extract_pdf(
            BytesIO(corrupted_pdf),
            max_size_bytes=1024 * 1024,
        )


def test_extract_pdf_rejects_encrypted_pdf() -> None:
    buffer = BytesIO()

    writer = PdfWriter()
    writer.add_blank_page(width=612, height=792)
    writer.encrypt("secret")
    writer.write(buffer)

    with pytest.raises(
        InvalidPdfError,
        match="Encrypted PDF files are not supported",
    ):
        extract_pdf(
            BytesIO(buffer.getvalue()),
            max_size_bytes=1024 * 1024,
        )

