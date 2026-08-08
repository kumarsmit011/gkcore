from pydantic import BaseModel
from datetime import date

class GodownRegister(BaseModel):
    goid: int
    productcode: int
    inoutflag: int = 0
    startdate: date = None
    enddate: date = None
