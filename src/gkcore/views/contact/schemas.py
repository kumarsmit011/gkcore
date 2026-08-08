import re
from pydantic import BaseModel, EmailStr, ValidationInfo, conint, constr, field_validator, model_validator
from typing import Optional, Dict, Literal
from typing_extensions import Self
from gkcore.views.contact.services import check_custid_exists, check_duplicate_contact_account_name, check_duplicate_contact_name


class BankDetails(BaseModel):
    accountno: Optional[constr(max_length=50)] = None
    bankname: Optional[constr(max_length=200)] = None
    branchname: Optional[constr(max_length=200)] = None
    ifsc: Optional[constr(max_length=20)] = None


class ContactDetails(BaseModel):
    csflag: Literal[3, 19]
    custaddr: Optional[constr(max_length=2000)] = None
    custemail: Optional[EmailStr] = None
    custfax: Optional[str] = None
    custname: constr(max_length=200)
    custpan: Optional[constr(max_length=10)] = None
    custphone: Optional[str] = None
    custtan: Optional[constr(max_length=10)] = None
    gst_party_type: Optional[Literal[0,1,2,3]] = None
    gst_reg_type: Optional[Literal[0,1,2,3]] = None
    gstin: Optional[Dict[conint(le=100), constr(max_length=15)]] = None
    tin: Optional[constr(max_length=11)] = None
    pincode: Optional[constr(max_length=10)] = None
    country: Optional[constr(max_length=200)] = None
    state: Optional[constr(max_length=200)] = None
    bankdetails: Optional[BankDetails] = None

    @field_validator('custphone')
    @classmethod
    def validate_phone_number(cls, value):
        # Basic regular expression for validating phone numbers.
        # This will match numbers with 9-15 numbers with optional '+' sign.
        phone_regex = re.compile(r'^\+?\d{9,15}$')

        if value and not phone_regex.match(value):
            raise ValueError(f"Invalid phone number: {value}")
        return value

    @field_validator('custfax')
    @classmethod
    def validate_fax_number(cls, value):
        # Basic regular expression for validating fax numbers.
        # This will match numbers with 9-15 numbers with optional '+' sign.
        fax_regex = re.compile(r'^\+?\d{9,15}$')

        if value and not fax_regex.match(value):
            raise ValueError(f"Invalid fax number: {value}")
        return value

    @model_validator(mode="after")
    def validate(self, info: ValidationInfo) -> Self:
        check_duplicate_contact_name(
             self.custname,
             info.context["orgcode"],
             getattr(self, "custid", None),
        )
        check_duplicate_contact_account_name(
             self.custname,
             info.context["orgcode"],
             getattr(self, "custid", None),
        )
        return self


class ContactDetailsUpdate(ContactDetails):
    custid: int

    @field_validator("custid")
    @classmethod
    def custid_validate(cls, value: int, info: ValidationInfo) -> int:
        check_custid_exists(
             value,
             info.context["orgcode"],
        )
        return value
