from pydantic import (
    BaseModel,
    Field,
    ValidationInfo,
    condecimal,
    field_validator,
    model_validator
)
from typing import Optional
from typing_extensions import Self

from gkcore.views.uom.services import unit_name_exists, uom_exists

class UnitOfMeasurement(BaseModel):
    unitname: str = Field(
        ..., max_length=255, description="Name of the unit of measurement."
    )
    description: Optional[str] = Field(
        None, description="Description of the unit."
    )
    conversionrate: Optional[condecimal(ge=0, decimal_places=2)] = Field(
        0.00, description="Conversion rate to the parent unit."
    )
    subunitof: Optional[int] = Field(
        None, description="Parent unit ID for sub-units."
    )
    uqc: Optional[int] = Field(
        None, description="GST-valid unit quantity code."
    )
    frequency: Optional[int] = Field(
        None, description="Frequency of usage."
    )


    @field_validator('subunitof')
    @classmethod
    def validate_subunitof(cls, value: Optional[int]) -> Optional[int]:
        """Ensure subunitof references an existing parent unit."""
        if value and not uom_exists(value):  # Replace with actual database check
            raise ValueError(f"Parent unit with ID {value} does not exist.")
        return value


    @field_validator('uqc')
    @classmethod
    def validate_uqc(cls, value: Optional[int]) -> Optional[int]:
        """Ensure UQC is valid if provided."""
        if value and not uom_exists(value, True):  # Replace with actual database check
            raise ValueError(f"UQC {value} is not valid.")
        return value


    @model_validator(mode="after")
    def validate_unit_uniqueness(self, info: ValidationInfo) -> Self:
        """Ensure unit name is unique within the organization."""
        if unit_name_exists(
                self.unitname,
                info.context["orgcode"],
                getattr(self, "uomid", None),
        ):
            raise ValueError(f"Unit name '{self.unitname}' already exists for this organization.")
        return self

class UnitOfMeasurementUpdate(UnitOfMeasurement):
    uomid: int
