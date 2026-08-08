from sqlalchemy import and_, or_, select
from gkcore import eng
from gkcore.models.gkdb import product, accounts


def check_duplicate_item_name(item_name, orgcode, current_item_code=None):
    """Check for entries with same name. Requires `item_name` and `orgcode`.
    `current_item_code` is required to exclude the current item from the filter while
    item name is being updated.
    """
    with eng.connect() as conn:
        statement = select([product.c.productcode]).where(
            and_(
                product.c.productdesc == item_name,
                product.c.orgcode == orgcode,
            )
        )
        if current_item_code:
            statement = statement.where(
                product.c.productcode != current_item_code,
            )
        product_results = conn.execute(statement)
        if product_results.rowcount:
            raise ValueError("This name is already used.")


def check_duplicate_item_account_name(account_name, orgcode, current_productcode=None):
    """Check for account entries with same name. Requires `account_name` and `orgcode`.
    `current_productcode` is required to exclude the current item from the filter while
    item name is being updated.
    """
    with eng.connect() as conn:
        if current_productcode:
            item = conn.execute(
                select([product.c.productdesc]).where(
                    product.c.productcode == current_productcode,
                )
            ).fetchone()
            if item["productdesc"] == account_name:
                return
        statement = select([accounts]).where(
            and_(
                or_(
                    accounts.c.accountname == account_name+" Sale",
                    accounts.c.accountname == account_name+" Purchase",
                ),
                accounts.c.orgcode == orgcode,
            )
        )
        item_results = conn.execute(statement)
        if item_results.rowcount:
            raise ValueError("This name is not available.")
