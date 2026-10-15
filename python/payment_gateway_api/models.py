from datetime import UTC, datetime
from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator


class PaymentRequest(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")

    card_number: Annotated[str, Field(pattern=r"^[0-9]{14,19}$", repr=False)]
    expiry_month: Annotated[int, Field(ge=1, le=12)]
    expiry_year: Annotated[int, Field(ge=1, le=9999)]
    currency: Literal["USD", "GBP", "EUR"]
    amount: Annotated[int, Field(ge=1, le=9223372036854775807)]
    cvv: Annotated[str, Field(pattern=r"^[0-9]{3,4}$", repr=False)]

    @model_validator(mode="after")
    def check_expiry(self):
        today = datetime.now(UTC)
        if (self.expiry_year, self.expiry_month) <= (today.year, today.month):
            raise ValueError("Expiry must be after the current month")
        return self


class Payment(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: UUID
    status: Literal["Authorized", "Declined"]
    card_number_last_four: str
    expiry_month: int
    expiry_year: int
    currency: str
    amount: int
