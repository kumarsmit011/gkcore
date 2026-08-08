from sqlalchemy import select, exists, and_
from gkcore.models.gkdb import unitofmeasurement
from gkcore import eng


def uom_exists(uomid: int, uqc: bool = False) -> bool:
    """Check if a parent unit exists in the database."""
    with eng.connect() as conn:
        query = exists().where(unitofmeasurement.c.uomid == uomid)
        if uqc:
            query = query.where(unitofmeasurement.c.sysunit == 1)
        return conn.execute(select([query])).scalar()


def unit_name_exists(unitname: str, orgcode: int, uomid: int|None = None) -> bool:
    """Check if a unit name already exists for a specific organization."""
    with eng.connect() as con:
        statement = exists().where(
            and_(
                unitofmeasurement.c.unitname == unitname,
                unitofmeasurement.c.orgcode == orgcode,
            )
        )
        if uomid:
            statement = statement.where(unitofmeasurement.c.uomid != uomid)

        return con.execute(select([statement])).scalar()
