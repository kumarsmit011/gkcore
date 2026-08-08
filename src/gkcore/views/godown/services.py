from gkcore import eng, enumdict
from sqlalchemy import select, and_, func
from gkcore.models.gkdb import godown, usergodown, stock, state

def getusergodowns(con, userid):
    uid = userid
    godowns = con.execute(
        select([godown]).where(
            and_(
                godown.c.goid.in_(
                    select([usergodown.c.goid]).where(usergodown.c.userid == uid)
                )
            )
        )
    )
    usergo = []
    srno = 1
    for row in godowns:
        godownstock = con.execute(
            select([func.count(stock.c.goid).label("godownstockstatus")]).where(
                stock.c.goid == row["goid"]
            )
        )

        godownstockcount = godownstock.fetchone()
        godownstatus = godownstockcount["godownstockstatus"]

        if godownstatus > 0:
            status = "Active"
        else:
            status = "Inactive"

        usergo.append(
            {
                "godownstatus": status,
                "srno": srno,
                "goid": row["goid"],
                "goname": row["goname"],
                "goaddr": row["goaddr"],
                "gocontact": row["gocontact"],
                "state": row["state"],
                "contactname": row["contactname"],
                "designation": row["designation"],
            }
        )

        srno = srno + 1
    return {"gkstatus": enumdict["Success"], "gkresult": usergo}


def state_exists(name):
    with eng.connect() as con:
        return bool(
            con.execute(
                state.select().where(state.c.statename == name)
            ).rowcount
        )

def check_duplicate_godown_name(godown_name, orgcode, current_goid=None):
    """Check for entries with same godown name. Requires `godown_name` and `orgcode`.
    `current_goid` is required to exclude the current item from the filter while
    item is being updated.
    """
    with eng.connect() as con:
        statement = select([godown.c.goid]).where(
            and_(
                godown.c.goname == godown_name,
                godown.c.orgcode == orgcode,
            )
        )
        if current_goid:
            statement = statement.where(
                godown.c.goid != current_goid,
            )
        if con.execute(statement).rowcount:
            raise ValueError("Godown name is already used.")
