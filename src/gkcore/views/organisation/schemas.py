from pydantic import BaseModel, EmailStr, Field, HttpUrl, constr, model_validator
from typing import Any, Optional, Dict
from datetime import date


# This will match numbers with 9-15 numbers with optional '+' sign.
PhoneStr = Field(pattern=r'^\+?\d{9,15}$', min_length=10, max_length=15, default=None)

# PAN pattern: 5 uppercase letters, 4 digits, 1 uppercase letter
PANStr = Field(pattern=r'^[A-Z]{5}[0-9]{4}[A-Z]$', min_length=10, max_length=10, default=None)

# IFSC pattern: 4 letters, 0, then 6 alphanumerics
IFSCStr = Field(pattern=r'^[A-Z]{4}0[A-Z0-9]{6}$', min_length=11, max_length=11, default=None)


def convert_blank_to_none(value: Any) -> Any:
    if isinstance(value, dict):
        return {k: convert_blank_to_none(v) for k, v in value.items()}
    elif isinstance(value, list):
        return [convert_blank_to_none(item) for item in value]
    elif value == "":
        return None
    return value


class CleanBaseModel(BaseModel):
    @model_validator(mode="before")
    @classmethod
    def clean_blank_strings(cls, data: Any) -> Any:
        return convert_blank_to_none(data)


class OrgDetails(CleanBaseModel):
    orgname: constr(max_length=200)
    orgcountry: constr(min_length=2, max_length=200)
    orgtype: constr(max_length=200)
    yearend: date
    yearstart: date
    ainvnoflag: Optional[int] = None
    avflag: Optional[int] = None
    avnoflag: Optional[int] = None
    billflag: Optional[int] = None
    invflag: Optional[int] = None
    invsflag: Optional[int] = None
    maflag: Optional[int] = None
    modeflag: Optional[int] = None
    orgaddr: Optional[constr(min_length=5, max_length=500)] = None
    orgcity: Optional[constr(min_length=2, max_length=100)] = None
    orgemail: Optional[EmailStr] = None
    orgfax: Optional[str] = PhoneStr
    orgfcradate: Optional[date] = None
    orgfcrano: Optional[constr(min_length=5, max_length=50)] = None
    orgmvat: Optional[constr(min_length=5, max_length=50)] = None
    orgpan: Optional[str] = PANStr
    orgpincode: Optional[constr(max_length=10)] = None
    orgregdate: Optional[date] = None
    orgregno: Optional[constr(min_length=1, max_length=50)] = None
    orgstate: Optional[constr(min_length=2, max_length=100)] = None
    orgstax: Optional[constr(min_length=5, max_length=50)] = None
    orgtelno: Optional[str] = PhoneStr
    orgwebsite: Optional[HttpUrl] = None


class OrgCreate(BaseModel):
    orgdetails: OrgDetails


class BankDetails(CleanBaseModel):
    accountno: Optional[constr(min_length=5, max_length=20)] = None
    bankname: Optional[constr(min_length=2, max_length=100)] = None
    branchname: Optional[constr(min_length=2, max_length=100)] = None
    ifsc: Optional[str] = IFSCStr


class OrgUpdate(CleanBaseModel):
    ainvnoflag: Optional[int] = None
    avflag: Optional[int] = None
    avnoflag: Optional[int] = None
    bankdetails: Optional[BankDetails] = None
    billflag: Optional[int] = None
    booksclosedflag: Optional[int] = None
    cin: Optional[constr(min_length=10, max_length=21)] = None
    gstin: Optional[Dict[str, constr(min_length=15, max_length=15)]] = None
    invflag: Optional[int] = None
    invsflag: Optional[int] = None
    maflag: Optional[int] = None
    modeflag: Optional[int] = None
    orgaddr: Optional[constr(min_length=5, max_length=500)] = None
    orgcity: Optional[constr(min_length=2, max_length=100)] = None
    orgcountry: Optional[constr(min_length=2, max_length=100)] = None
    orgemail: Optional[EmailStr] = None
    orgfax: Optional[str] = PhoneStr
    orgfcradate: Optional[date] = None
    orgfcrano: Optional[constr(min_length=5, max_length=50)] = None
    orgmvat: Optional[constr(min_length=5, max_length=50)] = None
    orgname: Optional[constr(min_length=2, max_length=100)] = None
    orgpan: Optional[str] = PANStr
    orgpincode: Optional[constr(min_length=1, max_length=10)] = None
    orgregdate: Optional[date] = None
    orgregno: Optional[constr(min_length=1, max_length=50)] = None
    orgstate: Optional[constr(min_length=2, max_length=100)] = None
    orgstax: Optional[constr(min_length=5, max_length=50)] = None
    orgtelno: Optional[constr(min_length=5, max_length=20)] = None
    orgtype: Optional[constr(min_length=2, max_length=100)] = None
    orgwebsite: Optional[constr(min_length=5, max_length=200)] = None
    roflag: Optional[int] = None
    tin: Optional[constr(min_length=5, max_length=15)] = None
    yearend: Optional[date] = None
    yearstart: Optional[date] = None
