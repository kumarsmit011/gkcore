from sqlalchemy.sql import select
from gkcore.models.gkdb import customerandsupplier


def get_party_details(connection, party_id):
    """Fetches party details of the given party_id (`custid` in `customerandsupplier`).
    """
    return connection.execute(
        select(
            [
                customerandsupplier.c.custid,
                customerandsupplier.c.custname,
                customerandsupplier.c.custaddr,
                customerandsupplier.c.custpan,
                customerandsupplier.c.custtan,
                customerandsupplier.c.gstin,
            ]
        ).where(customerandsupplier.c.custid == party_id)
    ).fetchone()
