from dataclasses import dataclass
from typing import BinaryIO

from pypdf import PdfReader
from pypdf.errors import PdfReadError


class PdfProcessingError(ValueError):
    """Base exception for PDF processing errors."""


class InvalidPdfError(PdfProcessingError):
    """Raised when the uploaded file is not a valid supported PDF."""


class PdfTooLargeError(PdfProcessingError):
    """Raised when the PDF exceeds the configured size limit."""


class PdfTextNotFoundError(PdfProcessingError):
    """Raised when no extractable text is found in the PDF."""


@dataclass(frozen=True, slots=True)
class ExtractedPdf:
    text: str
    page_count: int


def _get_stream_size(stream: BinaryIO) -> int:
    current_position = stream.tell()

    stream.seek(0, 2)
    size = stream.tell()

    stream.seek(current_position)

    return size


def normalize_text(text: str) -> str:
    normalized_lines = (
        " ".join(line.split())
        for line in text.splitlines()
    )

    return "\n".join(
        line for line in normalized_lines if line
    ).strip()


def extract_pdf(
    stream: BinaryIO,
    *,
    max_size_bytes: int,
) -> ExtractedPdf:
    if max_size_bytes <= 0:
        raise ValueError("max_size_bytes must be greater than zero")

    stream.seek(0)
    file_size = _get_stream_size(stream)

    if file_size == 0:
        raise InvalidPdfError("The PDF file is empty.")

    if file_size > max_size_bytes:
        raise PdfTooLargeError(
            f"The PDF file exceeds the maximum size of {max_size_bytes} bytes."
        )

    stream.seek(0)

    if stream.read(5) != b"%PDF-":
        raise InvalidPdfError("The uploaded file does not have a valid PDF signature.")

    stream.seek(0)

    try:
        reader = PdfReader(stream, strict=False)

        if reader.is_encrypted:
            raise InvalidPdfError("Encrypted PDF files are not supported.")

        page_count = len(reader.pages)
        page_texts: list[str] = []

        for page in reader.pages:
            page_text = normalize_text(page.extract_text() or "")

            if page_text:
                page_texts.append(page_text)

    except InvalidPdfError:
        raise
    except (PdfReadError, EOFError, ValueError) as exc:
        raise InvalidPdfError("The PDF file is corrupted or cannot be read.") from exc

    extracted_text = "\n\n".join(page_texts)

    if not extracted_text:
        raise PdfTextNotFoundError(
            "No extractable text was found in the PDF. "
            "Scanned documents require OCR, which is not supported."
        )

    return ExtractedPdf(
        text=extracted_text,
        page_count=page_count,
    )