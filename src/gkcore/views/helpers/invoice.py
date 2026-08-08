from gkcore.views.helpers.contact import get_party_details
from sqlalchemy.sql import select
from gkcore.models.gkdb import invoice, state, product, transaction
from sqlalchemy import func
from gkcore import enumdict


def get_invoice_details(connection, invoice_id):
    """ Fetches invoice details.

    Details will include,
    1. Invoice database fields: `invid`, `invoiceno`, `invnarration`, `contents`,
    `invoicedate`, `invoicetotal`, `icflag`, `custid`, `inoutflag`, `address`,
    `tax`, `taxflag`, `taxstate`, `sourcestate`, `cess` and `discount`.
    2. Party details - contact details of customer/seller.
    3. GSTIN.
    4. Item wise tax details.
    5. Invoice tax free total.
    6. Invoice tax included total.
    7. Cumulative tax amount for the invoice.
    8. Document No.
    """

    invoice_details = connection.execute(
        select(
            [
                invoice.c.invid,
                invoice.c.invoiceno,
                invoice.c.invnarration,
                invoice.c.contents,
                invoice.c.invoicedate,
                invoice.c.invoicetotal,
                invoice.c.icflag,
                invoice.c.custid,
                invoice.c.inoutflag,
                invoice.c.address,
                invoice.c.tax,
                invoice.c.taxflag,
                invoice.c.taxstate,
                invoice.c.sourcestate,
                invoice.c.cess,
                invoice.c.discount,
                invoice.c.consignee,
                transaction.c.transaction_details,
            ]
        )
        .select_from(invoice.join(transaction))
        .where(invoice.c.invid == invoice_id)
    ).fetchone()

    party_details = get_party_details(connection, invoice_details["custid"])

    try:
        gstin = list(invoice_details["transaction_details"]["contact"]["gstin"].values())[0]
    except (AttributeError, TypeError, IndexError):
        gstin = ""

    tax_details = []
    tax_name = None
    if invoice_details["taxflag"] == 22:
        tax_name = "VAT"
    elif invoice_details["taxflag"] == 7:
        if invoice_details["sourcestate"] == invoice_details["taxstate"]:
            tax_name = "SGST"
        else:
            tax_name = "IGST"


    tax_total = sum([float(value) for value in invoice_details["tax"].values()])
    invoice_total_taxfree = float(invoice_details["invoicetotal"])*100/(100+tax_total)

    for item_id, tax_percent in invoice_details["tax"].items():
        tax_percent = float(tax_percent)/2 if tax_name == "SGST" else float(tax_percent)
        item_qty = float(list(invoice_details["contents"][item_id].values())[0])
        item_price = float(list(invoice_details["contents"][item_id].keys())[0])
        item_discount = float(invoice_details["discount"][item_id])
        item_price_taxfree = item_price * item_qty - item_discount
        tax_amount = item_price_taxfree * tax_percent/100
        if not tax_amount:
            continue
        item_tax_details = {
            "product_id": item_id,
            "tax_amount": tax_amount,
            "tax_name": tax_name,
            "tax_str": f"{tax_percent}% {tax_name}",
            "tax_percent": tax_percent,
        }
        tax_details.append(item_tax_details)
        if tax_name == "SGST":
            tax_details.append(
                {
                    "product_id": item_id,
                    "tax_amount": tax_amount,
                    "tax_name": "CGST",
                    "tax_str": f"{tax_percent}% CGST",
                    "tax_percent": tax_percent,
                }
            )

    return {
        **dict(invoice_details),
        **dict(party_details),
        "document_no": invoice_details["invoiceno"],
        "tax_total": sum([float(value) for value in invoice_details["tax"].values()]),
        "tax_data": tax_details,
        "taxfree": f"{invoice_total_taxfree:.2f}",
        "taxed": float(invoice_details['invoicetotal']),
        "gstin": gstin,
    }


def get_business_item_invoice_data(
        connection,
        product_code,
        from_date = None,
        to_date = None,
):
    """Calculates total purchase and sales for a product. Product code is required, from
    date and to dates are optional. Returns tuple (Purchase Total, Sales Total)
    """
    statement = (
        select(
            [
                invoice.c.contents[str(product_code)],
                invoice.c.discount[str(product_code)],
                invoice.c.inoutflag,
            ]
        )
        .where(func.jsonb_extract_path_text(invoice.c.contents, str(product_code)) != None)
    )

    if from_date:
        statement = statement.where(invoice.c.invoicedate >= from_date)
    if to_date:
        statement = statement.where(invoice.c.invoicedate <= to_date)

    invoices = connection.execute(statement).fetchall()

    total_purchase = 0
    total_sale = 0
    for sale_obj, discount, inout_flag in invoices:
        for amount, quantity in sale_obj.items():
            if inout_flag == 9:
                total_purchase += float(amount)*float(quantity) - float(discount)
            if inout_flag == 15:
                total_sale += float(amount)*float(quantity) - float(discount)
    return total_purchase, total_sale


def get_org_invoice_data(
        connection,
        org_code,
        from_date = None,
        to_date = None,
        gsflag = None,
):
    """Calculates total purchase and sales for a org. Organization code is required,
    from date, to date and gsflag are optional. If gsflag is given it will give result
    for the given gsflag (Service:19, Product:7). Returns tuple (Purchase Total,
    Sales Total)
    """
    statement = select([product.c.productcode]).where(
            product.c.orgcode == org_code
        )
    if gsflag:
        statement = statement.where(product.c.gsflag == gsflag)
    business_items = connection.execute(statement).fetchall()
    org_total_purchase = 0
    org_total_sale = 0
    for product_code in business_items:
        total_purchase, total_sale = get_business_item_invoice_data(
            connection, product_code[0], from_date, to_date
        )
        org_total_purchase += total_purchase
        org_total_sale += total_sale
    return org_total_purchase, org_total_sale


def billwiseEntryLedger(con, orgcode, vouchercode, invid, drcrid):
    try:
        dcinfo = ""
        if invid == None:
            billdetl = con.execute(
                "select invid, adjamount from billwise where vouchercode = %d and orgcode =%d"
                % (vouchercode, orgcode)
            )
            billDetails = billdetl.fetchall()
            if len(billDetails) != 0:
                inno = "Invoice Nos.:"
                cmno = "Cash Memo Nos.:"
                for inv in billDetails:
                    invno = con.execute(
                        "select invoiceno, icflag from invoice where invid = %d and orgcode = %d"
                        % (inv["invid"], orgcode)
                    )
                    invinfo = invno.fetchone()
                    if invinfo["icflag"] == 9:
                        inno += (
                            str(invinfo["invoiceno"])
                            + ":"
                            + str(inv["adjamount"])
                            + ","
                        )
                        dcinfo = inno
                    else:
                        cmno += (
                            str(invinfo["invoiceno"])
                            + ":"
                            + str(inv["adjamount"])
                            + ","
                        )
                        dcinfo = cmno
        else:
            invno = con.execute(
                "select  invoiceno, icflag from invoice where invid = %d and orgcode = %d"
                % (invid, orgcode)
            )
            invinfo = invno.fetchone()
            if invinfo["icflag"] == 9:
                dcinfo = "Invoice No.:" + str(invinfo["invoiceno"])
            else:
                dcinfo = "Cash Memo No.:" + str(invinfo["invoiceno"])
        if drcrid != None:
            drcrno = con.execute(
                "select drcrno, dctypeflag from drcr where drcrid = %d and orgcode = %d"
                % (drcrid, orgcode)
            )
            drcrinfo = drcrno.fetchone()
            if drcrinfo["dctypeflag"] == 3:
                dcinfo = "Credit note no.:" + str(drcrinfo["drcrno"])
            else:
                dcinfo = "Dedit note no.:" + str(drcrinfo["drcrno"])
        return dcinfo
    except:
        return {"gkstatus": enumdict["ConnectionFailed"]}
