from sqlalchemy.sql import select
from gkcore.models.gkdb import accounts, groupsubgroups

def get_account_details(account_code, connection):
    """Fetches the account details and returns a dict with keys, "name", "group" and
    "sysaccount"."""
    account = connection.execute(
        select("*").where(accounts.c.accountcode == account_code)
    ).fetchone()
    return {
        "account_name": account["accountname"],
        "account_group": account["groupcode"],
        "is_sysaccount": account["sysaccount"]
    }


def get_account_grouping(connection, groupcode):
    """Fetch group data along with parent group data if exists.
    """
    group = connection.execute(
        select([groupsubgroups])
        .where(groupsubgroups.c.groupcode == groupcode)
    ).fetchone()
    if group["subgroupof"]:
        return {
            "subgroupcode": group["groupcode"],
            "subgroupname": group["groupname"],
            **get_account_grouping(connection, group["subgroupof"])
        }
    return {
        "groupcode": group["groupcode"],
        "groupname": group["groupname"],
    }
