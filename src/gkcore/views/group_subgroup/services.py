from sqlalchemy import and_, select
from gkcore import eng
from gkcore.models.gkdb import groupsubgroups


def check_duplicate_group_name(group_name, orgcode, current_groupcode=None):
    """Check for entries with same name. Requires `group_name` and `orgcode`.
    `current_groupcode` is required to exclude the current item from the filter while
    item name is being updated.
    """
    with eng.connect() as conn:
        statement = select([groupsubgroups.c.groupcode]).where(
            and_(
                groupsubgroups.c.groupname == group_name,
                groupsubgroups.c.orgcode == orgcode,
            )
        )
        if current_groupcode:
            statement = statement.where(
                groupsubgroups.c.groupcode != current_groupcode,
            )
        group_results = conn.execute(statement)
        if group_results.rowcount:
            raise ValueError("This name is already used.")


def check_groupcode_exists(groupcode, orgcode):
    with eng.connect() as conn:
        result = conn.execute(
            select([groupsubgroups.c.groupcode]).where(
                and_(
                    groupsubgroups.c.orgcode == orgcode,
                    groupsubgroups.c.groupcode == groupcode,
                )
            )
        )
        if result.rowcount == 0:
            raise ValueError("Invalid groupcode.")

def check_parent_group_exists(groupcode, orgcode):
    with eng.connect() as conn:
        result = conn.execute(
            select([groupsubgroups.c.groupcode]).where(
                and_(
                    groupsubgroups.c.orgcode == orgcode,
                    groupsubgroups.c.groupcode == groupcode,
                    groupsubgroups.c.subgroupof == None,
                )
            )
        )
        if result.rowcount == 0:
            raise ValueError("Invalid groupcode.")
