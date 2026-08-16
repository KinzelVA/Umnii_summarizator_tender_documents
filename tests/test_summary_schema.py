import pytest
from pydantic import ValidationError

from app.schemas.summary import TenderSummary


def test_tender_summary_accepts_complete_data() -> None:
    summary = TenderSummary(
        contract_amount="15 000 000 RUB",
        execution_deadlines="From 01.09.2026 to 31.12.2026",
        contractor_requirements=[
            "Valid license",
            "Experience with similar contracts",
        ],
        penalties=[
            "0.1% for each day of delay",
        ],
    )

    assert summary.contract_amount == "15 000 000 RUB"
    assert summary.execution_deadlines == "From 01.09.2026 to 31.12.2026"
    assert summary.contractor_requirements == [
        "Valid license",
        "Experience with similar contracts",
    ]
    assert summary.penalties == [
        "0.1% for each day of delay",
    ]


def test_tender_summary_allows_missing_information() -> None:
    summary = TenderSummary()

    assert summary.contract_amount is None
    assert summary.execution_deadlines is None
    assert summary.contractor_requirements == []
    assert summary.penalties == []


def test_tender_summary_rejects_invalid_list_fields() -> None:
    with pytest.raises(ValidationError):
        TenderSummary(
            contractor_requirements="Valid license",
        )
