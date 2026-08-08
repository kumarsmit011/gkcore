from gkcore.views.helpers.invoice import get_invoice_details
from sqlalchemy.sql import select
from gkcore.models.gkdb import drcr


def get_drcr_note_details(connection, drcr_id):
    """ Fetches debit-credit note entry details.

    Details will include,
    1. All debit-credit note database fields.
    2. Info available from `get_invoice_details` function.
    3. Item wise tax details for debit-credit note.
    4. Debit-credit note tax-free total.
    5. Debit-credit note tax included total.
    6. Cumulative tax amount for the debit-credit note.
    7. Document No.
    """

    drcr_note_details = connection.execute(
        select("*").where(drcr.c.drcrid == drcr_id)
    ).fetchone()
    invoice_details = get_invoice_details(connection, drcr_note_details["invid"])

    drcr_note_qty = drcr_note_details["reductionval"].pop("quantities", {})
    drcr_note_price = drcr_note_details["reductionval"]

    drcr_tax_details = []
    if invoice_details["taxflag"] == 22:
        tax_name = "VAT"
    elif invoice_details["taxflag"] == 7:
        if invoice_details["sourcestate"] == invoice_details["sourcestate"]:
            tax_name = "SGST" # "SGST" string handles both "SGST" and "CGST" for now
        else:
            tax_name = "IGST"

    total_amount = 0
    for item_id, qty in drcr_note_qty.items():
        tax_percent = float(invoice_details["tax"][item_id])
        if tax_percent == 0:
            continue
        price_taxfree = float(qty)*float(drcr_note_price[item_id])
        tax_amount = price_taxfree*tax_percent/100
        taxed_amount = price_taxfree+tax_amount
        # sale dr note: tax liability increases, sale increases
        # sale cr note: tax liability decreases, sale decreases
        # purchase dr note: tax asset increases, purchase increases
        # purchase cr note: tax asset decreases, purchase decreases
        #
        # for both sale and purchase,
        # debit note: increases the value (sales, purchase, tax)
        # credit note: decreases the value (sales, purchase, tax)
        drcr_note_sign = -1 if drcr_note_details["dctypeflag"] == 3 else 1
        total_amount += drcr_note_sign*taxed_amount
        if tax_name == "SGST": # For SGST and CGST tax amounts are half of the total GST
            tax_percent = tax_percent/2
            tax_amount = tax_amount/2
        item_tax_details = {
            "product_id": item_id,
            "tax_amount": drcr_note_sign*tax_amount,
            "tax_name": tax_name,
            "tax_str": f"{tax_percent}% {tax_name}",
            "tax_percent": tax_percent,
        }
        drcr_tax_details.append(item_tax_details)
        if tax_name == "SGST":
            tax_name = "CGST"
            drcr_tax_details.append(
                {
                    "product_id": item_id,
                    "tax_amount": drcr_note_sign*tax_amount,
                    "tax_name": tax_name,
                    "tax_str": f"{tax_percent}% {tax_name}",
                    "tax_percent": tax_percent,
                }
            )

    return {
        **drcr_note_details,
        **invoice_details,
        "document_no": drcr_note_details["drcrno"],
        "tax_data": drcr_tax_details,
        "taxed": total_amount,
    }
