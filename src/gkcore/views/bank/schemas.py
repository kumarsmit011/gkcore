from pydantic import BaseModel, constr
from typing import Optional


class BankCreate(BaseModel):
    account_name: constr(strip_whitespace=True, min_length=1)
    opening_balance: Optional[float] = 0.00
    bank_name: Optional[str] = None
    branch_name: Optional[str] = None
    ifsc: Optional[str] = None
    account_number: Optional[str] = None

class BankUpdate(BaseModel):
    id: int
    account_name: Optional[constr(strip_whitespace=True, min_length=1)] = None
    bank_name: Optional[str] = None
    branch_name: Optional[str] = None
    ifsc: Optional[str] = None
    account_number: Optional[str] = None
    opening_balance: Optional[float]
