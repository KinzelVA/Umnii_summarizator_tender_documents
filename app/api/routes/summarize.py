from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, File, HTTPException, UploadFile, status

from app.core.config import get_settings
from app.schemas.summary import TenderSummary
from app.services.llm import (
    LlmConnectionError,
    LlmProcessingError,
    LlmTimeoutError,
    summarize_tender,
)
from app.services.pdf import (
    InvalidPdfError,
    PdfTextNotFoundError,
    PdfTooLargeError,
    extract_pdf,
)

router = APIRouter(
    prefix="/api/v1",
    tags=["summarization"],
)

ALLOWED_PDF_CONTENT_TYPES = {
    "application/pdf",
    "application/x-pdf",
}


@router.post(
    "/summarize",
    response_model=TenderSummary,
    summary="Summarize tender documentation",
    description=(
        "Upload a PDF tender document and extract the contract amount, "
        "execution deadlines, contractor requirements, and penalties."
    ),
    responses={
        status.HTTP_400_BAD_REQUEST: {
            "description": "The PDF is invalid, encrypted, corrupted, or has no text layer.",
            "content": {
                "application/json": {
                    "example": {
                        "detail": (
                            "No extractable text was found in the PDF. "
                            "Scanned documents require OCR, which is not supported."
                        )
                    }
                }
            },
        },
        status.HTTP_413_CONTENT_TOO_LARGE: {
            "description": "The uploaded PDF exceeds the configured size limit.",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "The PDF file exceeds the maximum allowed size."
                    }
                }
            },
        },
        status.HTTP_415_UNSUPPORTED_MEDIA_TYPE: {
            "description": "The uploaded file is not a PDF.",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Only PDF files are supported."
                    }
                }
            },
        },
        status.HTTP_502_BAD_GATEWAY: {
            "description": "The LLM provider returned an invalid response.",
        },
        status.HTTP_503_SERVICE_UNAVAILABLE: {
            "description": "The LLM provider is unavailable.",
        },
        status.HTTP_504_GATEWAY_TIMEOUT: {
            "description": "The LLM provider request timed out.",
        },
    },
)
async def summarize_document(
    file: Annotated[
        UploadFile,
        File(
            description=(
                "Tender documentation in PDF format. "
                "The PDF must contain an extractable text layer."
            )
        ),
    ],
) -> TenderSummary:
    if (
        file.content_type not in ALLOWED_PDF_CONTENT_TYPES
        or not file.filename
        or Path(file.filename).suffix.lower() != ".pdf"
    ):
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Only PDF files are supported.",
        )

    settings = get_settings()

    try:
        extracted_pdf = extract_pdf(
            file.file,
            max_size_bytes=settings.max_pdf_size_bytes,
        )

        return await summarize_tender(
            extracted_pdf.text,
            base_url=settings.ollama_base_url,
            model=settings.ollama_model,
            context_length=settings.ollama_context_length,
            timeout_seconds=settings.llm_timeout_seconds,
        )

    except PdfTooLargeError as exc:
        raise HTTPException(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
            detail=str(exc),
        ) from exc

    except (InvalidPdfError, PdfTextNotFoundError) as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    except LlmTimeoutError as exc:
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="The LLM provider request timed out.",
        ) from exc

    except LlmConnectionError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="The LLM provider is unavailable.",
        ) from exc

    except LlmProcessingError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="The LLM provider returned an invalid response.",
        ) from exc

    finally:
        await file.close()