from sqlalchemy import and_, select
from gkcore import eng
from gkcore.models.gkdb import customerandsupplier, accounts


def check_duplicate_contact_name(contact_name, orgcode, current_custid=None):
    """Check for entries with same name. Requires `contact_name` and `orgcode`.
    `current_custid` is required to exclude the current item from the filter while
    item name is being updated.
    """
    with eng.connect() as conn:
        statement = select([customerandsupplier.c.custid]).where(
            and_(
                customerandsupplier.c.custname.ilike(contact_name),
                customerandsupplier.c.orgcode == orgcode,
            )
        )
        if current_custid:
            statement = statement.where(
                customerandsupplier.c.custid != current_custid,
            )
        contact_results = conn.execute(statement)
        if contact_results.rowcount:
            raise ValueError("This name is already used.")


def check_duplicate_contact_account_name(account_name, orgcode, current_custid=None):
    """Check for account entries with same name. Requires `account_name` and `orgcode`.
    `current_custid` is required to exclude the current item from the filter while
    item name is being updated.
    """
    with eng.connect() as conn:
        if current_custid:
            contact = conn.execute(
                select([customerandsupplier.c.custname]).where(
                    customerandsupplier.c.custid == current_custid,
                )
            ).fetchone()
            if contact["custname"] == account_name:
                return
        statement = select([accounts]).where(
            and_(
                accounts.c.accountname.ilike(account_name),
                accounts.c.orgcode == orgcode,
            )
        )
        contact_results = conn.execute(statement)
        if contact_results.rowcount:
            raise ValueError("This name is not available.")


def check_custid_exists(custid, orgcode):
    with eng.connect() as conn:
        result = conn.execute(
            select([customerandsupplier.c.custname]).where(
                and_(
                    customerandsupplier.c.orgcode == orgcode,
                    customerandsupplier.c.custid == custid,
                )
            )
        )
        if result.rowcount == 0:
            raise ValueError("Invalid custid.")
