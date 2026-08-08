import re
from pydantic import BaseModel, Field, constr, field_validator
from gkcore.models.gkdb import organisation
from gkcore import eng
from sqlalchemy.sql import select


class UserLogin(BaseModel):
    # Username can be of 3-40 charcters of alpha numeric or "_" type.
    username: constr(pattern=re.compile(r'^[a-zA-Z0-9_]{3,40}$'))
    # Userpassword can be of 128 charcters of alpha numeric type.
    userpassword: str = Field(min_length=3)


class OrgLogin(BaseModel):
    orgcode: int

    @field_validator('orgcode')
    @classmethod
    def validate_orgcode(cls, value):
        with eng.connect() as conn:
            org_query = conn.execute(
                select([organisation]).where(
                    organisation.c.orgcode == value
                )
            )
            if not org_query.rowcount:
                raise ValueError(
                    f"Organisation not found for orgcode: {value}"
                )
        return value
