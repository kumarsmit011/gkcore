from sqlalchemy import and_, select
from gkcore import eng
from gkcore.models.gkdb import godown, transfernote, product


def check_duplicate_transfer_note(transfernote_no, orgcode, current_transfernoteid=None):
    """Check for entries with same transfernote no. Requires `transfernote_no` and `orgcode`.
    `current_transfernoteid` is required to exclude the current item from the filter while
    item transfernote no is being updated.
    """
    with eng.connect() as con:
        statement = select([transfernote.c.transfernoteid]).where(
            and_(
                transfernote.c.transfernoteno == transfernote_no,
                transfernote.c.orgcode == orgcode,
            )
        )
        if current_transfernoteid:
            statement = statement.where(
                transfernote.c.transfernoteid != current_transfernoteid,
            )
        if con.execute(statement).rowcount:
            raise ValueError("Transfernote no is already used.")

def godown_exists(pk):
    with eng.connect() as con:
        return bool(
            con.execute(
                godown.select().where(godown.c.goid == pk)
            ).rowcount
        )

def item_exists(pk):
    with eng.connect() as con:
        return bool(
            con.execute(
                product.select().where(product.c.productcode == pk)
            ).rowcount
        )
