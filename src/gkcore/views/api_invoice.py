"""
Copyright (C) 2013, 2014, 2015, 2016 Digital Freedom Foundation
Copyright (C) 2017, 2018, 2019, 2020 Digital Freedom Foundation & Accion Labs Pvt. Ltd.
  This file is part of GNUKhata:A modular,robust and Free Accounting System.

  GNUKhata is Free Software; you can redistribute it and/or modify
  it under the terms of the GNU Affero General Public License as
  published by the Free Software Foundation; either version 3 of
  the License, or (at your option) any later version.

  GNUKhata is distributed in the hope that it will be useful, but
  WITHOUT ANY WARRANTY; without even the implied warranty of
  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
  GNU Affero General Public License for more details.

  You should have received a copy of the GNU Affero General Public
  License along with GNUKhata (COPYING); if not, write to the
  Free Software Foundation, Inc., 51 Franklin Street, Fifth Floor,
  Boston, MA  02110-1301  USA59 Temple Place, Suite 330,


Contributors:
"Krishnakant Mane" <kk@gmail.com>
"Ishan Masdekar " <imasdekar@dff.org.in>
"Navin Karkera" <navin@dff.org.in>
"Mohd. Talha Pawaty" <mtalha456@gmail.com>
"Vaibhav Kurhe" <vaibhav.kurhe@gmail.com>
"Bhavesh Bawadhane" <bbhavesh07@gmail.com>
"Prajkta Patkar" <prajakta@dff.org.in>
"Reshma Bhatwadekar" <bhatawadekar1reshma@gmail.com>
"Aditya Shukla" <adityashukla9158.as@gmail.com>
"Rupali Badgujar" <rupalibadgujar1234@gmail.com>
"Rohan Khairnar" <rohankhairnar5@gmail.com>
"""


from gkcore import eng, enumdict
from gkcore.models.gkdb import (
    invoice,
    transaction,
    dcinv,
    delchal,
    stock,
    product,
    customerandsupplier,
    unitofmeasurement,
    godown,
    rejectionnote,
    drcr,
    tax,
    state,
    users,
    goprod,
    organisation,
    accounts,
    state,
    vouchers,
    groupsubgroups,
    bankrecon,
    billwise,
    cslastprice,
    invoicebin,
    log,
)
from gkcore.views.api_tax import calTax
from sqlalchemy.sql import select
import json
from sqlalchemy.engine.base import Connection
from sqlalchemy import and_, exc, desc, func
from sqlalchemy.sql.expression import text
from pyramid.response import Response
from pyramid.view import view_defaults, view_config
from datetime import datetime, date
import jwt
import gkcore
from gkcore.utils import authCheck
from gkcore.views.organisation.services import get_organisation_profile
from gkcore.utils import authCheck, getUserRole
from gkcore.views.helpers.delivery_note import create_delivery_note, cancel_delivery_note
from gkcore.views.helpers.voucher import cancel_voucher
import traceback  # for printing detailed exception logs


def createAccount(con, type, accName, orgcode):
    try:
        """
        Purpose: Create account.
        While creating automatic voucher if required account not found then it will create that account.
        It reurns that created accounts accountcode.
        type is used to specify that what type of account is creating. Group name will be decides on basis of that.
        And if the account is default then proper defaultflag will set for that.
        """
        groupName = ""
        default = 0
        sys = 0
        # product sale account
        if type == 19:
            groupName = "Sales"
            # sales default account
            if accName == "Sale A/C":
                default = 19
        # product purchase account
        elif type == 16:
            groupName = "Purchase"
            # purchase default account
            if accName == "Purchase A/C":
                default = 16
        # default cash account
        elif type == 3:
            groupName = "Cash"
            default = 3
        # default bank account
        elif type == 2:
            groupName = "Bank"
            default = 2
        # Tax account
        elif type == 20:
            groupName = "Duties & Taxes"
            sys = 1
        # customer or supplier account when payment mode is on credit
        elif type == 15:
            custOrSupl = con.execute(
                select([customerandsupplier.c.csflag]).where(
                    and_(
                        customerandsupplier.c.custname == str(accName),
                        customerandsupplier.c.orgcode == orgcode,
                    )
                )
            )
            flagCS = custOrSupl.fetchone()
            # customer
            if int(flagCS["csflag"]) == 3:
                groupName = "Sundry Debtors"
            # suplier
            if int(flagCS["csflag"]) == 19:
                groupName = "Sundry Creditors for Purchase"
        # Roundoff default account
        elif type == 18:
            # Roundoff paid is in expense group
            if accName == "Round Off Paid":
                groupName = "Indirect Expense"
                default = 180
            # Roundoff received in income group
            if accName == "Round Off Received":
                groupName = "Indirect Income"
                default = 181

        group = con.execute(
            select([groupsubgroups.c.groupcode]).where(
                and_(
                    groupsubgroups.c.groupname == str(groupName),
                    groupsubgroups.c.orgcode == int(orgcode),
                )
            )
        )
        grpCode = group.fetchone()
        resultp = con.execute(
            accounts.insert(),
            {
                "accountname": accName,
                "groupcode": grpCode["groupcode"],
                "orgcode": orgcode,
                "defaultflag": default,
                "sysaccount": sys,
            },
        )
        # fetch accountcode
        accCode = con.execute(
            select([accounts.c.accountcode]).where(
                and_(
                    accounts.c.accountname == accName,
                    accounts.c.defaultflag == default,
                    accounts.c.orgcode == orgcode,
                )
            )
        )
        accountCode = accCode.fetchone()

        return {
            "gkstatus": enumdict["Success"],
            "accountcode": int(accountCode["accountcode"]),
        }
    except:
        print(traceback.format_exc())
        return {"gkstatus": gkcore.enumdict["ConnectionFailed"]}


def getDefaultAcc(con, queryParams, orgcode):
    """
    Purpose: Returns default accounts.
    Invoice type can be determined from inoutflag. (inoutflag = 9 = Purchase invoice, inoutflag = 15 = Purchase invoice,)
    Payment Mode  15 = on credit , 3 = Cash , 2 = Bank
    Tax Type = GST :7(As default) or 22:VAT
    taxtype as a keys for dictionary where percentage is key and_ amount is value.
    csname will have customer or supplier name.
    maflag = multiple account flag in organisations table. 1 =True i.e. each product account need to be debited / credited
    destination state is required to create accountname for tax
    taxDict = {"SGSTIN_MH@12%":600,"CESSIN_MH@2%":800}

    in case of Vat we need total taxable value and totaltax amount which will be dr/cr in sale/purchase a/c and vat a/c resprectively.
    So the structure of queryParams = {"invtype":19 or 16 ,"csname":customer/supplier name ,"pmtmode":2 or 3 or 15 or 4 or 5,"taxType":7 or 22,"gstname":"CGST / IGST","cessname":"cess","maflag":True /False,"products":{"productname":Taxable value,"productname1":Taxabe value,.........},"destination":taxstate,"totaltaxablevalue":value,"totalAmount":invoicetotal,"invoicedate":invDate,"invid":id,"invoiceno":invno,"taxpayement":VATtax,"prodData":productcode:taxabale value ....,"taxes":{productcode:tax}}

    payment modes = 2 - Bank (POS), 3  - Cash (POS), 4  - Bank (Party), 5  - Cash (Party), 15 - Credit

    * POS creates vouchers directly between sale/purchase a/c and mode of payment a/c.
    * Party creates voucher first between sale/purchase a/c and the party a/c, then between party a/c and mode of payment a/c.
    """
    taxRateDict = {
        1: 0.5,
        3: 1.5,
        5: 2.5,
        12: 6,
        18: 9,
        28: 14,
        0.1: 0.05,
        0.25: 0.125,
        1.5: 0.75,
        7.5: 3.75,
    }
    vouchers_List = []
    voucherDict = {}
    rd_VoucherDict = {}
    crs = {}
    drs = {}
    rdcrs = {}  # Round off crs
    rddrs = {}  # Round off drs
    Narration = ""
    v_No = []
    v_ID = []
    totalTaxableVal = float(queryParams["totaltaxablevalue"])
    total_amount = float(queryParams["totalAmount"])
    total_paid = queryParams["total_paid"]
    taxDict = {}
    taxRate = 0.00
    cessRate = 0.00

    isSale = int(queryParams["invtype"]) == 15
    invType = (
        ["Sale", "Sold", "to", "OUT", "Receipt"]
        if isSale
        else ["Purchase", "Bought", "from", "IN", "Payment"]
    )
    defAccFlag = 19 if isSale else 16
    formType = "invoice" if ("csname" in queryParams) else "point of sale"
    # first check the invoice type sale or purchase.
    # 15 = out = sale & 9 = in = purchase

    # if multiple account is 1 , then search for all the sale accounts of products in invoices
    if int(queryParams["maflag"]) == 1:
        prodData = queryParams["products"]
        for prod in prodData:
            proN = str(prod) + " " + invType[0]
            prodAcc = con.execute(
                select([accounts.c.accountcode]).where(
                    and_(
                        accounts.c.accountname == proN,
                        accounts.c.orgcode == orgcode,
                    )
                )
            )
            prodAccount = prodAcc.fetchone()

            try:
                accCode = prodAccount["accountcode"]
            except:
                a = createAccount(con, defAccFlag, str(proN), orgcode)
                accCode = a["accountcode"]
            if isSale:
                crs[accCode] = "%.2f" % float(prodData[prod])
            else:
                drs[accCode] = "%.2f" % float(prodData[prod])
    else:
        # if multiple acc is 0 , then select default sale account
        salesAccount = con.execute(
            select([accounts.c.accountcode]).where(
                and_(
                    accounts.c.defaultflag == defAccFlag,
                    accounts.c.orgcode == orgcode,
                )
            )
        )
        saleAcc = salesAccount.fetchone()

        try:
            accCode = saleAcc["accountcode"]
        except:
            a = createAccount(con, defAccFlag, invType[0] + " A/C", orgcode)
            accCode = a["accountcode"]
        if isSale:
            crs[accCode] = "%.2f" % float(totalTaxableVal)
        else:
            drs[accCode] = "%.2f" % float(totalTaxableVal)

    if int(queryParams["icflag"]) == 9:
        if total_paid:
            payment_narration = (
                f"{invType[4]} for {queryParams['csname']} ref {formType} no."
                f" {queryParams['invoiceno']}"
            )
            voucherDict = {
                **queryParams["payment_vouchers"],
                "voucherdate": queryParams["invoicedate"],
                "narration": payment_narration,
                "vouchertype": "receipt" if isSale else "payment",
                "invid": queryParams["invid"],
            }
            vouchers_List.append(voucherDict)
        custAcc = con.execute(
            select([accounts.c.accountcode]).where(
                and_(
                    accounts.c.accountname == queryParams["csname"],
                    accounts.c.orgcode == orgcode,
                )
            )
        )
        custAccount = custAcc.fetchone()

        try:
            custAccCode = custAccount["accountcode"]
        except:
            a = createAccount(con, 15, str(queryParams["csname"]), orgcode)
            custAccCode = a["accountcode"]

        if isSale:
            drs[custAccCode] = "%.2f" % float(total_amount)
        else:
            crs[custAccCode] = "%.2f" % float(total_amount)
        csa = custAccCode
    else:
        drs = queryParams["payment_vouchers"]["drs"]
        csa = con.execute(
            select([accounts.c.accountcode]).where(
                and_(
                    accounts.c.accountname == "Cash in hand",
                    accounts.c.orgcode == orgcode,
                )
            )
        ).scalar()


    Narration = (
        f'{invType[1]} goods worth rupees {total_paid:.2f} {invType[2]} {queryParams["csname"]} '
        f'ref {formType} no. {queryParams["invoiceno"]}'
    )

    # collect all taxaccounts with the value that needs to be dr or cr
    if int(queryParams["taxType"]) == 7:
        abv = con.execute(
            select([state.c.abbreviation]).where(
                state.c.statename == queryParams["destinationstate"]
            )
        )
        abb = abv.fetchone()
        taxName = queryParams["gstname"]
        if taxName == "CGST":
            for prod in queryParams["prodData"]:
                taxRate = float(queryParams["taxes"][prod])
                taxable = float(queryParams["prodData"][prod])
                if taxRate > 0.00:
                    tx = float(taxRate) / 2
                    # this is the value which is going to Dr/Cr
                    taxVal = taxable * (tx / 100)
                    isInt = ((taxRate * 10) % 10) == 0
                    if isInt:
                        taxRate = int(taxRate)
                    taxHalf = taxRateDict[taxRate]

                    taxNameSGST = (
                        "SGST"
                        + invType[3]
                        + "_"
                        + str(abb["abbreviation"])
                        + "@"
                        + str(taxHalf)
                        + "%"
                    )
                    taxNameCGST = (
                        "CGST"
                        + invType[3]
                        + "_"
                        + str(abb["abbreviation"])
                        + "@"
                        + str(taxHalf)
                        + "%"
                    )

                    if taxNameSGST not in taxDict:
                        taxDict[taxNameSGST] = "%.2f" % float(taxVal)
                        taxDict[taxNameCGST] = "%.2f" % float(taxVal)
                    else:
                        val = float(taxDict[taxNameSGST])
                        taxDict[taxNameSGST] = "%.2f" % float(taxVal + val)
                        taxDict[taxNameCGST] = "%.2f" % float(taxVal + val)

        if taxName == "IGST":
            for prod in queryParams["prodData"]:
                taxRate = float(queryParams["taxes"][prod])
                taxable = float(queryParams["prodData"][prod])
                if taxRate > 0.00:
                    tx = float(taxRate)
                    # this is the value which is going to Dr/Cr
                    taxVal = taxable * (tx / 100)
                    taxNameIGST = (
                        "IGST"
                        + invType[3]
                        + "_"
                        + str(abb["abbreviation"])
                        + "@"
                        + str(int(taxRate))
                        + "%"
                    )
                    if taxNameIGST not in taxDict:
                        taxDict[taxNameIGST] = "%.2f" % float(taxVal)
                    else:
                        val = float(taxDict[taxNameIGST])
                        taxDict[taxNameIGST] = "%.2f" % float(taxVal + val)

        for prod in queryParams["prodData"]:
            cessRate = float(queryParams["cess"][prod])
            CStaxable = float(queryParams["prodData"][prod])

            if cessRate > 0.00:
                cs = float(cessRate)
                # this is the value which is going to Dr/Cr
                csVal = CStaxable * (cs / 100)
                taxNameCESS = (
                    "CESS"
                    + invType[3]
                    + "_"
                    + str(abb["abbreviation"])
                    + "@"
                    + str(int(cs))
                    + "%"
                )
                if taxNameCESS not in taxDict:
                    taxDict[taxNameCESS] = "%.2f" % float(csVal)
                else:
                    val = float(taxDict[taxNameCESS])
                    taxDict[taxNameCESS] = "%.2f" % float(csVal + val)

        for Tax in taxDict:
            taxAcc = con.execute(
                select([accounts.c.accountcode]).where(
                    and_(
                        accounts.c.accountname == Tax,
                        accounts.c.orgcode == orgcode,
                    )
                )
            )
            taxRow = taxAcc.fetchone()

            try:
                accCode = taxRow["accountcode"]
            except:
                a = createAccount(con, 20, str(Tax), orgcode)
                accCode = a["accountcode"]
            if isSale:
                crs[accCode] = "%.2f" % float(taxDict[Tax])
            else:
                drs[accCode] = "%.2f" % float(taxDict[Tax])

    if int(queryParams["taxType"]) == 22:
        taxAcc = con.execute(
            select([accounts.c.accountcode]).where(
                and_(
                    accounts.c.accountname == "VAT_" + invType[3],
                    accounts.c.orgcode == orgcode,
                )
            )
        )
        taxRow = taxAcc.fetchone()

        try:
            accCode = taxRow["accountcode"]
        except:
            a = createAccount(con, 20, "VAT_" + invType[3], orgcode)
            accCode = a["accountcode"]

        for prod in queryParams["prodData"]:
            taxRate = float(queryParams["taxes"][prod])
            taxable = float(queryParams["prodData"][prod])
            if taxRate > 0.00:
                tx = float(taxRate)
                # this is the value which is going to Dr/Cr
                taxVal = taxable * (tx / 100)
                taxNameVAT = "VAT_" + invType[3]

                if taxNameVAT not in taxDict:
                    taxDict[taxNameVAT] = "%.2f" % float(taxVal)
                else:
                    val = float(taxDict[taxNameVAT])
                    taxDict[taxNameVAT] = "%.2f" % float(taxVal + val)


            if isSale:
                crs[accCode] = "%.2f" % float(taxVal)
            else:
                drs[accCode] = "%.2f" % float(taxVal)

    for Tax in taxDict:
        if isSale:
            crs[accCode] = "%.2f" % float(taxDict[Tax])
        else:
            drs[accCode] = "%.2f" % float(taxDict[Tax])

    voucherDict = {
        "drs": drs,
        "crs": crs,
        "voucherdate": queryParams["invoicedate"],
        "narration": Narration,
        "vouchertype": "sales" if isSale else "purchase",
        "invid": queryParams["invid"],
    }
    vouchers_List.append(voucherDict)

    # check whether amount paid is rounded off
    if "roundoffamt" in queryParams:
        isRoundOffPositive = float(queryParams["roundoffamt"]) > 0.00
        isRoundOffNegative = float(queryParams["roundoffamt"]) < 0.00
        if isRoundOffPositive:
            defRoundOffFlag = 180 if isSale else 181
            voucherType = "payment" if isSale else "receipt"
            narration = (
                "Round off amount spent" if isSale else "Round off amount earned"
            )
            accName = "Round Off Paid" if isSale else "Round Off Received"
        elif isRoundOffNegative:
            defRoundOffFlag = 181 if isSale else 180
            voucherType = "receipt" if isSale else "payment"
            narration = (
                "Round off amount earned" if isSale else "Round off amount spent"
            )
            accName = "Round Off Received" if isSale else "Round Off Paid"
        # user has spent rounded of amount
        roundAcc = con.execute(
            select([accounts.c.accountcode]).where(
                and_(
                    accounts.c.defaultflag == defRoundOffFlag,
                    accounts.c.orgcode == orgcode,
                )
            )
        )
        roundRow = roundAcc.fetchone()

        try:
            accCode = roundRow["accountcode"]
        except:
            a = createAccount(con, 18, accName, orgcode)
            accCode = a["accountcode"]
        if (isSale and isRoundOffPositive) or (
            not isSale and not isRoundOffPositive
        ):
            rddrs[accCode] = "%.2f" % float(queryParams["roundoffamt"])
        elif (isSale and not isRoundOffPositive) or (
            not isSale and isRoundOffPositive
        ):
            rdcrs[accCode] = "%.2f" % float(queryParams["roundoffamt"])

        if formType == "invoice":
            if (isSale and isRoundOffPositive) or (
                not isSale and not isRoundOffPositive
            ):
                rdcrs[csa] = "%.2f" % float(queryParams["roundoffamt"])
            elif (isSale and not isRoundOffPositive) or (
                not isSale and isRoundOffPositive
            ):
                rddrs[csa] = "%.2f" % float(queryParams["roundoffamt"])
            rd_VoucherDict = {
                "drs": rddrs,
                "crs": rdcrs,
                "voucherdate": queryParams["invoicedate"],
                "narration": narration,
                "vouchertype": "journal",
                "invid": queryParams["invid"],
            }
            vouchers_List.append(rd_VoucherDict)

    for vch in vouchers_List:
        drs = vch["drs"]
        crs = vch["crs"]
        vch["orgcode"] = orgcode

        # generate voucher number if it is not sent.

        if vch["vouchertype"] == "sales":
            initialType = "sl"
        if vch["vouchertype"] == "purchase":
            initialType = "pu"
        if vch["vouchertype"] == "payment":
            initialType = "pt"
        if vch["vouchertype"] == "receipt":
            initialType = "rt"
        if vch["vouchertype"] == "journal":
            initialType = "jr"
        vchCountResult = con.execute(
            text("select count(vouchercode) as vcount from vouchers where orgcode = :orgcode and vouchertype = :vouchertype"),
            orgcode = orgcode,
            vouchertype = vch["vouchertype"],
        )
        vchCount = vchCountResult.fetchone()
        initialType = initialType + str(vchCount["vcount"] + 1)

        vch["vouchernumber"] = initialType
        result = con.execute(vouchers.insert(), [vch])
        vouchercodedata = con.execute(
            "select max(vouchercode) as vcode from vouchers"
        )
        vouchercode = vouchercodedata.fetchone()
        for drkeys in list(drs.keys()):
            con.execute(
                "update accounts set vouchercount = vouchercount +1 where accountcode = %d"
                % (int(drkeys))
            )
            accgrpdata = con.execute(
                select(
                    [groupsubgroups.c.groupname, groupsubgroups.c.groupcode]
                ).where(
                    groupsubgroups.c.groupcode
                    == (
                        select([accounts.c.groupcode]).where(
                            accounts.c.accountcode == int(drkeys)
                        )
                    )
                )
            )
            accgrp = accgrpdata.fetchone()
            if accgrp["groupname"] == "Bank":
                recoresult = con.execute(
                    bankrecon.insert(),
                    [
                        {
                            "vouchercode": int(vouchercode["vcode"]),
                            "accountcode": drkeys,
                            "orgcode": orgcode,
                            "amount": float(drs[drkeys]),
                            "entry_type": "Dr",
                        }
                    ],
                )
        for crkeys in list(crs.keys()):
            con.execute(
                "update accounts set vouchercount = vouchercount +1 where accountcode = %d"
                % (int(crkeys))
            )
            accgrpdata = con.execute(
                select(
                    [groupsubgroups.c.groupname, groupsubgroups.c.groupcode]
                ).where(
                    groupsubgroups.c.groupcode
                    == (
                        select([accounts.c.groupcode]).where(
                            accounts.c.accountcode == int(crkeys)
                        )
                    )
                )
            )
            accgrp = accgrpdata.fetchone()
            if accgrp["groupname"] == "Bank":
                recoresult = con.execute(
                    bankrecon.insert(),
                    [
                        {
                            "vouchercode": int(vouchercode["vcode"]),
                            "accountcode": crkeys,
                            "orgcode": orgcode,
                            "amount": float(crs[crkeys]),
                            "entry_type": "Cr",
                        }
                    ],
                )
        v_No.append(vch["vouchernumber"])
        v_ID.append(int(vouchercode["vcode"]))
        # once transaction is made with cash or bank, we have to make entry of payment in invoice table and billwise table as well.
        if (
            total_paid
            and "Round off amount" not in vch["narration"]
        ):
            con.execute(
                invoice.update()
                .where(invoice.c.invid == queryParams["invid"])
                .values(amountpaid=total_paid)
            )
            con.execute(
                billwise.insert(),
                [
                    {
                        "vouchercode": int(vouchercode["vcode"]),
                        "adjamount": total_paid,
                        "invid": queryParams["invid"],
                        "orgcode": orgcode,
                    }
                ],
            )

    return {"gkstatus": enumdict["Success"], "vchNo": v_No, "vid": v_ID}


def gst(ProductCode, con):
    gstData = con.execute(
        select([product.c.gsflag, product.c.gscode]).where(
            product.c.productcode == ProductCode
        )
    )
    gst = gstData.fetchone()
    return {"gsflag": gst["gsflag"], "gscode": gst["gscode"]}


def getStateCode(StateName, con):
    stateData = con.execute(
        select([state.c.statecode]).where(state.c.statename == StateName)
    )
    staterow = stateData.fetchone()
    return {"statecode": staterow["statecode"]}


def getInvoiceData(con, orgcode, params):
    result = con.execute(
        select([invoice]).where(
            and_(invoice.c.invid == params["invid"], invoice.c.orgcode == orgcode)
        )
    )
    invrow = result.fetchone()
    roundoffvalue = 0.00
    if invrow["roundoffflag"] == 1:
        roundoffvalue = round(invrow["invoicetotal"])

    inv = {
        "roundoffvalue": "%.2f" % float(roundoffvalue),
        "invid": invrow["invid"],
        "taxflag": invrow["taxflag"],
        "invoiceno": invrow["invoiceno"],
        "ewaybillno": invrow["ewaybillno"],
        "invoicedate": datetime.strftime(invrow["invoicedate"], "%d-%m-%Y"),
        "icflag": invrow["icflag"],
        "invoicetotal": "%.2f" % float(invrow["invoicetotal"]),
        "invoicetotalword": invrow["invoicetotalword"],
        "bankdetails": invrow["bankdetails"],
        "orgstategstin": invrow["orgstategstin"],
        "paymentmode": invrow["paymentmode"],
        "inoutflag": invrow["inoutflag"],
        "roundoff": invrow["roundoffflag"],
        "narration": invrow["invnarration"],
        "discflag": invrow["discflag"],
    }

    # If purchase invoice, send suplier invoice no and date
    if invrow["inoutflag"] == 9:
        inv["supinvno"] = invrow["supinvno"] or ""
        inv["supinvdate"] = (
            datetime.strftime(invrow["supinvdate"], "%d-%m-%Y")
            if invrow["supinvdate"]
            else ""
        )

    # below field deletable is for check whether invoice having voucher or not
    # vch_count is checking whether there is any billwise entry of particular invid is available in billwise or not
    v_count = con.execute(
        "select count(vouchercode) as vcount from billwise where invid = '%d' "
        % (int(params["invid"]))
    )
    vch_count = v_count.fetchone()
    # vch_count is checking whether there is any entry of particular invid is available in dr cr table or not
    cd_count = con.execute(
        "select count(drcrno) as vcdcount from drcr where invid = '%d' "
        % (int(params["invid"]))
    )
    cdh_count = cd_count.fetchone()
    # r_count is checking whether there is any entry of particular invid is available in rejection note
    r_count = con.execute(
        "select count(rnno) as vrncount from rejectionnote where invid = '%d' "
        % (int(params["invid"]))
    )
    rc_count = r_count.fetchone()
    # if any bilwise or dr cr or rejection note is available then should send 1
    # 1 is : not delete and 0 is: delete permission.
    if (
        (vch_count["vcount"] > 0)
        or (cdh_count["vcdcount"] > 0)
        or (rc_count["vrncount"] > 0)
    ):
        inv["deletable"] = 1
    else:
        inv["deletable"] = 0
    inv["sourcestate"] = None
    inv["sourcestatecode"] = None
    if invrow["sourcestate"]:
        inv["sourcestate"] = invrow["sourcestate"]
        sourceStateCode = getStateCode(invrow["sourcestate"], con)["statecode"]
        inv["sourcestatecode"] = sourceStateCode
    if invrow["address"] == None:
        inv["address"] = ""
    else:
        inv["address"] = invrow["address"]
    if invrow["pincode"] == None:
        inv["pincode"] = ""
    else:
        inv["pincode"] = invrow["pincode"]
    if invrow["icflag"] == 9:
        inv["issuername"] = invrow["issuername"]
        inv["designation"] = invrow["designation"]
        inv["consignee"] = invrow["consignee"]
        inv["attachmentcount"] = invrow["attachmentcount"]
        if invrow["dateofsupply"] != None:
            inv["dateofsupply"] = datetime.strftime(
                invrow["dateofsupply"], "%d-%m-%Y"
            )
        else:
            inv["dateofsupply"] = ""
        inv["transportationmode"] = invrow["transportationmode"]
        inv["vehicleno"] = invrow["vehicleno"]
        inv["reversecharge"] = invrow["reversecharge"]
        inv["destinationstate"] = None
        inv["taxstatecode"] = None
        if invrow["taxstate"]:
            inv["destinationstate"] = invrow["taxstate"]
            taxStateCode = getStateCode(invrow["taxstate"], con)["statecode"]
            inv["taxstatecode"] = taxStateCode

        result = con.execute(
            select([dcinv.c.dcid]).where(dcinv.c.invid == invrow["invid"])
        )
        dcid = result.fetchone()
        if result.rowcount > 0:
            dc = con.execute(
                select([delchal.c.dcno, delchal.c.dcdate]).where(
                    delchal.c.dcid == dcid["dcid"]
                )
            )
            inv["dcid"] = dcid["dcid"]
            delchalData = dc.fetchone()
            if delchalData:
                inv["dcno"] = delchalData["dcno"]
                inv["dcdate"] = datetime.strftime(delchalData["dcdate"], "%d-%m-%Y")
        custandsup = con.execute(
            select(
                [
                    customerandsupplier.c.custname,
                    customerandsupplier.c.state,
                    customerandsupplier.c.custaddr,
                    customerandsupplier.c.custtan,
                    customerandsupplier.c.gstin,
                    customerandsupplier.c.csflag,
                    customerandsupplier.c.custphone,
                    customerandsupplier.c.pincode,
                    customerandsupplier.c.gst_reg_type,
                    customerandsupplier.c.gst_party_type,
                ]
            ).where(customerandsupplier.c.custid == invrow["custid"])
        )
        custData = custandsup.fetchone()

        if invrow["inoutflag"] == 15:
            custsc = inv["taxstatecode"]
            custSatename = inv["destinationstate"]
        else:
            custsc = inv["sourcestatecode"]
            custSatename = inv["sourcestate"]

        statelist = []
        if custData["gstin"] != None and bool(custData["gstin"]):
            # below code listed those state of customer which having gstin
            for statecd in custData["gstin"]:
                statedata = con.execute(
                    select([state.c.statename, state.c.statecode]).where(
                        state.c.statecode == statecd
                    )
                )
                statename = statedata.fetchone()
                statelist.append({statename["statecode"]: statename["statename"]})

            custsupstatecode = None
            if custData["state"]:
                custsupstatecode = getStateCode(custData["state"], con)["statecode"]
            if str(custsupstatecode) not in list(custData["gstin"].keys()):
                statelist.append({custsupstatecode: custData["state"]})
            if custsc != custsupstatecode and str(custsc) not in list(
                custData["gstin"].keys()
            ):
                statelist.append({custsc: custSatename})
        else:
            custsupstatecode = None
            if custData["state"]:
                custsupstatecode = getStateCode(custData["state"], con)["statecode"]
            statelist.append({custsupstatecode: custData["state"]})
            if custsc != custsupstatecode:
                statelist.append({custsc: custSatename})

        custSupDetails = {
            "custid": invrow["custid"],
            "custname": custData["custname"],
            "custsupstate": custData["state"],
            "custaddr": custData["custaddr"],
            "csflag": custData["csflag"],
            "pincode": custData["pincode"],
            "custphone": custData["custphone"],
            "custsupstatecode": custsupstatecode,
            "custgstinlist": custData["gstin"],
            "statelist": statelist,
            "gst_reg_type": custData["gst_reg_type"],
            "gst_party_type": custData["gst_party_type"],
        }

        if custData["custtan"] != None:
            custSupDetails["custtin"] = custData["custtan"]
        if custData["gstin"] != None:
            if invrow["inoutflag"] == 15:
                try:
                    custSupDetails["custgstin"] = custData["gstin"][
                        str(taxStateCode)
                    ]
                except:
                    custSupDetails["custgstin"] = None
            else:
                try:
                    custSupDetails["custgstin"] = custData["gstin"][
                        str(sourceStateCode)
                    ]
                except:
                    custSupDetails["custgstin"] = None

        inv["custSupDetails"] = custSupDetails
    else:
        result = con.execute(
            select([dcinv.c.dcid]).where(dcinv.c.invid == invrow["invid"])
        )
        dcid = result.fetchone()
        if result.rowcount > 0:
            dc = con.execute(
                select([delchal.c.dcno, delchal.c.dcdate]).where(
                    delchal.c.dcid == dcid["dcid"]
                )
            )
            inv["dcid"] = dcid["dcid"]
            delchalData = dc.fetchone()
            if delchalData:
                inv["dcno"] = delchalData["dcno"]
                inv["dcdate"] = datetime.strftime(delchalData["dcdate"], "%d-%m-%Y")
    # contents is a nested dictionary from invoice table.
    # It contains productcode as the key with a value as a dictionary.
    # this dictionary has two key value pairs, priceperunit and quantity.
    contentsData = invrow["contents"]
    # invContents is the finally dictionary which will not just have the dataset from original contents,
    # but also productdesc,unitname,freeqty,discount,taxname,taxrate,amount and taxam
    invContents = {}
    # get the dictionary of discount and access it inside the loop for one product each.
    # do the same with freeqty.
    totalDisc = 0.00
    totalTaxableVal = 0.00
    totalTaxAmt = 0.00
    totalCessAmt = 0.00
    discounts = invrow["discount"]
    freeqtys = invrow["freeqty"]
    # now looping through the contents.
    # pc will have the productcode which will be the ke in invContents.
    for pc in list(contentsData.keys()):
        if not pc:
            continue
        # freeqty and discount can be 0 as these field were not present in previous version of 4.25 hence we have to check if it is None or not and have to pass values accordingly for code optimization.
        if discounts != None:
            # discflag is for discount type. Percent=16/Amount=1
            # here we convert percent discount in to amount.
            if invrow["discflag"] == 16:
                qty = float(list(contentsData[str(pc)].keys())[0])
                price = float(list(contentsData[str(pc)].values())[0])
                totalWithoutDiscount = qty * price
                discount = totalWithoutDiscount * float(float(discounts[pc]) / 100)
            else:
                discount = discounts[pc]
        else:
            discount = 0.00

        if freeqtys != None:
            freeqty = freeqtys[pc]
        else:
            freeqty = 0.00
        prod = con.execute(
            select(
                [
                    product.c.productdesc,
                    product.c.uomid,
                    product.c.gsflag,
                    product.c.gscode,
                ]
            ).where(product.c.productcode == pc)
        )
        prodrow = prod.fetchone()
        if int(prodrow["gsflag"]) == 7:
            um = con.execute(
                select([unitofmeasurement.c.unitname]).where(
                    unitofmeasurement.c.uomid == int(prodrow["uomid"])
                )
            )
            unitrow = um.fetchone()
            unitofMeasurement = unitrow["unitname"]
            taxableAmount = (
                (float(contentsData[pc][list(contentsData[pc].keys())[0]]))
                * float(list(contentsData[pc].keys())[0])
            ) - float(discount)
        else:
            unitofMeasurement = ""
            taxableAmount = float(list(contentsData[pc].keys())[0]) - float(
                discount
            )

        taxRate = 0.00
        totalAmount = 0.00
        taxRate = float(invrow["tax"][pc])
        if int(invrow["taxflag"]) == 22:
            taxRate = float(invrow["tax"][pc])
            taxAmount = taxableAmount * float(taxRate / 100)
            taxname = "VAT"
            totalAmount = float(taxableAmount) + (
                float(taxableAmount) * float(taxRate / 100)
            )
            totalDisc = totalDisc + float(discount)
            totalTaxableVal = totalTaxableVal + taxableAmount
            totalTaxAmt = totalTaxAmt + taxAmount
            invContents[pc] = {
                "proddesc": prodrow["productdesc"],
                "gscode": prodrow["gscode"],
                "uom": unitofMeasurement,
                "qty": "%.2f"
                % (float(contentsData[pc][list(contentsData[pc].keys())[0]])),
                "freeqty": "%.2f" % (float(freeqty)),
                "priceperunit": "%.2f" % (float(list(contentsData[pc].keys())[0])),
                "discount": "%.2f" % (float(discounts[pc])),
                "taxableamount": "%.2f" % (float(taxableAmount)),
                "totalAmount": "%.2f" % (float(totalAmount)),
                "taxname": "VAT",
                "taxrate": "%.2f" % (float(taxRate)),
                "taxamount": "%.2f" % (float(taxAmount)),
            }

        else:
            cessRate = 0.00
            cessAmount = 0.00
            cessVal = 0.00
            taxname = ""
            if invrow["cess"]:
                cessVal = float(invrow["cess"][pc])
                cessAmount = taxableAmount * (cessVal / 100)
                totalCessAmt = totalCessAmt + cessAmount

            if invrow["sourcestate"] != invrow["taxstate"]:
                taxname = "IGST"
                taxAmount = taxableAmount * (taxRate / 100)
                totalAmount = taxableAmount + taxAmount + cessAmount
            else:
                taxname = "SGST"
                taxRate = taxRate / 2
                taxAmount = taxableAmount * (taxRate / 100)
                totalAmount = (
                    taxableAmount
                    + (taxableAmount * ((taxRate * 2) / 100))
                    + cessAmount
                )

            totalDisc = totalDisc + float(discount)
            totalTaxableVal = totalTaxableVal + taxableAmount
            totalTaxAmt = totalTaxAmt + taxAmount

            invContents[pc] = {
                "proddesc": prodrow["productdesc"],
                "gscode": prodrow["gscode"],
                "gsflag": prodrow["gsflag"],
                "uom": unitofMeasurement,
                "qty": "%.2f"
                % (float(contentsData[pc][list(contentsData[pc].keys())[0]])),
                "freeqty": "%.2f" % (float(freeqty)),
                "priceperunit": "%.2f" % (float(list(contentsData[pc].keys())[0])),
                "discount": "%.2f" % (float(discounts[pc])),
                "taxableamount": "%.2f" % (float(taxableAmount)),
                "totalAmount": "%.2f" % (float(totalAmount)),
                "taxname": taxname,
                "taxrate": "%.2f" % (float(taxRate)),
                "taxamount": "%.2f" % (float(taxAmount)),
                "cess": "%.2f" % (float(cessAmount)),
                "cessrate": "%.2f" % (float(cessVal)),
            }
    # below code is to check if invoicetotal is greater than ammount paid from invoice table. If invoicetotal is greater amountpaid it set billentrysingleflag to 0 else to 1 to create voucher for the same.
    billwiseentry = con.execute(
        "select invoicetotal, amountpaid from invoice where invid=%d and orgcode=%d"
        % (int(params["invid"]), orgcode)
    )
    billwise_entry = billwiseentry.fetchone()
    if billwise_entry["invoicetotal"] > billwise_entry["amountpaid"]:
        inv["billentrysingleflag"] = 0
    else:
        inv["billentrysingleflag"] = 1

    inv["totaldiscount"] = "%.2f" % (float(totalDisc))
    inv["totaltaxablevalue"] = "%.2f" % (float(totalTaxableVal))
    inv["totaltaxamt"] = "%.2f" % (float(totalTaxAmt))
    inv["totalcessamt"] = "%.2f" % (float(totalCessAmt))
    inv["taxname"] = taxname
    inv["invcontents"] = invContents
    voucherCount = con.execute(
        "select count(vouchercode) from vouchers where orgcode = %d and invid = %d"
        % (int(orgcode), int(params["invid"]))
    )
    vCount = voucherCount.fetchone()
    inv["vouchercount"] = vCount[0]
    immutable_data = con.execute(
        select([transaction.c.transaction_details])
        .where(transaction.c.transaction_id == invrow["immutable_data_id"])
    ).scalar()
    inv["immutable_data"] = immutable_data
    return inv

def getInvoiceList(con, orgcode, reqParams):
    invoices = []
    # flag 0=all, 1=sales, 2=purchase, others are invalid
    if (int(reqParams["flag"]) not in [0, 1, 2]):
        return invoices

    query = select([invoice]).where(and_(
        invoice.c.orgcode == orgcode,
        invoice.c.icflag == 9,
        invoice.c.invoicedate <= reqParams["todate"],
        invoice.c.invoicedate >= reqParams["fromdate"],
    ))

    if "orderflag" in reqParams:
        query = query.order_by(desc(invoice.c.invoicedate))
    else:
        query = query.order_by(invoice.c.invoicedate)

    result = con.execute(query)
    srno = 1
    # for each invoice
    for row in result:
        # when flag is 1, inoutflag should be 15 to return only sales invoices
        if reqParams["flag"] == "1" and row["inoutflag"] != 15:
            continue

        # when flag is 2, inoutflag should be 9 to return only purchase invoices
        if reqParams["flag"] == "2" and row["inoutflag"] != 9:
            continue

        if row["sourcestate"]:
            sourceStateCode = getStateCode(row["sourcestate"], con)["statecode"]
        if row["taxstate"]:
            destinationStateCode = getStateCode(row["taxstate"], con)["statecode"]
        dcno = ""
        dcdate = ""
        godowns = ""
        dcresult = con.execute(
            select([dcinv.c.dcid]).where(
                and_(
                    dcinv.c.orgcode == orgcode,
                    dcinv.c.invid == row["invid"],
                )
            )
        )
        dcresult = dcresult.fetchall()
        # Assuming there are multiple delivery challans for a single invoice.
        i = 1
        # fetch all delivery challans for an invoice.
        for dc in dcresult:
            if not dc["dcid"]:
                continue
            godownres = con.execute(
                "select goname, goaddr from godown where goid = (select distinct goid from stock where dcinvtnflag=4 and dcinvtnid=%d)"
                % int(dc["dcid"])
            )
            godownresult = godownres.fetchone()
            if godownresult != None:
                godownname = godownresult["goname"]
                godownaddrs = godownresult["goaddr"]
                godowns = godowns + godownname + "(" + godownaddrs + ")"
            else:
                godownname = ""
                godownaddrs = ""
                godowns = ""
            delchalres = con.execute(
                select([delchal.c.dcno, delchal.c.dcdate]).where(
                    and_(
                        delchal.c.orgcode == orgcode,
                        delchal.c.dcid == dc["dcid"],
                    )
                )
            )
            delchalres = delchalres.fetchone()
            if i == len(dcresult):
                dcno = dcno + delchalres["dcno"]
                dcdate = dcdate + str(
                    datetime.strftime(delchalres["dcdate"], "%d-%m-%Y")
                )

            else:
                dcno = dcno + delchalres["dcno"] + ", "
                dcdate = (
                    dcdate
                    + str(datetime.strftime(delchalres["dcdate"], "%d-%m-%Y"))
                    + ", "
                )

            i += 1
        taxamt = 0.00
        # calculate tax amount of an invoice.
        for productservice in row["contents"].keys():
            try:
                taxrate = "%.2f" % float(row["tax"][productservice])
                cessrate = 0.00
                if productservice in row["cess"]:
                    cessrate = "%.2f" % float(row["cess"][productservice])
                discount = 0.00
                # Fetching GSFlag of product.
                psdetails = con.execute(
                    select([product.c.gsflag]).where(
                        product.c.productcode == productservice
                    )
                )
                gsflag = psdetails.fetchone()["gsflag"]
                # Fetching discount and price for each product.
                # Taxabe amount is also found out considering whether the item is a product/service
                for productprice in row["contents"][productservice].keys():
                    ppu = productprice
                    if productservice in row["discount"]:
                        # discflag is for discount type. Percent=16/Amount=1
                        # here we convert percent discount in to amount.
                        if row["discflag"] == 16:
                            qty = float(
                                list(row["contents"][str(productservice)].keys())[0]
                            )
                            price = float(
                                list(row["contents"][str(productservice)].values())[
                                    0
                                ]
                            )
                            totalWithoutDiscount = qty * price
                            discount = totalWithoutDiscount * float(
                                float(row["discount"][productservice]) / 100
                            )
                        else:
                            discount = float(row["discount"][productservice])
                    qty = float(row["contents"][productservice][productprice])
                    # Calculating taxable amount(variable taxablevalue)
                    if int(gsflag) == 7:
                        taxablevalue = (
                            float("%.2f" % float(ppu)) * float("%.2f" % float(qty))
                        ) - float("%.2f" % float(discount))
                    else:
                        taxablevalue = float("%.2f" % float(ppu)) - float(
                            "%.2f" % float(discount)
                        )
                    # Calculating tax amount.
                    taxamt = (
                        taxamt
                        + float(
                            "%.2f" % ((taxablevalue * float(taxrate)) / float(100))
                        )
                        + float(
                            "%.2f" % ((taxablevalue * float(cessrate)) / float(100))
                        )
                    )
            except:
                pass
        netamt = float(row["invoicetotal"]) - taxamt
        cresult = con.execute(
            select(
                [
                    customerandsupplier.c.custname,
                    customerandsupplier.c.csflag,
                    customerandsupplier.c.custtan,
                    customerandsupplier.c.gstin,
                ]
            ).where(customerandsupplier.c.custid == row["custid"])
        )
        customerdetails = cresult.fetchone()
        # TIN/GSTIN of customer/supplier is found out.
        if int(row["taxflag"]) == 7:
            if int(customerdetails["csflag"]) == 3:
                try:
                    if destinationStateCode not in customerdetails["gstin"]:
                        if (
                            "0" + str(destinationStateCode)
                            in customerdetails["gstin"]
                        ):
                            destinationStateCode = "0" + str(destinationStateCode)
                    custtin = customerdetails["gstin"][str(destinationStateCode)]
                except:
                    custtin = None
            else:
                try:
                    if sourceStateCode not in customerdetails["gstin"]:
                        if "0" + str(sourceStateCode) in customerdetails["gstin"]:
                            sourceStateCode = "0" + str(sourceStateCode)
                    custtin = customerdetails["gstin"][str(sourceStateCode)]
                except:
                    custtin = None
        else:
            try:
                custtin = customerdetails["custtan"]
            except:
                custtin = None

        # below code is to check if invoicetotal is greater than ammount paid from invoice table. If invoicetotal is greater amountpaid it set billentryflag to 0 else to 1 to create voucher for the same.
        billentryflag = 1
        billwiseentry = con.execute(
            "select 1 from invoice where invid=%d and orgcode=%d and invoicetotal > amountpaid "
            % (row["invid"], orgcode)
        )
        billwise_entry = billwiseentry.rowcount
        if billwiseentry != None and billwise_entry > 0:
            billentryflag = 0

        # below code is to check invid is present in dcinv table or drcr table. If invid present it set cancleflag 1 else 0 to cancel the invoice from list of invoice.
        cancelinv = 1
        exist_drcr = con.execute(
            "select count(invid) as invcount from drcr where invid=%d and orgcode=%d"
            % (row["invid"], orgcode)
        )
        existDrcr = exist_drcr.fetchone()
        if existDrcr["invcount"] > 0:
            cancelinv = 0

        immutable_data = con.execute(
            select([transaction.c.transaction_details])
            .where(transaction.c.transaction_id == row["immutable_data_id"])
        ).scalar()

        invoices.append({
            "srno": srno,
            "invoiceno": row["invoiceno"],
            "invid": row["invid"],
            "dcno": dcno,
            "dcdate": dcdate,
            "netamt": "%.2f" % netamt,
            "taxamt": "%.2f" % taxamt,
            "godown": godowns,
            "custname": customerdetails["custname"],
            "csflag": customerdetails["csflag"],
            "custtin": custtin,
            "invoicedate": datetime.strftime(
                row["invoicedate"], "%d-%m-%Y"
            ),
            "grossamt": "%.2f" % float(row["invoicetotal"]),
            "cancelflag": cancelinv,
            "billentryflag": billentryflag,
            "inoutflag": row["inoutflag"],
            "immutable_data": immutable_data,
        })
        srno += 1
    return invoices

"""
Updates the Duplicate invoice numbers to be unique by prefixing them with a counter, i.e. counter-inv_no
"""


def rename_inv_no_uniquely(con, orgcode):
    try:
        invoice_list = con.execute(
            select([invoice.c.invid, invoice.c.invoiceno]).where(
                invoice.c.orgcode == orgcode
            )
        ).fetchall()
        if len(invoice_list) > 1:
            invoice_map = {}
            for inv in invoice_list:
                no = inv["invoiceno"]
                if no in invoice_map:
                    invoice_map[no] += 1
                    new_no = str(invoice_map[no]) + "-" + str(no)
                    con.execute(
                        invoice.update()
                        .where(invoice.c.invid == inv["invid"])
                        .values(invoiceno=new_no)
                    )
                else:
                    invoice_map[no] = 0
        return 1
    except:
        print(traceback.format_exc())
        return 0


@view_defaults(route_name="invoice")
class api_invoice(object):
    def __init__(self, request):
        self.request = request

    @view_config(request_method="POST", renderer="json")
    def addInvoice(self):
        try:
            token = self.request.headers["gktoken"]
        except:
            return {"gkstatus": gkcore.enumdict["UnauthorisedAccess"]}
        authDetails = authCheck(token)
        if authDetails["auth"] == False:
            return {"gkstatus": enumdict["UnauthorisedAccess"]}
        else:
            with eng.begin() as con:
                dtset = self.request.json_body
                invdataset = dtset["payload"]["invoice"]
                result_count = con.execute(
                    select([invoice.c.invoiceno]).where(
                        and_(
                            invoice.c.orgcode == authDetails["orgcode"],
                            func.lower(invoice.c.invoiceno) == func.lower(invdataset["invoiceno"]),
                        )
                    )
                ).rowcount
                result_count += con.execute(
                    select([invoicebin.c.invoiceno]).where(
                        and_(
                            invoicebin.c.orgcode == authDetails["orgcode"],
                            func.lower(invoicebin.c.invoiceno) == func.lower(invdataset["invoiceno"]),
                        )
                    )
                ).rowcount

                if result_count > 0:
                    # Duplicate entry found, handle accordingly
                    return {"gkstatus": enumdict["DuplicateEntry"]}

                delivery_note_id = create_delivery_note(
                    con,
                    dtset,
                    authDetails["orgcode"],
                )

                dcinvdataset = {}
                freeqty = invdataset["freeqty"]
                discount = invdataset["discount"]
                stockdataset = dtset["payload"]["stock"]
                items = invdataset["contents"]
                invdataset["orgcode"] = authDetails["orgcode"]
                stockdataset["orgcode"] = authDetails["orgcode"]
                invdataset["dcid"] = delivery_note_id
                queryParams = {}
                voucherData = {}
                pricedetails = []
                payment_vouchers = invdataset["payment_vouchers"]
                total_paid = 0.00
                if payment_vouchers.get("crs"):
                    total_paid = sum(
                       [float(row) for row in payment_vouchers["crs"].values()]
                    )

                if total_paid != float(invdataset["invoicetotal"]):
                    invdataset["paymentmode"] = 15

                # Check for duplicate entry before insertion

                if "pricedetails" in invdataset:
                    pricedetails = invdataset["pricedetails"]
                    invdataset.pop("pricedetails", pricedetails)
                godown_id = dtset["delchalPayload"]["stockdata"]["goid"]
                godown_details = con.execute(
                    select([godown])
                    .where(godown.c.goid==godown_id)
                ).fetchone()
                contact_id = invdataset["custid"]
                contact_details = con.execute(
                    select([customerandsupplier])
                    .where(customerandsupplier.c.custid == contact_id)
                ).fetchone()
                product_id_values = list(items.keys())
                products = con.execute(
                    select([product.c.productcode, product.c.productdesc, product.c.gscode])
                    .where(product.c.productcode.in_(product_id_values))
                ).fetchall()
                product_details = {
                    id: {
                        "productcode": id,
                        "productdesc": name,
                        "gscode": hsn,
                    }
                    for id, name, hsn in products
                }
                org_details = get_organisation_profile(authDetails["orgcode"])
                transaction_details = {
                    "godown": dict(godown_details),
                    "contact": dict(contact_details),
                    "products": product_details,
                    "organisation": org_details,
                }
                transaction_id = con.execute(
                    transaction.insert()
                    .values(transaction_details=transaction_details)
                ).inserted_primary_key
                invdataset["immutable_data_id"] = transaction_id[0]
                result = con.execute(invoice.insert(), [invdataset])
                if len(pricedetails) > 0:
                    for price in pricedetails:
                        price["orgcode"] = authDetails["orgcode"]
                        cslastpriceResult = con.execute(select([cslastprice]).where(
                            and_(
                                cslastprice.c.orgcode == price["orgcode"],
                                cslastprice.c.custid == price["custid"],
                                cslastprice.c.productcode == price["productcode"],
                                cslastprice.c.inoutflag == price["inoutflag"],
                            )
                        ))
                        if (cslastpriceResult.fetchone()):
                            con.execute(
                                cslastprice.update()
                                .where(
                                    and_(
                                        cslastprice.c.custid == price["custid"],
                                        cslastprice.c.productcode
                                        == price["productcode"],
                                        cslastprice.c.inoutflag == price["inoutflag"],
                                        cslastprice.c.orgcode == price["orgcode"],
                                    )
                                ).values(price)
                            )
                        else:
                            con.execute(cslastprice.insert(), [price])
                # when delivery note is selected
                if "dcid" in invdataset:
                    if result.rowcount == 1:
                        icflag = (
                            int(invdataset["icflag"]) if "icflag" in invdataset else 9
                        )
                        result = con.execute(
                            text("select max(invid) as invid from invoice where custid = :custid and invoiceno = :invoiceno and orgcode = :orgcode and icflag = :icflag"),
                            custid = invdataset["custid"],
                            invoiceno = invdataset["invoiceno"],
                            orgcode = invdataset["orgcode"],
                            icflag = icflag,
                        )
                        invoiceid = result.fetchone()
                        dcinvdataset["dcid"] = invdataset["dcid"]
                        dcinvdataset["invid"] = invoiceid["invid"]
                        dcinvdataset["orgcode"] = invdataset["orgcode"]
                        dcinvdataset["invprods"] = stockdataset["items"]
                        result = con.execute(dcinv.insert(), [dcinvdataset])
                        if result.rowcount != 1:
                            return {"gkstatus": gkcore.enumdict["ConnectionFailed"]}

                        # check automatic voucher flag if it is 1 get maflag
                        avfl = con.execute(
                            select([organisation.c.avflag]).where(
                                organisation.c.orgcode == invdataset["orgcode"]
                            )
                        )
                        av = avfl.fetchone()
                        if av["avflag"] == 1:
                            avData = invdataset["av"]
                            mafl = con.execute(
                                select([organisation.c.maflag]).where(
                                    organisation.c.orgcode == invdataset["orgcode"]
                                )
                            )
                            maFlag = mafl.fetchone()
                            csName = con.execute(
                                select([customerandsupplier.c.custname]).where(
                                    and_(
                                        customerandsupplier.c.orgcode
                                        == invdataset["orgcode"],
                                        customerandsupplier.c.custid
                                        == int(invdataset["custid"]),
                                    )
                                )
                            )
                            CSname = csName.fetchone()
                            queryParams = {
                                "invtype": invdataset["inoutflag"],
                                "icflag": invdataset["icflag"],
                                "taxType": invdataset["taxflag"],
                                "destinationstate": invdataset["taxstate"],
                                "totaltaxablevalue": avData["totaltaxable"],
                                "maflag": maFlag["maflag"],
                                "totalAmount": (invdataset["invoicetotal"]),
                                "invoicedate": invdataset["invoicedate"],
                                "invid": invoiceid["invid"],
                                "invoiceno": invdataset["invoiceno"],
                                "csname": CSname["custname"],
                                "taxes": invdataset["tax"],
                                "cess": invdataset["cess"],
                                "products": avData["product"],
                                "prodData": avData["prodData"],
                                "payment_vouchers": payment_vouchers,
                                "total_paid": total_paid,
                            }
                            # when invoice total is rounded off
                            if invdataset["roundoffflag"] == 1:
                                roundOffAmount = float(
                                    invdataset["invoicetotal"]
                                ) - round(float(invdataset["invoicetotal"]))
                                if float(roundOffAmount) != 0.00:
                                    queryParams["roundoffamt"] = float(
                                        roundOffAmount
                                    )

                            if int(invdataset["taxflag"]) == 7:
                                queryParams["gstname"] = avData["avtax"]["GSTName"]
                                queryParams["cessname"] = avData["avtax"][
                                    "CESSName"
                                ]

                            if int(invdataset["taxflag"]) == 22:
                                queryParams["taxpayment"] = avData["taxpayment"]

                            # call getDefaultAcc
                            av_Result = getDefaultAcc(
                                con, queryParams, int(invdataset["orgcode"])
                            )
                            if av_Result["gkstatus"] == 0:
                                voucherData["status"] = 0
                                voucherData["vchno"] = av_Result["vchNo"]
                                voucherData["vchid"] = av_Result["vid"]
                            else:
                                voucherData["status"] = 1
                        return {
                            "gkstatus": enumdict["Success"],
                            "gkresult": invoiceid["invid"],
                            "vchData": voucherData,
                        }
                else:
                    # if it is cash memo
                    if "icflag" in invdataset:
                        result = con.execute(
                            text("select max(invid) as invid from invoice where invoiceno = :invoiceno and orgcode = :orgcode and icflag = 3"),
                            invoiceno = invdataset["invoiceno"],
                            orgcode = invdataset["orgcode"],
                        )
                        invoiceid = result.fetchone()
                        stockdataset["dcinvtnid"] = invoiceid["invid"]
                        for item in list(items.keys()):
                            gstResult = gst(item, con)
                            if int(gstResult["gsflag"]) == 7:
                                itemQty = float(list(items[item].values())[0])
                                itemRate = float(list(items[item].keys())[0])
                                itemTotalDiscount = float(discount.get(item, 0))
                                itemDiscount = 0
                                if itemQty:
                                    itemDiscount = itemTotalDiscount / itemQty
                                stockdataset["rate"] = itemRate - itemDiscount
                                stockdataset["productcode"] = item
                                stockdataset["qty"] = itemQty + float(freeqty[item])
                                stockdataset["dcinvtnflag"] = "3"
                                stockdataset["stockdate"] = invdataset[
                                    "invoicedate"
                                ]
                                result = con.execute(
                                    stock.insert(), [stockdataset]
                                )

                        # check automatic voucher flag if it is 1 get maflag
                        avfl = con.execute(
                            select([organisation.c.avflag]).where(
                                organisation.c.orgcode == invdataset["orgcode"]
                            )
                        )
                        av = avfl.fetchone()
                        if av["avflag"] == 1:
                            avData = invdataset["av"]
                            mafl = con.execute(
                                select([organisation.c.maflag]).where(
                                    organisation.c.orgcode == invdataset["orgcode"]
                                )
                            )
                            maFlag = mafl.fetchone()
                            queryParams = {
                                "invtype": invdataset["inoutflag"],
                                "icflag": invdataset["icflaginoutflag"],
                                "taxType": invdataset["taxflag"],
                                "destinationstate": invdataset["taxstate"],
                                "totaltaxablevalue": avData["totaltaxable"],
                                "maflag": maFlag["maflag"],
                                "totalAmount": invdataset["invoicetotal"],
                                "invoicedate": invdataset["invoicedate"],
                                "invid": invoiceid["invid"],
                                "invoiceno": invdataset["invoiceno"],
                                "taxes": invdataset["tax"],
                                "cess": invdataset["cess"],
                                "products": avData["product"],
                                "prodData": avData["prodData"],
                                "payment_vouchers": payment_vouchers,
                                "total_paid": total_paid,
                            }
                            # when invoice total rounded off
                            if int(invdataset["roundoffflag"]) == 1:
                                roundOffAmount = float(
                                    invdataset["invoicetotal"]
                                ) - round(float(invdataset["invoicetotal"]))
                                if float(roundOffAmount) != 0.00:
                                    queryParams["roundoffamt"] = float(
                                        roundOffAmount
                                    )

                            if int(invdataset["taxflag"]) == 7:
                                queryParams["gstname"] = avData["avtax"]["GSTName"]
                                queryParams["cessname"] = avData["avtax"][
                                    "CESSName"
                                ]
                            if int(invdataset["taxflag"]) == 22:
                                queryParams["taxpayment"] = avData["taxpayment"]
                            # call getDefaultAcc
                            av_Result = getDefaultAcc(
                                con, queryParams, int(invdataset["orgcode"])
                            )
                            if av_Result["gkstatus"] == 0:
                                voucherData["status"] = 0
                                voucherData["vchno"] = av_Result["vchNo"]
                                voucherData["vchid"] = av_Result["vid"]
                            else:
                                voucherData["status"] = 1
                        return {
                            "gkstatus": enumdict["Success"],
                            "gkresult": invoiceid["invid"],
                            "vchData": voucherData,
                        }
                    else:
                        result = con.execute(
                            text("select max(invid) as invid from invoice where custid = :custid and invoiceno = :invoiceno and orgcode = :orgcode and icflag = 9"),
                            custid = invdataset["custid"],
                            invoiceno = invdataset["invoiceno"],
                            orgcode = invdataset["orgcode"],
                        )
                        invoiceid = result.fetchone()
                        stockdataset["dcinvtnid"] = invoiceid["invid"]
                        stockdataset["stockdate"] = invdataset["invoicedate"]
                        for item in list(items.keys()):
                            gstResult = gst(item, con)
                            if int(gstResult["gsflag"]) == 7:
                                itemQty = float(list(items[item].values())[0])
                                itemRate = float(list(items[item].keys())[0])
                                itemTotalDiscount = float(discount.get(item, 0))
                                itemDiscount = 0
                                if itemQty:
                                    itemDiscount = itemTotalDiscount / itemQty
                                stockdataset["rate"] = itemRate - itemDiscount
                                stockdataset["productcode"] = item
                                stockdataset["qty"] = itemQty + float(freeqty[item])
                                stockdataset["dcinvtnflag"] = "9"
                                result = con.execute(
                                    stock.insert(), [stockdataset]
                                )
                            # check automatic voucher flag if it is 1 get maflag
                        avfl = con.execute(
                            select([organisation.c.avflag]).where(
                                organisation.c.orgcode == invdataset["orgcode"]
                            )
                        )
                        av = avfl.fetchone()
                        if av["avflag"] == 1:
                            avData = invdataset["av"]
                            mafl = con.execute(
                                select([organisation.c.maflag]).where(
                                    organisation.c.orgcode == invdataset["orgcode"]
                                )
                            )
                            maFlag = mafl.fetchone()
                            csName = con.execute(
                                select([customerandsupplier.c.custname]).where(
                                    and_(
                                        customerandsupplier.c.orgcode
                                        == invdataset["orgcode"],
                                        customerandsupplier.c.custid
                                        == int(invdataset["custid"]),
                                    )
                                )
                            )
                            CSname = csName.fetchone()
                            queryParams = {
                                "invtype": invdataset["inoutflag"],
                                "icflag": invdataset["icflaginoutflag"],
                                "taxType": invdataset["taxflag"],
                                "destinationstate": invdataset["taxstate"],
                                "totaltaxablevalue": avData["totaltaxable"],
                                "maflag": maFlag["maflag"],
                                "totalAmount": invdataset["invoicetotal"],
                                "invoicedate": invdataset["invoicedate"],
                                "invid": invoiceid["invid"],
                                "invoiceno": invdataset["invoiceno"],
                                "csname": CSname["custname"],
                                "taxes": invdataset["tax"],
                                "cess": invdataset["cess"],
                                "products": avData["product"],
                                "prodData": avData["prodData"],
                                "payment_vouchers": payment_vouchers,
                                "total_paid": total_paid,
                            }
                            # when invoice total rounded off
                            if invdataset["roundoffflag"] == 1:
                                roundOffAmount = float(
                                    invdataset["invoicetotal"]
                                ) - round(float(invdataset["invoicetotal"]))
                                if float(roundOffAmount) != float(0):
                                    queryParams["roundoffamt"] = float(
                                        roundOffAmount
                                    )

                            if int(invdataset["taxflag"]) == 7:
                                queryParams["gstname"] = avData["avtax"]["GSTName"]
                                queryParams["cessname"] = avData["avtax"][
                                    "CESSName"
                                ]
                            if int(invdataset["taxflag"]) == 22:
                                queryParams["taxpayment"] = avData["taxpayment"]
                            # call getDefaultAcc
                            av_Result = getDefaultAcc(
                                con, queryParams, int(invdataset["orgcode"])
                            )
                            if av_Result["gkstatus"] == 0:
                                voucherData["status"] = 0
                                voucherData["vchno"] = av_Result["vchNo"]
                                voucherData["vchid"] = av_Result["vid"]
                            else:
                                voucherData["status"] = 1
                        return {
                            "gkstatus": enumdict["Success"],
                            "gkresult": invoiceid["invid"],
                            "vchData": voucherData,
                        }

    @view_config(request_method="GET", request_param="inv=all", renderer="json")
    def getAllinvoices(self):
        try:
            token = self.request.headers["gktoken"]
        except:
            return {"gkstatus": gkcore.enumdict["UnauthorisedAccess"]}
        authDetails = authCheck(token)
        if authDetails["auth"] == False:
            return {"gkstatus": gkcore.enumdict["UnauthorisedAccess"]}
        else:
            try:
                self.con = eng.connect()
                result = self.con.execute(
                    select(
                        [
                            invoice.c.invoiceno,
                            invoice.c.inoutflag,
                            invoice.c.invid,
                            invoice.c.invoicedate,
                            invoice.c.custid,
                            invoice.c.invoicetotal,
                            invoice.c.attachmentcount,
                        ]
                    )
                    .where(
                        and_(
                            invoice.c.orgcode == authDetails["orgcode"],
                            invoice.c.icflag == 9,
                        )
                    )
                    .order_by(invoice.c.invoicedate)
                )
                invoices = []
                for row in result:
                    customer = self.con.execute(
                        select(
                            [
                                customerandsupplier.c.custname,
                                customerandsupplier.c.csflag,
                            ]
                        ).where(customerandsupplier.c.custid == row["custid"])
                    )
                    custname = customer.fetchone()
                    if "type" in self.request.params:
                        if (
                            str(self.request.params["type"]) == "sale"
                            and int(row["inoutflag"]) == 15
                        ):
                            invoices.append(
                                {
                                    "invoiceno": row["invoiceno"],
                                    "invid": row["invid"],
                                    "custname": custname["custname"],
                                    "csflag": custname["csflag"],
                                    "invoicedate": datetime.strftime(
                                        row["invoicedate"], "%d-%m-%Y"
                                    ),
                                    "invoicetotal": "%.2f" % float(row["invoicetotal"]),
                                    "attachmentcount": row["attachmentcount"],
                                }
                            )
                        elif (
                            str(self.request.params["type"]) == "purchase"
                            and int(row["inoutflag"]) == 15
                        ):
                            invoices.append(
                                {
                                    "invoiceno": row["invoiceno"],
                                    "invid": row["invid"],
                                    "custname": custname["custname"],
                                    "csflag": custname["csflag"],
                                    "invoicedate": datetime.strftime(
                                        row["invoicedate"], "%d-%m-%Y"
                                    ),
                                    "invoicetotal": "%.2f" % float(row["invoicetotal"]),
                                    "attachmentcount": row["attachmentcount"],
                                }
                            )
                    else:
                        invoices.append(
                            {
                                "invoiceno": row["invoiceno"],
                                "invid": row["invid"],
                                "custname": custname["custname"],
                                "csflag": custname["csflag"],
                                "invoicedate": datetime.strftime(
                                    row["invoicedate"], "%d-%m-%Y"
                                ),
                                "invoicetotal": "%.2f" % float(row["invoicetotal"]),
                                "attachmentcount": row["attachmentcount"],
                            }
                        )
                return {"gkstatus": gkcore.enumdict["Success"], "gkresult": invoices}

            except:
                return {"gkstatus": gkcore.enumdict["ConnectionFailed"]}
            finally:
                self.con.close()

    @view_config(request_method="GET", request_param="inv=alldeleted", renderer="json")
    def getAllcanceledinvoices(self):
        try:
            token = self.request.headers["gktoken"]
        except:
            return {"gkstatus": gkcore.enumdict["UnauthorisedAccess"]}
        authDetails = authCheck(token)
        if authDetails["auth"] == False:
            return {"gkstatus": gkcore.enumdict["UnauthorisedAccess"]}
        else:
            try:
                self.con = eng.connect()
                result = self.con.execute(
                    select(
                        [
                            invoicebin.c.invoiceno,
                            invoicebin.c.inoutflag,
                            invoicebin.c.invid,
                            invoicebin.c.invoicedate,
                            invoicebin.c.custid,
                            invoicebin.c.invoicetotal,
                            invoicebin.c.attachmentcount,
                        ]
                    )
                    .where(
                        and_(
                            invoicebin.c.orgcode == authDetails["orgcode"],
                            invoicebin.c.icflag == 9,
                        )
                    )
                    .order_by(invoicebin.c.invoicedate)
                )
                invoices = []
                for row in result:
                    customer = self.con.execute(
                        select(
                            [
                                customerandsupplier.c.custname,
                                customerandsupplier.c.csflag,
                            ]
                        ).where(customerandsupplier.c.custid == row["custid"])
                    )
                    custname = customer.fetchone()
                    if "type" in self.request.params:
                        if (
                            str(self.request.params["type"]) == "sale"
                            and int(row["inoutflag"]) == 15
                        ):
                            invoices.append(
                                {
                                    "invoiceno": row["invoiceno"],
                                    "invid": row["invid"],
                                    "custname": custname["custname"],
                                    "csflag": custname["csflag"],
                                    "invoicedate": datetime.strftime(
                                        row["invoicedate"], "%d-%m-%Y"
                                    ),
                                    "invoicetotal": "%.2f" % float(row["invoicetotal"]),
                                    "attachmentcount": row["attachmentcount"],
                                }
                            )
                        elif (
                            str(self.request.params["type"]) == "purchase"
                            and int(row["inoutflag"]) == 9
                        ):
                            invoices.append(
                                {
                                    "invoiceno": row["invoiceno"],
                                    "invid": row["invid"],
                                    "custname": custname["custname"],
                                    "csflag": custname["csflag"],
                                    "invoicedate": datetime.strftime(
                                        row["invoicedate"], "%d-%m-%Y"
                                    ),
                                    "invoicetotal": "%.2f" % float(row["invoicetotal"]),
                                    "attachmentcount": row["attachmentcount"],
                                }
                            )
                    else:
                        invoices.append(
                            {
                                "invoiceno": row["invoiceno"],
                                "invid": row["invid"],
                                "custname": custname["custname"],
                                "csflag": custname["csflag"],
                                "invoicedate": datetime.strftime(
                                    row["invoicedate"], "%d-%m-%Y"
                                ),
                                "invoicetotal": "%.2f" % float(row["invoicetotal"]),
                                "attachmentcount": row["attachmentcount"],
                            }
                        )
                return {"gkstatus": gkcore.enumdict["Success"], "gkresult": invoices}

            except:
                return {"gkstatus": gkcore.enumdict["ConnectionFailed"]}
            finally:
                self.con.close()

    """
    This method gives all invoices which are not fully rejected yet.
    It is used in rejection note, to prepare rejection note against these invoices.
    """
    @view_config(
        route_name="invoice_nonrejected", request_method="GET", renderer="json"
    )
    def nonRejected(self):
        try:
            token = self.request.headers["gktoken"]
        except:
            return {"gkstatus": enumdict["UnauthorisedAccess"]}
        authDetails = authCheck(token)
        if authDetails["auth"] == False:
            return {"gkstatus": enumdict["UnauthorisedAccess"]}
        else:
            try:
                self.con = eng.connect()
                invResult = self.con.execute(
                    select(
                        [
                            invoice.c.invid,
                            invoice.c.inoutflag,
                            invoice.c.invoicedate,
                            invoice.c.contents,
                            invoice.c.invoiceno,
                            invoice.c.custid,
                            invoice.c.taxflag,
                            invoice.c.sourcestate,
                            invoice.c.taxstate,
                        ]
                    ).where(
                        and_(
                            invoice.c.orgcode == authDetails["orgcode"],
                            invoice.c.icflag == 9,
                        )
                    )
                )
                allinv = invResult.fetchall()
                allinvids = []
                for invrow in allinv:
                    # keep an empty dictionary for rejectable products.
                    rejContents = {}
                    rejectedResult = self.con.execute(
                        select([rejectionnote.c.rnid, rejectionnote.c.rejprods]).where(
                            and_(
                                rejectionnote.c.orgcode == authDetails["orgcode"],
                                rejectionnote.c.invid == invrow["invid"],
                            )
                        )
                    )
                    rejectedNotes = rejectedResult.fetchall()
                    gscounter = 0
                    for content in list(invrow["contents"].keys()):
                        qty = float(list(invrow["contents"][content].values())[0])
                        # for goods quantity will not be 0 anytime
                        if qty > 0:
                            gscounter = gscounter + 1
                            # check whether this product is rejected before.
                            # if there are no rejections then just add the quantity directly to the rejContents.
                            if rejectedResult.rowcount == 0:
                                rejContents[content] = qty
                            else:
                                # Now query each note to see if this product is partially or fully rejected.

                                for rejrow in rejectedNotes:
                                    rejdict = rejrow["rejprods"]
                                    if content in rejdict:
                                        qty = qty - float(
                                            list(rejrow["rejprods"][content].values())[
                                                0
                                            ]
                                        )
                                        if qty > 0:
                                            rejContents[content] = qty
                                        else:
                                            if content in rejContents:
                                                rejContents.pop(content)
                    if gscounter > 0 and len(rejContents) > 0:
                        custandsup = self.con.execute(
                            select(
                                [
                                    customerandsupplier.c.custname,
                                    customerandsupplier.c.state,
                                    customerandsupplier.c.custaddr,
                                    customerandsupplier.c.custtan,
                                    customerandsupplier.c.gstin,
                                    customerandsupplier.c.csflag,
                                ]
                            ).where(customerandsupplier.c.custid == invrow["custid"])
                        )
                        custData = custandsup.fetchone()
                        custSupDetails = {
                            "custname": custData["custname"],
                            "custaddr": custData["custaddr"],
                            "csflag": custData["csflag"],
                        }

                        if int(invrow["taxflag"]) == 22:
                            if custData["custtan"] != None:
                                custSupDetails["custtin"] = custData["custtan"]
                                custSupDetails["custstate"] = custData["state"]
                        else:
                            if invrow["sourcestate"] != None:
                                sourceStateCode = getStateCode(
                                    invrow["sourcestate"], self.con
                                )["statecode"]
                                custSupDetails["custstate"] = invrow["sourcestate"]
                            if invrow["taxstate"] != None:
                                taxStateCode = getStateCode(
                                    invrow["taxstate"], self.con
                                )["statecode"]
                                custSupDetails["custstate"] = invrow["taxstate"]
                            if custData["gstin"] != None:
                                if int(custData["csflag"]) == 3:
                                    try:
                                        custSupDetails["custgstin"] = custData["gstin"][
                                            str(taxStateCode)
                                        ]

                                    except:
                                        custSupDetails["custgstin"] = None
                                else:
                                    try:
                                        custSupDetails["custgstin"] = custData["gstin"][
                                            str(sourceStateCode)
                                        ]

                                    except:
                                        custSupDetails["custgstin"] = None
                        allinvids.append(
                            {
                                "invid": invrow["invid"],
                                "invoiceno": invrow["invoiceno"],
                                "inoutflag": invrow["inoutflag"],
                                "invoicedate": datetime.strftime(
                                    invrow["invoicedate"], "%d-%m-%Y"
                                ),
                                "rejcontent": rejContents,
                                "custsupdetail": custSupDetails,
                            }
                        )

                self.con.close()
                return {"gkstatus": enumdict["Success"], "gkresult": allinvids}
            except exc.IntegrityError:
                return {"gkstatus": enumdict["ActionDisallowed"]}
            except:
                return {"gkstatus": enumdict["ConnectionFailed"]}
            finally:
                self.con.close()

    """This method gives list of invoices. with all details of invoice.
    This method will be used to see report of list of invoices.
    Input parameters are: flag- 0=all invoices, 1=sales invoices, 2=purchase invoices
    fromdate and todate this is time period to see all invoices.
    orderflag is checked in request params for sorting date in descending order."""

    @view_config(
        route_name="invoice_list",
        request_method="GET",
        request_param="type=list",
        renderer="json",
    )
    def getListofInvoices(self):
        try:
            token = self.request.headers["gktoken"]
        except:
            return {"gkstatus": gkcore.enumdict["UnauthorisedAccess"]}
        authDetails = authCheck(token)
        if authDetails["auth"] == False:
            return {"gkstatus": gkcore.enumdict["UnauthorisedAccess"]}
        else:
            with eng.connect() as con:
                invoices = getInvoiceList(
                    con, authDetails["orgcode"], self.request.params
                )
                return {"gkstatus": gkcore.enumdict["Success"], "gkresult": invoices}

        """This function gives list of invoices. with all details of canceled invoice.
    This method will be used to see report of list of invoices.
    Input parameters are: flag- 0=all invoices, 1=sales invoices, 2=purchase invoices
    fromdate and todate this is time period to see all invoices.
    orderflag is checked in request params for sorting date in descending order."""

    @view_config(
        route_name="invoice_list",
        request_method="GET",
        request_param="type=listdeleted",
        renderer="json",
    )
    def getListofcancelledInvoices(self):
        try:
            token = self.request.headers["gktoken"]
        except:
            return {"gkstatus": gkcore.enumdict["UnauthorisedAccess"]}
        authDetails = authCheck(token)
        if authDetails["auth"] == False:
            return {"gkstatus": gkcore.enumdict["UnauthorisedAccess"]}
        else:
            with eng.connect() as con:
                # fetch all invoices
                query = select([invoicebin]).where(and_(
                    invoicebin.c.orgcode == authDetails["orgcode"],
                    invoicebin.c.icflag == 9,
                    invoicebin.c.invoicedate <= self.request.params["todate"],
                    invoicebin.c.invoicedate >= self.request.params["fromdate"],
                ))

                if "orderflag" in self.request.params:
                    query = query.order_by(desc(invoicebin.c.invoicedate))
                else:
                    query = query.order_by(invoicebin.c.invoicedate)

                result = con.execute(query)
                invoices = []
                srno = 1
                # for each invoice
                for row in result:
                    if row["sourcestate"] != None:
                        sourceStateCode = getStateCode(row["sourcestate"], con)[
                            "statecode"
                        ]
                    if row["taxstate"] != None:
                        destinationStateCode = getStateCode(row["taxstate"], con)[
                            "statecode"
                        ]
                    dcno = ""
                    dcdate = ""
                    godowns = ""
                    if row["dcinfo"] != None:
                        delinfo = row["dcinfo"]
                        dcno = delinfo["dcno"]
                        dcdate = delinfo["dcdate"]
                        if "goid" in delinfo:
                            godownres = con.execute(
                                "select goname, goaddr from godown where goid = %d"
                                % int(row["dcinfo"]["goid"])
                            )
                            godownresult = godownres.fetchone()
                            if godownresult != None:
                                godownname = godownresult["goname"]
                                godownaddrs = godownresult["goaddr"]
                                godowns = godowns + godownname + "(" + godownaddrs + ")"
                            else:
                                godownname = ""
                                godownaddrs = ""
                                godowns = ""
                    taxamt = 0.00
                    # calculate tax amount of an invoice.
                    for productservice in row["contents"].keys():
                        try:
                            taxrate = "%.2f" % float(row["tax"][productservice])
                            cessrate = 0.00
                            if productservice in row["cess"]:
                                cessrate = "%.2f" % float(row["cess"][productservice])
                            discount = 0.00
                            # Fetching GSFlag of product.
                            psdetails = con.execute(
                                select([product.c.gsflag]).where(
                                    product.c.productcode == productservice
                                )
                            )
                            gsflag = psdetails.fetchone()["gsflag"]
                            # Fetching discount and price for each product.
                            # Taxabe amount is also found out considering whether the item is a product/service
                            for productprice in row["contents"][productservice].keys():
                                ppu = productprice
                                if productservice in row["discount"]:
                                    # discflag is for discount type. Percent=16/Amount=1
                                    # here we convert percent discount in to amount.
                                    if row["discflag"] == 16:
                                        qty = float(
                                            list(
                                                row["contents"][
                                                    str(productservice)
                                                ].keys()
                                            )[0]
                                        )
                                        price = float(
                                            list(
                                                row["contents"][
                                                    str(productservice)
                                                ].values()
                                            )[0]
                                        )
                                        totalWithoutDiscount = qty * price
                                        discount = totalWithoutDiscount * float(
                                            float(row["discount"][productservice]) / 100
                                        )
                                    else:
                                        discount = float(
                                            row["discount"][productservice]
                                        )
                                qty = float(
                                    row["contents"][productservice][productprice]
                                )
                                # Calculating taxable amount(variable taxablevalue)
                                if int(gsflag) == 7:
                                    taxablevalue = (
                                        float("%.2f" % float(ppu))
                                        * float("%.2f" % float(qty))
                                    ) - float("%.2f" % float(discount))
                                else:
                                    taxablevalue = float("%.2f" % float(ppu)) - float(
                                        "%.2f" % float(discount)
                                    )
                                # Calculating tax amount.
                                taxamt = (
                                    taxamt
                                    + float(
                                        "%.2f"
                                        % ((taxablevalue * float(taxrate)) / float(100))
                                    )
                                    + float(
                                        "%.2f"
                                        % (
                                            (taxablevalue * float(cessrate))
                                            / float(100)
                                        )
                                    )
                                )
                        except:
                            pass
                    netamt = float(row["invoicetotal"]) - taxamt
                    cresult = con.execute(
                        select(
                            [
                                customerandsupplier.c.custname,
                                customerandsupplier.c.csflag,
                                customerandsupplier.c.custtan,
                                customerandsupplier.c.gstin,
                            ]
                        ).where(customerandsupplier.c.custid == row["custid"])
                    )
                    customerdetails = cresult.fetchone()
                    # TIN/GSTIN of customer/supplier is found out.
                    if int(row["taxflag"]) == 7:
                        if int(customerdetails["csflag"]) == 3:
                            try:
                                custtin = customerdetails["gstin"][
                                    str(destinationStateCode)
                                ]
                            except:
                                custtin = None
                        else:
                            try:
                                custtin = customerdetails["gstin"][str(sourceStateCode)]
                            except:
                                custtin = None
                    else:
                        try:
                            custtin = customerdetails["custtan"]
                        except:
                            custtin = None

                    # below code is to check invid is present in dcinv table or drcr table. If invid present it set cancleflag 1 else 0 to cancel the invoice from list of invoice.
                    cancelinv = 1
                    exist_drcr = con.execute(
                        "select count(invid) as invcount from drcr where invid=%d and orgcode=%d"
                        % (row["invid"], authDetails["orgcode"])
                    )
                    existDrcr = exist_drcr.fetchone()
                    if existDrcr["invcount"] > 0:
                        cancelinv = 0

                    # flag=0, all invoices.
                    if self.request.params["flag"] == "0":
                        invoices.append(
                            {
                                "srno": srno,
                                "invoiceno": row["invoiceno"],
                                "invid": row["invid"],
                                "dcno": dcno,
                                "godown": godowns,
                                "dcdate": dcdate,
                                "netamt": "%.2f" % netamt,
                                "taxamt": "%.2f" % taxamt,
                                "custname": customerdetails["custname"],
                                "csflag": customerdetails["csflag"],
                                "inoutflag": row["inoutflag"],
                                "custtin": custtin,
                                "invoicedate": datetime.strftime(
                                    row["invoicedate"], "%d-%m-%Y"
                                ),
                                "grossamt": "%.2f" % float(row["invoicetotal"]),
                                "cancelflag": cancelinv,
                            }
                        )
                        srno += 1
                    # flag=1, sales invoices
                    elif self.request.params["flag"] == "1" and row["inoutflag"] == 15:
                        invoices.append(
                            {
                                "srno": srno,
                                "invoiceno": row["invoiceno"],
                                "invid": row["invid"],
                                "dcno": dcno,
                                "godown": godowns,
                                "dcdate": dcdate,
                                "netamt": "%.2f" % netamt,
                                "taxamt": "%.2f" % taxamt,
                                "custname": customerdetails["custname"],
                                "csflag": customerdetails["csflag"],
                                "inoutflag": row["inoutflag"],
                                "custtin": custtin,
                                "invoicedate": datetime.strftime(
                                    row["invoicedate"], "%d-%m-%Y"
                                ),
                                "grossamt": "%.2f" % float(row["invoicetotal"]),
                                "cancelflag": cancelinv,
                            }
                        )
                        srno += 1
                    # flag=2, purchase invoices.
                    elif self.request.params["flag"] == "2" and row["inoutflag"] == 9:
                        invoices.append(
                            {
                                "srno": srno,
                                "invoiceno": row["invoiceno"],
                                "invid": row["invid"],
                                "dcno": dcno,
                                "godown": godowns,
                                "dcdate": dcdate,
                                "netamt": "%.2f" % netamt,
                                "taxamt": "%.2f" % taxamt,
                                "custname": customerdetails["custname"],
                                "csflag": customerdetails["csflag"],
                                "inoutflag": row["inoutflag"],
                                "custtin": custtin,
                                "invoicedate": datetime.strftime(
                                    row["invoicedate"], "%d-%m-%Y"
                                ),
                                "grossamt": "%.2f" % float(row["invoicetotal"]),
                                "cancelflag": cancelinv,
                            }
                        )
                        srno += 1
                return {"gkstatus": gkcore.enumdict["Success"], "gkresult": invoices}

    @view_config(
        route_name="invoice_list_rectify", request_method="GET", renderer="json"
    )
    def getListofInvoices_rectify(self):
        """
        The code is to get list of invoices which can be rectified.
        Only those invoice which have not used in either of the documents like rejection note,credit/debit note.
        also transactions have not made.
        """
        try:
            token = self.request.headers["gktoken"]
        except:
            return {"gkstatus": gkcore.enumdict["UnauthorisedAccess"]}
        authDetails = authCheck(token)
        if authDetails["auth"] == False:
            return {"gkstatus": gkcore.enumdict["UnauthorisedAccess"]}
        else:
            with eng.connect() as con:
                org = authDetails["orgcode"]
                # An empty list into which invoices shall be appended.
                list_Invoices = []
                # Fetching id, number, date of all invoices.
                # check whether invtype does exist and further check its type
                invoices = con.execute(
                    "select invid,invoiceno,invoicedate,custid from invoice where invid not in (select invid from drcr where orgcode = %d) and invid not in (select invid from rejectionnote where orgcode = %d) and invid not in(select invid from billwise where orgcode = %d) and orgcode = %d and icflag = 9 and inoutflag = %d order by invoicedate desc"
                    % (org, org, org, org, int(self.request.params["invtype"]))
                )
                invoicesData = invoices.fetchall()

                # Appending dictionaries into empty list.
                # Each dictionary has details of an invoice viz. id, number, date, total amount, amount paid and balance.
                for inv in invoicesData:
                    custData = con.execute(
                        select(
                            [
                                customerandsupplier.c.custname,
                                customerandsupplier.c.csflag,
                                customerandsupplier.c.custid,
                            ]
                        ).where(customerandsupplier.c.custid == inv["custid"])
                    )
                    customerdata = custData.fetchone()
                    list_Invoices.append(
                        {
                            "invid": inv["invid"],
                            "invoiceno": inv["invoiceno"],
                            "invoicedate": datetime.strftime(
                                inv["invoicedate"], "%d-%m-%Y"
                            ),
                            "custname": customerdata["custname"],
                            "custid": customerdata["custid"],
                            "csflag": customerdata["csflag"],
                        }
                    )
                return {"gkstatus": enumdict["Success"], "invoices": list_Invoices}

    @view_config(route_name="invoice_invid", request_method="GET", renderer="json")
    def getInvoiceDetails(self):
        """
        purpose: gets details on an invoice given it's invid.
        The details include related customer or supplier details as well as calculation of amount.
        Description:
        This function returns a single record as key:value pare for an invoice given it's invid.
        Depending on the invoice type it will return the details on customer or supplier.
        It also calculates total amount, taxable amount with all the taxes.
        The function returns a nested dictionary with dicts for products with their costing details, free quantyty etc.
        If address equal to none then send null value otherwise respected address.
        "inoutflag" gives invoice is in or out (i.e Purchase or Sale) for sales invoice "inoutflag"=15 and for Purchase invoice "inoutflag"=9.
        Note: the details such as state code, place of supplyer etc depends on the tax type.
        The above mentioned and some more fields are only returned if the tax is GST.
        """
        try:
            token = self.request.headers["gktoken"]
        except:
            return {"gkstatus": gkcore.enumdict["UnauthorisedAccess"]}
        authDetails = authCheck(token)
        if authDetails["auth"] == False:
            return {"gkstatus": gkcore.enumdict["UnauthorisedAccess"]}
        else:
            with eng.connect() as con:
                invid = self.request.matchdict["invid"]
                inv = getInvoiceData(
                    con,
                    authDetails["orgcode"],
                    {"invid": invid},
                )
                if not len(inv):
                    raise Exception("Issue fetching Invoice Data")
                return {"gkstatus": gkcore.enumdict["Success"], "gkresult": inv}

    """
    This is a function to update an invoice.
    This function is primarily used to enable editing of invoices.
    It receives a dictionary with information regarding an invoice, changes to be made in stock if any and delivery notes linked if any.
    """

    @view_config(route_name="invoice_invid", request_method="PUT", renderer="json")
    def editInvoice(self):
        try:
            token = self.request.headers["gktoken"]
        except:
            return {"gkstatus": gkcore.enumdict["UnauthorisedAccess"]}
        authDetails = authCheck(token)
        if authDetails["auth"] == False:
            return {"gkstatus": enumdict["UnauthorisedAccess"]}
        with eng.begin() as con:
            # Data is stored in a variable dtset.
            dtset = self.request.json_body
            # Empty dictionary to store details of delivery challan linked if any.
            dcinvdataset = {}
            # Details of invoice and stock are stored in separate variables.
            invdataset = dtset["invoice"]
            invid = self.request.matchdict["invid"]
            stockdataset = dtset["stock"]
            discount = invdataset["discount"]
            items = invdataset["contents"]
            invdataset["orgcode"] = authDetails["orgcode"]
            stockdataset["orgcode"] = authDetails["orgcode"]
            voucherData = {}
            pricedetails = []
            if "pricedetails" in invdataset:
                pricedetails = invdataset["pricedetails"]
                invdataset.pop("pricedetails", pricedetails)

            godown_id = dtset["stock"]["goid"]
            godown_details = con.execute(
                select([godown])
                .where(godown.c.goid==godown_id)
            ).fetchone()
            contact_id = invdataset["custid"]
            contact_details = con.execute(
                select([customerandsupplier])
                .where(customerandsupplier.c.custid == contact_id)
            ).fetchone()
            product_id_values = list(items.keys())
            products = con.execute(
                select([product.c.productcode, product.c.productdesc, product.c.gscode])
                .where(product.c.productcode.in_(product_id_values))
            ).fetchall()
            product_details = {
                id: {
                    "productcode": id,
                    "productdesc": name,
                    "gscode": hsn,
                }
                for id, name, hsn in products
            }
            transaction_details = {
                "godown": dict(godown_details),
                "contact": dict(contact_details),
                "products": product_details,
            }
            immutable_data_id = con.execute(
                select([invoice.c.immutable_data_id])
                .where(invoice.c.invid == invid)
            ).scalar()
            con.execute(
                transaction.update()
                .where(transaction.c.transaction_id == immutable_data_id)
                .values(transaction_details=transaction_details)
            )

            # Entries in dcinv and stock tables are deleted to avoid duplicate entries.
            stockresult = con.execute(
                select([stock.c.stockid]).where(and_(
                    stock.c.dcinvtnid == invid,
                    stock.c.dcinvtnflag == 9,
                ))
            )
            stockid = stockresult.scalar()
            if stockid:
                deletestock = con.execute(
                    stock.delete().where(stock.c.stockid == stockid)
                )
            dcinvresult = con.execute(
                select([dcinv.c.dcinvid]).where(dcinv.c.invid == invid)
            )
            dcinvid = dcinvresult.scalar()
            if dcinvid:
                deletedcinv = con.execute(
                    dcinv.delete().where(dcinv.c.invid == invid)
                )

            # If delivery chalan is linked  details of invoice are updated and a new entry is made in the dcinv table.
            if "dcid" in invdataset:
                dcinvdataset["dcid"] = invdataset.pop("dcid")
                dcinvdataset["orgcode"] = invdataset["orgcode"]
                dcinvdataset["invid"] = invid
                dcinvdataset["invprods"] = stockdataset["items"]
                updateinvoice = con.execute(
                    invoice.update()
                    .where(invoice.c.invid == invid)
                    .values(invdataset)
                )
                if len(pricedetails) > 0:
                    for price in pricedetails:
                        price["orgcode"] = authDetails["orgcode"]
                        updateprice = con.execute(
                            cslastprice.update()
                            .where(
                                and_(
                                    cslastprice.c.custid == price["custid"],
                                    cslastprice.c.productcode
                                    == price["productcode"],
                                    cslastprice.c.inoutflag
                                    == price["inoutflag"],
                                    cslastprice.c.orgcode == price["orgcode"],
                                )
                            )
                            .values(price)
                        )
                result = con.execute(dcinv.insert(), [dcinvdataset])
                if result.rowcount > 0:
                    avfl = con.execute(
                        select([organisation.c.avflag]).where(
                            organisation.c.orgcode == invdataset["orgcode"]
                        )
                    )
                    av = avfl.fetchone()
                    if av["avflag"] == 1:
                        avData = dtset["av"]
                        voucherresult = con.execute(
                            select([vouchers.c.vouchercode]).where(
                                vouchers.c.invid == invid
                            )
                        )
                        voucherid = voucherresult.scalar()
                        if voucherid:
                            deletevch = con.execute(
                                vouchers.delete().where(
                                    vouchers.c.vouchercode == voucherid
                                )
                            )
                        mafl = con.execute(
                            select([organisation.c.maflag]).where(
                                organisation.c.orgcode == invdataset["orgcode"]
                            )
                        )
                        maFlag = mafl.fetchone()
                        csName = con.execute(
                            select([customerandsupplier.c.custname]).where(
                                and_(
                                    customerandsupplier.c.orgcode
                                    == invdataset["orgcode"],
                                    customerandsupplier.c.custid
                                    == int(invdataset["custid"]),
                                )
                            )
                        )
                        CSname = csName.fetchone()
                        queryParams = {
                            "invtype": invdataset["inoutflag"],
                            "taxType": invdataset["taxflag"],
                            "destinationstate": invdataset["taxstate"],
                            "totaltaxablevalue": avData["totaltaxable"],
                            "maflag": maFlag["maflag"],
                            "totalAmount": invdataset["invoicetotal"],
                            "invoicedate": invdataset["invoicedate"],
                            "invid": invid,
                            "invoiceno": invdataset["invoiceno"],
                            "csname": CSname["custname"],
                            "taxes": invdataset["tax"],
                            "cess": invdataset["cess"],
                            "products": avData["product"],
                            "prodData": avData["prodData"],
                        }
                        # when invoice total is rounded off
                        if invdataset["roundoffflag"] == 1:
                            roundOffAmount = float(
                                invdataset["invoicetotal"]
                            ) - round(float(invdataset["invoicetotal"]))
                            if float(roundOffAmount) != 0.00:
                                queryParams["roundoffamt"] = float(
                                    roundOffAmount
                                )

                        if int(invdataset["taxflag"]) == 7:
                            queryParams["gstname"] = avData["avtax"]["GSTName"]
                            queryParams["cessname"] = avData["avtax"][
                                "CESSName"
                            ]

                        if int(invdataset["taxflag"]) == 22:
                            queryParams["taxpayment"] = avData["taxpayment"]
                        # call getDefaultAcc
                        a = getDefaultAcc(
                            con, queryParams, int(invdataset["orgcode"])
                        )
                        if a["gkstatus"] == 0:
                            voucherData["status"] = 0
                            voucherData["vchno"] = a["vchNo"]
                            voucherData["vchid"] = a["vid"]
                        else:
                            voucherData["status"] = 1
                return {"gkstatus": enumdict["Success"], "vchData": voucherData}

            # If no delivery challan is linked an entry is made in stock table after invoice details are updated.
            updateinvoice = con.execute(
                invoice.update()
                .where(invoice.c.invid == invid)
                .values(invdataset)
            )
            if len(pricedetails) > 0:
                for price in pricedetails:
                    price["orgcode"] = authDetails["orgcode"]
                    updateprice = con.execute(
                        cslastprice.update()
                        .where(
                            and_(
                                cslastprice.c.custid == price["custid"],
                                cslastprice.c.productcode
                                == price["productcode"],
                                cslastprice.c.inoutflag
                                == price["inoutflag"],
                                cslastprice.c.orgcode == price["orgcode"],
                            )
                        )
                        .values(price)
                    )
            # Code for updating bankdetails when user switch to cash payment from bank.
            getpaymentmode = int(
                invdataset["paymentmode"]
            )  # Loading paymentmode.
            idinv = int(invid)  # Loading invoiceid.
            # checking paymentmod whether it is 2 or 3 (i.e. 2 -> bank (pos), 3 -> cash (pos), 4 -> bank (party), 5 -> cash (party)).
            if getpaymentmode in [3, 5]:
                # Updating bankdetails to NULL if paymentmod is 3 or 5.
                updatebankdetails = con.execute(
                    "update invoice set bankdetails = NULL where invid = %d"
                    % (idinv)
                )
            result = con.execute(
                select([invoice.c.invid, invoice.c.invoicedate]).where(
                    and_(
                        invoice.c.custid == invdataset["custid"],
                        invoice.c.invoiceno == invdataset["invoiceno"],
                    )
                )
            )
            invoiceid = result.fetchone()
            stockdataset["dcinvtnid"] = invoiceid["invid"]
            stockdataset["stockdate"] = invdataset["invoicedate"]
            stockdataset["dcinvtnflag"] = "9"
            for item in list(items.keys()):
                itemQty = float(list(items[item].values())[0])
                itemRate = float(list(items[item].keys())[0])
                itemTotalDiscount = float(discount.get(item, 0))
                itemDiscount = 0
                if itemQty:
                    itemDiscount = itemTotalDiscount / itemQty
                stockdataset["rate"] = itemRate - itemDiscount
                stockdataset["productcode"] = item
                stockdataset["qty"] = itemQty
                result = con.execute(stock.insert(), [stockdataset])
            avfl = con.execute(
                select([organisation.c.avflag]).where(
                    organisation.c.orgcode == invdataset["orgcode"]
                )
            )
            av = avfl.fetchone()
            if av["avflag"] == 1:
                avData = dtset["av"]
                voucherresult = con.execute(
                    select([vouchers.c.vouchercode]).where(
                        vouchers.c.invid == invid
                    )
                )
                voucherid = voucherresult.scalar()
                if voucherid:
                    deletevch = con.execute(
                        vouchers.delete().where(
                            vouchers.c.vouchercode == voucherid
                        )
                    )
                mafl = con.execute(
                    select([organisation.c.maflag]).where(
                        organisation.c.orgcode == invdataset["orgcode"]
                    )
                )
                maFlag = mafl.fetchone()
                csName = con.execute(
                    select([customerandsupplier.c.custname]).where(
                        and_(
                            customerandsupplier.c.orgcode
                            == invdataset["orgcode"],
                            customerandsupplier.c.custid
                            == int(invdataset["custid"]),
                        )
                    )
                )
                CSname = csName.fetchone()
                queryParams = {
                    "invtype": invdataset["inoutflag"],
                    "pmtmode": invdataset["paymentmode"],
                    "taxType": invdataset["taxflag"],
                    "destinationstate": invdataset["taxstate"],
                    "totaltaxablevalue": avData["totaltaxable"],
                    "maflag": maFlag["maflag"],
                    "totalAmount": invdataset["invoicetotal"],
                    "invoicedate": invdataset["invoicedate"],
                    "invid": invoiceid["invid"],
                    "invoiceno": invdataset["invoiceno"],
                    "csname": CSname["custname"],
                    "taxes": invdataset["tax"],
                    "cess": invdataset["cess"],
                    "products": avData["product"],
                    "prodData": avData["prodData"],
                }
                # when invoice total is rounded off
                if invdataset["roundoffflag"] == 1:
                    roundOffAmount = float(
                        invdataset["invoicetotal"]
                    ) - round(float(invdataset["invoicetotal"]))
                    if float(roundOffAmount) != 0.00:
                        queryParams["roundoffamt"] = float(roundOffAmount)
                if int(invdataset["taxflag"]) == 7:
                    queryParams["gstname"] = avData["avtax"]["GSTName"]
                    queryParams["cessname"] = avData["avtax"]["CESSName"]

                if int(invdataset["taxflag"]) == 22:
                    queryParams["taxpayment"] = avData["taxpayment"]
                # call getDefaultAcc
                a = getDefaultAcc(
                    con, queryParams, int(invdataset["orgcode"])
                )
                if a["gkstatus"] == 0:
                    voucherData["status"] = 0
                    voucherData["vchno"] = a["vchNo"]
                    voucherData["vchid"] = a["vid"]
                else:
                    voucherData["status"] = 1
            return {"gkstatus": enumdict["Success"], "vchData": voucherData}

    # Delete the invoice entry from invoice table using invid and store in invoicebin
    # table. Also delete billwise entry and stock entry for same invid and corsponding
    # vouchers as well.
    @view_config(route_name="invoice_cancel", request_method="DELETE", renderer="json")
    def cancelInvoice(self):
        try:
            token = self.request.headers["gktoken"]
        except:
            return {"gkstatus": enumdict["UnauthorisedAccess"]}
        authDetails = authCheck(token)
        if authDetails["auth"] == False:
            return {"gkstatus": enumdict["UnauthorisedAccess"]}
        with eng.begin() as con:
            invid = self.request.matchdict["invid"]

            drcrnote = con.execute(
                drcr.select().where(
                    drcr.c.invid == invid
                )
            )

            if drcrnote.rowcount:
                return {
                    "gkstatus": enumdict["ActionDisallowed"],
                    "error": "Cancel not allowed; Related debit/Credit note exists"
                }
            # to fetch data of all data of cancel invoice.
            invoicedata = con.execute(
                select([invoice]).where(invoice.c.invid == invid)
            )
            invoicedata = invoicedata.fetchone()

            # Add all data of cancel invoice into invoicebin
            invoiceBinData = dict(invoicedata.items())

            # Remove fields that are not present in invoicebin table
            for field in [
                'ewaybillno',
                'supinvno',
                'supinvdate',
            ]:
                del invoiceBinData[field]

            # below query is for delete billwise entry for cancel invoice.
            con.execute(
                "delete from billwise where invid=%d and orgcode=%d"
                % (int(invid), authDetails["orgcode"])
            )

            # Update invoiceBinDat with details of the related delivery note
            # and cancel the delivery note.
            delivery_note_details = cancel_delivery_note(
                con, int(invid), authDetails["orgcode"]
            )
            if delivery_note_details:
                invoiceBinData.update({
                    "dcinfo": {
                        "dcno": delivery_note_details.get("dcno"),
                        "dcdate": delivery_note_details.get("dcdate"),
                        "goid": delivery_note_details.get("goid"),
                    },
                })

            invbin = con.execute(invoicebin.insert(), [invoiceBinData])

            # below query to get voucher code for cancel invoice for delete corsponding vouchers.
            voucher_code = con.execute(
                "select vouchercode as vcode from vouchers where invid=%d and orgcode=%d"
                % (int(invid), authDetails["orgcode"])
            )
            voucherCode = voucher_code.fetchall()

            if voucherCode is not None:
                # function call to delete vouchers
                for vcode in voucherCode:
                    cancel_voucher(
                        con, vcode["vcode"], authDetails["orgcode"]
                    )

            # To delete invoice entry from invoice table
            con.execute(
                "delete from invoice where invid=%d and orgcode=%d"
                % (int(invid), authDetails["orgcode"])
            )

            logdata = {}
            logdata["orgcode"] = authDetails["orgcode"]
            logdata["userid"] = authDetails["userid"]
            logdata["time"] = datetime.today().strftime("%Y-%m-%d %H:%M:%S")
            logdata["activity"] = (
                str(invoicedata["invoiceno"]) + " Invoice Cancelled"
            )
            con.execute(log.insert(), [logdata])
            return {"gkstatus": enumdict["Success"]}

    @view_config(route_name="invoice_invid", request_method="DELETE", renderer="json")
    def deleteinvoice(self):
        try:
            token = self.request.headers["gktoken"]
        except:
            return {"gkstatus": enumdict["UnauthorisedAccess"]}
        authDetails = authCheck(token)
        if authDetails["auth"] == False:
            return {"gkstatus": enumdict["UnauthorisedAccess"]}
        else:
            try:
                self.con = eng.connect()
                invid = self.request.matchdict["invid"]
                # delete vouchers, stock, dcinv, invoice with invid if available
                try:
                    deletevoucher = self.con.execute(
                        vouchers.delete().where(vouchers.c.invid == invid)
                    )
                except:
                    pass
                try:
                    deletestock = self.con.execute(
                        stock.delete().where(
                            and_(
                                stock.c.dcinvtnid == invid,
                                stock.c.dcinvtnflag == 9,
                            )
                        )
                    )
                except:
                    pass
                try:
                    deletedcinv = self.con.execute(
                        dcinv.delete().where(dcinv.c.invid == invid)
                    )
                except:
                    pass
                deleteinvoice = self.con.execute(
                    invoice.delete().where(invoice.c.invid == invid)
                )
                return {"gkstatus": enumdict["Success"]}
            except:
                return {"gkstatus": enumdict["ConnectionFailed"]}
            finally:
                self.con.close()

    @view_config(request_method="PUT", request_param="type=bwa", renderer="json")
    def updatePayment(self):
        """
                purpose: updates the total payed amount for a certain bill or invoice or puts it on account for custommer/supplyer.
                Description:
                The function will take invid and amount received.
                The function also takes a flag called payflag.
                This flag will have the value 1:advance,2:billwise,15:on-account.
                If payflag = 2 then function will update the invoice table,
                with the given amount by incrementing paydamount for the given invoice.
                Else the amount will be added to either advamce for value 1 and onaccamt for value 15,
                Both in customer table, which implies that csid must be needed.
        There will be an icFlag which will determine if it's  an incrementing or decrement.
        """
        try:
            token = self.request.headers["gktoken"]
        except:
            return {"gkstatus": gkcore.enumdict["UnauthorisedAccess"]}
        authDetails = authCheck(token)
        if authDetails["auth"] == False:
            return {"gkstatus": gkcore.enumdict["UnauthorisedAccess"]}
        else:
            try:
                self.con = eng.connect()
                payflag = int(self.request.params["payflag"])
                pdamt = float(self.request.params["pdamt"])
                if payflag == 1:
                    icFlag = int(self.request.params["icflag"])
                    custid = int(self.request.params["custid"])
                    if icFlag == 9:
                        result = self.con.execute(
                            "update customerandsupplier set advamt = advamt + %f where custid = %d"
                            % (pdamt, custid)
                        )
                    else:
                        result = self.con.execute(
                            "update customerandsupplier set advamt = advamt - %f where custid = %d"
                            % (pdamt, custid)
                        )
                if payflag == 15:
                    icFlag = int(self.request.params["icflag"])
                    custid = int(self.request.params["custid"])
                    if icFlag == 9:
                        result = self.con.execute(
                            "update customerandsupplier set onaccamt = onaccamt + %f where custid = %d"
                            % (pdamt, custid)
                        )
                    else:
                        result = self.con.execute(
                            "update customerandsupplier set onaccamt = onaccamt - %f where custid = %d"
                            % (pdamt, custid)
                        )
                if payflag == 2:
                    invid = int(self.request.params["invid"])
                    result = self.con.execute(
                        "update invoice set amountpaid = amountpaid + %f where invid = %d"
                        % (pdamt, invid)
                    )
                return {"gkstatus": enumdict["Success"]}

            except exc.IntegrityError:
                return {"gkstatus": enumdict["DuplicateEntry"]}
            except:
                return {"gkstatus": gkcore.enumdict["ConnectionFailed"]}
            finally:
                self.con.close()

    @view_config(route_name="invoice_cancel", request_method="GET", renderer="json")
    def getCancelledInvoiceDetails(self):
        """
        purpose: gets details on a canceled invoice given it's invid.
        The details include related customer or supplier details as well as calculation of amount.
        Description:
        This function returns a single record as key:value pare for canceled invoice given it's invid.
        Depending on the invoice type it will return the details on customer or supplier.
        It also calculates total amount, taxable amount with all the taxes.
        The function returns a nested dictionary with dicts for products with their costing details, free quantyty etc.
        If address equal to none then send null value otherwise respected address.
        "inoutflag" gives invoice is in or out (i.e Purchase or Sale) for sales invoice "inoutflag"=15 and for Purchase invoice "inoutflag"=9.
        Note: the details such as state code, place of supplyer etc depends on the tax type.
        The above mentioned and some more fields are only returned if the tax is GST.
        """
        try:
            token = self.request.headers["gktoken"]
        except:
            return {"gkstatus": gkcore.enumdict["UnauthorisedAccess"]}
        authDetails = authCheck(token)
        if authDetails["auth"] == False:
            return {"gkstatus": gkcore.enumdict["UnauthorisedAccess"]}
        else:
            with eng.connect() as con:
                result = con.execute(
                    select([invoicebin]).where(
                        invoicebin.c.invid == self.request.matchdict["invid"]
                    )
                )
                invrow = result.fetchone()

                immutable_data = con.execute(
                    select([transaction.c.transaction_details])
                    .where(transaction.c.transaction_id == invrow["immutable_data_id"])
                ).scalar()

                inv = {
                    "invid": invrow["invid"],
                    "taxflag": invrow["taxflag"],
                    "invoiceno": invrow["invoiceno"],
                    "invoicedate": datetime.strftime(invrow["invoicedate"], "%d-%m-%Y"),
                    "icflag": invrow["icflag"],
                    "invoicetotal": "%.2f" % float(invrow["invoicetotal"]),
                    "invoicetotalword": invrow["invoicetotalword"],
                    "bankdetails": invrow["bankdetails"],
                    "orgstategstin": invrow["orgstategstin"],
                    "paymentmode": invrow["paymentmode"],
                    "inoutflag": invrow["inoutflag"],
                    "discflag": invrow["discflag"],
                    "immutable_data": immutable_data,
                }

                if invrow["sourcestate"] != None:
                    inv["sourcestate"] = invrow["sourcestate"]
                    inv["sourcestatecode"] = getStateCode(
                        invrow["sourcestate"], con
                    )["statecode"]
                    sourceStateCode = getStateCode(invrow["sourcestate"], con)[
                        "statecode"
                    ]
                if invrow["address"] == None:
                    inv["address"] = ""
                else:
                    inv["address"] = invrow["address"]
                if invrow["pincode"] == None:
                    inv["pincode"] = ""
                else:
                    inv["pincode"] = invrow["pincode"]
                if invrow["icflag"] == 9:
                    inv["issuername"] = invrow["issuername"]
                    inv["designation"] = invrow["designation"]
                    inv["consignee"] = invrow["consignee"]
                    inv["attachmentcount"] = invrow["attachmentcount"]
                    if invrow["dateofsupply"] != None:
                        inv["dateofsupply"] = datetime.strftime(
                            invrow["dateofsupply"], "%d-%m-%Y"
                        )
                    else:
                        inv["dateofsupply"] = ""
                    inv["transportationmode"] = invrow["transportationmode"]
                    inv["vehicleno"] = invrow["vehicleno"]
                    inv["reversecharge"] = invrow["reversecharge"]
                    if invrow["taxstate"] != None:
                        inv["destinationstate"] = invrow["taxstate"]
                        taxStateCode = getStateCode(invrow["taxstate"], con)[
                            "statecode"
                        ]
                        inv["taxstatecode"] = taxStateCode
                    if invrow["dcinfo"] != None:
                        inv["dcno"] = invrow["dcinfo"]["dcno"]
                    else:
                        inv["dcno"] = ""
                    custandsup = con.execute(
                        select(
                            [
                                customerandsupplier.c.custname,
                                customerandsupplier.c.state,
                                customerandsupplier.c.custaddr,
                                customerandsupplier.c.pincode,
                                customerandsupplier.c.custtan,
                                customerandsupplier.c.gstin,
                                customerandsupplier.c.csflag,
                            ]
                        ).where(customerandsupplier.c.custid == invrow["custid"])
                    )
                    custData = custandsup.fetchone()
                    custsupstatecode = getStateCode(custData["state"], con)[
                        "statecode"
                    ]
                    custSupDetails = {
                        "custname": custData["custname"],
                        "custsupstate": custData["state"],
                        "custaddr": custData["custaddr"],
                        "csflag": custData["csflag"],
                        "pincode": custData["pincode"],
                        "custsupstatecode": custsupstatecode,
                    }
                    if custData["custtan"] != None:
                        custSupDetails["custtin"] = custData["custtan"]
                    if custData["gstin"] != None:
                        if int(custData["csflag"]) == 3:
                            try:
                                custSupDetails["custgstin"] = custData["gstin"][
                                    str(taxStateCode)
                                ]
                            except:
                                custSupDetails["custgstin"] = None
                        else:
                            try:
                                custSupDetails["custgstin"] = custData["gstin"][
                                    str(sourceStateCode)
                                ]
                            except:
                                custSupDetails["custgstin"] = None

                    inv["custSupDetails"] = custSupDetails
                # contents is a nested dictionary from invoice table.
                # It contains productcode as the key with a value as a dictionary.
                # this dictionary has two key value pairs, priceperunit and quantity.
                contentsData = invrow["contents"]
                # invContents is the finally dictionary which will not just have the dataset from original contents,
                # but also productdesc,unitname,freeqty,discount,taxname,taxrate,amount and taxam
                invContents = {}
                # get the dictionary of discount and access it inside the loop for one product each.
                # do the same with freeqty.
                totalDisc = 0.00
                totalTaxableVal = 0.00
                totalTaxAmt = 0.00
                totalCessAmt = 0.00
                discounts = invrow["discount"]
                freeqtys = invrow["freeqty"]
                # now looping through the contents.
                # pc will have the productcode which will be the ke in invContents.
                for pc in list(contentsData.keys()):
                    # freeqty and discount can be 0 as these field were not present in previous version of 4.25 hence we have to check if it is None or not and have to pass values accordingly for code optimization.
                    if discounts != None:
                        # discflag is for discount type. Percent=16/Amount=1
                        # here we convert percent discount in to amount.
                        if invrow["discflag"] == 16:
                            qty = float(list(contentsData[str(pc)].keys())[0])
                            price = float(list(contentsData[str(pc)].values())[0])
                            totalWithoutDiscount = qty * price
                            discount = totalWithoutDiscount * float(
                                float(discounts[pc]) / 100
                            )
                        else:
                            discount = discounts[pc]
                    else:
                        discount = 0.00

                    if freeqtys != None:
                        freeqty = freeqtys[pc]
                    else:
                        freeqty = 0.00
                    prod = con.execute(
                        select(
                            [
                                product.c.productdesc,
                                product.c.uomid,
                                product.c.gsflag,
                                product.c.gscode,
                            ]
                        ).where(product.c.productcode == pc)
                    )
                    prodrow = prod.fetchone()
                    if int(prodrow["gsflag"]) == 7:
                        um = con.execute(
                            select([unitofmeasurement.c.unitname]).where(
                                unitofmeasurement.c.uomid == int(prodrow["uomid"])
                            )
                        )
                        unitrow = um.fetchone()
                        unitofMeasurement = unitrow["unitname"]
                        taxableAmount = (
                            (float(contentsData[pc][list(contentsData[pc].keys())[0]]))
                            * float(list(contentsData[pc].keys())[0])
                        ) - float(discount)
                    else:
                        unitofMeasurement = ""
                        taxableAmount = float(list(contentsData[pc].keys())[0]) - float(
                            discount
                        )

                    taxRate = 0.00
                    totalAmount = 0.00
                    taxRate = float(invrow["tax"][pc])
                    if int(invrow["taxflag"]) == 22:
                        taxRate = float(invrow["tax"][pc])
                        taxAmount = taxableAmount * float(taxRate / 100)
                        taxname = "VAT"
                        totalAmount = float(taxableAmount) + (
                            float(taxableAmount) * float(taxRate / 100)
                        )
                        totalDisc = totalDisc + float(discount)
                        totalTaxableVal = totalTaxableVal + taxableAmount
                        totalTaxAmt = totalTaxAmt + taxAmount
                        invContents[pc] = {
                            "proddesc": prodrow["productdesc"],
                            "gscode": prodrow["gscode"],
                            "uom": unitofMeasurement,
                            "qty": "%.2f"
                            % (
                                float(
                                    contentsData[pc][list(contentsData[pc].keys())[0]]
                                )
                            ),
                            "freeqty": "%.2f" % (float(freeqty)),
                            "priceperunit": "%.2f"
                            % (float(list(contentsData[pc].keys())[0])),
                            "discount": "%.2f" % (float(discounts[pc])),
                            "taxableamount": "%.2f" % (float(taxableAmount)),
                            "totalAmount": "%.2f" % (float(totalAmount)),
                            "taxname": "VAT",
                            "taxrate": "%.2f" % (float(taxRate)),
                            "taxamount": "%.2f" % (float(taxAmount)),
                        }

                    else:
                        cessRate = 0.00
                        cessAmount = 0.00
                        cessVal = 0.00
                        taxname = ""
                        if invrow["cess"]:
                            cessVal = float(invrow["cess"][pc])
                            cessAmount = taxableAmount * (cessVal / 100)
                            totalCessAmt = totalCessAmt + cessAmount

                        if invrow["sourcestate"] != invrow["taxstate"]:
                            taxname = "IGST"
                            taxAmount = taxableAmount * (taxRate / 100)
                            totalAmount = taxableAmount + taxAmount + cessAmount
                        else:
                            taxname = "SGST"
                            taxRate = taxRate / 2
                            taxAmount = taxableAmount * (taxRate / 100)
                            totalAmount = (
                                taxableAmount
                                + (taxableAmount * ((taxRate * 2) / 100))
                                + cessAmount
                            )

                        totalDisc = totalDisc + float(discount)
                        totalTaxableVal = totalTaxableVal + taxableAmount
                        totalTaxAmt = totalTaxAmt + taxAmount

                        invContents[pc] = {
                            "proddesc": prodrow["productdesc"],
                            "gscode": prodrow["gscode"],
                            "gsflag": prodrow["gsflag"],
                            "uom": unitofMeasurement,
                            "qty": "%.2f"
                            % (
                                float(
                                    contentsData[pc][list(contentsData[pc].keys())[0]]
                                )
                            ),
                            "freeqty": "%.2f" % (float(freeqty)),
                            "priceperunit": "%.2f"
                            % (float(list(contentsData[pc].keys())[0])),
                            "discount": "%.2f" % (float(discounts[pc])),
                            "taxableamount": "%.2f" % (float(taxableAmount)),
                            "totalAmount": "%.2f" % (float(totalAmount)),
                            "taxname": taxname,
                            "taxrate": "%.2f" % (float(taxRate)),
                            "taxamount": "%.2f" % (float(taxAmount)),
                            "cess": "%.2f" % (float(cessAmount)),
                            "cessrate": "%.2f" % (float(cessVal)),
                        }
                    invContents[pc]["discflag"] = invrow["discflag"]
                inv["totaldiscount"] = "%.2f" % (float(totalDisc))
                inv["totaltaxablevalue"] = "%.2f" % (float(totalTaxableVal))
                inv["totaltaxamt"] = "%.2f" % (float(totalTaxAmt))
                inv["totalcessamt"] = "%.2f" % (float(totalCessAmt))
                inv["taxname"] = taxname
                inv["invcontents"] = invContents

                return {"gkstatus": gkcore.enumdict["Success"], "gkresult": inv}

    @view_config(request_method="GET", request_param="type=bwa", renderer="json")
    def getCSUPBills(self):
        """
                Purpose: gets list of unpaid bills for a given customerandsupplier or supplier.
                Takes the person's id and returns a grid containing bills.
        Apart from the bills it also returns customerandsupplier or supplyer name.
                Description:
                The function will take customerandsupplier or supplier id while orgcode is  taken from token.
                The invoice table will be scanned for all the bills concerning the party.
                If the total amount is greater than amountpaid(which is 0 by default ) then the bill qualifies to be returned.
                The function will return json object with gkstatus,csName:name of the party and gkresult:grid of bills.
        The bills grid calld gkresult will return a list as it's value.
                The columns will be as follows:
                Bill no., Bill date, Customer/ supplier name,total amount and outstanding.
                the outstanding is calculated as total - amountpaid.
        """
        try:
            token = self.request.headers["gktoken"]
        except:
            return {"gkstatus": gkcore.enumdict["UnauthorisedAccess"]}
        authDetails = authCheck(token)
        if authDetails["auth"] == False:
            return {"gkstatus": gkcore.enumdict["UnauthorisedAccess"]}
        else:
            try:
                self.con = eng.connect()
                unpaidBillsRecords = self.con.execute(
                    select(
                        [
                            invoice.c.invid,
                            invoice.c.invoiceno,
                            invoice.c.invoicedate,
                            invoice.c.custid,
                            invoice.c.invoicetotal,
                            invoice.c.amountpaid,
                        ]
                    ).where(
                        and_(
                            invoice.c.custid == self.request.params["custid"],
                            invoice.c.invoicetotal > invoice.c.amountpaid,
                        )
                    )
                )

                unpaidBills = unpaidBillsRecords.fetchall()
                bills = []
                for bill in unpaidBills:
                    upb = {}
                    upb["invid"] = bill["invid"]
                    upb["invoiceno"] = bill["invoiceno"]
                    upb["invoicedate"] = datetime.strftime(
                        bill["invoicedate"], "%d-%m-%Y"
                    )
                    upb["invoicetotal"] = "%.2f" % float(bill["invoicetotal"])
                    upb["pendingamount"] = "%.2f" % (
                        float(bill["invoicetotal"]) - float(bill["amountpaid"])
                    )
                    bills.append(upb)
                custNameData = self.con.execute(
                    select([customerandsupplier.c.custname]).where(
                        customerandsupplier.c.custid == self.request.params["custid"]
                    )
                )
                custnameRecord = custNameData.fetchone()
                csName = custnameRecord["custname"]
                gkresult = {"csname": csName, "unpaidbills": bills}
                return {"gkstatus": enumdict["Success"], "gkresult": gkresult}
            except exc.IntegrityError:
                return {"gkstatus": enumdict["ActionDisallowed"]}
            except:
                return {"gkstatus": enumdict["ConnectionFailed"]}
            finally:
                self.con.close()

    @view_config(route_name="invoice_id", request_method="GET", renderer="json")
    def getinvid(self):
        try:
            token = self.request.headers["gktoken"]
        except:
            return {"gkstatus": gkcore.enumdict["UnauthorisedAccess"]}
        authDetails = authCheck(token)
        if authDetails["auth"] == False:
            return {"gkstatus": gkcore.enumdict["UnauthorisedAccess"]}
        else:
            with eng.connect() as con:
                invcount = con.execute(
                    "select count(invid) as icount from invoice where inoutflag=%d and orgcode = %d"
                    % (int(self.request.params["type"]), authDetails["orgcode"])
                )
                invoicecount = invcount.fetchone()
                invoiceBinCount = invcount = con.execute(
                    "select count(invid) as icount from invoicebin where inoutflag=%d and orgcode = %d"
                    % (int(self.request.params["type"]), authDetails["orgcode"])
                ).fetchone()
                invid = int(invoicecount["icount"]) + int(invoiceBinCount["icount"]) + 1
                return {"gkstatus": 0, "invoiceid": invid}

    @view_config(request_method="GET", request_param="forvoucher", renderer="json")
    def getforvoucher(self):
        try:
            token = self.request.headers["gktoken"]
        except:
            return {"gkstatus": gkcore.enumdict["UnauthorisedAccess"]}
        authDetails = authCheck(token)
        if authDetails["auth"] == False:
            return {"gkstatus": gkcore.enumdict["UnauthorisedAccess"]}
        else:
            try:
                self.con = eng.connect()
                invsData = self.con.execute(
                    "select invid from invoice where icflag = 9 and orgcode = %d except select invid from vouchers where orgcode = %d"
                    % (authDetails["orgcode"], authDetails["orgcode"])
                )
                invoices = []
                for inv in invsData:
                    filteredInvoices = self.con.execute(
                        select(
                            [
                                invoice.c.invoiceno,
                                invoice.c.inoutflag,
                                invoice.c.invoicedate,
                                invoice.c.custid,
                                invoice.c.invoicetotal,
                            ]
                        ).where(invoice.c.invid == inv["invid"])
                    )
                    invdataset = filteredInvoices.fetchone()
                    csdata = self.con.execute(
                        select(
                            [
                                customerandsupplier.c.custname,
                                customerandsupplier.c.csflag,
                            ]
                        ).where(customerandsupplier.c.custid == invdataset["custid"])
                    )
                    custname = csdata.fetchone()
                    invoices.append(
                        {
                            "invoiceno": invdataset["invoiceno"],
                            "invid": inv["invid"],
                            "custname": custname["custname"],
                            "inoutflag": invdataset["inoutflag"],
                            "invoicedate": datetime.strftime(
                                invdataset["invoicedate"], "%d-%m-%Y"
                            ),
                            "invoicetotal": "%.2f" % float(invdataset["invoicetotal"]),
                        }
                    )

                return {"gkstatus": gkcore.enumdict["Success"], "gkresult": invoices}
            except:
                return {"gkstatus": gkcore.enumdict["ConnectionFailed"]}
            finally:
                self.con.close()

    @view_config(route_name="cashmemo", request_method="GET", renderer="json")
    def getAllcashmemos(self):
        try:
            token = self.request.headers["gktoken"]
        except:
            return {"gkstatus": gkcore.enumdict["UnauthorisedAccess"]}
        authDetails = authCheck(token)
        if authDetails["auth"] == False:
            return {"gkstatus": gkcore.enumdict["UnauthorisedAccess"]}
        else:
            with eng.connect() as con:
                table = invoice
                is_cancelled = False
                if int(self.request.params.get("cancelled", 0)) == 1:
                    table = invoicebin
                    is_cancelled = True
                inoutflag = self.request.params.get("inoutflag")

                statement = select(
                        [
                            table.c.invoiceno,
                            table.c.invid,
                            table.c.invoicedate,
                            table.c.invoicetotal,
                            table.c.immutable_data_id,
                        ]
                    ).where(
                        and_(
                            table.c.orgcode == authDetails["orgcode"],
                            table.c.icflag == 3,
                        )
                    )
                if inoutflag:
                    statement = statement.where(
                        table.c.inoutflag == inoutflag
                    )
                result = con.execute(
                    statement.order_by(table.c.invoicedate)
                ).fetchall()
                invoices = []
                for row in result:
                    immutable_data = con.execute(
                        select([transaction.c.transaction_details])
                        .where(transaction.c.transaction_id == row["immutable_data_id"])
                    ).scalar()
                    invoices.append(
                        {
                            "deletedFlag": is_cancelled,
                            "invoiceno": row["invoiceno"],
                            "invid": row["invid"],
                            "invoicedate": datetime.strftime(
                                row["invoicedate"], "%d-%m-%Y"
                            ),
                            "invoicetotal": float(row["invoicetotal"]),
                            "immutable_data": immutable_data,
                        }
                    )
                return {"gkstatus": gkcore.enumdict["Success"], "gkresult": invoices}

    @view_config(route_name="invoice_attachment", request_method="GET", renderer="json")
    def getInvoiceAttachment(self):
        try:
            token = self.request.headers["gktoken"]
        except:
            return {"gkstatus": enumdict["UnauthorisedAccess"]}
        authDetails = authCheck(token)
        if authDetails["auth"] == False:
            return {"gkstatus": enumdict["UnauthorisedAccess"]}
        else:
            with eng.connect() as con:
                ur = getUserRole(authDetails["userid"], authDetails["orgcode"])
                urole = ur["gkresult"]
                invid = self.request.matchdict["invid"]
                invoiceData = con.execute(
                    select([invoice.c.invoiceno, invoice.c.attachment]).where(
                        and_(invoice.c.invid == invid)
                    )
                )
                attachment = invoiceData.fetchone()
                return {
                    "gkstatus": enumdict["Success"],
                    "gkresult": attachment["attachment"],
                    "invoiceno": attachment["invoiceno"],
                    "userrole": urole["userrole"],
                }

    @view_config(route_name="delnote_unbilled", request_method="GET", renderer="json")
    def unbilled_delnotes(self):
        try:
            token = self.request.headers["gktoken"]
        except:
            return {"gkstatus": enumdict["UnauthorisedAccess"]}
        authDetails = authCheck(token)
        if authDetails["auth"] == False:
            return {"gkstatus": enumdict["UnauthorisedAccess"]}
        else:
            with eng.connect() as con:
                orgcode = authDetails["orgcode"]
                try:
                    dataset = self.request.json_body
                except:
                    dataset = {
                        "inputdate": self.request.params["inputdate"],
                        "type": self.request.params["type"],
                    }
                inputdate = dataset["inputdate"]
                new_inputdate = dataset["inputdate"]
                new_inputdate = datetime.strptime(new_inputdate, "%Y-%m-%d")
                dc_unbilled = []
                alldcids = con.execute(
                    select([delchal.c.dcid, delchal.c.dcdate])
                    .distinct()
                    .where(
                        and_(
                            delchal.c.orgcode == orgcode,
                            delchal.c.dcdate <= new_inputdate,
                            stock.c.orgcode == orgcode,
                            stock.c.dcinvtnflag == 4,
                            delchal.c.dcid == stock.c.dcinvtnid,
                        )
                    )
                    .order_by(delchal.c.dcdate)
                )
                alldcids = alldcids.fetchall()
                dcResult = []
                i = 0
                while i < len(alldcids):
                    dcid = alldcids[i]
                    invidresult = con.execute(
                        select([dcinv.c.invid]).where(
                            and_(
                                dcid[0] == dcinv.c.dcid,
                                dcinv.c.orgcode == orgcode,
                                invoice.c.orgcode == orgcode,
                                invoice.c.invid == dcinv.c.invid,
                                invoice.c.invoicedate <= new_inputdate,
                            )
                        )
                    )
                    invidresult = invidresult.fetchall()
                    if len(invidresult) == 0:
                        dcprodresult = con.execute(
                            select([stock.c.productcode, stock.c.qty]).where(
                                and_(
                                    stock.c.orgcode == orgcode,
                                    stock.c.dcinvtnflag == 4,
                                    dcid[0] == stock.c.dcinvtnid,
                                )
                            )
                        )
                        dcprodresult = dcprodresult.fetchall()
                        # This code is for rejection note
                        # even if an invoice is not prepared and rejection note prepared for whole delivery note then it should not come into unbilled delivery note.
                        allrnidres = con.execute(
                            select([rejectionnote.c.rnid])
                            .distinct()
                            .where(
                                and_(
                                    rejectionnote.c.orgcode == orgcode,
                                    rejectionnote.c.rndate <= new_inputdate,
                                    rejectionnote.c.dcid == dcid[0],
                                )
                            )
                        )
                        allrnidres = allrnidres.fetchall()
                        rnprodresult = []
                        # get stock respected to all rejection notes
                        for rnid in allrnidres:
                            temp = con.execute(
                                select([stock.c.productcode, stock.c.qty]).where(
                                    and_(
                                        stock.c.orgcode == orgcode,
                                        stock.c.dcinvtnflag == 18,
                                        stock.c.dcinvtnid == rnid[0],
                                    )
                                )
                            )
                            temp = temp.fetchall()
                            rnprodresult.append(temp)
                        matchedproducts = []
                        remainingproducts = {}
                        totalqtyofdcprod = {}
                        for eachitem in dcprodresult:
                            totalqtyofdcprod.update({eachitem[0]: eachitem[1]})
                        for row in rnprodresult:
                            for prodc, qty in row:
                                if prodc in remainingproducts:
                                    remainingproducts[prodc] = float(
                                        remainingproducts[prodc]
                                    ) + float(qty)
                                    if float(remainingproducts[prodc]) >= float(
                                        totalqtyofdcprod[prodc]
                                    ):
                                        matchedproducts.append(prodc)
                                        del remainingproducts[prodc]
                                elif float(qty) >= float(totalqtyofdcprod[prodc]):
                                    matchedproducts.append(prodc)
                                else:
                                    remainingproducts.update({prodc: float(qty)})
                        if len(matchedproducts) == len(dcprodresult):
                            # Now we have got the delchals, for which invoices are also sent completely.
                            alldcids.remove(dcid)
                            i -= 1
                    else:
                        # invid's will be distinct only. So no problem to explicitly applying distinct clause.
                        dcprodresult = con.execute(
                            select([stock.c.productcode, stock.c.qty]).where(
                                and_(
                                    stock.c.orgcode == orgcode,
                                    stock.c.dcinvtnflag == 4,
                                    dcid[0] == stock.c.dcinvtnid,
                                )
                            )
                        )
                        dcprodresult = dcprodresult.fetchall()

                        dcdataqty = temp = con.execute(
                            select([delchal.c.contents]).where(
                                and_(
                                    delchal.c.orgcode == orgcode,
                                    delchal.c.dcid == dcid[0],
                                )
                            )
                        )
                        dcprodqty = dcdataqty.fetchone()
                        proddata = dcprodqty["contents"]
                        # I am assuming :productcode must be distinct. So, I haven't applied distinct construct.
                        # what if dcprodresult or invprodresult is empty?
                        invprodresult = []
                        for invid in invidresult:
                            temp = con.execute(
                                select([invoice.c.contents]).where(
                                    and_(
                                        invoice.c.orgcode == orgcode,
                                        invid == invoice.c.invid,
                                    )
                                )
                            )
                            temp = temp.fetchall()
                            # Below two lines are intentionally repeated. It's not a mistake.
                            temp = temp[0]
                            temp = temp[0]
                            invprodresult.append(temp)
                        # Now we have to compare the two results: dcprodresult and invprodresult
                        # I assume that the delchal must have at most only one entry for a particular product. If not, then it's a bug and needs to be rectified.
                        # But, in case of invprodresult, there can be more than one productcodes mentioned. This is because, with one delchal, there can be many invoices linked.
                        matchedproducts = []
                        remainingproducts = {}
                        totalqtyofdcprod = {}
                        for pc in list(proddata.keys()):
                            # for eachitem in dcprodresult:
                            # dcprodresult is a list of tuples. eachitem is one such tuple.
                            totalqtyofdcprod.update(
                                {pc: proddata[pc][list(proddata[pc].keys())[0]]}
                            )
                            for eachinvoice in invprodresult:
                                # invprodresult is a list of dictionaries. eachinvoice is one such dictionary.
                                for eachproductcode in list(eachinvoice.keys()):
                                    # eachitem[0] is unique. It's not repeated.
                                    dcprodcode = pc
                                    if int(dcprodcode) == int(eachproductcode):
                                        # this means that the product in delchal matches with the product in invoice
                                        # now we will check its quantity
                                        invqty = list(
                                            eachinvoice[eachproductcode].values()
                                        )[0]
                                        dcqty = proddata[pc][
                                            list(proddata[pc].keys())[0]
                                        ]
                                        if float(dcqty) == float(
                                            invqty
                                        ):  # conversion of datatypes to compatible ones is very important when comparing them.
                                            # this means the quantity of current individual product is matched exactly
                                            matchedproducts.append(int(eachproductcode))
                                        elif float(dcqty) > float(invqty):
                                            # this means current invoice has not billed the whole product quantity.
                                            if dcprodcode in list(
                                                remainingproducts.keys()
                                            ):
                                                if float(dcqty) == (
                                                    float(remainingproducts[dcprodcode])
                                                    + float(invqty)
                                                ):
                                                    matchedproducts.append(
                                                        int(eachproductcode)
                                                    )
                                                    # whether we use eachproductcode or dcprodcode, doesn't matter. Because, both values are the same here.
                                                    del remainingproducts[
                                                        (eachproductcode)
                                                    ]
                                                else:
                                                    # It must not be the case that below addition is greater than dcqty.
                                                    remainingproducts[
                                                        dcprodcode
                                                    ] = float(
                                                        remainingproducts[dcprodcode]
                                                    ) + float(
                                                        invqty
                                                    )
                                            else:
                                                remainingproducts.update(
                                                    {dcprodcode: float(invqty)}
                                                )
                                        else:
                                            # "dcqty < invqty" should never happen.
                                            # It could happen when multiple delivery chalans have only one invoice.
                                            pass

                        # This code is for rejection note
                        allrnidres = con.execute(
                            select([rejectionnote.c.rnid])
                            .distinct()
                            .where(
                                and_(
                                    rejectionnote.c.orgcode == orgcode,
                                    rejectionnote.c.rndate <= new_inputdate,
                                    rejectionnote.c.dcid == dcid[0],
                                )
                            )
                        )
                        allrnidres = allrnidres.fetchall()
                        rnprodresult = []
                        # get stock respected to all rejection notes
                        for rnid in allrnidres:
                            temp = con.execute(
                                select([stock.c.productcode, stock.c.qty]).where(
                                    and_(
                                        stock.c.orgcode == orgcode,
                                        stock.c.dcinvtnflag == 18,
                                        stock.c.dcinvtnid == rnid[0],
                                    )
                                )
                            )
                            temp = temp.fetchall()
                            rnprodresult.append(temp)
                        for row in rnprodresult:
                            for prodc, qty in row:
                                if prodc in remainingproducts:
                                    remainingproducts[prodc] = float(
                                        remainingproducts[prodc]
                                    ) + float(qty)
                                    if float(remainingproducts[prodc]) >= float(
                                        totalqtyofdcprod[prodc]
                                    ):
                                        matchedproducts.append(prodc)
                                        del remainingproducts[prodc]

                        if len(matchedproducts) == len(dcprodresult):
                            # Now we have got the delchals, for which invoices are also sent completely.
                            alldcids.remove(dcid)
                            i -= 1
                    i += 1
                    pass

                for eachdcid in alldcids:
                    singledcResult = con.execute(
                        select(
                            [
                                delchal.c.dcid,
                                delchal.c.inoutflag,
                                delchal.c.dcno,
                                delchal.c.dcdate,
                                delchal.c.dateofsupply,
                                delchal.c.dcflag,
                                customerandsupplier.c.custname,
                                customerandsupplier.c.csflag,
                                delchal.c.attachmentcount,
                            ]
                        )
                        .distinct()
                        .where(
                            and_(
                                delchal.c.orgcode == orgcode,
                                customerandsupplier.c.orgcode == orgcode,
                                eachdcid[0] == delchal.c.dcid,
                                delchal.c.custid == customerandsupplier.c.custid,
                                stock.c.dcinvtnflag == 4,
                                eachdcid[0] == stock.c.dcinvtnid,
                            )
                        )
                    )
                    singledcResult = singledcResult.fetchone()
                    dcResult.append(singledcResult)
                temp_dict = {}
                srno = 1
                if dataset["type"] == "invoice":
                    for row in dcResult:
                        temp_dict = {
                            "dcid": row["dcid"],
                            "srno": srno,
                            "dcno": row["dcno"],
                            "dcdate": datetime.strftime(row["dcdate"], "%d-%m-%Y"),
                            "dcflag": row["dcflag"],
                            "csflag": row["csflag"],
                            "inoutflag": row["inoutflag"],
                            "custname": row["custname"],
                            "attachmentcount": row["attachmentcount"],
                        }
                        if row["dateofsupply"] != None:
                            temp_dict["dateofsupply"] = datetime.strftime(
                                row["dateofsupply"], "%d-%m-%Y"
                            )
                        else:
                            temp_dict["dateofsupply"] = row["dateofsupply"]
                        if temp_dict["dcflag"] == 19:
                            # We don't have to consider sample.
                            temp_dict["dcflag"] = "Sample"
                        elif temp_dict["dcflag"] == 6:
                            # we ignore this as well
                            temp_dict["dcflag"] = "Free Replacement"
                        if (
                            temp_dict["dcflag"] != "Sample"
                            and temp_dict["dcflag"] != "Free Replacement"
                        ):
                            dc_unbilled.append(temp_dict)
                            srno += 1
                else:
                    # type=rejection note
                    # Here even delivery type sample and free Replacement can also be rejected.
                    for row in dcResult:
                        temp_dict = {
                            "dcid": row["dcid"],
                            "srno": srno,
                            "dcno": row["dcno"],
                            "dcdate": datetime.strftime(row["dcdate"], "%d-%m-%Y"),
                            "dcflag": row["dcflag"],
                            "csflag": row["csflag"],
                            "inoutflag": row["inoutflag"],
                            "custname": row["custname"],
                            "attachmentcount": row["attachmentcount"],
                        }
                        dc_unbilled.append(temp_dict)
                        srno += 1
                return {"gkstatus": enumdict["Success"], "gkresult": dc_unbilled}

    """
        This function gives details of single rejection note from it's invid.
        The details include related customer or supplier and sales or purchase invoice details as well as calculation of amount.
        It also calculates total amount, taxable amount, new taxable amount with all the taxes.
        The function returns a dictionary with the details.
        'item' dictionary contains details product and tax calculation values.
        'delchal' dictionary contains 'customerandsupplier details.
        'invDetails' dictionary contains request invoice details.
    """

    @view_config(
        request_method="GET", request_param="type=nonrejectedinvprods", renderer="json"
    )
    def nonRejectedInvProds(self):
        try:
            token = self.request.headers["gktoken"]
        except:
            return {"gkstatus": enumdict["UnauthorisedAccess"]}
        authDetails = authCheck(token)
        if authDetails["auth"] == False:
            return {"gkstatus": enumdict["UnauthorisedAccess"]}
        else:
            try:
                self.con = eng.connect()
                dataset = self.request.json_body
                invid = dataset["invid"]
                invprodresult = []
                orgcode = authDetails["orgcode"]
                userId = authDetails["userid"]
                userDetails = self.con.execute(
                    text("select username, orgs->':orgcode'->'userrole' as userrole from gkusers where userid = :userid"),
                    orgcode = orgcode,
                    userid = userId,
                ).fetchone()
                temp = self.con.execute(
                    select([invoice]).where(
                        and_(invoice.c.orgcode == orgcode, invoice.c.invid == invid)
                    )
                )
                invData = temp.fetchone()
                invprodresult.append(invData["contents"])
                qtyc = invData["contents"]
                discounts = invData["discount"]
                invDetails = {
                    "invno": invData["invoiceno"],
                    "invdate": datetime.strftime(invData["invoicedate"], "%d-%m-%Y"),
                    "taxflag": invData["taxflag"],
                    "tax": invData["tax"],
                    "invoicetotal": float(invData["invoicetotal"]),
                    "orgstategstin": invData["orgstategstin"],
                    "inoutflag": invData["inoutflag"],
                }
                if invData["inoutflag"] == 15:
                    invDetails["issuername"] = invData["issuername"]
                    invDetails["designation"] = invData["designation"]
                else:
                    invDetails["issuername"] = userDetails["username"]
                    invDetails["designation"] = userDetails["userrole"]

                if invData["sourcestate"] != None or invData["taxstate"] != None:
                    # Please keep in mind that state of invoice in front end is always set as sourcestate key of invdetails.
                    # if inoutflag is 15 customer/supplier state is taxstate and invoice state is sourcestate else customer/supllier state is sourcestate and invoice state is taxstate
                    if invData["inoutflag"] == 15:
                        invDetails["sourcestate"] = invData["sourcestate"]
                        invDetails["taxstate"] = invData["taxstate"]
                    else:
                        invDetails["sourcestate"] = invData["taxstate"]
                        invDetails["taxstate"] = invData["sourcestate"]
                if invData["address"] != "":
                    invDetails["address"] = invData["address"]

                totalDisc = 0.00
                totalTaxableVal = 0.00
                totalTaxAmt = 0.00
                totalCessAmt = 0.00

                items = {}
                for eachitem in list(qtyc.keys()):
                    productdata = self.con.execute(
                        select(
                            [
                                product.c.productdesc,
                                product.c.uomid,
                                product.c.gsflag,
                                product.c.gscode,
                            ]
                        ).where(
                            and_(
                                product.c.productcode == int(eachitem),
                                product.c.gsflag == 7,
                            )
                        )
                    )
                    productdesc = productdata.fetchone()
                    if productdesc == None:
                        continue
                    uomresult = self.con.execute(
                        select([unitofmeasurement.c.unitname]).where(
                            unitofmeasurement.c.uomid == productdesc["uomid"]
                        )
                    )
                    unitnamrrow = uomresult.fetchone()
                    uom = unitnamrrow["unitname"]
                    freeqtys = invData["freeqty"]
                    if discounts != None:
                        # discflag is for discount type. Percent=16/Amount=1
                        # here we convert percent discount in to amount.
                        if invData["discflag"] == 16:
                            qty = float(list(invData["contents"][eachitem].keys())[0])
                            price = float(
                                list(invData["contents"][eachitem].values())[0]
                            )
                            totalWithoutDiscount = qty * price
                            discount = totalWithoutDiscount * float(
                                float(discounts[eachitem]) / 100
                            )
                        else:
                            discount = discounts[eachitem]
                    else:
                        discount = 0.00
                    if freeqtys != None:
                        freeqty = freeqtys[eachitem]
                    else:
                        freeqty = 0.00
                    items[int(eachitem)] = {}
                    result = "%.2f" % float(list(qtyc[eachitem].values())[0])
                    ppu = list(qtyc[eachitem].keys())[0]
                    items[int(eachitem)] = {"qty": "%.2f" % float(result)}
                    # Checking Rejection Note Qty.
                    allrnidres = self.con.execute(
                        select([rejectionnote.c.rnid])
                        .distinct()
                        .where(
                            and_(
                                rejectionnote.c.orgcode == orgcode,
                                rejectionnote.c.invid == invid,
                            )
                        )
                    )
                    allrnidres = allrnidres.fetchall()
                    rnprodresult = []
                    # get stock respected to all rejection notes
                    for rnid in allrnidres:
                        # checking in rnid into stock table
                        temp = self.con.execute(
                            select([stock.c.productcode, stock.c.qty]).where(
                                and_(
                                    stock.c.orgcode == orgcode,
                                    stock.c.dcinvtnflag == 18,
                                    stock.c.dcinvtnid == rnid[0],
                                )
                            )
                        )
                        tempall = temp.fetchall()
                        rnprodresult.append(tempall)
                    for rnproddata in rnprodresult:
                        for row in rnproddata:
                            if int(row["productcode"]) == int(eachitem):
                                changedqty = float(
                                    items[int(row["productcode"])]["qty"]
                                ) - float(row["qty"])
                        items[int(eachitem)] = {"qty": "%.2f" % float(changedqty)}
                    taxableAmount = (
                        float(ppu) * float(items[int(eachitem)]["qty"])
                    ) - float(discount)
                    taxRate = 0.00
                    totalAmount = 0.00
                    taxRate = float(invData["tax"][eachitem])
                    if int(invData["taxflag"]) == 22:
                        taxRate = float(invData["tax"][eachitem])
                        taxAmount = taxableAmount * float(taxRate / 100)
                        taxname = "VAT"
                        totalAmount = float(taxableAmount) + (
                            float(taxableAmount) * float(taxRate / 100)
                        )
                        totalDisc = totalDisc + float(discount)
                        totalTaxableVal = totalTaxableVal + taxableAmount
                        totalTaxAmt = totalTaxAmt + taxAmount
                        items[int(eachitem)] = {
                            "productdesc": productdesc["productdesc"],
                            "gscode": productdesc["gscode"],
                            "qty": float(items[int(eachitem)]["qty"]),
                            "feeqty": "%.2f" % (float(freeqty)),
                            "priceperunit": "%.2f"
                            % (float(list(qtyc[eachitem].keys())[0])),
                            "discount": "%.2f" % (float(discounts[eachitem])),
                            "taxableamount": "%.2f" % (float(taxableAmount)),
                            "totalAmount": "%.2f" % (float(totalAmount)),
                            "taxname": "VAT",
                            "taxrate": "%.2f" % (float(taxRate)),
                            "taxamount": "%.2f" % (float(taxAmount)),
                            "uom": uom,
                        }
                    else:
                        cessRate = 0.00
                        cessAmount = 0.00
                        cessVal = 0.00
                        taxname = ""
                        if invData["cess"]:
                            cessVal = float(invData["cess"][eachitem])
                            cessAmount = taxableAmount * (cessVal / 100)
                            totalCessAmt = totalCessAmt + cessAmount

                        if invData["sourcestate"] != invData["taxstate"]:
                            taxname = "IGST"
                            taxAmount = taxableAmount * (taxRate / 100)
                            totalAmount = taxableAmount + taxAmount + cessAmount
                        else:
                            taxname = "SGST"
                            taxRate = taxRate / 2
                            taxAmount = taxableAmount * (taxRate / 100)
                            totalAmount = (
                                taxableAmount
                                + (taxableAmount * ((taxRate * 2) / 100))
                                + cessAmount
                            )

                        totalDisc = totalDisc + float(discount)
                        totalTaxableVal = totalTaxableVal + taxableAmount
                        totalTaxAmt = totalTaxAmt + taxAmount

                        items[int(eachitem)] = {
                            "productdesc": productdesc["productdesc"],
                            "gscode": productdesc["gscode"],
                            "qty": float(items[int(eachitem)]["qty"]),
                            "discount": "%.2f" % (float(discounts[eachitem])),
                            "taxableamount": "%.2f" % (float(taxableAmount)),
                            "totalAmount": "%.2f" % (float(totalAmount)),
                            "taxname": taxname,
                            "taxrate": "%.2f" % (float(taxRate)),
                            "taxamount": "%.2f" % (float(taxAmount)),
                            "priceperunit": "%.2f"
                            % (float(list(qtyc[eachitem].keys())[0])),
                            "cess": "%.2f" % (float(cessAmount)),
                            "cessrate": "%.2f" % (float(cessVal)),
                            "uom": uom,
                        }
                items[int(eachitem)]["discflag"] = invData["discflag"]
                invDetails["totaldiscount"] = "%.2f" % (float(totalDisc))
                invDetails["totaltaxablevalue"] = "%.2f" % (float(totalTaxableVal))
                invDetails["totaltaxamt"] = "%.2f" % (float(totalTaxAmt))
                invDetails["totalcessamt"] = "%.2f" % (float(totalCessAmt))
                for productcode in list(items.keys()):
                    if items[productcode]["qty"] == 0:
                        del items[productcode]
                temp = self.con.execute(
                    select([dcinv.c.dcid]).where(
                        and_(dcinv.c.orgcode == orgcode, dcinv.c.invid == invid)
                    )
                )
                temp = temp.fetchone()
                dcdetails = {}
                custdata = self.con.execute(
                    select([customerandsupplier]).where(
                        customerandsupplier.c.custid.in_(
                            select([invoice.c.custid]).where(invoice.c.invid == invid)
                        )
                    )
                )
                custname = custdata.fetchone()
                custsupstatecodedata = getStateCode(custname["state"], self.con)[
                    "statecode"
                ]
                dcdetails = {
                    "custname": custname["custname"],
                    "custaddr": custname["custaddr"],
                    "custtin": custname["custtan"],
                    "custsupstatecodedata": custsupstatecodedata,
                    "taxflag": invData["taxflag"],
                }
                if int(invData["taxflag"]) == 22:
                    if custname["custtan"] != None:
                        dcdetails["custtin"] = custname["custtan"]
                        dcdetails["custstate"] = custname["state"]
                else:
                    if invData["sourcestate"] != None or invData["taxstate"] != None:
                        if invData["inoutflag"] == 15:
                            sourceStateCode = getStateCode(
                                invData["taxstate"], self.con
                            )["statecode"]
                            dcdetails["custstate"] = invData["taxstate"]
                        else:
                            taxStateCode = getStateCode(
                                invData["sourcestate"], self.con
                            )["statecode"]
                            dcdetails["custstate"] = invData["sourcestate"]
                    if custname["gstin"] != None:
                        if int(invData["inoutflag"]) == 15:
                            try:
                                dcdetails["custgstin"] = custname["gstin"][
                                    str(sourceStateCode)
                                ]

                            except:
                                dcdetails["custgstin"] = None
                        else:
                            try:
                                dcdetails["custgstin"] = custname["gstin"][
                                    str(taxStateCode)
                                ]

                            except:
                                dcdetails["custgstin"] = None
                if temp:
                    result = self.con.execute(
                        select([delchal]).where(delchal.c.dcid == temp[0])
                    )
                    delchaldata = result.fetchone()
                    stockdataval = self.con.execute(
                        select([stock.c.goid]).where(
                            and_(stock.c.dcinvtnflag == 4, stock.c.dcinvtnid == temp[0])
                        )
                    )
                    stockdata = stockdataval.fetchone()
                    dcdetails["dcid"] = temp[0]
                    dcdetails["dcflag"] = delchaldata["dcflag"]

                    if stockdata["goid"] != None:
                        godata = self.con.execute(
                            select(
                                [godown.c.goname, godown.c.state, godown.c.goaddr]
                            ).where(godown.c.goid == stockdata["goid"])
                        )
                        goname = godata.fetchone()
                        dcdetails["goid"] = stockdata["goid"]
                        dcdetails["goname"] = goname["goname"]
                        dcdetails["gostate"] = goname["state"]
                        dcdetails["goaddr"] = goname["goaddr"]

                return {
                    "gkstatus": enumdict["Success"],
                    "gkresult": items,
                    "delchal": dcdetails,
                    "invDetails": invDetails,
                }
            except:
                return {"gkstatus": enumdict["ConnectionFailed"]}
            finally:
                self.con.close()

    @view_config(route_name="invoice_crdrid", request_method="GET", renderer="json")
    def getcrdrid(self):
        try:
            token = self.request.headers["gktoken"]
        except:
            return {"gkstatus": gkcore.enumdict["UnauthorisedAccess"]}
        authDetails = authCheck(token)
        if authDetails["auth"] == False:
            return {"gkstatus": gkcore.enumdict["UnauthorisedAccess"]}
        else:
            with eng.connect() as con:
                invid = self.request.matchdict["invid"]
                delchalresult = con.execute(
                    select([drcr.c.drcrid, drcr.c.dctypeflag]).where(
                        drcr.c.invid == invid
                    )
                )
                data_dict = {}
                for row in delchalresult:
                    drcrid = row[drcr.c.drcrid]
                    dctypeflag = row[drcr.c.dctypeflag]
                    data_dict[drcrid] = dctypeflag
                return {"gkstatus": 0, "data": data_dict}

    @view_config(route_name="invoice_rnid", request_method="GET", renderer="json")
    def getrnid(self):
        try:
            token = self.request.headers["gktoken"]
        except:
            return {"gkstatus": gkcore.enumdict["UnauthorisedAccess"]}
        authDetails = authCheck(token)
        if authDetails["auth"] == False:
            return {"gkstatus": gkcore.enumdict["UnauthorisedAccess"]}
        else:
            try:
                self.con = eng.connect()
                invid = self.request.matchdict["invid"]
                rejectionresult = self.con.execute(
                    select([rejectionnote.c.rnid]).where(
                        rejectionnote.c.invid == invid
                    )
                )
                rejectioninfo = rejectionresult.fetchone()
                return {"gkstatus": 0, "data": rejectioninfo[0]}
            except:
                return {"gkstatus": gkcore.enumdict["ConnectionFailed"]}
            finally:
                self.con.close()
