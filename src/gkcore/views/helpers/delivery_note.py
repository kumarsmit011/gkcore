from datetime import datetime
from sqlalchemy.sql import select, and_
from gkcore.models.gkdb import (
    dcinv,
    delchal,
    delchalbin,
    product,
    stock,
)


def create_delivery_note(con, payload, org_code):
    """Create delivery note and update stock with the details in the given payload."""

    delivery_note_details = payload['delchalPayload']["delchaldata"]
    delivery_note_details["orgcode"] = org_code
    items = delivery_note_details["contents"]
    item_id_values = list(items.keys())

    # Fetch gsflag of invoice items.
    # gsflag 7 represents goods (products), 13 represents services.
    gsflag_values = con.execute(
        select([product.c.productcode, product.c.gsflag])
        .where(product.c.productcode.in_(item_id_values))
    ).fetchall()

    # Proceed only if invoice items contain products since services won't have
    # delivery note.
    product_id_values = [id for id, flag in gsflag_values if flag == 7]
    if not product_id_values:
        return

    # Remove services, if any, from delivery note details
    products = {id: val for id, val in items.items() if int(id) in product_id_values}
    delivery_note_details["contents"] = products

    # Create delivery note and fetch its id
    delivery_note_id = con.execute(
        delchal.insert(), [delivery_note_details]
    ).inserted_primary_key[0]

    # Update stock data based on the delivery note details.
    # dicintnflag 4 indicates that the stock movement is recorded as part of
    # creating delivery note.
    stock_details = payload['delchalPayload']["stockdata"]
    stock_details["dcinvtnflag"] = 4
    stock_details["dcinvtnid"] = delivery_note_id
    stock_details["stockdate"] = delivery_note_details["dcdate"]
    stock_details["orgcode"] = org_code

    item_wise_discount = payload["payload"]["invoice"]["discount"]
    item_wise_free_qty = delivery_note_details["freeqty"]

    for product_id, transaction_details in products.items():
        # transaction_details is a dictionary with product rate as key and qty as value
        rate = float(list(transaction_details.keys())[0])
        qty = float(list(transaction_details.values())[0])
        total_discount = float(item_wise_discount.get(product_id, 0))
        discount = 0
        if qty:
            discount = total_discount / qty
        stock_details["rate"] = rate - discount
        stock_details["productcode"] = product_id
        stock_details["qty"] = qty + float(item_wise_free_qty[product_id])
        result = con.execute(stock.insert(), [stock_details])

    return delivery_note_id


def move_delivery_note_to_bin(con, delivery_note_id, org_code):
    """Soft delete delivery note record with the given id by removing it
    from delchal table and adding to delchalbin table.
    """

    # Fetch details of the given delivery note from the delchal table
    delivery_note = con.execute(
        select([delchal]).where(delchal.c.dcid == delivery_note_id)
    ).fetchone()
    delivery_note_archive = dict(delivery_note.items())

    # Fetch adjusted stock id and related godown id from stock table.
    # dcinvtnflag 4 is used to filter stock adjustment by delivery note.
    adjusted_stock = con.execute(
        select([stock.c.stockid, stock.c.goid]).where(and_(
            stock.c.dcinvtnid == int(delivery_note_id),
            stock.c.dcinvtnflag == 4,
            stock.c.orgcode == org_code,
        ))
    ).fetchone()

    # If stock record exists, update delivery_note_archive with godown id
    # and delete the stock record.
    godown_id = None
    if hasattr(adjusted_stock, "stockid"):
        stock_id = adjusted_stock["stockid"]
        godown_id = adjusted_stock["goid"]
        delivery_note_archive.update({
            "goid": godown_id,
        })
        con.execute(stock.delete().where(stock.c.stockid == stock_id))

    # Move delivery note data from delchal table to delchalbin table
    con.execute(delchalbin.insert(), [delivery_note_archive])
    con.execute(
        delchal.delete().where(and_(
            delchal.c.dcid == int(delivery_note_id),
            delchal.c.orgcode == org_code,
        ))
    )

    # Return related data
    return {
        **delivery_note_archive,
        "dcno": delivery_note["dcno"],
        "dcdate": datetime.strftime(delivery_note["dcdate"], "%d-%m-%Y"),
    }


def cancel_delivery_note(con, invoice_id, org_code):
    """Cancel delivery note related to the given invoice id.
    This updates all tables affected by the given delivery note. It also calls
    move_delivery_note_to_bin function for soft deleting the delivery note
    record by moving it from delchal table to the delchalbin table."""

    # Fetch details of delivery note related to the given invoice from dcinv table
    delivery_note = con.execute(
        select([dcinv.c.dcinvid, dcinv.c.dcid]).where(and_(
            dcinv.c.invid == int(invoice_id),
            dcinv.c.orgcode == org_code,
        ))
    ).fetchone()

    # Exit if no related delivery note found
    if not hasattr(delivery_note, "dcinvid"):
        return None

    # Delete dcinv record which connects invoice and delivery note
    con.execute(
        dcinv.delete()
        .where(dcinv.c.dcinvid == delivery_note["dcinvid"])
    )

    delivery_note_details = None
    if delivery_note["dcid"]:
        # Soft delete delivery note
        delivery_note_details = move_delivery_note_to_bin(
            con, delivery_note["dcid"], org_code,
        )

    return delivery_note_details
