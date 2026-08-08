"""
This file is part of GNUKhata:A modular,robust and Free Accounting System.

License: AGPLv3

Contributors:
"Sai Karthik" <kskarthik@disroot.org>
"Krishnakant Mane" <kkmane@riseup.net>
"Ishan Masdekar " <imasdekar@dff.org.in>
"Navin Karkera" <navin@dff.org.in>
'Prajkta Patkar'<prajakta@dff.org.in>
'Reshma Bhatwadekar'<reshma_b@riseup.net>
"Sanket Kolnoorkar"<Sanketf123@gmail.com>
'Aditya Shukla' <adityashukla9158.as@gmail.com>
'Pravin Dake' <pravindake24@gmail.com>

"""

import os
from gkcore import eng
from gkcore.data.uoms import UQC_LIST
from gkcore.views.api_invoice import rename_inv_no_uniquely
from sqlalchemy.exc import IntegrityError
from gkcore.models import gkdb
from sqlalchemy import and_, func, select
from gkcore.models.meta import (
    does_foreignkey_exist,
    does_check_constraint_exist,
    does_unique_constraint_exist,
    does_primarykey_exist,
    columnExists,
    tableExists,
    getOnDelete,
    uniqueConstraintExists,
)
from gkcore.models.gkdb import state, bank
from datetime import datetime, timedelta
import traceback


def migrate():
    """
    This function will be called only once while upgrading gnukhata.
    The function will be mostly concerned with adding new fields to the databse or altering those which are present.
    The columnExists() function will be used to check if a certain column exists.
    If the function returns False then the field is created.
    For example:
    We check if the field stockdate is present.
    If it is not present it means that this is an upgrade.
    """
    with eng.connect() as con:
        organisations = con.execute(select([gkdb.organisation.c.orgcode]))
        allorg = organisations.fetchall()
        if not tableExists("cslastprice"):
            con.execute(
                "create table cslastprice(cslpid serial, lastprice numeric(13,2), inoutflag integer, custid integer NOT NULL,productcode integer NOT NULL,orgcode integer NOT NULL, primary key (cslpid), constraint cslastprice_orgcode_fkey FOREIGN KEY (orgcode) REFERENCES organisation(orgcode), constraint cslastprice_custid_fkey FOREIGN KEY (custid) REFERENCES customerandsupplier(custid),constraint cslastprice_productcode_fkey FOREIGN KEY (productcode) REFERENCES product(productcode), unique(orgcode, custid, productcode, inoutflag))"
            )
            inoutflags = [9, 15]
            for orgid in allorg:
                numberOfInvoices = con.execute(
                    select([func.count(gkdb.invoice.c.invid).label("invoices")])
                )
                invoices = numberOfInvoices.fetchone()
                if int(invoices["invoices"]) > 0:
                    customers = con.execute(
                        select([gkdb.customerandsupplier.c.custid]).where(
                            gkdb.customerandsupplier.c.orgcode
                            == int(orgid["orgcode"])
                        )
                    )
                    customerdata = customers.fetchall()
                    products = con.execute(
                        select([gkdb.product.c.productcode]).where(
                            gkdb.product.c.orgcode == int(orgid["orgcode"])
                        )
                    )
                    productdata = products.fetchall()
                    for customer in customerdata:
                        for product in productdata:
                            for inoutflag in inoutflags:
                                try:
                                    lastInvoice = con.execute(
                                        "select max(invid) as invid from invoice where orgcode = %d and contents ? '%s' and inoutflag = %d and custid = %d"
                                        % (
                                            int(orgid["orgcode"]),
                                            str(product["productcode"]),
                                            int(inoutflag),
                                            int(customer["custid"]),
                                        )
                                    )
                                    lastInvoiceId = lastInvoice.fetchone()["invid"]
                                    if lastInvoiceId != None:
                                        lastPriceData = con.execute(
                                            select([gkdb.invoice.c.contents]).where(
                                                and_(
                                                    gkdb.invoice.c.invid
                                                    == int(lastInvoiceId),
                                                    gkdb.product.c.orgcode
                                                    == int(orgid["orgcode"]),
                                                )
                                            )
                                        )
                                        lastPriceDict = lastPriceData.fetchone()[
                                            "contents"
                                        ]
                                        productCode = product["productcode"]
                                        if (
                                            str(productCode).decode("utf-8")
                                            in lastPriceDict
                                        ):
                                            lastPriceValue = list(
                                                lastPriceDict[
                                                    str(productCode).decode("utf-8")
                                                ].keys()
                                            )[0]
                                            priceDetails = {
                                                "custid": int(customer["custid"]),
                                                "productcode": int(
                                                    product["productcode"]
                                                ),
                                                "orgcode": int(orgid["orgcode"]),
                                                "inoutflag": int(inoutflag),
                                                "lastprice": float(lastPriceValue),
                                            }
                                            lastPriceEntry = con.execute(
                                                gkdb.cslastprice.insert(),
                                                [priceDetails],
                                            )
                                except:
                                    pass
    with eng.connect() as con:
        if not does_foreignkey_exist(
                eng,
                "unitofmeasurement",
                "unitofmeasurement_subunitof_fkey"
        ):
            con.execute(
                "alter table unitofmeasurement add  foreign key (subunitof) references unitofmeasurement(uomid)"
            )


        if not columnExists("unitofmeasurement", "description"):
            con.execute("alter table unitofmeasurement add description text")
            con.execute(
                "alter table unitofmeasurement add sysunit integer default 0"
            )

        # Add default UQCs
        for unit, desc in list(UQC_LIST.items()):
            if not con.execute(
                    select([gkdb.unitofmeasurement])
                    .where(
                        and_(
                            gkdb.unitofmeasurement.c.unitname == unit,
                            gkdb.unitofmeasurement.c.sysunit == 1,
                        )
                    )
            ).fetchone():
                con.execute(
                    gkdb.unitofmeasurement.insert(),
                    [
                        {
                            "unitname": unit,
                            "description": desc,
                            "conversionrate": 0.00,
                            "sysunit": 1,
                        }
                    ],
                )

            UQC_LIST.pop(unit, 0)

        if not columnExists("unitofmeasurement", "uqc"):
            con.execute("alter table unitofmeasurement add uqc integer")

    with eng.connect() as con:
        if not does_foreignkey_exist(
                eng,
                "groupsubgroups",
                "groupsubgroups_subgroupof_fkey"
        ):
            con.execute(
                "alter table groupsubgroups add  foreign key (subgroupof) references groupsubgroups(groupcode)"
            )
        if not does_foreignkey_exist(
                eng,
                "categorysubcategories",
                "categorysubcategories_subcategoryof_fkey"
        ):
            con.execute(
                "alter table categorysubcategories add  foreign key (subcategoryof) references categorysubcategories(categorycode)"
            )

    with eng.connect() as con:
        # discount flag is use to check whether discount is in percent or in amount.
        # 1 = discount in amount, 16 = discount in percent.
        if not columnExists("delchal", "discflag"):
            con.execute(
                "alter table invoicebin add column discflag integer default 1"
            )
            con.execute(
                "alter table invoice add column discflag integer default 1"
            )
            con.execute(
                "alter table delchal add column discflag integer default 1"
            )
            # in product following two collumns are added for discount in percent and in amount.
            con.execute(
                "alter table product add column percentdiscount numeric(5,2) default 0.00"
            )
            con.execute(
                "alter table product add column amountdiscount numeric(13,2) default 0.00"
            )

    with eng.connect() as con:
        # Round off is use to detect that total amount of invoice is rounded off or not.
        # If the field is not exist then it will create field.
        if not columnExists("purchaseorder", "roundoffflag"):
            con.execute(
                "alter table purchaseorder add column roundoffflag integer default 0"
            )
            con.execute(
                "alter table delchal add column roundoffflag integer default 0"
            )
            con.execute(
                "alter table drcr add column roundoffflag integer default 0"
            )

    with eng.connect() as con:
        # remove goid if present
        if columnExists("purchaseorder", "goid"):
            con.execute("alter table purchaseorder drop column goid")
            con.execute("alter table rejectionnote drop column goid")
            con.execute("alter table drcr drop column goid")
            con.execute("alter table budget drop column goid")
            con.execute("alter table vouchers drop column goid")
            con.execute("alter table invoice drop column goid")
            con.execute("alter table delchal drop column goid")

    with eng.connect() as con:
        # Round off is use to detect that total amount of invoice is rounded off or not.
        # If the field is not exist then it will create field.
        # Round Off Paid and Round Off Received account will genrate which is use while creating voucher for that invoice.
        if not columnExists("invoice", "roundoffflag"):
            con.execute(
                "alter table invoice add column roundoffflag integer default 0"
            )
            for orgcode in allorg:
                result = con.execute(
                    select([gkdb.accounts.c.accountcode]).where(
                        and_(
                            gkdb.accounts.c.orgcode == orgcode["orgcode"],
                            gkdb.accounts.c.accountname == "Round Off Paid",
                        )
                    )
                )
                account = result.fetchone()
                if account == None:
                    grpCodePaid = con.execute(
                        select([gkdb.groupsubgroups.c.groupcode]).where(
                            and_(
                                gkdb.groupsubgroups.c.groupname
                                == "Indirect Expense",
                                gkdb.groupsubgroups.c.orgcode == orgcode["orgcode"],
                            )
                        )
                    )
                    grpCodeP = grpCodePaid.fetchone()
                    ropAdd = con.execute(
                        gkdb.accounts.insert(),
                        [
                            {
                                "accountname": "Round Off Paid",
                                "groupcode": grpCodeP["groupcode"],
                                "orgcode": orgcode["orgcode"],
                                "defaultflag": 180,
                            }
                        ],
                    )
                    grpCodeReceived = con.execute(
                        select([gkdb.groupsubgroups.c.groupcode]).where(
                            and_(
                                gkdb.groupsubgroups.c.groupname
                                == "Indirect Income",
                                gkdb.groupsubgroups.c.orgcode == orgcode["orgcode"],
                            )
                        )
                    )
                    grpCodeR = grpCodeReceived.fetchone()
                    rorAdd = con.execute(
                        gkdb.accounts.insert(),
                        [
                            {
                                "accountname": "Round Off Received",
                                "groupcode": grpCodeR["groupcode"],
                                "orgcode": orgcode["orgcode"],
                                "defaultflag": 181,
                            }
                        ],
                    )

    with eng.connect() as con:
        # In Below query we are adding field pincode to invoice table
        if not columnExists("invoice", "pincode"):
            con.execute("alter table invoice add pincode text")
        # In Below query we are adding field pincode to invoicebin table
        if not columnExists("invoicebin", "pincode"):
            con.execute("alter table invoicebin add pincode text")
        # In Below query we are adding field pincode to customersupplier table
        if not columnExists("customerandsupplier", "pincode"):
            con.execute("alter table customerandsupplier add pincode text")
        # In Below query we are adding field pincode to purchaseorder table
        if not columnExists("purchaseorder", "pincode"):
            con.execute("alter table purchaseorder add pincode text")

    with eng.connect() as con:
        if not columnExists("customerandsupplier", "gst_reg_type"):
            con.execute(
                "alter table customerandsupplier add gst_reg_type integer"
            )
        if not columnExists("customerandsupplier", "gst_party_type"):
            con.execute(
                "alter table customerandsupplier add gst_party_type integer"
            )

    with eng.connect() as con:
        # Below query is to remove gbflag if it exists.
        if columnExists("godown", "gbflag"):
            con.execute("alter table godown drop column gbflag")

    with eng.connect() as con:
        # In Below query we are adding field dcinfo to invoicebin table
        if not columnExists("invoicebin", "dcinfo"):
            con.execute("alter table invoicebin add dcinfo jsonb")

    with eng.connect() as con:
        if not columnExists("organisation", "avnoflag"):
            con.execute(
                "alter table organisation add avnoflag integer default 0"
            )
        if not columnExists("organisation", "ainvnoflag"):
            con.execute(
                "alter table organisation add ainvnoflag integer default 0"
            )
        if not columnExists("organisation", "modeflag"):
            con.execute(
                "alter table organisation add modeflag integer default 1"
            )
        if not columnExists("organisation", "avflag"):
            con.execute(
                "alter table organisation add avflag integer default 1"
            )
        if not columnExists("organisation", "maflag"):
            con.execute(
                "alter table organisation add maflag integer default 0"
            )

    with eng.connect() as con:
        if not columnExists("accounts", "sysaccount"):
            con.execute(
                "alter table accounts add sysaccount integer default 0"
            )
            con.execute(
                "update accounts set sysaccount=1 where accountname in ('Closing Stock', 'Opening Stock', 'Profit & Loss', 'Stock at the Beginning')"
            )
        if not columnExists("accounts", "defaultflag"):
            con.execute(
                "alter table accounts add defaultflag integer default 0"
            )
            for orgcode in allorg:
                try:
                    groupdata = con.execute(
                        select([gkdb.groupsubgroups.c.groupcode]).where(
                            and_(
                                gkdb.groupsubgroups.c.orgcode == orgcode["orgcode"],
                                gkdb.groupsubgroups.c.groupname
                                == "Current Liabilities",
                            )
                        )
                    )
                    groupCode = groupdata.fetchone()
                    subGroup = {
                        "groupname": "Duties & Taxes",
                        "subgroupof": groupCode["groupcode"],
                        "orgcode": orgcode["orgcode"],
                    }
                    con.execute(gkdb.groupsubgroups.insert(), subGroup)

                    chartofacc = [
                        "Cash in hand",
                        "Krishi Kalyan Cess",
                        "Swachh Bharat Cess",
                        "Electricity Expense",
                        "Professional Fees",
                        "Sale A/C",
                        "Purchase A/C",
                        "Discount Paid",
                        "Bonus",
                        "Depreciation Expense",
                        "Discount Received",
                        "Salary",
                        "Bank Charges",
                        "Rent",
                        "Travel Expense",
                        "Accumulated Depreciation",
                        "Miscellaneous Expense",
                        "VAT_OUT",
                        "VAT_IN",
                    ]
                    for acc in chartofacc:
                        accname = con.execute(
                            select([gkdb.accounts.c.accountcode]).where(
                                and_(
                                    gkdb.accounts.c.orgcode == orgcode["orgcode"],
                                    gkdb.accounts.c.accountname == acc,
                                )
                            )
                        )
                        acname = accname.fetchone()
                        if acname == None:
                            if acc == "Cash in hand":
                                cash = con.execute(
                                    select([gkdb.groupsubgroups.c.groupcode]).where(
                                        and_(
                                            gkdb.groupsubgroups.c.groupname
                                            == "Cash",
                                            gkdb.groupsubgroups.c.orgcode
                                            == orgcode["orgcode"],
                                        )
                                    )
                                )
                                cashgrp = cash.fetchone()
                                cashadd = con.execute(
                                    gkdb.accounts.insert(),
                                    {
                                        "accountname": "Cash in hand",
                                        "groupcode": cashgrp["groupcode"],
                                        "orgcode": orgcode["orgcode"],
                                        "defaultflag": 3,
                                    },
                                )
                            elif acc == "Krishi Kalyan Cess":
                                cess = con.execute(
                                    select([gkdb.groupsubgroups.c.groupcode]).where(
                                        and_(
                                            gkdb.groupsubgroups.c.groupname
                                            == "Duties & Taxes",
                                            gkdb.groupsubgroups.c.orgcode
                                            == orgcode["orgcode"],
                                        )
                                    )
                                )
                                cesscode = cess.fetchone()
                                cessadd = con.execute(
                                    gkdb.accounts.insert(),
                                    [
                                        {
                                            "accountname": "Krishi Kalyan Cess",
                                            "groupcode": cesscode["groupcode"],
                                            "orgcode": orgcode["orgcode"],
                                        }
                                    ],
                                )
                            elif acc == "VAT_OUT":
                                vout = con.execute(
                                    select([gkdb.groupsubgroups.c.groupcode]).where(
                                        and_(
                                            gkdb.groupsubgroups.c.groupname
                                            == "Duties & Taxes",
                                            gkdb.groupsubgroups.c.orgcode
                                            == orgcode["orgcode"],
                                        )
                                    )
                                )
                                voutcode = vout.fetchone()
                                voutadd = con.execute(
                                    gkdb.accounts.insert(),
                                    [
                                        {
                                            "accountname": "VAT_OUT",
                                            "groupcode": voutcode["groupcode"],
                                            "orgcode": orgcode["orgcode"],
                                            "sysaccount": 1,
                                        }
                                    ],
                                )
                            elif acc == "VAT_IN":
                                vin = con.execute(
                                    select([gkdb.groupsubgroups.c.groupcode]).where(
                                        and_(
                                            gkdb.groupsubgroups.c.groupname
                                            == "Duties & Taxes",
                                            gkdb.groupsubgroups.c.orgcode
                                            == orgcode["orgcode"],
                                        )
                                    )
                                )
                                vincode = vin.fetchone()
                                vinadd = con.execute(
                                    gkdb.accounts.insert(),
                                    [
                                        {
                                            "accountname": "VAT_IN",
                                            "groupcode": vincode["groupcode"],
                                            "orgcode": orgcode["orgcode"],
                                            "sysaccount": 1,
                                        }
                                    ],
                                )
                            elif acc == "Swachh Bharat Cess":
                                bcess = con.execute(
                                    select([gkdb.groupsubgroups.c.groupcode]).where(
                                        and_(
                                            gkdb.groupsubgroups.c.groupname
                                            == "Duties & Taxes",
                                            gkdb.groupsubgroups.c.orgcode
                                            == orgcode["orgcode"],
                                        )
                                    )
                                )
                                cesscode = bcess.fetchone()
                                bcessadd = con.execute(
                                    gkdb.accounts.insert(),
                                    [
                                        {
                                            "accountname": "Swachh Bharat Cess",
                                            "groupcode": cesscode["groupcode"],
                                            "orgcode": orgcode["orgcode"],
                                        }
                                    ],
                                )
                            elif acc == "Salary":
                                sal = con.execute(
                                    select([gkdb.groupsubgroups.c.groupcode]).where(
                                        and_(
                                            gkdb.groupsubgroups.c.groupname
                                            == "Direct Expense",
                                            gkdb.groupsubgroups.c.orgcode
                                            == orgcode["orgcode"],
                                        )
                                    )
                                )
                                salcode = sal.fetchone()
                                saladd = con.execute(
                                    gkdb.accounts.insert(),
                                    [
                                        {
                                            "accountname": "Salary",
                                            "groupcode": salcode["groupcode"],
                                            "orgcode": orgcode["orgcode"],
                                        }
                                    ],
                                )
                            elif acc == "Miscellaneous Expense":
                                miscex = con.execute(
                                    select([gkdb.groupsubgroups.c.groupcode]).where(
                                        and_(
                                            gkdb.groupsubgroups.c.groupname
                                            == "Direct Expense",
                                            gkdb.groupsubgroups.c.orgcode
                                            == orgcode["orgcode"],
                                        )
                                    )
                                )
                                miscexcode = miscex.fetchone()
                                miscexadd = con.execute(
                                    gkdb.accounts.insert(),
                                    [
                                        {
                                            "accountname": "Miscellaneous Expense",
                                            "groupcode": miscexcode["groupcode"],
                                            "orgcode": orgcode["orgcode"],
                                        }
                                    ],
                                )
                            elif acc == "Bank Charges":
                                bnkch = con.execute(
                                    select([gkdb.groupsubgroups.c.groupcode]).where(
                                        and_(
                                            gkdb.groupsubgroups.c.groupname
                                            == "Direct Expense",
                                            gkdb.groupsubgroups.c.orgcode
                                            == orgcode["orgcode"],
                                        )
                                    )
                                )
                                bnkchcode = bnkch.fetchone()
                                bnkchadd = con.execute(
                                    gkdb.accounts.insert(),
                                    [
                                        {
                                            "accountname": "Bank Charges",
                                            "groupcode": bnkchcode["groupcode"],
                                            "orgcode": orgcode["orgcode"],
                                        }
                                    ],
                                )
                            elif acc == "Rent":
                                rent = con.execute(
                                    select([gkdb.groupsubgroups.c.groupcode]).where(
                                        and_(
                                            gkdb.groupsubgroups.c.groupname
                                            == "Direct Expense",
                                            gkdb.groupsubgroups.c.orgcode
                                            == orgcode["orgcode"],
                                        )
                                    )
                                )
                                rentcode = rent.fetchone()
                                rentadd = con.execute(
                                    gkdb.accounts.insert(),
                                    [
                                        {
                                            "accountname": "Rent",
                                            "groupcode": rentcode["groupcode"],
                                            "orgcode": orgcode["orgcode"],
                                        }
                                    ],
                                )
                            elif acc == "Travel Expense":
                                travel = con.execute(
                                    select([gkdb.groupsubgroups.c.groupcode]).where(
                                        and_(
                                            gkdb.groupsubgroups.c.groupname
                                            == "Direct Expense",
                                            gkdb.groupsubgroups.c.orgcode
                                            == orgcode["orgcode"],
                                        )
                                    )
                                )
                                travelcode = travel.fetchone()
                                traveladd = con.execute(
                                    gkdb.accounts.insert(),
                                    [
                                        {
                                            "accountname": "Travel Expense",
                                            "groupcode": travelcode["groupcode"],
                                            "orgcode": orgcode["orgcode"],
                                        }
                                    ],
                                )
                            elif acc == "Electricity Expense":
                                elect = con.execute(
                                    select([gkdb.groupsubgroups.c.groupcode]).where(
                                        and_(
                                            gkdb.groupsubgroups.c.groupname
                                            == "Direct Expense",
                                            gkdb.groupsubgroups.c.orgcode
                                            == orgcode["orgcode"],
                                        )
                                    )
                                )
                                electcode = elect.fetchone()
                                electadd = con.execute(
                                    gkdb.accounts.insert(),
                                    [
                                        {
                                            "accountname": "Electricity Expense",
                                            "groupcode": electcode["groupcode"],
                                            "orgcode": orgcode["orgcode"],
                                        }
                                    ],
                                )
                            elif acc == "Professional Fees":
                                fees = con.execute(
                                    select([gkdb.groupsubgroups.c.groupcode]).where(
                                        and_(
                                            gkdb.groupsubgroups.c.groupname
                                            == "Direct Expense",
                                            gkdb.groupsubgroups.c.orgcode
                                            == orgcode["orgcode"],
                                        )
                                    )
                                )
                                feescode = fees.fetchone()
                                feesadd = con.execute(
                                    gkdb.accounts.insert(),
                                    [
                                        {
                                            "accountname": "Professional Fees",
                                            "groupcode": feescode["groupcode"],
                                            "orgcode": orgcode["orgcode"],
                                        }
                                    ],
                                )
                            elif acc == "Discount Paid":
                                disc = con.execute(
                                    select([gkdb.groupsubgroups.c.groupcode]).where(
                                        and_(
                                            gkdb.groupsubgroups.c.groupname
                                            == "Indirect Expense",
                                            gkdb.groupsubgroups.c.orgcode
                                            == orgcode["orgcode"],
                                        )
                                    )
                                )
                                disccode = disc.fetchone()
                                discadd = con.execute(
                                    gkdb.accounts.insert(),
                                    [
                                        {
                                            "accountname": "Discount Paid",
                                            "groupcode": disccode["groupcode"],
                                            "orgcode": orgcode["orgcode"],
                                        }
                                    ],
                                )
                            elif acc == "Bonus":
                                bonus = con.execute(
                                    select([gkdb.groupsubgroups.c.groupcode]).where(
                                        and_(
                                            gkdb.groupsubgroups.c.groupname
                                            == "Indirect Expense",
                                            gkdb.groupsubgroups.c.orgcode
                                            == orgcode["orgcode"],
                                        )
                                    )
                                )
                                bonuscode = bonus.fetchone()
                                bonusadd = con.execute(
                                    gkdb.accounts.insert(),
                                    [
                                        {
                                            "accountname": "Bonus",
                                            "groupcode": bonuscode["groupcode"],
                                            "orgcode": orgcode["orgcode"],
                                        }
                                    ],
                                )
                            elif acc == "Depreciation Expense":
                                depex = con.execute(
                                    select([gkdb.groupsubgroups.c.groupcode]).where(
                                        and_(
                                            gkdb.groupsubgroups.c.groupname
                                            == "Indirect Expense",
                                            gkdb.groupsubgroups.c.orgcode
                                            == orgcode["orgcode"],
                                        )
                                    )
                                )
                                depexcode = depex.fetchone()
                                depexadd = con.execute(
                                    gkdb.accounts.insert(),
                                    [
                                        {
                                            "accountname": "Depreciation Expense",
                                            "groupcode": depexcode["groupcode"],
                                            "orgcode": orgcode["orgcode"],
                                        }
                                    ],
                                )
                            elif acc == "Accumulated Depreciation":
                                accdep = con.execute(
                                    select([gkdb.groupsubgroups.c.groupcode]).where(
                                        and_(
                                            gkdb.groupsubgroups.c.groupname
                                            == "Fixed Assets",
                                            gkdb.groupsubgroups.c.orgcode
                                            == orgcode["orgcode"],
                                        )
                                    )
                                )
                                accdepcode = accdep.fetchone()
                                accdepadd = con.execute(
                                    gkdb.accounts.insert(),
                                    {
                                        "accountname": "Accumulated Depreciation",
                                        "groupcode": accdepcode["groupcode"],
                                        "orgcode": orgcode["orgcode"],
                                    },
                                )
                            elif acc == "Discount Received":
                                discpur = con.execute(
                                    select([gkdb.groupsubgroups.c.groupcode]).where(
                                        and_(
                                            gkdb.groupsubgroups.c.groupname
                                            == "Indirect Income",
                                            gkdb.groupsubgroups.c.orgcode
                                            == orgcode["orgcode"],
                                        )
                                    )
                                )
                                discpurcd = discpur.fetchone()
                                discadd = con.execute(
                                    gkdb.accounts.insert(),
                                    {
                                        "accountname": "Discount Received",
                                        "groupcode": discpurcd["groupcode"],
                                        "orgcode": orgcode["orgcode"],
                                    },
                                )
                            elif acc == "Sale A/C":
                                sale = con.execute(
                                    select([gkdb.groupsubgroups.c.groupcode]).where(
                                        and_(
                                            gkdb.groupsubgroups.c.groupname
                                            == "Sales",
                                            gkdb.groupsubgroups.c.orgcode
                                            == orgcode["orgcode"],
                                        )
                                    )
                                )
                                salecode = sale.fetchone()
                                if salecode == None:
                                    acsale = con.execute(
                                        select(
                                            [gkdb.groupsubgroups.c.groupcode]
                                        ).where(
                                            and_(
                                                gkdb.groupsubgroups.c.groupname
                                                == "Direct Income",
                                                gkdb.groupsubgroups.c.orgcode
                                                == orgcode["orgcode"],
                                            )
                                        )
                                    )
                                    saleCode = acsale.fetchone()
                                    saleData = con.execute(
                                        gkdb.groupsubgroups.insert(),
                                        {
                                            "groupname": "Sales",
                                            "subgroupof": saleCode["groupcode"],
                                            "orgcode": orgcode["orgcode"],
                                        },
                                    )
                                    saleadd = con.execute(
                                        gkdb.accounts.insert(),
                                        {
                                            "accountname": "Sale A/C",
                                            "groupcode": salecode["groupcode"],
                                            "orgcode": orgcode["orgcode"],
                                            "defaultflag": 19,
                                        },
                                    )
                                else:
                                    saleadd = con.execute(
                                        gkdb.accounts.insert(),
                                        {
                                            "accountname": "Sale A/C",
                                            "groupcode": salecode["groupcode"],
                                            "orgcode": orgcode["orgcode"],
                                            "defaultflag": 19,
                                        },
                                    )
                            elif acc == "Purchase A/C":
                                purch = con.execute(
                                    select([gkdb.groupsubgroups.c.groupcode]).where(
                                        and_(
                                            gkdb.groupsubgroups.c.groupname
                                            == "Purchase",
                                            gkdb.groupsubgroups.c.orgcode
                                            == orgcode["orgcode"],
                                        )
                                    )
                                )
                                purchcd = purch.fetchone()
                                if purchcd == None:
                                    acpurc = con.execute(
                                        select(
                                            [gkdb.groupsubgroups.c.groupcode]
                                        ).where(
                                            and_(
                                                gkdb.groupsubgroups.c.groupname
                                                == "Direct Expense",
                                                gkdb.groupsubgroups.c.orgcode
                                                == orgcode["orgcode"],
                                            )
                                        )
                                    )
                                    purCode = acpurc.fetchone()
                                    insData = con.execute(
                                        gkdb.groupsubgroups.insert(),
                                        [
                                            {
                                                "groupname": "Purchase",
                                                "subgroupof": purCode["groupcode"],
                                                "orgcode": orgcode["orgcode"],
                                            },
                                            {
                                                "groupname": "Consumables",
                                                "subgroupof": purCode["groupcode"],
                                                "orgcode": orgcode["orgcode"],
                                            },
                                        ],
                                    )
                                    purchadd = con.execute(
                                        gkdb.accounts.insert(),
                                        {
                                            "accountname": "Purchase A/C",
                                            "groupcode": purchcd["groupcode"],
                                            "orgcode": orgcode["orgcode"],
                                            "defaultflag": 16,
                                        },
                                    )
                                else:
                                    purchadd = con.execute(
                                        gkdb.accounts.insert(),
                                        {
                                            "accountname": "Purchase A/C",
                                            "groupcode": purchcd["groupcode"],
                                            "orgcode": orgcode["orgcode"],
                                            "defaultflag": 16,
                                        },
                                    )
                        elif acc == "Cash in hand":
                            con.execute(
                                "update accounts set defaultflag = 3 where accountcode =%d"
                                % int(acname["accountcode"])
                            )
                        elif acc == "Sale A/C":
                            con.execute(
                                "update accounts set defaultflag = 19 where accountcode =%d"
                                % int(acname["accountcode"])
                            )
                        elif acc == "Purchase A/C":
                            con.execute(
                                "update accounts set defaultflag = 16 where accountcode =%d"
                                % int(acname["accountcode"])
                            )
                        elif acc == "Round Off Paid":
                            con.execute(
                                "update accounts set defaultflag = 180 where accountcode =%d"
                                % int(acname["accountcode"])
                            )
                        elif acc == "Round Off Received":
                            con.execute(
                                "update accounts set defaultflag = 181 where accountcode =%d"
                                % int(acname["accountcode"])
                            )
                        elif acc == "VAT_IN":
                            con.execute(
                                "update accounts set defaultflag = 0, sysaccount = 1 where accountcode =%d"
                                % int(acname["accountcode"])
                            )
                        elif acc == "VAT_OUT":
                            con.execute(
                                "update accounts set defaultflag = 0, sysaccount = 1 where accountcode =%d"
                                % int(acname["accountcode"])
                            )
                        else:
                            con.execute(
                                "update accounts set defaultflag = 0 where accountcode =%d"
                                % int(acname["accountcode"])
                            )
                except:
                    continue

    with eng.connect() as con:
        if not columnExists("organisation", "bankdetails"):
            con.execute("alter table organisation add bankdetails json")

    with eng.connect() as con:
        if not columnExists("purchaseorder", "purchaseordertotal"):
            con.execute("drop table purchaseorder cascade")
            con.execute(
                "create table purchaseorder(orderid serial, orderno text not null, orderdate timestamp not null, creditperiod text, payterms text, modeoftransport text, issuername text, designation text, schedule jsonb, taxstate text, psflag integer not null, csid integer, togodown integer, taxflag integer default 22, tax jsonb, cess jsonb,purchaseordertotal numeric(13,2) not null, pototalwords text, sourcestate text, orgstategstin text, attachment json, attachmentcount integer default 0, consignee jsonb, freeqty jsonb, reversecharge text, bankdetails jsonb, vehicleno text, dateofsupply timestamp, discount jsonb, paymentmode integer default 22, address text, orgcode integer not null, primary key(orderid), foreign key (csid) references customerandsupplier(custid) ON DELETE CASCADE, foreign key (togodown) references godown(goid) ON DELETE CASCADE, foreign key (orgcode) references organisation(orgcode) ON DELETE CASCADE)"
            )
            con.execute(
                "create index purchaseorder_orgcodeindex on purchaseorder using btree(orgcode)"
            )
            con.execute(
                "create index purchaseorder_date on purchaseorder using btree(orderdate)"
            )
            con.execute(
                "create index purchaseorder_togodown on purchaseorder using btree(togodown)"
            )

    with eng.connect() as con:
        if not columnExists("invoice", "invoicetotalword"):
            con.execute("alter table invoice add invoicetotalword text")

    with eng.connect() as con:
        if not columnExists("delchal", "taxflag"):
            con.execute(
                "alter table delchal add taxflag integer, add contents jsonb, add tax jsonb, add cess jsonb, add taxstate text, add sourcestate text, add orgstategstin text, add freeqty jsonb, add discount jsonb, add delchaltotal numeric(13,2), add dateofsupply timestamp, add vehicleno text"
            )

    with eng.connect() as con:
        if not columnExists("delchal", "inoutflag"):
            con.execute("alter table delchal add inoutflag integer")
            # This code will assign inoutflag for delivery chalan where inoutflag is blank.
            alldelchal = con.execute(
                select([gkdb.delchal.c.dcid]).where(
                    gkdb.delchal.c.inoutflag == None
                )
            )
            # here we will be fetching all the delchal data
            delchals = alldelchal.fetchall()
            for delchal in delchals:
                delchalid = int(delchal["dcid"])
                stockdata = con.execute(
                    select([gkdb.stock.c.inout]).where(
                        and_(
                            gkdb.stock.c.dcinvtnid == delchalid,
                            gkdb.stock.c.dcinvtnflag == 4,
                        )
                    )
                )
                inout = stockdata.fetchone()
                inoutflag = inout["inout"]
                con.execute(
                    "update delchal set inoutflag = %d where dcid=%d"
                    % (int(inoutflag), int(delchalid))
                )

    with eng.connect() as con:
        if not columnExists("invoice", "inoutflag"):
            con.execute("alter table invoice add inoutflag integer")
            # This code will assign inoutflag for invoice or cashmemo where inoutflag is blank.
            allinvoice = con.execute(
                select(
                    [
                        gkdb.invoice.c.invid,
                        gkdb.invoice.c.custid,
                        gkdb.invoice.c.icflag,
                    ]
                ).where(gkdb.invoice.c.inoutflag == None)
            )
            # Here we fetching all "custid", "icflag" and "invid".
            dict = allinvoice.fetchall()
            for singleinv in dict:
                sincustid = singleinv["custid"]
                invid = singleinv["invid"]
                icflag = singleinv["icflag"]
                # First we checking the icflag (i.e 3 for "cashmemo", 9 for "invoice")
                if icflag == 3:
                    con.execute(
                        "update invoice set inoutflag = 15 where invid=%d"
                        % int(invid)
                    )
                else:
                    cussupdata = con.execute(
                        select([gkdb.customerandsupplier.c.csflag]).where(
                            gkdb.customerandsupplier.c.custid == sincustid
                        )
                    )
                    # Here we fetching all "csflag" on the basis of "sincustid" (i.e "custid")
                    csflagsingle = cussupdata.fetchone()
                    for cussup in csflagsingle:
                        # if "csflag" is 19 (i.e "supplier") then set inoutflag=9 (i.e "in") else "csflag" is 3 (i.e "customer" and set "inoutflag=15" (i.e "out"))
                        if cussup == 19:
                            con.execute(
                                "update invoice set inoutflag = 9 where invid=%d"
                                % int(invid)
                            )
                        else:
                            con.execute(
                                "update invoice set inoutflag = 15 where invid=%d"
                                % int(invid)
                            )

    with eng.connect() as con:
        if not columnExists("invoice", "address"):
            con.execute("alter table invoice add address text")

    with eng.connect() as con:
        if not columnExists("customerandsupplier", "bankdetails"):
            con.execute(
                "alter table customerandsupplier add bankdetails jsonb"
            )

    with eng.connect() as con:
        if not columnExists("invoice", "paymentmode"):
            con.execute("alter table invoice add paymentmode integer")
            # Code for assinging paymentmode where paymentmode is blank and bank details are present.
            bankresult = con.execute(
                select([gkdb.invoice.c.invid, gkdb.invoice.c.bankdetails]).where(
                    gkdb.invoice.c.paymentmode == None
                )
            )
            # Fetching invid,bankdetails using fetchall() method in list.for loop is used to fetch each record in bankresult.
            dict = bankresult.fetchall()
            for invdata in dict:
                # Storing account number,ifsc number,invoice id in invaccno,invifsc,invoid respectively
                invaccno = invdata["bankdetails"]["accountno"]
                invifsc = invdata["bankdetails"]["ifsc"]
                invoid = invdata["invid"]
                # Checking for bankdetails,if accountno and ifsc are present then set paymentmode=2 else set paymentmode=3.
                if invaccno == "" or invifsc == "":
                    con.execute(
                        "update invoice set paymentmode=3 where invid = %d"
                        % int(invoid)
                    )
                else:
                    con.execute(
                        "update invoice set paymentmode=2 where invid = %d"
                        % int(invoid)
                    )

    with eng.connect() as con:
        if not columnExists("delchal", "consignee"):
            con.execute("alter table delchal add consignee jsonb")

    with eng.connect() as con:
        if not columnExists("invoice", "orgstategstin"):
            con.execute("alter table invoice add orgstategstin text")
        if not columnExists("invoice", "cess"):
            con.execute("alter table invoice add cess jsonb")

    with eng.connect() as con:
        if not tableExists("state"):
            con.execute(
                "create table state( statecode integer,statename text,primary key (statecode))"
            )
        if not columnExists("state", "abbreviation"):
            con.execute("alter table state add abbreviation text")

        statescount = con.execute(
            select([func.count(gkdb.state.c.statecode).label("numberofstates")])
        )
        numberofstates = statescount.fetchone()
        if int(numberofstates["numberofstates"]) == 0:
            con.execute(
                "insert into state( statecode, statename, abbreviation)values(1, 'Jammu and Kashmir', 'JK')"
            )
            con.execute(
                "insert into state( statecode, statename, abbreviation)values(2, 'Himachal Pradesh', 'HP')"
            )
            con.execute(
                "insert into state( statecode, statename, abbreviation)values(3, 'Punjab', 'PB')"
            )
            con.execute(
                "insert into state( statecode, statename, abbreviation)values(4, 'Chandigarh', 'CH')"
            )
            con.execute(
                "insert into state( statecode, statename, abbreviation)values(5, 'Uttarakhand', 'UK')"
            )
            con.execute(
                "insert into state( statecode, statename, abbreviation)values(6, 'Haryana', 'HR')"
            )
            con.execute(
                "insert into state( statecode, statename, abbreviation)values(7, 'Delhi', 'DL')"
            )
            con.execute(
                "insert into state( statecode, statename, abbreviation)values(8, 'Rajasthan', 'RJ')"
            )
            con.execute(
                "insert into state( statecode, statename, abbreviation)values(9, 'Uttar Pradesh', 'UP')"
            )
            con.execute(
                "insert into state( statecode, statename, abbreviation)values(10, 'Bihar', 'BR')"
            )
            con.execute(
                "insert into state( statecode, statename, abbreviation)values(11, 'Sikkim', 'SK')"
            )
            con.execute(
                "insert into state( statecode, statename, abbreviation)values(12, 'Arunachal Pradesh', 'AR')"
            )
            con.execute(
                "insert into state( statecode, statename, abbreviation)values(13, 'Nagaland', 'NL')"
            )
            con.execute(
                "insert into state( statecode, statename, abbreviation)values(14, 'Manipur', 'MN')"
            )
            con.execute(
                "insert into state( statecode, statename, abbreviation)values(15, 'Mizoram', 'MZ')"
            )
            con.execute(
                "insert into state( statecode, statename, abbreviation)values(16, 'Tripura', 'TR')"
            )
            con.execute(
                "insert into state( statecode, statename, abbreviation)values(17, 'Meghalaya', 'ML')"
            )
            con.execute(
                "insert into state( statecode, statename, abbreviation)values(18, 'Assam', 'AS')"
            )
            con.execute(
                "insert into state( statecode, statename, abbreviation)values(19, 'West Bcon.l', 'WB')"
            )
            con.execute(
                "insert into state( statecode, statename, abbreviation)values(20, 'Jharkhand', 'JH')"
            )
            con.execute(
                "insert into state( statecode, statename, abbreviation)values(21, 'Odisha', 'OR')"
            )
            con.execute(
                "insert into state( statecode, statename, abbreviation)values(22, 'Chhattisgarh', 'CG')"
            )
            con.execute(
                "insert into state( statecode, statename, abbreviation)values(23, 'Madhya Pradesh', 'MP')"
            )
            con.execute(
                "insert into state( statecode, statename, abbreviation)values(24, 'Gujarat', 'GJ')"
            )
            con.execute(
                "insert into state( statecode, statename, abbreviation)values(25, 'Daman and Diu (Old)', 'DD')"
            )
            con.execute(
                "insert into state( statecode, statename, abbreviation)values(26, 'Daman and Diu & Dadra and Nagar Haveli (New)', 'DH')"
            )
            con.execute(
                "insert into state( statecode, statename, abbreviation)values(27, 'Maharashtra', 'MH')"
            )
            con.execute(
                "insert into state( statecode, statename, abbreviation)values(28, 'Andhra Pradesh', 'AP')"
            )
            con.execute(
                "insert into state( statecode, statename, abbreviation)values(29, 'Karnataka', 'KA')"
            )
            con.execute(
                "insert into state( statecode, statename, abbreviation)values(30, 'Goa', 'GA')"
            )
            con.execute(
                "insert into state( statecode, statename, abbreviation)values(31, 'Lakshdweep', 'LD')"
            )
            con.execute(
                "insert into state( statecode, statename, abbreviation)values(32, 'Kerala', 'KL')"
            )
            con.execute(
                "insert into state( statecode, statename, abbreviation)values(33, 'Tamil Nadu', 'TN')"
            )
            con.execute(
                "insert into state( statecode, statename, abbreviation)values(34, 'Pondicherry', 'PY')"
            )
            con.execute(
                "insert into state( statecode, statename, abbreviation)values(35, 'Andaman and Nicobar Islands', 'AN')"
            )
            con.execute(
                "insert into state( statecode, statename, abbreviation)values(36, 'Telangana', 'TS')"
            )
            con.execute(
                "insert into state( statecode, statename, abbreviation)values(37, 'Andhra Pradesh (New)', 'AP')"
            )
            con.execute(
                "insert into state( statecode, statename, abbreviation)values(38, 'Ladakh', 'LA')"
            )

    with eng.connect() as con:
        if columnExists("invoice", "reversecharge"):
            countResult = con.execute(
                select([func.count(gkdb.invoice.c.reversecharge).label("revcount")])
            )
            countData = countResult.fetchone()
            if int(countData["revcount"]) > 0:
                con.execute(
                    "update invoice set reversecharge = '0' where reversecharge=null"
                )

    with eng.connect() as con:
        if columnExists("invoice", "cancelflag"):
            con.execute("alter table invoice drop column cancelflag")
        if columnExists("invoice", "canceldate"):
            con.execute("alter table invoice drop column canceldate")
        if columnExists("invoice", "taxstate"):
            con.execute(
                "update invoice set taxstate = null where taxstate = '' or taxstate = 'none'"
            )
        if not columnExists("invoice", "consignee"):
            con.execute(
                "alter table invoice add consignee jsonb, add sourcestate text ,add discount jsonb ,add taxflag integer default 22, add reversecharge text, add bankdetails jsonb,add transportationmode text,add vehicleno text,add dateofsupply timestamp"
            )
        if columnExists("invoice", "taxflag"):
            con.execute("update invoice set taxflag = 22 where taxflag=null")

    with eng.connect() as con:
        if columnExists("delchal", "issuerid"):
            con.execute("alter table delchal drop column issuerid")

    with eng.connect() as con:
        if not columnExists("organisation", "gstin"):
            con.execute("alter table organisation add gstin jsonb")
        if not columnExists("customerandsupplier", "gstin"):
            con.execute("alter table customerandsupplier add gstin jsonb")

    with eng.connect() as con:
        if not columnExists("product", "gscode"):
            con.execute("alter table product add gscode text")
        if not columnExists("product", "gsflag"):
            con.execute("alter table product add gsflag integer")
            con.execute("update product set gsflag = 7 where gsflag=null")

    with eng.connect() as con:
        if not columnExists("product", "prodsp"):
            con.execute("alter table product add prodsp numeric(13,2)")
        if not columnExists("product", "prodmrp"):
            con.execute("alter table product add prodmrp numeric(13,2)")

    with eng.connect() as con:
        if not tableExists("billwise"):
            con.execute(
                "create table billwise(billid serial, vouchercode integer, invid integer, adjdate timestamp, adjamount numeric (12,2), orgcode integer, primary key (billid), foreign key (vouchercode) references vouchers(vouchercode), foreign key(invid) references invoice(invid), foreign key (orgcode) references organisation (orgcode))"
            )

    with eng.connect() as con:
        if not tableExists("rejectionnote"):
            con.execute(
                "create table rejectionnote(rnid serial, rnno text not null, rndate timestamp not null, rejprods jsonb not null ,inout integer not null, dcid integer, invid integer, issuerid integer, orgcode integer not null, rejnarration text, primary key(rnid), foreign key (dcid) references delchal(dcid) ON DELETE CASCADE, foreign key (invid) references invoice(invid) ON DELETE CASCADE, foreign key (issuerid) references users(userid) ON DELETE CASCADE, foreign key (orgcode) references organisation(orgcode) ON DELETE CASCADE, unique(rnno, inout, orgcode))"
            )
        if not columnExists("rejectionnote", "rejprods"):
            con.execute(
                "alter table rejectionnote add rejprods jsonb, add rejectedtotal numeric(13,2)"
            )

    with eng.connect() as con:
        if not tableExists("drcr"):
            con.execute(
                "create table drcr(drcrid serial,drcrno text NOT NULL, drcrdate timestamp NOT NULL, dctypeflag integer default 3, totreduct numeric(13,2), reductionval jsonb, reference jsonb, attachment jsonb, drcrnarration text, attachmentcount integer default 0, userid integer,invid integer, rnid integer,orgcode integer NOT NULL, primary key (drcrid), constraint drcr_orgcode_fkey FOREIGN KEY (orgcode) REFERENCES organisation(orgcode), constraint drcr_userid_fkey FOREIGN KEY (userid) REFERENCES users(userid),constraint drcr_invid_fkey FOREIGN KEY (invid) REFERENCES invoice(invid), constraint drcr_rnid_fkey FOREIGN KEY (rnid) REFERENCES rejectionnote(rnid),CONSTRAINT drcr_orgcode_drcrno_dctypeflag UNIQUE(orgcode,drcrno,dctypeflag), CONSTRAINT drcr_orgcode_invid_dctypeflag UNIQUE(orgcode,invid,dctypeflag), CONSTRAINT drcr_orgcode_rnid_dctypeflag UNIQUE(orgcode,rnid,dctypeflag))"
            )
        if not columnExists("drcr", "drcrmode"):
            con.execute("alter table drcr add drcrmode integer default 4")
        if not columnExists("vouchers", "drcrid"):
            con.execute("alter table vouchers add drcrid integer")
            con.execute(
                "alter table vouchers add foreign key(drcrid) references drcr(drcrid)"
            )

    with eng.connect() as con:
        if not columnExists("organisation", "invsflag"):
            con.execute(
                "alter table organisation add invsflag integer default 1"
            )
        if not columnExists("organisation", "billflag"):
            con.execute(
                "alter table organisation add billflag integer default 1"
            )

    with eng.connect() as con:
        if not columnExists("vouchers", "instrumentno"):
            con.execute("alter table vouchers add instrumentno text")
        if not columnExists("vouchers", "branchname"):
            con.execute("alter table vouchers add branchname text")
        if not columnExists("vouchers", "bankname"):
            con.execute("alter table vouchers add bankname text")
        if not columnExists("vouchers", "instrumentdate"):
            con.execute("alter table vouchers add instrumentdate timestamp")

    with eng.connect() as con:
        if not columnExists("organisation", "logo"):
            con.execute("alter table organisation add logo json")

    with eng.connect() as con:
        if not columnExists("dcinv", "invprods"):
            con.execute("alter table dcinv add invprods jsonb")

    with eng.connect() as con:
        if not columnExists("transfernote", "duedate"):
            con.execute("alter table transfernote add duedate timestamp")
        if not columnExists("transfernote", "grace"):
            con.execute("alter table transfernote add grace integer")
        if not columnExists("transfernote", "fromgodown"):
            con.execute("alter table transfernote add fromgodown integer")

    with eng.connect() as con:
        if columnExists("product", "specs"):
            con.execute("alter table product alter specs drop not null")
        if columnExists("product", "uomid"):
            con.execute("alter table product alter uomid drop not null")

    with eng.connect() as con:
        if columnExists("transfernote", "canceldate"):
            con.execute("alter table transfernote drop column canceldate")
        if columnExists("transfernote", "cancelflag"):
            con.execute("alter table transfernote drop column cancelflag")

    with eng.connect() as con:
        if not columnExists("invoice", "freeqty"):
            con.execute("alter table invoice add freeqty jsonb")
        if not columnExists("invoice", "amountpaid"):
            con.execute(
                "alter table invoice add amountpaid numeric default 0.00"
            )

    with eng.connect() as con:
        if not columnExists("stock", "stockdate"):
            con.execute("alter table stock add stockdate timestamp")

    with eng.connect() as con:
        if not columnExists("delchal", "attachment"):
            con.execute("alter table delchal add attachment json")
        if not columnExists("delchal", "attachmentcount"):
            con.execute(
                "alter table delchal add attachmentcount integer default 0"
            )

    with eng.connect() as con:
        if not columnExists("invoice", "attachment"):
            con.execute("alter table invoice add attachment json")
        if not columnExists("invoice", "attachmentcount"):
            con.execute(
                "alter table invoice add attachmentcount integer default 0"
            )
        if not columnExists("invoice", "ewaybillno"):
            con.execute("alter table invoice add ewaybillno text")

    with eng.connect() as con:
        if not columnExists("drcr", "drcrnarration"):
            con.execute("alter table drcr add drcrnarration text")
        if not columnExists("invoice", "invnarration"):
            con.execute("alter table invoice add invnarration text")
        if not columnExists("purchaseorder", "psnarration"):
            con.execute("alter table purchaseorder add psnarration text")
        if not columnExists("rejectionnote", "rejnarration"):
            con.execute("alter table rejectionnote add rejnarration text")
        if not columnExists("delchal", "totalinword"):
            con.execute("alter table delchal add totalinword text")
        if not columnExists("delchalbin", "totalinword"):
            con.execute("alter table delchalbin add totalinword text")
        if not columnExists("rejectionnote", "rejnarration"):
            con.execute("alter table rejectionnote add rejnarration text")
        # In Below query we are adding field invnarration to invoicebin table
        if not columnExists("invoicebin", "invnarration"):
            con.execute("alter table invoicebin add invnarration text")
        # In Below query we are adding field dcnarration to delchal table
        if not columnExists("delchal", "dcnarration"):
            con.execute("alter table delchal add dcnarration text")
        # In Below query we are adding field dcnarration to delchalbin table
        if not columnExists("delchalbin", "dcnarration"):
            con.execute("alter table delchalbin add dcnarration text")

    with eng.connect() as con:
        if not tableExists("usergodown"):
            con.execute(
                "create table usergodown(ugid serial, goid integer, userid integer, orgcode integer, primary key(ugid), foreign key (goid) references godown(goid),  foreign key (userid) references users(userid), foreign key (orgcode) references organisation(orgcode))"
            )

    with eng.connect() as con:
        if not tableExists("log"):
            con.execute(
                "create table log(logid serial, time timestamp, activity text, userid integer, orgcode integer,  primary key (logid), foreign key(userid) references users(userid), foreign key (orgcode) references organisation(orgcode))"
            )

    with eng.connect() as con:
        if does_foreignkey_exist(
                eng,
                "delchal",
                "delchal_custid_fkey"
        ):
            con.execute(
                "ALTER TABLE delchal DROP CONSTRAINT delchal_custid_fkey, ADD CONSTRAINT delchal_custid_fkey FOREIGN KEY (custid) REFERENCES customerandsupplier(custid)"
            )
        if does_foreignkey_exist(
                eng,
                "invoice",
                "invoice_custid_fkey"
        ):
            con.execute(
                "ALTER TABLE invoice DROP CONSTRAINT invoice_custid_fkey, ADD CONSTRAINT invoice_custid_fkey FOREIGN KEY (custid) REFERENCES customerandsupplier(custid)"
            )

    with eng.connect() as con:
        if not does_unique_constraint_exist(
                eng,
                "goprod",
                "goprod_goid_productcode_orgcode_key"
        ):
            con.execute(
                "alter table goprod add UNIQUE(goid,productcode,orgcode)"
            )
        if not does_unique_constraint_exist(
                eng,
                "product",
                "product_productdesc_orgcode_key"
        ):
            con.execute("alter table product add UNIQUE(productdesc,orgcode)")

    with eng.connect() as con:
        if not does_unique_constraint_exist(
                eng,
                "customerandsupplier",
                "customerandsupplier_orgcode_custname_gstin_key"
        ):
            con.execute(
                "alter table customerandsupplier add UNIQUE(orgcode,custname,gstin)"
            )

    with eng.connect() as con:
        if not does_foreignkey_exist(
                eng,
                "transfernote",
                "transfernote_fromgodown_fkey"
        ):
            con.execute(
                "alter table transfernote add foreign key(fromgodown) references godown(goid)"
            )

    with eng.connect() as con:
        if not tableExists("budget"):
            con.execute(
                "create table budget (budid serial, budname text not null,budtype int not null, startdate timestamp not null,enddate timestamp not null,contents jsonb not null,gaflag int not null,projectcode int, orgcode int not null, primary key(budid),foreign key(projectcode) references projects(projectcode) , foreign key(orgcode) references organisation(orgcode) ON DELETE CASCADE)"
            )
            # In Below query we are removing company preference option Accounting with Invoicing. This query is written under above condition because we want to run the query only once while migrating to version 6.0
            con.execute(
                "update organisation set billflag=1 where invflag=0 and invsflag=1 and billflag=0"
            )


    with eng.connect() as con:
            # Below query is to create a new table to store cancelled deliverynotes.
        if not tableExists("delchalbin"):
            con.execute(
                "create table delchalbin(dcid serial, dcno text NOT NULL, dcdate timestamp NOT NULL, dcflag integer NOT NULL, taxflag integer default 7, discflag integer default 1,contents jsonb, tax jsonb, cess jsonb, issuername text, designation text, noofpackages integer, modeoftransport text, attachment json, consignee jsonb, taxstate text,sourcestate text, orgstategstin text, freeqty jsonb, discount jsonb, vehicleno text, dateofsupply timestamp, delchaltotal numeric(13,2) NOT NULL, goid integer, attachmentcount integer default 0, orgcode integer NOT NULL, custid integer, orderid integer, inoutflag integer NOT NULL, roundoffflag integer default 0, totalinword text, dcnarration text, primary key(dcid), foreign key(orderid) references purchaseorder(orderid), foreign key(custid) references customerandsupplier(custid), foreign key(orgcode) references organisation(orgcode) ON DELETE CASCADE,foreign key(goid) references godown(goid))"
            )
            con.execute(
                "create index delchalbin_orgcodeindex on delchalbin using btree(orgcode)"
            )
            con.execute(
                "create index delchalbin_dcnoindex on delchalbin using btree(dcno)"
            )


    with eng.connect() as con:
            # In Below queries we are creating new table invoivebin which is act as bin for cancelled invoices.
        if not tableExists("invoicebin"):
            con.execute(
                "create table invoicebin(invid serial, invoiceno text NOT NULL, invoicedate  timestamp NOT NULL, taxflag integer default 22, contents jsonb, issuername text, designation text, tax jsonb, cess jsonb, amountpaid numeric(13,2) default 0.00, invoicetotal numeric(13,2) NOT NULL, icflag integer default 9, taxstate text, sourcestate text, orgstategstin text, attachment json, attachmentcount integer default 0, orderid integer,orgcode integer NOT NULL, custid integer, consignee jsonb, freeqty jsonb, reversecharge text, bankdetails jsonb, transportationmode text,vehicleno text, dateofsupply timestamp, discount jsonb, paymentmode integer default 2,address text, inoutflag integer,invoicetotalword text, primary key(invid),foreign key(orderid) references purchaseorder(orderid),foreign key(custid) references customerandsupplier(custid), foreign key (orgcode) references organisation(orgcode) ON DELETE CASCADE)"
            )
            con.execute(
                "create index invoicebin_orgcodeindex on invoicebin using btree(orgcode)"
            )
            con.execute(
                "create index invoicebin_invoicenoindex on invoicebin using btree(invoiceno)"
            )
        else:
            # below code is for add forign key constraint to orgcode when it is not available in invoicebin table
            fkeyavlb = getOnDelete("invoicebin", "invoicebin_orgcode_fkey")
            if fkeyavlb == None:
                # this condition is apply for forign key available but not ondelete cascade
                con.execute(
                    "alter table invoicebin drop constraint invoicebin_orgcode_fkey"
                )
                con.execute(
                    "alter table invoicebin add constraint invoicebin_orgcode_fkey foreign key(orgcode) references organisation(orgcode) on delete cascade"
                )
            if fkeyavlb == False:
                # this condition is apply for forign key and ondelete cascade both are not available
                con.execute(
                    "alter table invoicebin add constraint invoicebin_orgcode_fkey foreign key(orgcode) references organisation(orgcode) on delete cascade"
                )
            if fkeyavlb == "CASCADE":
                pass

    with eng.connect() as con:
        # Add config columns for user and organisation if not present and init to {}
        if not columnExists("users", "userconf"):
            con.execute("alter table users add userconf jsonb default '{}'")

    with eng.connect() as con:
        if not columnExists("organisation", "orgconf"):
            con.execute(
                "alter table organisation add orgconf jsonb default '{}'"
            )

    with eng.connect() as con:
        if tableExists("tax2"):
            # A table called tax2 was created for dev purpose and was in use for a while, so rename this table if it exists
            if tableExists("tax"):
                oldTaxLength = con.execute(
                    "select COUNT(taxid) as count from tax"
                ).fetchone()
                newTaxLength = con.execute(
                    "select COUNT(taxid) as count from tax2"
                ).fetchone()
                if oldTaxLength["count"] > 0 and newTaxLength["count"] == 0:
                    # If tax2 table was created but the data in tax was not migrated to tax2
                    # delete tax2 table and just add the column taxfromdate to table tax and add org yearstart dates in that column
                    con.execute("drop table if exists tax2")
                    con.execute("alter table tax add taxfromdate date")

                    orgs = con.execute(
                        "select orgcode, yearstart, yearend from organisation"
                    ).fetchall()
                    dates = {}
                    for org in orgs:
                        dates[org["orgcode"]] = {
                            "from": org["yearstart"],
                            "to": org["yearend"],
                        }

                    taxes = con.execute("select orgcode from tax").fetchall()
                    for tax in taxes:
                        from_date = dates[tax["orgcode"]]["from"]
                        to_date = dates[tax["orgcode"]]["to"]
                        con.execute(
                            "insert into tax(taxfromdate)values('%s')"
                            % (str(from_date),)
                        )
                else:
                    con.execute("drop table if exists tax")
            # If the table tax didn't exists rename tax2 to tax and rename the indexes
            con.execute("alter table if exists tax2 rename to tax")
            con.execute("alter index if exists taxindex2 rename to taxindex")
            con.execute(
                "alter index if exists tax_taxindex2 rename to tax_taxindex"
            )
        elif tableExists("tax") and (not columnExists("tax", "taxfromdate")):
            # If the old tax table did not have taxfromdate column, add the column and fill it with org yearstart dates
            con.execute("alter table tax add taxfromdate date")

            orgs = con.execute(
                "select orgcode, yearstart, yearend from organisation"
            ).fetchall()
            dates = {}
            for org in orgs:
                dates[org["orgcode"]] = {
                    "from": org["yearstart"],
                    "to": org["yearend"],
                }

            taxes = con.execute("select orgcode from tax").fetchall()
            for tax in taxes:
                from_date = dates[tax["orgcode"]]["from"]
                to_date = dates[tax["orgcode"]]["to"]
                con.execute(
                    "insert into tax(taxfromdate)values('%s')" % (str(from_date),)
                )


    with eng.connect() as con:
        if not columnExists("invoice", "supinvno"):
            con.execute("alter table invoice add supinvno text")
        if not columnExists("invoice", "supinvdate"):
            con.execute("alter table invoice add supinvdate date")


    with eng.connect() as con:
        if uniqueConstraintExists(
            "invoice", ["orgcode", "invoiceno", "custid", "icflag"]
        ):
            print("Invoice Unique Constraint Update")
            # rename invoice numbers that will violate the new constraint
            orgs = con.execute(
                select([gkdb.organisation.c.orgcode])
            ).fetchall()
            rename_success = True
            for org in orgs:
                if not rename_inv_no_uniquely(con, org["orgcode"]):
                    rename_success = False
            # drop the old constraint
            if rename_success:
                con.execute(
                    "ALTER TABLE invoice DROP CONSTRAINT IF EXISTS invoice_orgcode_invoiceno_custid_icflag_key"
                )
                con.execute(
                    "ALTER TABLE invoice DROP CONSTRAINT IF EXISTS invoice_orgcode_invoiceno_key"
                )
                con.execute(
                    "ALTER TABLE invoice ADD CONSTRAINT invoice_orgcode_invoiceno_key UNIQUE(orgcode, invoiceno)"
                )


    with eng.connect() as con:
        if not columnExists("stock", "rate"):
            con.execute(
                "alter table stock add rate numeric(13,2) default 0.00"
            )

        # return 0


    with eng.connect() as con:
        # Migration for users -> gkusers
        # Decoupling users and organisations
        gkusersExist = tableExists("gkusers")
        usersExist = tableExists("users")
        oldUsersLength = 0
        gkusersLength = 0
        if usersExist:
            oldUsersLength = con.execute(
                "select COUNT(userid) as count from users"
            ).scalar()
            # print("Old users length = %d"%(oldUsersLength["count"]))
        if gkusersExist:
            gkusersLength = con.execute(
                select([func.count(gkdb.gkusers.c.userid).label("count")])
            ).scalar()
            # print("GK users length = %d"%(gkusersLength["count"]))
        if (not gkusersExist and usersExist) or (
            gkusersExist
            and usersExist
            and oldUsersLength > 0
            and gkusersLength == 0
        ):
            con.execute(
                "create table if not exists gkusers(userid serial, username text NOT NULL, userpassword text NOT NULL, userquestion text NOT NULL, useranswer text NOT NULL, orgs jsonb default '{}', primary key (userid), unique(username))"
            )
            if not columnExists("organisation", "users"):
                con.execute(
                    "alter table organisation add users jsonb default '{}'"
                )

            # prepare the tables that have userid as their Foreign Key for step 6
            # remove the old fkey constraints, change the old column name,
            # create the new column without fk pointing to users2 (must be done after the data migration),
            # update the old indexes with new fk
            con.execute("drop index if exists logindex")

            con.execute(
                "alter table log drop constraint if exists log_userid_fkey"
            )
            con.execute(
                "alter table rejectionnote drop constraint if exists rejectionnote_issuerid_fkey"
            )
            con.execute(
                "alter table drcr drop constraint if exists drcr_userid_fkey"
            )
            con.execute(
                "alter table usergodown drop constraint if exists usergodown_userid_fkey"
            )

            if not columnExists("log", "_userid"):
                print("renaming old userid columns to _userid")
                con.execute("alter table log rename column userid to _userid")
                con.execute("alter table drcr rename column userid to _userid")
                con.execute(
                    "alter table usergodown rename column userid to _userid"
                )
                con.execute(
                    "alter table rejectionnote rename column issuerid to _issuerid"
                )
            if not columnExists("log", "userid"):
                print("Adding a new column called userid, to store the new userid")
                con.execute("alter table log add userid integer default -1")
                con.execute(
                    "alter table rejectionnote add issuerid integer default -1"
                )
                con.execute("alter table drcr add userid integer default -1")
                con.execute(
                    "alter table usergodown add userid integer default -1"
                )

                con.execute("create index logindex on log (userid, activity)")

            allUserData = list(con.execute(select([gkdb.users])).fetchall())
            # (1) Loop through all the users
            notUniqueUsers = {}
            for uindex, udata in enumerate(allUserData):
                orgcode = udata["orgcode"]
                # print(1)
                orgData = con.execute(
                    select(
                        [gkdb.organisation.c.orgname, gkdb.organisation.c.orgtype]
                    ).where(gkdb.organisation.c.orgcode == orgcode)
                ).fetchone()

                # print(2)
                # (2) Find entries in allUserData with the same username and orgname
                # (same org, multiple Financial Years)
                otherFY = []
                orgs = {}
                orgs[udata["orgcode"]] = {
                    "userconf": udata["userconf"],
                    "invitestatus": True,
                    "userrole": udata["userrole"],
                }
                for uindex2 in range(uindex + 1, len(allUserData)):
                    # print(uindex2)
                    udata2 = allUserData[uindex2]
                    if udata["username"] == udata2["username"]:
                        orgData2 = con.execute(
                            select(
                                [
                                    gkdb.organisation.c.orgname,
                                    gkdb.organisation.c.orgtype,
                                ]
                            ).where(
                                gkdb.organisation.c.orgcode == udata2["orgcode"]
                            )
                        ).fetchone()
                        if (
                            orgData["orgname"] == orgData2["orgname"]
                            and orgData["orgtype"] == orgData2["orgtype"]
                        ):
                            print("FY org found %s" % (str(udata2["orgcode"])))
                            otherFY.append(
                                {
                                    "orgcode": udata2["orgcode"],
                                    "olduserid": udata2["userid"],
                                    "index": uindex2,
                                }
                            )
                            orgs[udata2["orgcode"]] = {
                                "userconf": udata2["userconf"],
                                "invitestatus": True,
                                "userrole": udata2["userrole"],
                            }
                        else:
                            # if user name is not unique across orgs
                            notUniqueUsers[udata2["username"]] = True
                            print(
                                "username: %s not unique, has to be renamed"
                                % (udata2["username"])
                            )

                if udata["username"] in notUniqueUsers:
                    # (3) create a unique user name (org name + user name)
                    orgname = "_".join(orgData["orgname"].split(" "))
                    orgtype = "p" if orgData["orgtype"] == "Profit Making" else "np"
                    uname = orgname + "_" + orgtype + "_" + udata["username"]
                else:
                    uname = udata["username"]

                # (4) create a table entry in users2 and userorg tables
                newUserData = {
                    "username": uname,
                    "userpassword": udata["userpassword"],
                    "userquestion": udata["userquestion"],
                    "useranswer": udata["useranswer"],
                    "userconf": {},
                    "orgs": orgs,
                }

                con.execute(gkdb.gkusers.insert(), [newUserData])

                # remove data from users table, if the user has a unique name
                """ Deletes old DB data, so commenting it out till dev is completed
                if udata["username"] not in notUniqueUsers:
                    con.execute(gkdb.users.delete().where(gkdb.users.c.userid == udata["userid"]))
                """

                newUserId = con.execute(
                    select([gkdb.gkusers.c.userid]).where(
                        gkdb.gkusers.c.username == uname
                    )
                ).fetchone()

                # ToDo: Update orgs table with userid
                con.execute(
                    "update organisation set users = jsonb_set(users, '{%s}', 'true') where orgcode = %d;"
                    % (
                        str(newUserId["userid"]),
                        udata["orgcode"],
                    )
                )

                # (5) If for the same org, multiple financial years are found,
                # add them to userorg table with the above created userid and
                # remove those entries from the allUserData array
                print("OtherFY len = %d" % (len(otherFY)))
                for udata3 in otherFY:
                    # remove data from users table, if the user has a unique name
                    """Deletes old DB data, so commenting it out till dev is completed
                    if udata["username"] not in notUniqueUsers:
                        con.execute(gkdb.users.delete().where(gkdb.users.c.userid == udata3["olduserid"]))
                    """
                    allUserData.pop(udata3["index"])
                    # Update orgs table with userid
                    con.execute(
                        "update organisation set users = jsonb_set(users, '{%s}', 'true') where orgcode = %d;"
                        % (
                            str(newUserId["userid"]),
                            udata3["orgcode"],
                        )
                    )

                    # (6.1) Update the tables where userid from users table was a Foreign Key
                    # tables to update log, rejectionnote, drcr, usergodown
                    con.execute(
                        "update log set userid = %d where _userid = %d"
                        % (newUserId["userid"], udata3["olduserid"])
                    )

                    con.execute(
                        "update rejectionnote set issuerid = %d where _issuerid = %d"
                        % (newUserId["userid"], udata3["olduserid"])
                    )

                    con.execute(
                        "update drcr set userid = %d where _userid = %d"
                        % (newUserId["userid"], udata3["olduserid"])
                    )

                    con.execute(
                        "update usergodown set userid = %d where _userid = %d"
                        % (newUserId["userid"], udata3["olduserid"])
                    )

                # (6.2) Update the tables where userid from users table was a Foreign Key
                # tables to update log, rejectionnote, drcr, usergodown
                con.execute(
                    "update log set userid = %d where _userid = %d"
                    % (newUserId["userid"], udata["userid"])
                )

                con.execute(
                    "update rejectionnote set issuerid = %d where _issuerid = %d"
                    % (newUserId["userid"], udata["userid"])
                )

                con.execute(
                    "update drcr set userid = %d where _userid = %d"
                    % (newUserId["userid"], udata["userid"])
                )

                con.execute(
                    "update usergodown set userid = %d where _userid = %d"
                    % (newUserId["userid"], udata["userid"])
                )
            # (7) After updating all the tables where userid was a fkey, add back the fkey constraint pointing to users2 table
            con.execute(
                "alter table log drop constraint if exists log_userid_fkey"
            )
            con.execute(
                "alter table log add constraint log_userid_fkey foreign key(userid) references gkusers(userid)"
            )

            con.execute(
                "alter table rejectionnote drop constraint if exists rejectionnote_issuerid_fkey"
            )
            con.execute(
                "alter table rejectionnote add constraint rejectionnote_issuerid_fkey foreign key(issuerid) references gkusers(userid)"
            )

            con.execute(
                "alter table drcr drop constraint if exists drcr_userid_fkey"
            )
            con.execute(
                "alter table drcr add constraint drcr_userid_fkey foreign key(userid) references gkusers(userid)"
            )

            con.execute(
                "alter table usergodown drop constraint if exists usergodown_userid_fkey"
            )
            con.execute(
                "alter table usergodown add constraint usergodown_userid_fkey foreign key(userid) references gkusers(userid) on delete cascade"
            )

        # End of Migration for users -> gkusers

    with eng.connect() as con:
        # Add opening stock value that corresponds to the product opening stock qty that has been entered
        if not columnExists("goprod", "openingstockvalue"):
            con.execute(
                "alter table goprod add openingstockvalue numeric(13,2) default 0.00"
            )

    with eng.connect() as con:
        orgDatum = con.execute(
            "select orgcode, orgstate from organisation"
        ).fetchall()
        states = con.execute(select([state.c.statename])).fetchall()
        states = [i[0].lower() for i in list(states or [])]
        for orgData in orgDatum:
            if str(orgData["orgstate"]).lower() not in states:
                con.execute(
                    "update organisation set orgstate = ''  where orgcode = %d"
                    % (orgData["orgcode"])
                )
        con.execute(
            "alter table organisation alter column orgstate set NOT NULL"
        )

    with eng.connect() as con:
        counter = 0
        con.execute("update product set gsflag = 7  where gsflag = NULL")
        prodDatum = con.execute(
            "select productcode, productdesc from product"
        ).fetchall()
        for prodData in prodDatum:
            if not prodData["productdesc"]:
                con.execute(
                    "update product set productdesc = 'gk-product-%s'  where productcode = %d"
                    % (str(counter), prodData["productcode"])
                )
                counter = counter + 1
        con.execute(
            "alter table product alter column gsflag set NOT NULL, alter column productdesc set NOT NULL"
        )

    with eng.begin() as con:
        con.execute("alter table bankrecon drop constraint if exists bankrecon_vouchercode_accountcode_key")
        con.execute("alter table bankrecon add column if not exists entry_type text")
        con.execute("alter table bankrecon add column if not exists amount float")

    with eng.begin() as con:
        con.execute("alter table customerandsupplier add column if not exists country text")
        con.execute("alter table customerandsupplier add column if not exists tin text")

    with eng.begin() as con:
        con.execute("alter table organisation add column if not exists tin text")

    with eng.begin() as con:
        if not does_foreignkey_exist(
                eng,
                "categorysubcategories",
                "categorysubcategories_subcategoryof_fkey"
        ):
            con.execute(
                "alter table categorysubcategories add  foreign key (subcategoryof) references categorysubcategories(categorycode)"
            )
        if not does_foreignkey_exist(
                eng,
                "unitofmeasurement",
                "unitofmeasurement_subunitof_fkey"
        ):
            con.execute(
            "alter table unitofmeasurement add  foreign key (subunitof) references unitofmeasurement(uomid)"
            )
        con.execute("alter table organisation add column if not exists invflag Integer default 0 ")
        con.execute("alter table vouchers add column if not exists invid Integer")
        if not does_foreignkey_exist(
                eng,
                "vouchers",
                "vouchers_invid_fkey"
        ):
            con.execute(
                "alter table vouchers add foreign key (invid) references invoice(invid)"
            )
        con.execute("alter table users add column if not exists themename text default 'Default'")

    with eng.begin() as con:
        con.execute("alter table transfernote add column if not exists recieveddate date")
        con.execute("alter table delchal add column if not exists noofpackages int")
        con.execute("alter table delchal add column if not exists modeoftransport text")

    with eng.begin() as con:
        if does_unique_constraint_exist(
                eng,
                "customerandsupplier",
                "customerandsupplier_orgcode_custname_custemail_csflag_key"
        ):
            con.execute(
                "alter table customerandsupplier drop constraint customerandsupplier_orgcode_custname_custemail_csflag_key"
            )
        if does_unique_constraint_exist(
                eng,
                "customerandsupplier",
                "customerandsupplier_orgcode_custname_custpan_csflag_key"
        ):
            con.execute(
                "alter table customerandsupplier drop constraint customerandsupplier_orgcode_custname_custpan_csflag_key"
            )
        if does_unique_constraint_exist(
                eng,
                "customerandsupplier",
                "customerandsupplier_orgcode_custname_custtan_csflag_key"
        ):
            con.execute(
                "alter table customerandsupplier drop constraint customerandsupplier_orgcode_custname_custtan_csflag_key"
            )
        if does_unique_constraint_exist(
                eng,
                "customerandsupplier",
                "customerandsupplier_orgcode_custname_gstin_key"
        ):
            con.execute(
                "alter table customerandsupplier drop constraint customerandsupplier_orgcode_custname_gstin_key"
            )
        if does_unique_constraint_exist(
                eng,
                "customerandsupplier",
                "customerandsupplier_orgcode_custname_tin_key"
        ):
            con.execute(
                "alter table customerandsupplier drop constraint customerandsupplier_orgcode_custname_tin_key"
            )

        if not does_unique_constraint_exist(
                eng,
                "customerandsupplier",
                "customerandsupplier_orgcode_custemail_key"
        ):
            con.execute(
                "alter table customerandsupplier add constraint customerandsupplier_orgcode_custemail_key unique (orgcode, custemail)"
            )
        if not does_unique_constraint_exist(
                eng,
                "customerandsupplier",
                "customerandsupplier_orgcode_custpan_key"
        ):
            con.execute(
                "alter table customerandsupplier add constraint customerandsupplier_orgcode_custpan_key unique (orgcode, custpan)"
            )
        if not does_unique_constraint_exist(
                eng,
                "customerandsupplier",
                "customerandsupplier_orgcode_custtan_key"
        ):
            con.execute(
                "alter table customerandsupplier add constraint customerandsupplier_orgcode_custtan_key unique (orgcode, custtan)"
            )
        if not does_unique_constraint_exist(
                eng,
                "customerandsupplier",
                "customerandsupplier_orgcode_gstin_key"
        ):
            con.execute(
                "alter table customerandsupplier add constraint customerandsupplier_orgcode_gstin_key unique (orgcode, gstin)"
            )
        if not does_unique_constraint_exist(
                eng,
                "customerandsupplier",
                "customerandsupplier_orgcode_tin_key"
        ):
            con.execute(
                "alter table customerandsupplier add constraint customerandsupplier_orgcode_tin_key unique (orgcode, tin)"
            )
        if not does_primarykey_exist(
                eng,
                "state",
                "state_pkey"
        ):
                con.execute(
                    "alter table state add primary key (statecode)"
                )


        with eng.begin() as con:

            con.execute(
                "alter table unitofmeasurement add column if not exists orgcode int references organisation"
            )
            if not does_foreignkey_exist(
                    eng,
                    "unitofmeasurement",
                    "unitofmeasurement_orgcode_fkey"
            ):
                con.execute(
                    "alter table unitofmeasurement add foreign key (orgcode) references organisation(orgcode)"
                )
            if does_unique_constraint_exist(
                    eng,
                    "unitofmeasurement",
                    "unitofmeasurement_unitname_key"
            ):
                con.execute(
                    "alter table unitofmeasurement drop constraint unitofmeasurement_unitname_key"
                )
            if not does_unique_constraint_exist(
                    eng,
                    "unitofmeasurement",
                    "unitofmeasurement_orgcode_unitname_key"
            ):
                con.execute(
                    "alter table unitofmeasurement add constraint unitofmeasurement_orgcode_unitname_key unique (orgcode, unitname)"
                )

        with eng.begin() as conn:
            if not tableExists("transaction"):
                query = """create table transaction(
                    transaction_id serial,
                    transaction_details jsonb,
                    primary key (transaction_id)
                )"""
                conn.execute(query)
            conn.execute("alter table invoice add column if not exists immutable_data_id Integer")
            if not does_foreignkey_exist(
                eng,
                "invoice",
                "invoice_transaction_id_fkey"
            ):
                conn.execute("""
                    alter table invoice add foreign key (immutable_data_id)
                    references transaction(transaction_id)
                """)
            conn.execute("alter table invoicebin add column if not exists immutable_data_id Integer")
            if not does_foreignkey_exist(
                eng,
                "invoicebin",
                "invoicebin_transaction_id_fkey"
            ):
                conn.execute("""
                    alter table invoicebin add foreign key (immutable_data_id)
                    references transaction(transaction_id)
                """)
            conn.execute("alter table purchaseorder add column if not exists immutable_data_id Integer")
            if not does_foreignkey_exist(
                eng,
                "purchaseorder",
                "purchaseorder_transaction_id_fkey"
            ):
                conn.execute("""
                    alter table purchaseorder add foreign key (immutable_data_id)
                    references transaction(transaction_id)
                """)
            conn.execute("alter table transfernote add column if not exists immutable_data_id Integer")
            if not does_foreignkey_exist(
                eng,
                "transfernote",
                "transfernote_transaction_id_fkey"
            ):
                conn.execute("""
                    alter table transfernote add foreign key (immutable_data_id)
                    references transaction(transaction_id)
                """)

        with eng.begin() as con:
            con.execute("alter table organisation add column if not exists cin text")

    with eng.begin() as conn:
        if not tableExists("bank"):
            bank.create(eng)

    with eng.begin() as con:
        MAX_UPLOAD_SIZE = os.environ.get("GKCORE_MAX_UPLOAD_SIZE") or 1048576

        if not does_check_constraint_exist(
            con,
            "organisation",
            "check_logo_size",
        ):
            con.execute(
                "alter table organisation add constraint check_logo_size check (length(logo::text) <= %d)"
                % (MAX_UPLOAD_SIZE)
            )
        if not does_check_constraint_exist(
            con,
            "vouchers",
            "check_attachment_size",
        ):
            con.execute(
                "alter table vouchers add constraint check_attachment_size check (length(attachment::text) <= %d)"
                % (MAX_UPLOAD_SIZE)
            )
        if not does_check_constraint_exist(
            con,
            "invoice",
            "check_attachment_size",
        ):
            con.execute(
                "alter table invoice add constraint check_attachment_size check (length(attachment::text) <= %d)"
                % (MAX_UPLOAD_SIZE)
            )
        if not does_check_constraint_exist(
            con,
            "invoicebin",
            "check_attachment_size",
        ):
            con.execute(
                "alter table invoicebin add constraint check_attachment_size check (length(attachment::text) <= %d)"
                % (MAX_UPLOAD_SIZE)
            )
        if not does_check_constraint_exist(
            con,
            "delchal",
            "check_attachment_size",
        ):
            con.execute(
                "alter table delchal add constraint check_attachment_size check (length(attachment::text) <= %d)"
                % (MAX_UPLOAD_SIZE)
            )
        if not does_check_constraint_exist(
            con,
            "delchalbin",
            "check_attachment_size",
        ):
            con.execute(
                "alter table delchalbin add constraint check_attachment_size check (length(attachment::text) <= %d)"
                % (MAX_UPLOAD_SIZE)
            )
        if not does_check_constraint_exist(
            con,
            "purchaseorder",
            "check_attachment_size",
        ):
            con.execute(
                "alter table purchaseorder add constraint check_attachment_size check (length(attachment::text) <= %d)"
                % (MAX_UPLOAD_SIZE)
            )
        if not does_check_constraint_exist(
            con,
            "drcr",
            "check_attachment_size",
        ):
            con.execute(
                "alter table drcr add constraint check_attachment_size check (length(attachment::text) <= %d)"
                % (MAX_UPLOAD_SIZE)
            )

        print("Database migration successful")
