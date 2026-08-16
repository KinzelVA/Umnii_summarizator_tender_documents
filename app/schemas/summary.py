from pydantic import BaseModel, Field


class TenderSummary(BaseModel):
    contract_amount: str | None = Field(
        default=None,
        description=(
            "Contract amount exactly as stated in the tender documentation. "
            "Null if the amount is not found."
        ),
        examples=["15 000 000 RUB"],
    )
    execution_deadlines: str | None = Field(
        default=None,
        description=(
            "Contract execution deadlines or period. "
            "Null if the deadlines are not found."
        ),
        examples=["From 01.09.2026 to 31.12.2026"],
    )
    contractor_requirements: list[str] = Field(
        default_factory=list,
        description="Key requirements imposed on the contractor.",
        examples=[
            [
                "Valid license for the required activity",
                "Experience with similar contracts",
            ]
        ],
    )
    penalties: list[str] = Field(
        default_factory=list,
        description="Penalties, fines, and late-payment provisions.",
        examples=[
            [
                "0.1% of the unfulfilled obligation for each day of delay",
            ]
        ],
    )
