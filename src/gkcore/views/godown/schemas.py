import re
from gkcore.views.godown.services import check_duplicate_godown_name, state_exists
from pydantic import BaseModel, Field, field_validator, model_validator, ValidationInfo
from typing import Optional
from typing_extensions import Self

class GodownDetails(BaseModel):
    goname: str = Field(..., min_length=5, max_length=100, description="Name of the godown.")
    goaddr: Optional[str] = Field(None, max_length=255, description="Address of the godown.")
    state: Optional[str] = Field(None, max_length=100, description="State where the godown is located.")
    gocontact: Optional[str] = Field(None, description="Contact number (10-digit).")
    contactname: Optional[str] = Field(None, max_length=100, description="Name of the contact person.")


    @field_validator('gocontact')
    @classmethod
    def validate_gocontact(cls, value):
        # Basic regular expression for validating phone numbers.
        # This will match numbers with 9-15 numbers with optional '+' sign.
        phone_regex = re.compile(r'^\+?\d{9,15}$')

        if value and not phone_regex.match(value):
            raise ValueError(f"Invalid phone number: {value}")
        return value

    @field_validator("state")
    @classmethod
    def validate_state(cls, value: Optional[str]) -> Optional[str]:
        """Ensure the state name is valid if provided."""
        if value and not state_exists(value):
            raise ValueError(f"{value} does not exist.")
        return value

    @model_validator(mode="after")
    def validate(self, info: ValidationInfo) -> Self:
        check_duplicate_godown_name(
             self.goname,
             info.context["orgcode"],
             getattr(self, "goid", None),
        )
        return self


class GodownDetailsUpdate(GodownDetails):
    goid: int
