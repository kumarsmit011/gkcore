from pydantic import BaseModel, constr
from typing import Optional


class AccountLog(BaseModel):
     activity: Optional[constr(max_length=1000)]
