from gkcore.views.helpers.account import get_account_details
from gkcore.views.helpers.invoice import get_invoice_details
from gkcore.views.helpers.drcr_note import get_drcr_note_details
from sqlalchemy.sql import select, and_
from gkcore.models.gkdb import (
    accounts,
    billwise,
    groupsubgroups,
    invoice,
    product,
    projects,
    voucherbin,
    vouchers,
)
from sqlalchemy import func, or_


def get_voucher_accounts(accounts_list, entry_type, connection):
    """Fetches the account details of voucher accounts and returns a list of dicts
    with account details."""
    voucher_accounts = []
    for account_code in accounts_list.keys():
        account_details = get_account_details(account_code, connection)
        account_details.update(
            {"amount": float(accounts_list[account_code]), "entry_type": entry_type}
        )
        voucher_accounts.append(account_details)
    return voucher_accounts


def get_transaction_details(connection, voucher_row, entry_type=None):
    """Returns details of a transaction. Dr/Cr items will be listed in a unified list
    with "name", "group", "sysaccount", "amount and entry_type" data.
    Parameters: `connection`, `voucher_row`, `entry_type`
    `entry_type` can be "Dr" or "Cr", by default its None.
    """
    transaction_details = dict(voucher_row)
    if not entry_type:
        transaction_details["transactions"] = [
            *get_voucher_accounts(voucher_row["drs"], "Dr", connection),
            *get_voucher_accounts(voucher_row["crs"], "Cr", connection),
        ]
    elif entry_type in ["Dr", "Cr"]:
        transaction_details["transactions"] = [
            *get_voucher_accounts(voucher_row[entry_type.lower()+"s"], entry_type, connection),
        ]
    else:
        raise AttributeError("'entry_type' accepts only 'Dr' and 'Cr' as allowed values")
    return transaction_details


def get_voucher_details(connection, voucher_row):
    """Fetch voucher details from voucher table and related tables. Currently, this
    function looks into invoice and debit-credit note tables. It can be expanded if
    there are other related tables.
    """
    voucher_details = get_transaction_details(connection, voucher_row)
    if voucher_row["invid"]:
        voucher_details.update(
            {
                "record_type": "invoice",
                **get_invoice_details(connection, voucher_row["invid"]),
            }
        )
    if voucher_row["drcrid"]:
        voucher_details.update(
            {
                "record_type": "drcr_note",
                **get_drcr_note_details(connection, voucher_row["drcrid"]),
            }
        )
    return voucher_details


def get_org_vouchers(
        connection,
        org_code,
        account_code=None,
        from_date=None,
        to_date=None,
        entry_type=None,
        is_cancelled=False,
        ignored_accounts=None,
):
    """ Fetches vouchers for an organization.

    This supports,
    1. Filter by period. Default is entire financial year.
    2. Filter with account. Default fetches all accounts.
    3. Filter with entry type (Dr, Cr). Default fetches all entries.
    4. Filter with cancelled status. Default is False.

    """
    voucher_table = voucherbin if is_cancelled else vouchers
    statement = select([voucher_table]).where(voucher_table.c.orgcode == org_code)
    if account_code:
        if entry_type:
            statement = statement.where(
                func.jsonb_extract_path_text(
                    getattr(voucher_table.c, entry_type.lower()+"s"), str(account_code)
                ) != None
            )
        else:
            statement = statement.where(
                or_(
                    func.jsonb_extract_path_text(
                        voucher_table.c.crs, str(account_code)
                    ) != None,
                    func.jsonb_extract_path_text(
                        voucher_table.c.drs, str(account_code)
                    ) != None,
                )
            )
    if from_date:
        statement = statement.where(voucher_table.c.voucherdate >= from_date)
    if to_date:
        statement = statement.where(voucher_table.c.voucherdate <= to_date)
    if ignored_accounts:
        for ignored_account_code in ignored_accounts:
            statement = statement.where(
                and_(
                    func.jsonb_extract_path_text(
                        voucher_table.c.crs, str(ignored_account_code)
                    ) == None,
                    func.jsonb_extract_path_text(
                        voucher_table.c.drs, str(ignored_account_code)
                    ) == None,
                )
            )
    return connection.execute(statement).fetchall()


def get_account_dr_sign(connection, account_id):
    """ This function checks if the increase in account head amounts to a Debit entry.
    If it is an asset account, it will return +1 since a Debit entry for asset means
    increase. For liability it will be -1 since a Debit entry for liability means
    decrease. The value for for dr_sign will switch between 1 and -1 wrt the behaviour
    of the account head to have Dr/Cr entry on increase or decrease.
    """

    account_details = connection.execute(
        select([accounts.c.groupcode]).where(accounts.c.accountcode == account_id)
    ).fetchone()
    group_details = connection.execute(
        select([groupsubgroups.c.subgroupof, groupsubgroups.c.groupname]).where(
            groupsubgroups.c.groupcode == account_details["groupcode"]
        )
    ).fetchone()
    if group_details["subgroupof"]:
        group_details = connection.execute(
            select([groupsubgroups.c.subgroupof, groupsubgroups.c.groupname]).where(
                groupsubgroups.c.groupcode == group_details["subgroupof"]
            )
        ).fetchone()

    # groups where Dr entry means increase in modern golden rules of accounting.
    dr_positive_groups = [
        "Current Assets",
        "Direct Expense",
        "Fixed Assets",
        "Indirect Expense",
        "Investments",
        "Loans(Asset)",
        "Reserves",
        "Miscellaneous Expenses(Asset)",
        "Current Assets",
    ]
    # groups where Cr entry means increase in modern golden rules of accounting.
    dr_negative_groups = [
        "Current Liabilities",
        "Direct Income",
        "Indirect Income",
        "Loans(Liability)",
        "Capital",
    ]

    if group_details["groupname"] in dr_positive_groups:
        return 1
    if group_details["groupname"] in dr_negative_groups:
        return -1
    raise Exception(
        f"Group {group_details['groupname']} is not in `get_account_dr_sign` function."
    )


def generate_consolidated_voucher_data(connection, voucher_rows, account_id):
    """ Calculate consolidated data for a list of vouchers.

    This function accept SQLAlchemy result proxy rows of voucher table and account_id
    to which consolidated data is generated.

    This should be automatically fetched from account_id.

    This function will give,
    1. Voucher list with voucher details,
    2. Total voucher amount,
    3. Total taxed amount,
    4. Total taxes,
    5. Tax strings for the tax entries in the voucher,
    6. Total credit entry,
    7. Total debit entry.
    """


    dr_sign = get_account_dr_sign(connection, account_id)
    cr_sign = -1*dr_sign
    voucher_total = 0
    taxed_total = 0
    tax_strings = set()
    tax_totals = {}
    dr_total = 0
    cr_total = 0
    voucher_list = []
    for voucher_row in voucher_rows:
        voucher_details = get_voucher_details(connection, voucher_row)
        cr_amount = cr_sign * float(voucher_details["crs"].get(str(account_id), 0))
        dr_amount = dr_sign * float(voucher_details["drs"].get(str(account_id), 0))
        dr_total += dr_amount
        cr_total += cr_amount
        amount = cr_amount + dr_amount
        voucher_details["taxed"] = voucher_details.get("taxed") or amount
        voucher_details["tax_data"] = voucher_details.get("tax_data") or []
        voucher_details["custname"] = (
            voucher_details.get("custname") or voucher_details["vouchertype"].title()
        )
        taxed_total += voucher_details["taxed"]
        voucher_details["amount"] = amount
        voucher_total += amount
        for tax_item in voucher_details["tax_data"]:
            tax_str = tax_item["tax_str"]
            tax_strings.add(tax_str)
            tax_totals[tax_str] = (
                tax_totals.get(tax_str, 0) + float(tax_item["tax_amount"])
            )
        voucher_list.append(voucher_details)
    return {
        "vouchers": voucher_list,
        "voucher_total": voucher_total,
        "taxed_total": taxed_total,
        "tax_strings": tax_strings,
        "tax_totals": tax_totals,
        "cr_total": cr_total,
        "dr_total": dr_total,
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

def move_voucher_to_bin(con, voucher_code):
    """Soft delete voucher record with the given voucher code by removing it
    from voucher table and adding to voucherbin table.
    """
    voucher = con.execute(
        select([vouchers]).where(vouchers.c.vouchercode == int(voucher_code))
    ).fetchone()
    voucherbin_data = dict(voucher.items())

    project_name = con.execute(
        select([projects.c.projectname]).where(
            projects.c.projectcode == voucher["projectcode"]
        )
    ).scalar() or ""

    drs = voucher["drs"]
    crs = voucher["crs"]
    drs_with_account_names = {}
    crs_with_account_names = {}

    for dr in list(drs.keys()):
        # Update voucher count in accounts table
        con.execute(
            accounts.update()
            .where(accounts.c.accountcode == int(dr))
            .values(vouchercount = accounts.c.vouchercount - 1)
        )
        # Get dr account names to be stored in voucherbin table for backwards compatibility
        dr_account_name = con.execute(
            select([accounts.c.accountname])
            .where(accounts.c.accountcode == int(dr))
        ).scalar()
        drs_with_account_names[dr_account_name] = drs[dr]

    for cr in list(crs.keys()):
        # Update voucher count in accounts table
        con.execute(
            accounts.update()
            .where(accounts.c.accountcode == int(cr))
            .values(vouchercount = accounts.c.vouchercount - 1)
        )
        # Get cr account names to be stored in voucherbin table for backwards compatibility
        cr_account_name = con.execute(
            select([accounts.c.accountname])
            .where(accounts.c.accountcode == int(cr))
        ).scalar()
        crs_with_account_names[cr_account_name] = crs[cr]

    # Add Drs and Crs with account names and project name to voucherbin_data
    # and insert it to voucherbin table.
    voucherbin_data.update({
        "drs": drs_with_account_names,
        "crs": crs_with_account_names,
        "projectname": project_name,
    })
    con.execute(voucherbin.insert(), [voucherbin_data])

    # Delete voucher from voucher table
    con.execute(
        vouchers.delete().where(and_(
            vouchers.c.vouchercode == int(voucher_code),
            vouchers.c.lockflag == 'f',
        ))
    )

def cancel_voucher(con, voucher_code, org_code):
    """Cancel voucher with the given voucher code.
    This updates all tables affected by the given voucher. It also calls
    move_voucher_to_bin function for soft deleting the voucher record by moving
    it to the voucherbin table."""

    # Fetch related billwise entries
    billwise_entries = con.execute(
        select([billwise.c.invid])
        .where(billwise.c.vouchercode == int(voucher_code))
    ).fetchall()
    for billwise_entry in billwise_entries:
        adjusted_amount = con.execute(
            select([billwise.c.adjadmount]).where(and_(
                billwise.c.vouchercode == int(voucher_code),
                billwise.c.invid == billwise_entry["invid"],
            ))
        ).fetchone()

        # Deduct the amount in billwise entry from invoice
        con.execute(
            invoice.update().where(and_(
                invoice.amountpaid == float(adjusted_amount["adjamount"]),
                invoice.c.invid == billwise_entry["invid"],
                invoice.c.orgcode == int(org_code),
            ))
        )

        # If the given voucher is for invoice, check for related round-off voucher
        # and soft delete it and delete its billwise entry.
        invoice_round_off_voucher_id = con.execute(
            select([vouchers.c.vouchercode]).where(and_(
                vouchers.c.invid == int(billwise_entry["invid"]),
                vouchers.c.orgcode == int(org_code),
                vouchers.c.narration.like("Round off amount%"),
            ))
        ).scalar()
        if invoice_round_off_voucher_id:
            con.execute(
                billwise.delete()
                .where(billwise.c.vouchercode == int(invoice_round_off_voucher_id))
            )
            move_voucher_to_bin(con, invoice_round_off_voucher_id)

    # Delete billwise entry of the given voucher
    con.execute(
        billwise.delete()
        .where(billwise.c.vouchercode == int(voucher_code))
    )

    # If the given voucher is for debit or credit note,
    # check for related round-off voucher and soft delete it.
    drcr_note_id = con.execute(
        select([vouchers.c.drcrid])
        .where(vouchers.c.vouchercode == int(voucher_code))
    ).scalar()
    if drcr_note_id:
        drcr_note_round_off_voucher_id = con.execute(
            select([vouchers.c.vouchercode]).where(
                and_(
                    vouchers.c.drcrid == int(drcr_note_id),
                    vouchers.c.orgcode == int(orgcode),
                    vouchers.c.narration.like("Round off amount%"),
                )
            )
        ).scalar()
        if drcr_note_round_off_voucher:
            move_voucher_to_bin(con, drcr_note_round_off_voucher_id)

    # Soft delete the given voucher
    move_voucher_to_bin(con, voucher_code)
