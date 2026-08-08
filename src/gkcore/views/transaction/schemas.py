from pydantic import BaseModel, ValidationInfo, model_validator, field_validator
from typing import Dict, Optional, Literal
from typing_extensions import Self
from datetime import date

from gkcore.views.transaction.services import check_voucher_exists

class VoucherDetails(BaseModel):
    voucherdate: date
    narration: Optional[str] = ""
    drs: Dict[int, float]
    crs: Dict[int, float]
    vouchertype: Optional[
        Literal[
            "payment",
            "receipt",
            "journal",
            "contra",
            "sales",
            "purchase",
            "creditnote",
            "debitnote",
            "salesreturn",
            "purchasereturn",
        ]
    ] = None
    invid: Optional[str] = None
    drcrid: Optional[str] = None
    projectcode: Optional[int] = None

    @model_validator(mode="after")
    def validate(self) -> Self:
        total_cr = sum(self.crs.values())
        total_dr = sum(self.drs.values())
        if total_cr != total_dr:
            raise ValueError(f"Total credit ({total_cr}) must equal total debit ({total_dr})")
        return self


class VoucherUpdateDetails(VoucherDetails):
    vouchercode: int
    vouchernumber: str

    @model_validator(mode="after")
    def validate(self, info: ValidationInfo) -> Self:
        total_cr = sum(self.crs.values())
        total_dr = sum(self.drs.values())
        if total_cr != total_dr:
            raise ValueError(f"Total credit ({total_cr}) must equal total debit ({total_dr})")
        check_voucher_exists(
            self.vouchernumber,
            self.vouchercode,
            info.context["orgcode"],
        )
        return self
