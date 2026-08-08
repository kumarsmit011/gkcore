from gkcore.models.gkdb import accounts
from sqlalchemy.sql import select


def reset_acc_defaults(con, orgcode):
    acc_list = con.execute(
        select([accounts.c.accountcode, accounts.c.accountname]).where(
            accounts.c.orgcode == orgcode
        )
    ).fetchall()
    default_acc = {
        "Bank A/C": 2,
        "Cash in hand": 3,
        "Purchase A/C": 16,
        "Sale A/C": 19,
        "Round Off Paid": 180,
        "Round Off Received": 181,
    }
    for acc in acc_list:
        default_code = 0
        if acc["accountname"] in default_acc:
            default_code = default_acc[acc["accountname"]]
        con.execute(
            accounts.update()
            .where(accounts.c.accountcode == acc["accountcode"])
            .values(defaultflag=default_code)
        )
