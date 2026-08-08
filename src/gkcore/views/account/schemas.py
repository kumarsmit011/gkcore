from pydantic import BaseModel, model_validator
from typing import Optional
from typing_extensions import Self

class AccountDetails(BaseModel):
    accountcode: Optional[int] = None
    accountname: Optional[str] = None

    @model_validator(mode="after")
    def validate_transfer_data(self, info) -> Self:
        # Custom validation for unique transfernote and orgcode
        if not (self.accountcode or self.accountname):
            raise ValueError("Either account code or account name is required.")
