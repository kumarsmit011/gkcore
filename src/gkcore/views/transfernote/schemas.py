from pydantic import BaseModel, condecimal, field_validator, model_validator
from typing import Dict, Optional
from typing_extensions import Self
from datetime import date
from .services import (
    check_duplicate_transfer_note, godown_exists, item_exists
)


class TransferData(BaseModel):
    duedate: date
    fromgodown: int
    grace: Optional[int] = None
    issuername: str
    nopkt: Optional[int] = None
    togodown: int
    transfernotedate: date
    transfernoteno: str
    transportationmode: str

    @field_validator("fromgodown", "togodown")
    @classmethod
    def validate_godown_exists(cls, value):
        if not godown_exists(value):
            raise ValueError(f"{value} does not exist.")
        return value

    @model_validator(mode="after")
    def validate_transfer_data(self, info) -> Self:
        # Custom validation for unique transfernote and orgcode
        if check_duplicate_transfer_note(
                self.transfernoteno,
             info.context["orgcode"],
             getattr(self, "transfernoteid", None),
        ):
            raise ValueError("Duplicate transfer note number for this organization.")
        # Validation for grace period
        if self.grace and self.grace < 0:
            raise ValueError("Grace period must be a non-negative value.")
        # Validation for due date and transfernotedate
        if self.duedate < self.transfernotedate:
            raise ValueError("Due date cannot be before the transfer note date.")
        return self


class StockData(BaseModel):
    items: Dict[str, condecimal(gt=0)]  # Dictionary of items with positive decimal values

    @model_validator(mode="after")
    def validate_items(self, info) -> Self:
        # Custom validation for items (e.g., checking if items exist in the database)
        for item_id in self.items.keys():
            if not item_exists(item_id):
                raise ValueError(f"Item {item_id} does not exist.")
        return self


class TransfernoteDetails(BaseModel):
    stockdata: StockData
    transferdata: TransferData


class ApproveTransferNote(BaseModel):
    transfernoteid: int
    recieveddate: date
