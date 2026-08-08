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
"Reshma Bhatwadekar" <reshma@dff.org.in>
"Vasudha Kadge" <kadge.vasudha@gmail.com>
'Abhijith Balan'<abhijith@dff.org.in>
"""
from gkcore import eng, enumdict
from gkcore.models.gkdb import (
    invoice,
    transaction,
    tax,
    state,
    drcr,
    customerandsupplier,
    users,
    product,
    unitofmeasurement,
    organisation,
    accounts,
    vouchers,
    stock,
)
from sqlalchemy.sql import select
from sqlalchemy import and_, exc, func
from sqlalchemy.sql.expression import text
from pyramid.view import view_defaults, view_config
from datetime import datetime
import gkcore
from gkcore.utils import authCheck, getUserRole
from gkcore.views.api_invoice import getStateCode, createAccount
import traceback  # for printing detailed exception logs


@view_defaults(route_name="drcrnote", renderer="json")
class api_drcr(object):
    def __init__(self, request):
        self.request = request

    @view_config(request_method="POST", renderer="json")
    def createDrCrNote(self):
        try:
            token = self.request.headers["gktoken"]
        except:
            return {"gkstatus": gkcore.enumdict["UnauthorisedAccess"]}
        authDetails = authCheck(token)
        if authDetails["auth"] == False:
            return {"gkstatus": enumdict["UnauthorisedAccess"]}
        with eng.begin() as con:
            wholedataset = self.request.json_body
            dataset = wholedataset["dataset"]
            vdataset = wholedataset["vdataset"]
            dataset["orgcode"] = authDetails["orgcode"]
            # Check for duplicate entry before insertion
            result_duplicate_check = con.execute(
                select([drcr.c.drcrno]).where(
                    and_(
                        drcr.c.orgcode == authDetails["orgcode"],
                        func.lower(drcr.c.drcrno) == func.lower(dataset["drcrno"]),
                    )
                )
            )

            if result_duplicate_check.rowcount > 0:
                # Duplicate entry found, handle accordingly
                return {"gkstatus": enumdict["DuplicateEntry"]}

            result = con.execute(drcr.insert(), [dataset])
            lastdrcr = con.execute(
                select([drcr.c.drcrid]).where(
                    and_(
                        drcr.c.invid == dataset["invid"],
                        drcr.c.drcrno == dataset["drcrno"],
                        drcr.c.orgcode == dataset["orgcode"],
                        drcr.c.dctypeflag == dataset["dctypeflag"],
                    )
                )
            )
            drcrid = lastdrcr.fetchone()
            if int(dataset["drcrmode"]) == 18:
                stockdataset = {
                    "dcinvtnid": drcrid["drcrid"],
                    "orgcode": dataset["orgcode"],
                    "stockdate": dataset["drcrdate"],
                }
                if int(dataset["dctypeflag"]) == 3:
                    stockdataset["inout"] = 9
                    if int(vdataset["inoutflag"]) == 15:
                        # value dcinvtnflag set to 2 when if Goods returned are of bad quality else set 7 from front.
                        stockdataset["dcinvtnflag"] = int(dataset["dcinvtnflag"])
                    else:
                        stockdataset["dcinvtnflag"] = 7
                else:
                    stockdataset["inout"] = 15
                    stockdataset["dcinvtnflag"] = 7

                if "goid" in vdataset:
                    stockdataset["goid"] = vdataset["goid"]

                # Iterate through the keys and values using a for loop
                if "quantities" in dataset["reductionval"]:
                    for key, value in dataset["reductionval"]["quantities"].items():
                        stockdataset["qty"] = value
                        stockdataset["productcode"] = key
                        itemPrice = con.execute(
                            select([product.c.prodmrp]).where(
                                product.c.productcode == stockdataset["productcode"]
                            )
                        )
                        itemP = itemPrice.fetchone()
                        stockdataset["rate"] = itemP[0]
                        con.execute(stock.insert(), stockdataset)

            # check automatic voucher flag  if it is 1 get maflag
            avfl = con.execute(
                select([organisation.c.avflag]).where(
                    organisation.c.orgcode == dataset["orgcode"]
                )
            )
            av = avfl.fetchone()
            if av["avflag"] != 1:
                return {
                    "gkstatus": enumdict["Success"],
                    "gkresult": drcrid["drcrid"],
                }

            mafl = con.execute(
                select([organisation.c.maflag]).where(
                    organisation.c.orgcode == dataset["orgcode"]
                )
            )
            maFlag = mafl.fetchone()
            queryParams = {
                "maflag": maFlag["maflag"],
                "cessname": "CESS",
                "drcrid": drcrid["drcrid"],
            }
            queryParams.update(dataset)
            queryParams.update(vdataset)
            if dataset["roundoffflag"] == 1:
                roundOffAmount = float(dataset["totreduct"]) - round(
                    float(dataset["totreduct"])
                )
                if float(roundOffAmount) != 0.00:
                    queryParams["roundoffamt"] = float(roundOffAmount)

            drcrautoVch = drcrVoucher(con, queryParams, int(dataset["orgcode"]))
            return {
                "gkstatus": enumdict["Success"],
                "vchCode": {"vflag": 1, "vchCode": drcrautoVch},
                "gkresult": drcrid["drcrid"],
            }

    @view_config(request_method="GET", request_param="drcr=single", renderer="json")
    def getDrCrDetails(self):
        """
        purpose: gets details of single debit or credit note from it's drcrid.
        The details include related customer or supplier and sales or purchase invoice details as well as calculation of amount.
        Description:
        This function returns a single record as key:value pair for debit-credit note given it's drcrid.
        Depending upon dctypeflag(for credit note it is "3" and for debit note it is"4")it will return the details of debit note and credit note.
        It also calculates total amount, taxable amount, new taxable amount, total debited/credited value with all the taxes.
        The function returns a dictionary with the details of debit & credit note.
        If reference equal to none then send null value otherwise respected reference credit/debit note number and credit/debit note date.
        """
        try:
            token = self.request.headers["gktoken"]
        except:
            return {"gkstatus": gkcore.enumdict["UnauthorisedAccess"]}
        authDetails = authCheck(token)
        if authDetails["auth"] == False:
            return {"gkstatus": gkcore.enumdict["UnauthorisedAccess"]}
        with eng.connect() as con:
            # taken credit/debit note data on the basis on drcrid
            drcrresult = con.execute(
                select([drcr]).where(drcr.c.drcrid == self.request.params["drcrid"])
            )
            drcrrow = drcrresult.fetchone()
            invdata = {}
            custSupDetails = {}
            drcrdata = {}
            drcrdata = {
                "drcrid": drcrrow["drcrid"],
                "drcrno": drcrrow["drcrno"],
                "drcrdate": datetime.strftime(drcrrow["drcrdate"], "%d-%m-%Y"),
                "dctypeflag": drcrrow["dctypeflag"],
                "totreduct": "%.2f" % float(drcrrow["totreduct"]),
                "reduct": drcrrow["reductionval"],
                "drcrmode": drcrrow["drcrmode"],
                "drcrnarration": drcrrow["drcrnarration"],
            }
            # this will show that total amount is rounded of or not
            drcrdata["roundedoffflag"] = drcrrow["roundoffflag"]
            drcrdata["roundedoffvalue"] = "%.2f" % float(
                round(drcrrow["totreduct"])
            )
            # reference is a dictionary which contains reference number as key and reference date as value.
            # if reference field is not None then send refernce dictionary.
            if drcrrow["reference"] == None:
                drcrdata["reference"] = ""
            else:
                drcrrow["reference"]["dcdate"] = datetime.strftime(
                    datetime.strptime(
                        drcrrow["reference"]["dcdate"], "%Y-%m-%d"
                    ).date(),
                    "%d-%m-%Y",
                )
                drcrdata["reference"] = drcrrow["reference"]
            # taken data of invoice on the basis of invid.
            invresult = con.execute(
                select([invoice]).where(invoice.c.invid == drcrrow["invid"])
            )
            invrow = invresult.fetchone()
            invdata = {
                "invid": invrow["invid"],
                "invoiceno": invrow["invoiceno"],
                "invoicedate": datetime.strftime(invrow["invoicedate"], "%d-%m-%Y"),
                "inoutflag": invrow["inoutflag"],
                "taxflag": invrow["taxflag"],
                "tax": invrow["tax"],
                "orgstategstin": invrow["orgstategstin"],
                "icflag": invrow["icflag"],
            }
            drcrdata["contents"] = invrow["contents"]
            contentsData = invrow["contents"]
            if invrow["sourcestate"]:
                invdata["sourcestate"] = invrow["sourcestate"]
                sourceStateCode = getStateCode(invrow["sourcestate"], con)[
                    "statecode"
                ]
                invdata["sourcestatecode"] = sourceStateCode
            if invrow["taxstate"]:
                invdata["taxstate"] = invrow["taxstate"]
                taxStateCode = getStateCode(invrow["taxstate"], con)[
                    "statecode"
                ]
                invdata["taxstatecode"] = taxStateCode
            # taken data of customerandsupplier on the basis of custid
            custresult = con.execute(
                select(
                    [
                        customerandsupplier.c.custid,
                        customerandsupplier.c.custname,
                        customerandsupplier.c.custaddr,
                        customerandsupplier.c.gstin,
                        customerandsupplier.c.custtan,
                        customerandsupplier.c.csflag,
                        customerandsupplier.c.pincode,
                    ]
                ).where(customerandsupplier.c.custid == invrow["custid"])
            )
            custrow = custresult.fetchone()
            custSupDetails = {
                "custid": custrow["custid"],
                "custname": custrow["custname"],
                "custaddr": custrow["custaddr"],
                "gstin": custrow["gstin"],
                "custtin": custrow["custtan"],
                "pincode": custrow["pincode"],
            }
            # tin and gstin checked.
            if custSupDetails["custtin"] != None:
                custSupDetails["custtin"] = custSupDetails["custtin"]
            if custSupDetails["gstin"] != None:
                if int(custrow["csflag"]) == 3:
                    try:
                        custSupDetails["custgstin"] = custrow["gstin"][
                            str(taxStateCode)
                        ]
                    except:
                        custSupDetails["custgstin"] = None
                else:
                    try:
                        custSupDetails["custgstin"] = custrow["gstin"][
                            str(sourceStateCode)
                        ]
                    except:
                        custSupDetails["custgstin"] = None
            drcrdata["custSupDetails"] = custSupDetails

            # all data checked using inout flag,
            if int(invrow["inoutflag"]) == 15:
                # if inoutflag=15 then issuername and designation is same as invoice details
                invdata["issuername"] = invrow["issuername"]
                invdata["designation"] = invrow["designation"]
            elif int(invrow["inoutflag"]) == 9:
                # if inoutflag=9 then issuername and designation is taken from login details.
                # user deatils
                userrow = con.execute(
                    text("select username, orgs->':orgcode'->'userrole' as userrole from gkusers where userid = :userid"),
                    orgcode = authDetails["orgcode"],
                    userid = drcrrow["userid"],
                ).fetchone()
                userdata = {
                    "userid": drcrrow["userid"],
                    "username": userrow["username"],
                    "userrole": userrow["userrole"],
                }
                invdata["issuername"] = userrow["username"]
                invdata["designation"] = userrow["userrole"]

            # calculations
            # contents is a nested dictionary from drcr table.
            # It contains productcode as the key with a value as a dictionary.
            # this dictionary has two key value pair, priceperunit and quantity.
            idrateData = drcrrow["reductionval"]
            # drcrdata is the final dictionary which will not just have the dataset from original contents,
            # but also productdesc,unitname,taxname,taxrate,amount and taxamount
            # invdata containing invoice details.
            drcrContents = {}
            idrate = {}
            # get the dictionary of discount and access it inside the loop for one product each.
            totalTaxableVal = 0.00
            totalTaxAmt = 0.00
            totalCessAmt = 0.00

            # pc will have the productcode which will be the key in contentsData.
            for pc in list(idrateData.keys()):
                if str(pc) != "quantities":
                    pcquantity = 0.00
                    if drcrrow["drcrmode"] and int(drcrrow["drcrmode"]) == 18:
                        pcquantity = (
                            idrateData["quantities"][pc]
                            if "quantities" in idrateData
                            else 0
                        )
                    else:
                        pcquantity = float(
                            contentsData[pc][list(contentsData[pc].keys())[0]]
                        )
                    prodresult = con.execute(
                        select(
                            [
                                product.c.productdesc,
                                product.c.uomid,
                                product.c.gsflag,
                                product.c.gscode,
                            ]
                        ).where(product.c.productcode == pc)
                    )
                    prodrow = prodresult.fetchone()
                    # product or service check and taxableAmount calculate=newppu*newqty
                    taxRate = 0.00
                    totalAmount = 0.00
                    taxRate = float(invrow["tax"][pc])
                    if int(invrow["taxflag"]) == 22:
                        umresult = con.execute(
                            select([unitofmeasurement.c.unitname]).where(
                                unitofmeasurement.c.uomid == int(prodrow["uomid"])
                            )
                        )
                        umrow = umresult.fetchone()
                        unitofMeasurement = umrow["unitname"]
                        if drcrrow["drcrmode"] and int(drcrrow["drcrmode"]) == 18:
                            reductprice = float(idrateData[pc]) * float(idrateData["quantities"][pc])
                        else:
                            reductprice = (
                                float(
                                    contentsData[pc][
                                        list(contentsData[pc].keys())[0]
                                    ]
                                )
                            ) * (float(idrateData[pc]))
                        taxRate = float(invrow["tax"][pc])
                        taxAmount = reductprice * float(taxRate / 100)
                        taxname = "VAT"
                        totalAmount = reductprice + taxAmount
                        totalTaxableVal = totalTaxableVal + reductprice
                        totalTaxAmt = totalTaxAmt + taxAmount
                        drcrContents[pc] = {
                            "proddesc": prodrow["productdesc"],
                            "gscode": prodrow["gscode"],
                            "uom": unitofMeasurement,
                            "qty": "%.2f" % float(pcquantity),
                            "priceperunit": "%.2f"
                            % (float(list(contentsData[pc].keys())[0])),
                            "totalAmount": "%.2f" % (float(totalAmount)),
                            "taxname": "VAT",
                            "taxrate": "%.2f" % (float(taxRate)),
                            "taxamount": "%.2f" % (float(taxAmount)),
                            "newtaxableamnt": "%.2f" % (float(reductprice)),
                            "reductionval": "%.2f" % float(idrateData[pc]),
                        }
                    else:
                        if int(prodrow["gsflag"]) == 7:
                            umresult = con.execute(
                                select([unitofmeasurement.c.unitname]).where(
                                    unitofmeasurement.c.uomid
                                    == int(prodrow["uomid"])
                                )
                            )
                            umrow = umresult.fetchone()
                            unitofMeasurement = umrow["unitname"]
                            if (
                                drcrrow["drcrmode"]
                                and int(drcrrow["drcrmode"]) == 18
                            ):
                                reductprice = (
                                    float(
                                       drcrdata["reduct"][pc]
                                    )
                                ) * (float(idrateData["quantities"][pc]))
                            else:
                                reductprice = (
                                    float(
                                        contentsData[pc][
                                            list(contentsData[pc].keys())[0]
                                        ]
                                    )
                                ) * (float(idrateData[pc]))
                        else:
                            unitofMeasurement = ""
                            reductprice = float(idrateData[pc])
                        cessRate = 0.00
                        cessAmount = 0.00
                        cessVal = 0.00
                        taxname = ""
                        if invrow["cess"]:
                            cessVal = float(invrow["cess"][pc])
                            cessAmount = reductprice * (cessVal / 100)
                            totalCessAmt = totalCessAmt + cessAmount
                        goid_result = con.execute(
                                select([stock.c.goid]).where(
                                    and_(
                                        stock.c.productcode == pc,
                                        stock.c.orgcode == authDetails["orgcode"],
                                    )
                                )
                            )

                        goid = goid_result.scalar()
                        if invrow["sourcestate"] != invrow["taxstate"]:
                            taxname = "IGST"
                            taxAmount = reductprice * (taxRate / 100)
                            totalAmount = reductprice + taxAmount + cessAmount
                        else:
                            taxname = "SGST"
                            # SGST and CGST rates are equal and exactly half the IGST rate.
                            taxAmount = reductprice * (taxRate / 200)
                            totalAmount = reductprice + (2 * taxAmount) + cessAmount
                        totalTaxableVal = totalTaxableVal + reductprice
                        totalTaxAmt = totalTaxAmt + taxAmount
                        drcrContents[pc] = {
                            "proddesc": prodrow["productdesc"],
                            "gscode": prodrow["gscode"],
                            "uom": unitofMeasurement,
                            "qty": "%.2f" % float(pcquantity),
                            "priceperunit": "%.2f"
                            % (float(list(contentsData[pc].keys())[0])),
                            "totalAmount": "%.2f" % (float(totalAmount)),
                            "taxname": taxname,
                            "taxrate": "%.2f" % (float(taxRate)),
                            "taxamount": "%.2f" % (float(taxAmount)),
                            "cess": "%.2f" % (float(cessAmount)),
                            "cessrate": "%.2f" % (float(cessVal)),
                            "newtaxableamnt": "%.2f" % (float(reductprice)),
                            "reductionval": "%.2f" % float(idrateData[pc]),
                            "gsflag": prodrow["gsflag"],
                            "goid": goid,
                        }
            drcrdata["totaltaxablevalue"] = "%.2f" % (float(totalTaxableVal))
            drcrdata["totaltaxamt"] = "%.2f" % (float(totalTaxAmt))
            drcrdata["totalcessamt"] = "%.2f" % (float(totalCessAmt))
            drcrdata["taxname"] = taxname
            drcrdata["drcrcontents"] = drcrContents
            drcrdata["invdata"] = invdata
            # Flag sent to indicate whether goods returned where of badquality.
            drcrGetSingleStockResult = con.execute(
                "select count(stock.dcinvtnflag) as drcrcount from stock where stock.dcinvtnflag = 2 and stock.dcinvtnid = %d and orgcode = %d"
                % (int(self.request.params["drcrid"]), int(authDetails["orgcode"]))
            ).fetchone()
            if int(drcrGetSingleStockResult["drcrcount"]) == 0:
                drcrdata["badquality"] = 0
            else:
                drcrdata["badquality"] = 1
            immutable_data = con.execute(
                select([transaction.c.transaction_details])
                .where(transaction.c.transaction_id == invrow["immutable_data_id"])
            ).scalar()
            drcrdata["immutable_data"] = immutable_data
            return {"gkstatus": gkcore.enumdict["Success"], "gkresult": drcrdata}

    @view_config(request_method="GET", request_param="drcr=all", renderer="json")
    def getAlldrcr(self):
        try:
            token = self.request.headers["gktoken"]
        except:
            return {"gkstatus": gkcore.enumdict["UnauthorisedAccess"]}
        authDetails = authCheck(token)
        if authDetails["auth"] == False:
            return {"gkstatus": gkcore.enumdict["UnauthorisedAccess"]}
        with eng.connect() as con:
            # inoutflag query param is used to filter entries by sales and purchases
            # 9 -> purchase, 15 -> sales, 0 -> all.
            inoutflag = [self.request.params.get("inoutflag")]
            if (
                    self.request.params.get("inoutflag") == "0"
                    or not self.request.params.get("inoutflag")
            ):
                inoutflag = ["9", "15"]
            result = con.execute(
                select(
                    [
                        drcr.c.drcrno,
                        drcr.c.drcrid,
                        drcr.c.drcrdate,
                        drcr.c.invid,
                        drcr.c.dctypeflag,
                        drcr.c.totreduct,
                        drcr.c.attachmentcount,
                    ]
                )
                .where(drcr.c.orgcode == authDetails["orgcode"])
                .order_by(drcr.c.drcrdate)
            ).fetchall()
            drcrdata = []
            for row in result:
                # invoice,cust
                inv = con.execute(
                    select([invoice.c.custid, invoice.c.immutable_data_id]).where(and_(
                        invoice.c.invid == row["invid"],
                        invoice.c.inoutflag.in_(inoutflag)
                    ))
                )
                invdata = inv.fetchone()
                if not invdata:
                    continue
                custsupp = con.execute(
                    select(
                        [
                            customerandsupplier.c.custname,
                            customerandsupplier.c.csflag,
                        ]
                    ).where(customerandsupplier.c.custid == invdata["custid"])
                )
                custsuppdata = custsupp.fetchone()
                immutable_data = con.execute(
                    select([transaction.c.transaction_details])
                    .where(transaction.c.transaction_id == invdata["immutable_data_id"])
                ).scalar()
                rowdata = {
                    "drcrid": row["drcrid"],
                    "drcrno": row["drcrno"],
                    "drcrdate": datetime.strftime(
                        row["drcrdate"], "%d-%m-%Y"
                        ),
                    "dctypeflag": row["dctypeflag"],
                    "totreduct": "%.2f" % float(row["totreduct"]),
                    "invid": row["invid"],
                    "attachmentcount": row["attachmentcount"],
                    "immutable_data": immutable_data,
                    "custid": invdata["custid"],
                    "custname": custsuppdata["custname"],
                    "csflag": custsuppdata["csflag"],
                }
                if "drcrflag" in self.request.params:
                    if int(self.request.params["drcrflag"]) == int(
                        row["dctypeflag"]
                    ):
                        drcrdata.append(rowdata)
                else:
                    drcrdata.append(rowdata)
            return {"gkstatus": gkcore.enumdict["Success"], "gkresult": drcrdata}

    """
    Deleteing drcr on the basis of reference field and drcrid
    if credit/debit note number is not used as reference then it can be deleted.
    """

    @view_config(request_method="DELETE")
    def deletedrcr(self):
        try:
            token = self.request.headers["gktoken"]
        except:
            return {"gkstatus": enumdict["UnauthorisedAccess"]}
        authDetails = authCheck(token)
        if authDetails["auth"] == False:
            return {"gkstatus": enumdict["UnauthorisedAccess"]}
        with eng.begin() as con:
            dataset = self.request.json_body
            result = con.execute(
                select([drcr.c.drcrid, drcr.c.reference]).where(
                    drcr.c.drcrid == dataset["drcrid"]
                )
            )
            row = result.fetchone()
            if not row["reference"]:
                con.execute(
                    vouchers.delete().where(vouchers.c.drcrid == dataset["drcrid"])
                )
                con.execute(
                    drcr.delete().where(drcr.c.drcrid == dataset["drcrid"])
                )
                return {"gkstatus": enumdict["Success"]}
            return {"gkstatus": enumdict["ActionDisallowed"]}

    @view_config(request_method="GET", request_param="attach=image", renderer="json")
    def getattachment(self):
        try:
            token = self.request.headers["gktoken"]
        except:
            return {"gkstatus": enumdict["UnauthorisedAccess"]}
        authDetails = authCheck(token)
        if authDetails["auth"] == False:
            return {"gkstatus": enumdict["UnauthorisedAccess"]}
        with eng.connect() as con:
            ur = getUserRole(authDetails["userid"], authDetails["orgcode"])
            urole = ur["gkresult"]
            drcrid = self.request.params["drcrid"]
            drcrData = con.execute(
                select([drcr.c.drcrno, drcr.c.attachment]).where(
                    drcr.c.drcrid == drcrid
                )
            )
            attachment = drcrData.fetchone()
            return {
                "gkstatus": enumdict["Success"],
                "gkresult": attachment["attachment"],
                "drcrno": attachment["drcrno"],
                "userrole": urole["userrole"],
            }

    """This is a function to update .
    This function is primarily used to enable editing of debit and credit note.
    It receives a dictionary with information regarding debit and credit note
        Update for debit and credit note."""

    @view_config(request_method="PUT", renderer="json")
    def editDrCrNote(self):
        try:
            token = self.request.headers["gktoken"]
        except:
            return {"gkstatus": gkcore.enumdict["UnauthorisedAccess"]}
        authDetails = authCheck(token)
        if authDetails["auth"] == False:
            return {"gkstatus": enumdict["UnauthorisedAccess"]}
        with eng.begin() as con:
            dataset = self.request.json_body
            result = con.execute(
                drcr.update()
                .where(drcr.c.drcrid == dataset["drcrid"])
                .values(dataset)
            )
            return {"gkstatus": enumdict["Success"]}

    @view_config(request_method="GET", request_param="inv=all", renderer="json")
    def getAllinvoices(self):
        try:
            token = self.request.headers["gktoken"]
        except:
            return {"gkstatus": gkcore.enumdict["UnauthorisedAccess"]}
        authDetails = authCheck(token)
        if authDetails["auth"] == False:
            return {"gkstatus": gkcore.enumdict["UnauthorisedAccess"]}
        with eng.connect() as con:
            drcrflag = int(self.request.params["drcrflag"])
            DrCrInvs = []
            invsInDrCr = con.execute(
                select([drcr.c.invid]).where(
                    and_(
                        drcr.c.orgcode == authDetails["orgcode"],
                        drcr.c.dctypeflag == drcrflag,
                    )
                )
            )
            invData = con.execute(
                select(
                    [
                        invoice.c.invoiceno,
                        invoice.c.invid,
                        invoice.c.invoicedate,
                        invoice.c.custid,
                        invoice.c.inoutflag,
                        invoice.c.invoicetotal,
                        invoice.c.attachmentcount,
                    ]
                )
                .where(
                    and_(
                        invoice.c.orgcode == authDetails["orgcode"],
                    )
                )
                .order_by(invoice.c.invoicedate)
            )
            lastdrcrno = con.execute(
                "select drcrno from drcr where drcrid = (select max(drcrid) from drcr where orgcode=%d and dctypeflag=%d)"
                % (int(authDetails["orgcode"]), int(drcrflag))
            )
            lastdrcrno = lastdrcrno.fetchone()
            if lastdrcrno == None:
                lastdrcrno = ""
            else:
                lastdrcrno = lastdrcrno[0]
            for DrCrInv in invsInDrCr:
                DrCrInvs.append(DrCrInv["invid"])
            invoices = []
            for row in invData:
                if row["invid"] not in DrCrInvs:
                    customer = con.execute(
                        select(
                            [
                                customerandsupplier.c.custname,
                                customerandsupplier.c.csflag,
                            ]
                        ).where(customerandsupplier.c.custid == row["custid"])
                    )
                    custname = customer.fetchone()
                    rowdata = {
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
                    if "type" in self.request.params:
                        if (
                            str(self.request.params["type"]) == "sale"
                            and row["inoutflag"] == 15
                        ):
                            invoices.append(rowdata)
                        elif (
                            str(self.request.params["type"]) == "purchase"
                            and row["inoutflag"] == 9
                        ):
                            invoices.append(rowdata)
                    else:
                        invoices.append(rowdata)
            return {
                "gkstatus": gkcore.enumdict["Success"],
                "gkresult": invoices,
                "lastdrcrno": lastdrcrno,
            }


def drcrVoucher(con, queryParams, orgcode):
    """
    This function creates voucher for Debit and Credit Notes.

    When a Debit Note or Credit Note is created corresponding voucher must also be created.
    GNUKhata has vouchers of types Debit Note and Credit Note. The choice of accounts for
    creating these vouchers depends on the purpose for which a Debit  or a Credit Note is
    created. This could be either change in the amount to be paid or recived or a change in
    the quantity of products.

    When there is change in price, Discount Paid/Discount Received accounts, Party's account and
    accounts of taxes are used to create vouchers. When there is change in quantity, corresponding
    Sale/Purchase accounts, Party's Account, and accounts of taxes are used. The name of these
    accounts are found out using information from queryParams variable passed to this function.
    Then, corresponding account codes are found out and a dictionary is created with crs, drs,
    type of voucher, narration and id of Debit/Credit Note. This dictionary is used to create a
    Debit or Credit Note Voucher.
    """
    # taxRateDict = {5: 2.5, 12: 6, 18: 9, 28: 14}
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
    voucherDict = {}
    vouchersList = []
    vchCodes = []
    taxDict = {}
    crs = {}
    drs = {}
    rdcrs = {}
    rddrs = {}
    taxAmount = 0.00
    cessAmount = 0.00
    cgstAmount = 0.00
    sgstAmount = 0.00
    totalTaxableVal = "%.2f" % float(queryParams["totaltaxable"])

    if (queryParams["custname"]):
        partyaccount = con.execute(
            select([accounts.c.accountcode]).where(
                and_(
                    accounts.c.accountname == queryParams["custname"],
                    accounts.c.orgcode == orgcode,
                )
            )
        )
        partyaccountcode = partyaccount.fetchone()
        if int(queryParams["drcrmode"]) == 4:
            discountpaidaccount = con.execute(
                select([accounts.c.accountcode]).where(
                    and_(
                        accounts.c.accountname == "Discount Paid",
                        accounts.c.orgcode == orgcode,
                    )
                )
            )
            discountpaidaccountcode = discountpaidaccount.fetchone()
            discountreceivedaccount = con.execute(
                select([accounts.c.accountcode]).where(
                    and_(
                        accounts.c.accountname == "Discount Received",
                        accounts.c.orgcode == orgcode,
                    )
                )
            )
            discountreceivedaccountcode = discountreceivedaccount.fetchone()
            if (
                int(queryParams["dctypeflag"]) == 3
                and int(queryParams["inoutflag"]) == 15
            ):
                crs[partyaccountcode["accountcode"]] = queryParams["totreduct"]
                drs[discountpaidaccountcode["accountcode"]] = totalTaxableVal
                if int(queryParams["taxflag"]) == 7 and queryParams.get("taxstate"):
                    abv = con.execute(
                        select([state.c.abbreviation]).where(
                            state.c.statename == queryParams["taxstate"]
                        )
                    )
                    abb = abv.fetchone()
                    taxName = queryParams["taxname"]
                    if taxName == "SGST":
                        for prod in queryParams["prodData"]:
                            taxRate = float(queryParams["taxes"][prod])
                            taxable = float(queryParams["reductionval"][prod])
                            if taxRate > 0.00:
                                tx = float(taxRate) / 2
                                taxHalf = taxRateDict[float(taxRate)]
                                # this is the value which is going to Dr/Cr
                                taxVal = taxable * (tx / 100) * float(queryParams["reductionval"]["quantities"][prod])
                                taxNameSGST = (
                                    "SGSTOUT_"
                                    + str(abb["abbreviation"])
                                    + "@"
                                    + str(taxHalf)
                                    + "%"
                                )
                                taxNameCGST = (
                                    "CGSTOUT_"
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
                            taxable = float(queryParams["reductionval"][prod])
                            if taxRate > 0.00:
                                tx = float(taxRate)
                                # this is the value which is going to Dr/Cr
                                taxVal = taxable * (tx / 100) * float(queryParams["reductionval"]["quantities"][prod])
                                taxNameIGST = (
                                    "IGSTOUT_"
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
                                "CESSOUT_"
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
                        drs[taxRow["accountcode"]] = "%.2f" % float(taxDict[Tax])
                else:
                    vatoutaccount = con.execute(
                        select([accounts.c.accountcode]).where(
                            and_(
                                accounts.c.accountname == "VAT_OUT",
                                accounts.c.orgcode == orgcode,
                            )
                        )
                    )
                    vatoutaccountcode = vatoutaccount.fetchone()
                    for prod in queryParams["taxes"]:
                        taxAmount = taxAmount + float(queryParams["reductionval"][prod]) * (
                            float(queryParams["taxes"][prod]) / 100
                        ) * float(queryParams["reductionval"]["quantities"][prod])
                    drs[vatoutaccountcode["accountcode"]] = "%.2f" % float(taxAmount)

                Narration = (
                    "Paid Rupees "
                    + "%.2f" % float(queryParams["totreduct"])
                    + " to "
                    + str(queryParams["custname"])
                    + " ref Credit Note No. "
                    + str(queryParams["drcrno"])
                )

                voucherDict = {
                    "drs": drs,
                    "crs": crs,
                    "voucherdate": queryParams["drcrdate"],
                    "narration": Narration,
                    "vouchertype": "creditnote",
                    "drcrid": queryParams["drcrid"],
                }
                vouchersList.append(voucherDict)

                # check whether amount paid is rounded off
                if "roundoffamt" in queryParams:
                    if float(queryParams["roundoffamt"]) < 0.00:
                        # user has spent rounded of amount
                        roundAcc = con.execute(
                            select([accounts.c.accountcode]).where(
                                and_(
                                    accounts.c.defaultflag == 180,
                                    accounts.c.orgcode == orgcode,
                                )
                            )
                        )
                        roundRow = roundAcc.fetchone()

                        try:
                            accCode = roundRow["accountcode"]
                        except:
                            a = createAccount(con, 18, "Round Off Paid", orgcode)
                            accCode = a["accountcode"]

                        rddrs[accCode] = "%.2f" % float(abs(queryParams["roundoffamt"]))
                        rdcrs[partyaccountcode["accountcode"]] = "%.2f" % float(
                            abs(queryParams["roundoffamt"])
                        )
                        rd_VoucherDict = {
                            "drs": rddrs,
                            "crs": rdcrs,
                            "voucherdate": queryParams["drcrdate"],
                            "narration": "Round off amount %.2f spent"
                            % float(abs(queryParams["roundoffamt"])),
                            "vouchertype": "journal",
                            "drcrid": queryParams["drcrid"],
                        }
                        vouchersList.append(rd_VoucherDict)

                    if float(queryParams["roundoffamt"]) > 0.00:
                        # user has earned rounded of amount
                        roundAcc = con.execute(
                            select([accounts.c.accountcode]).where(
                                and_(
                                    accounts.c.defaultflag == 181,
                                    accounts.c.orgcode == orgcode,
                                )
                            )
                        )
                        roundRow = roundAcc.fetchone()

                        try:
                            accCode = roundRow["accountcode"]
                        except:
                            a = createAccount(con, 18, "Round Off Received", orgcode)
                            accCode = a["accountcode"]

                        rdcrs[accCode] = "%.2f" % float(queryParams["roundoffamt"])
                        rddrs[partyaccountcode["accountcode"]] = "%.2f" % float(
                            queryParams["roundoffamt"]
                        )

                        rd_VoucherDict = {
                            "drs": rddrs,
                            "crs": rdcrs,
                            "voucherdate": queryParams["drcrdate"],
                            "narration": "Round off amount %.2f earned"
                            % float(queryParams["roundoffamt"]),
                            "vouchertype": "journal",
                            "drcrid": queryParams["drcrid"],
                        }
                        vouchersList.append(rd_VoucherDict)

            elif (
                int(queryParams["dctypeflag"]) == 3
                and int(queryParams["inoutflag"]) == 9
            ):
                crs[partyaccountcode["accountcode"]] = queryParams["totreduct"]
                drs[discountpaidaccountcode["accountcode"]] = totalTaxableVal
                if int(queryParams["taxflag"]) == 7 and queryParams.get("taxstate"):
                    abv = con.execute(
                        select([state.c.abbreviation]).where(
                            state.c.statename == queryParams["taxstate"]
                        )
                    )
                    abb = abv.fetchone()
                    taxName = queryParams["taxname"]
                    if taxName == "SGST":
                        for prod in queryParams["prodData"]:
                            taxRate = float(queryParams["taxes"][prod])
                            taxable = float(queryParams["reductionval"][prod])
                            if taxRate > 0.00:
                                taxHalf = taxRateDict[float(taxRate)]
                                tx = float(taxRate) / 2
                                # this is the value which is going to Dr/Cr
                                taxVal = taxable * (tx / 100) * float(queryParams["reductionval"]["quantities"][prod])
                                taxNameSGST = (
                                    "SGSTIN_"
                                    + str(abb["abbreviation"])
                                    + "@"
                                    + str(taxHalf)
                                    + "%"
                                )
                                taxNameCGST = (
                                    "CGSTIN_"
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
                            taxable = float(queryParams["reductionval"][prod])
                            if taxRate > 0.00:
                                tx = float(taxRate)
                                # this is the value which is going to Dr/Cr
                                taxVal = taxable * (tx / 100) * float(queryParams["reductionval"]["quantities"][prod])
                                taxNameIGST = (
                                    "IGSTIN_"
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
                                "CESSIN_"
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
                        drs[taxRow["accountcode"]] = "%.2f" % float(taxDict[Tax])
                else:
                    vatoutaccount = con.execute(
                        select([accounts.c.accountcode]).where(
                            and_(
                                accounts.c.accountname == "VAT_IN",
                                accounts.c.orgcode == orgcode,
                            )
                        )
                    )
                    vatoutaccountcode = vatoutaccount.fetchone()
                    for prod in queryParams["taxes"]:
                        taxAmount = taxAmount + float(queryParams["reductionval"][prod]) * (
                            float(queryParams["taxes"][prod]) / 100
                        ) * float(queryParams["reductionval"]["quantities"][prod])
                    drs[vatoutaccountcode["accountcode"]] = "%.2f" % float(taxAmount)

                Narration = (
                    "Paid Rupees "
                    + "%.2f" % float(queryParams["totreduct"])
                    + " to "
                    + str(queryParams["custname"])
                    + " ref Credit Note No. "
                    + str(queryParams["drcrno"])
                )

                voucherDict = {
                    "drs": drs,
                    "crs": crs,
                    "voucherdate": queryParams["drcrdate"],
                    "narration": Narration,
                    "vouchertype": "creditnote",
                    "drcrid": queryParams["drcrid"],
                }
                vouchersList.append(voucherDict)

                # check whether amount paid is rounded off
                if "roundoffamt" in queryParams:
                    if float(queryParams["roundoffamt"]) < 0.00:
                        # user has spent rounded of amount
                        roundAcc = con.execute(
                            select([accounts.c.accountcode]).where(
                                and_(
                                    accounts.c.defaultflag == 180,
                                    accounts.c.orgcode == orgcode,
                                )
                            )
                        )
                        roundRow = roundAcc.fetchone()

                        try:
                            accCode = roundRow["accountcode"]
                        except:
                            a = createAccount(con, 18, "Round Off Paid", orgcode)
                            accCode = a["accountcode"]

                        rddrs[accCode] = "%.2f" % float(abs(queryParams["roundoffamt"]))
                        rdcrs[partyaccountcode["accountcode"]] = "%.2f" % float(
                            abs(queryParams["roundoffamt"])
                        )
                        rd_VoucherDict = {
                            "drs": rddrs,
                            "crs": rdcrs,
                            "voucherdate": queryParams["drcrdate"],
                            "narration": "Round off amount %.2f spent"
                            % float(abs(queryParams["roundoffamt"])),
                            "vouchertype": "journal",
                            "drcrid": queryParams["drcrid"],
                        }
                        vouchersList.append(rd_VoucherDict)

                    if float(queryParams["roundoffamt"]) > 0.00:
                        # user has earned rounded of amount
                        roundAcc = con.execute(
                            select([accounts.c.accountcode]).where(
                                and_(
                                    accounts.c.defaultflag == 181,
                                    accounts.c.orgcode == orgcode,
                                )
                            )
                        )
                        roundRow = roundAcc.fetchone()

                        try:
                            accCode = roundRow["accountcode"]
                        except:
                            a = createAccount(con, 18, "Round Off Received", orgcode)
                            accCode = a["accountcode"]

                        rdcrs[accCode] = "%.2f" % float(queryParams["roundoffamt"])
                        rddrs[partyaccountcode["accountcode"]] = "%.2f" % float(
                            queryParams["roundoffamt"]
                        )

                        rd_VoucherDict = {
                            "drs": rddrs,
                            "crs": rdcrs,
                            "voucherdate": queryParams["drcrdate"],
                            "narration": "Round off amount %.2f earned"
                            % float(queryParams["roundoffamt"]),
                            "vouchertype": "journal",
                            "drcrid": queryParams["drcrid"],
                        }
                        vouchersList.append(rd_VoucherDict)

            elif (
                int(queryParams["dctypeflag"]) == 4
                and int(queryParams["inoutflag"]) == 15
            ):
                drs[partyaccountcode["accountcode"]] = queryParams["totreduct"]
                crs[discountreceivedaccountcode["accountcode"]] = totalTaxableVal
                if int(queryParams["taxflag"]) == 7 and queryParams.get("taxstate"):
                    abv = con.execute(
                        select([state.c.abbreviation]).where(
                            state.c.statename == queryParams["taxstate"]
                        )
                    )
                    abb = abv.fetchone()
                    taxName = queryParams["taxname"]
                    if taxName == "SGST":
                        for prod in queryParams["prodData"]:
                            taxRate = float(queryParams["taxes"][prod])
                            taxable = float(queryParams["reductionval"][prod])
                            if taxRate > 0.00:
                                tx = float(taxRate) / 2
                                taxHalf = taxRateDict[float(taxRate)]
                                # this is the value which is going to Dr/Cr
                                taxVal = taxable * (tx / 100) * float(queryParams["reductionval"]["quantities"][prod])
                                taxNameSGST = (
                                    "SGSTOUT_"
                                    + str(abb["abbreviation"])
                                    + "@"
                                    + str(taxHalf)
                                    + "%"
                                )
                                taxNameCGST = (
                                    "CGSTOUT_"
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
                            taxable = float(queryParams["reductionval"][prod])
                            if taxRate > 0.00:
                                tx = float(taxRate)
                                # this is the value which is going to Dr/Cr
                                taxVal = taxable * (tx / 100) * float(queryParams["reductionval"]["quantities"][prod])
                                taxNameIGST = (
                                    "IGSTOUT_"
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
                                "CESSOUT_"
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
                        crs[taxRow["accountcode"]] = "%.2f" % float(taxDict[Tax])
                else:
                    vatoutaccount = con.execute(
                        select([accounts.c.accountcode]).where(
                            and_(
                                accounts.c.accountname == "VAT_OUT",
                                accounts.c.orgcode == orgcode,
                            )
                        )
                    )
                    vatoutaccountcode = vatoutaccount.fetchone()
                    for prod in queryParams["taxes"]:
                        taxAmount = taxAmount + float(queryParams["reductionval"][prod]) * (
                            float(queryParams["taxes"][prod]) / 100
                        ) * float(queryParams["reductionval"]["quantities"][prod])
                    crs[vatoutaccountcode["accountcode"]] = "%.2f" % float(taxAmount)

                Narration = (
                    "Received Rupees "
                    + "%.2f" % float(queryParams["totreduct"])
                    + " to "
                    + str(queryParams["custname"])
                    + " ref Debit Note No. "
                    + str(queryParams["drcrno"])
                )

                voucherDict = {
                    "drs": drs,
                    "crs": crs,
                    "voucherdate": queryParams["drcrdate"],
                    "narration": Narration,
                    "vouchertype": "debitnote",
                    "drcrid": queryParams["drcrid"],
                }
                vouchersList.append(voucherDict)

                # check whether amount paid is rounded off
                if "roundoffamt" in queryParams:
                    if float(queryParams["roundoffamt"]) > 0.00:
                        # user has spent rounded of amount
                        roundAcc = con.execute(
                            select([accounts.c.accountcode]).where(
                                and_(
                                    accounts.c.defaultflag == 180,
                                    accounts.c.orgcode == orgcode,
                                )
                            )
                        )
                        roundRow = roundAcc.fetchone()

                        try:
                            accCode = roundRow["accountcode"]
                        except:
                            a = createAccount(con, 18, "Round Off Paid", orgcode)
                            accCode = a["accountcode"]

                        rddrs[accCode] = "%.2f" % float(queryParams["roundoffamt"])
                        rdcrs[partyaccountcode["accountcode"]] = "%.2f" % float(
                            queryParams["roundoffamt"]
                        )
                        rd_VoucherDict = {
                            "drs": rddrs,
                            "crs": rdcrs,
                            "voucherdate": queryParams["drcrdate"],
                            "narration": "Round off amount %.2f spent"
                            % float(queryParams["roundoffamt"]),
                            "vouchertype": "journal",
                            "drcrid": queryParams["drcrid"],
                        }
                        vouchersList.append(rd_VoucherDict)

                    if float(queryParams["roundoffamt"]) < 0.00:
                        # user has earned rounded of amount
                        roundAcc = con.execute(
                            select([accounts.c.accountcode]).where(
                                and_(
                                    accounts.c.defaultflag == 181,
                                    accounts.c.orgcode == orgcode,
                                )
                            )
                        )
                        roundRow = roundAcc.fetchone()

                        try:
                            accCode = roundRow["accountcode"]
                        except:
                            a = createAccount(con, 18, "Round Off Received", orgcode)
                            accCode = a["accountcode"]

                        rdcrs[accCode] = "%.2f" % float(abs(queryParams["roundoffamt"]))
                        rddrs[partyaccountcode["accountcode"]] = "%.2f" % float(
                            abs(queryParams["roundoffamt"])
                        )

                        rd_VoucherDict = {
                            "drs": rddrs,
                            "crs": rdcrs,
                            "voucherdate": queryParams["drcrdate"],
                            "narration": "Round off amount %.2f earned"
                            % float(abs(queryParams["roundoffamt"])),
                            "vouchertype": "journal",
                            "drcrid": queryParams["drcrid"],
                        }
                        vouchersList.append(rd_VoucherDict)

            elif (
                int(queryParams["dctypeflag"]) == 4
                and int(queryParams["inoutflag"]) == 9
            ):
                drs[partyaccountcode["accountcode"]] = queryParams["totreduct"]
                crs[discountreceivedaccountcode["accountcode"]] = totalTaxableVal
                if int(queryParams["taxflag"]) == 7 and queryParams.get("taxstate"):
                    abv = con.execute(
                        select([state.c.abbreviation]).where(
                            state.c.statename == queryParams["taxstate"]
                        )
                    )
                    abb = abv.fetchone()
                    taxName = queryParams["taxname"]
                    if taxName == "SGST":
                        for prod in queryParams["prodData"]:
                            taxRate = float(queryParams["taxes"][prod])
                            taxable = float(queryParams["reductionval"][prod])
                            if taxRate > 0.00:
                                tx = float(taxRate) / 2
                                taxHalf = taxRateDict[float(taxRate)]
                                # this is the value which is going to Dr/Cr
                                taxVal = taxable * (tx / 100) * float(queryParams["reductionval"]["quantities"][prod])
                                taxNameSGST = (
                                    "SGSTIN_"
                                    + str(abb["abbreviation"])
                                    + "@"
                                    + str(taxHalf)
                                    + "%"
                                )
                                taxNameCGST = (
                                    "CGSTIN_"
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
                            taxable = float(queryParams["reductionval"][prod])
                            if taxRate > 0.00:
                                tx = float(taxRate)
                                # this is the value which is going to Dr/Cr
                                taxVal = taxable * (tx / 100) * float(queryParams["reductionval"]["quantities"][prod])
                                taxNameIGST = (
                                    "IGSTIN_"
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
                                "CESSIN_"
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
                        crs[taxRow["accountcode"]] = "%.2f" % float(taxDict[Tax])
                else:
                    vatoutaccount = con.execute(
                        select([accounts.c.accountcode]).where(
                            and_(
                                accounts.c.accountname == "VAT_IN",
                                accounts.c.orgcode == orgcode,
                            )
                        )
                    )
                    vatoutaccountcode = vatoutaccount.fetchone()
                    for prod in queryParams["taxes"]:
                        taxAmount = taxAmount + float(queryParams["reductionval"][prod]) * (
                            float(queryParams["taxes"][prod]) / 100
                        ) * float(queryParams["reductionval"]["quantities"][prod])
                    crs[vatoutaccountcode["accountcode"]] = "%.2f" % float(taxAmount)

                Narration = (
                    "Paid Rupees "
                    + "%.2f" % float(queryParams["totreduct"])
                    + " to "
                    + str(queryParams["custname"])
                    + " ref Debit Note No. "
                    + str(queryParams["drcrno"])
                )

                voucherDict = {
                    "drs": drs,
                    "crs": crs,
                    "voucherdate": queryParams["drcrdate"],
                    "narration": Narration,
                    "vouchertype": "debitnote",
                    "drcrid": queryParams["drcrid"],
                }
                vouchersList.append(voucherDict)

                # check whether amount paid is rounded off
                if "roundoffamt" in queryParams:
                    if float(queryParams["roundoffamt"]) > 0.00:
                        # user has spent rounded of amount
                        roundAcc = con.execute(
                            select([accounts.c.accountcode]).where(
                                and_(
                                    accounts.c.defaultflag == 180,
                                    accounts.c.orgcode == orgcode,
                                )
                            )
                        )
                        roundRow = roundAcc.fetchone()

                        try:
                            accCode = roundRow["accountcode"]
                        except:
                            a = createAccount(con, 18, "Round Off Paid", orgcode)
                            accCode = a["accountcode"]

                        rddrs[accCode] = "%.2f" % float(queryParams["roundoffamt"])
                        rdcrs[partyaccountcode["accountcode"]] = "%.2f" % float(
                            queryParams["roundoffamt"]
                        )
                        rd_VoucherDict = {
                            "drs": rddrs,
                            "crs": rdcrs,
                            "voucherdate": queryParams["drcrdate"],
                            "narration": "Round off amount %.2f spent"
                            % float(queryParams["roundoffamt"]),
                            "vouchertype": "journal",
                            "drcrid": queryParams["drcrid"],
                        }
                        vouchersList.append(rd_VoucherDict)

                    if float(queryParams["roundoffamt"]) < 0.00:
                        # user has earned rounded of amount
                        roundAcc = con.execute(
                            select([accounts.c.accountcode]).where(
                                and_(
                                    accounts.c.defaultflag == 181,
                                    accounts.c.orgcode == orgcode,
                                )
                            )
                        )
                        roundRow = roundAcc.fetchone()

                        try:
                            accCode = roundRow["accountcode"]
                        except:
                            a = createAccount(con, 18, "Round Off Received", orgcode)
                            accCode = a["accountcode"]

                        rdcrs[accCode] = "%.2f" % float(abs(queryParams["roundoffamt"]))
                        rddrs[partyaccountcode["accountcode"]] = "%.2f" % float(
                            abs(queryParams["roundoffamt"])
                        )

                        rd_VoucherDict = {
                            "drs": rddrs,
                            "crs": rdcrs,
                            "voucherdate": queryParams["drcrdate"],
                            "narration": "Round off amount %.2f earned"
                            % float(abs(queryParams["roundoffamt"])),
                            "vouchertype": "journal",
                            "drcrid": queryParams["drcrid"],
                        }
                        vouchersList.append(rd_VoucherDict)

        elif int(queryParams["drcrmode"]) == 18:
            vchProdAcc = ""
            if (
                int(queryParams["dctypeflag"]) == 3
                and int(queryParams["inoutflag"]) == 15
            ):
                crs[partyaccountcode["accountcode"]] = queryParams["totreduct"]
                if int(queryParams["maflag"]) == 1:
                    prodDataP = queryParams["product"]
                    for prod in prodDataP:
                        proN = str(prod) + " Sale"
                        prodAcc = con.execute(
                            select([accounts.c.accountcode]).where(
                                and_(
                                    accounts.c.accountname == proN,
                                    accounts.c.orgcode == orgcode,
                                )
                            )
                        )
                        prodAccount = prodAcc.fetchone()
                        drs[prodAccount["accountcode"]] = "%.2f" % float(
                            prodDataP[prod]
                        )
                        vchProdAcc = prodAccount["accountcode"]
                else:
                    # if multiple acc is 0 , then select default sale account
                    salesAccount = con.execute(
                        select([accounts.c.accountcode]).where(
                            and_(
                                accounts.c.defaultflag == 19,
                                accounts.c.orgcode == orgcode,
                            )
                        )
                    )
                    saleAcc = salesAccount.fetchone()
                    drs[saleAcc["accountcode"]] = totalTaxableVal
                    vchProdAcc = saleAcc["accountcode"]
                if int(queryParams["taxflag"]) == 7 and queryParams.get("taxstate"):
                    abv = con.execute(
                        select([state.c.abbreviation]).where(
                            state.c.statename == queryParams["taxstate"]
                        )
                    )
                    abb = abv.fetchone()
                    taxName = queryParams["taxname"]
                    if taxName == "SGST":
                        for prod in queryParams["prodData"]:
                            taxRate = float(queryParams["taxes"][prod])
                            taxable = float(queryParams["reductionval"][prod])
                            if taxRate > 0.00:
                                tx = float(taxRate) / 2
                                taxHalf = taxRateDict[float(taxRate)]
                                # this is the value which is going to Dr/Cr
                                taxVal = taxable * (tx / 100) * float(queryParams["reductionval"]["quantities"][prod])
                                taxNameSGST = (
                                    "SGSTOUT_"
                                    + str(abb["abbreviation"])
                                    + "@"
                                    + str(taxHalf)
                                    + "%"
                                )
                                taxNameCGST = (
                                    "CGSTOUT_"
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
                            taxable = float(queryParams["reductionval"][prod])
                            if taxRate > 0.00:
                                tx = float(taxRate)
                                # this is the value which is going to Dr/Cr
                                taxVal = taxable * (tx / 100) * float(queryParams["reductionval"]["quantities"][prod])
                                taxNameIGST = (
                                    "IGSTOUT_"
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
                                "CESSOUT_"
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
                        drs[taxRow["accountcode"]] = "%.2f" % float(taxDict[Tax])
                else:
                    vatoutaccount = con.execute(
                        select([accounts.c.accountcode]).where(
                            and_(
                                accounts.c.accountname == "VAT_OUT",
                                accounts.c.orgcode == orgcode,
                            )
                        )
                    )
                    vatoutaccountcode = vatoutaccount.fetchone()
                    for prod in queryParams["taxes"]:
                        taxAmount = taxAmount + float(queryParams["reductionval"][prod]) * (
                            float(queryParams["taxes"][prod]) / 100
                        ) * float(queryParams["reductionval"]["quantities"][prod])
                    drs[vatoutaccountcode["accountcode"]] = "%.2f" % float(taxAmount)

                Narration = (
                    "Received goods worth Rupees "
                    + "%.2f" % float(queryParams["totreduct"])
                    + " returned by "
                    + str(queryParams["custname"])
                    + " ref Credit Note No. "
                    + str(queryParams["drcrno"])
                )

                voucherDict = {
                    "drs": drs,
                    "crs": crs,
                    "voucherdate": queryParams["drcrdate"],
                    "narration": Narration,
                    "vouchertype": "creditnote",
                    "drcrid": queryParams["drcrid"],
                }
                vouchersList.append(voucherDict)

                # check whether amount paid is rounded off
                if "roundoffamt" in queryParams:
                    if float(queryParams["roundoffamt"]) < 0.00:
                        # user has spent rounded of amount
                        roundAcc = con.execute(
                            select([accounts.c.accountcode]).where(
                                and_(
                                    accounts.c.defaultflag == 180,
                                    accounts.c.orgcode == orgcode,
                                )
                            )
                        )
                        roundRow = roundAcc.fetchone()

                        try:
                            accCode = roundRow["accountcode"]
                        except:
                            a = createAccount(con, 18, "Round Off Paid", orgcode)
                            accCode = a["accountcode"]

                        rddrs[accCode] = "%.2f" % float(abs(queryParams["roundoffamt"]))
                        rdcrs[vchProdAcc] = "%.2f" % float(
                            abs(queryParams["roundoffamt"])
                        )
                        rd_VoucherDict = {
                            "drs": rddrs,
                            "crs": rdcrs,
                            "voucherdate": queryParams["drcrdate"],
                            "narration": "Round off amount %.2f spent"
                            % float(abs(queryParams["roundoffamt"])),
                            "vouchertype": "journal",
                            "drcrid": queryParams["drcrid"],
                        }
                        vouchersList.append(rd_VoucherDict)

                    if float(queryParams["roundoffamt"]) > 0.00:
                        # user has earned rounded of amount
                        roundAcc = con.execute(
                            select([accounts.c.accountcode]).where(
                                and_(
                                    accounts.c.defaultflag == 181,
                                    accounts.c.orgcode == orgcode,
                                )
                            )
                        )
                        roundRow = roundAcc.fetchone()

                        try:
                            accCode = roundRow["accountcode"]
                        except:
                            a = createAccount(con, 18, "Round Off Received", orgcode)
                            accCode = a["accountcode"]

                        rdcrs[accCode] = "%.2f" % float(queryParams["roundoffamt"])
                        rddrs[vchProdAcc] = "%.2f" % float(queryParams["roundoffamt"])

                        rd_VoucherDict = {
                            "drs": rddrs,
                            "crs": rdcrs,
                            "voucherdate": queryParams["drcrdate"],
                            "narration": "Round off amount %.2f earned"
                            % float(queryParams["roundoffamt"]),
                            "vouchertype": "journal",
                            "drcrid": queryParams["drcrid"],
                        }
                        vouchersList.append(rd_VoucherDict)

            elif (
                int(queryParams["dctypeflag"]) == 3
                and int(queryParams["inoutflag"]) == 9
            ):
                crs[partyaccountcode["accountcode"]] = queryParams["totreduct"]
                if int(queryParams["maflag"]) == 1:
                    prodDataP = queryParams["product"]
                    for prod in prodDataP:
                        proN = str(prod) + " Purchase"
                        prodAcc = con.execute(
                            select([accounts.c.accountcode]).where(
                                and_(
                                    accounts.c.accountname == proN,
                                    accounts.c.orgcode == orgcode,
                                )
                            )
                        )
                        prodAccount = prodAcc.fetchone()
                        drs[prodAccount["accountcode"]] = "%.2f" % float(
                            prodDataP[prod]
                        )
                        vchProdAcc = prodAccount["accountcode"]
                else:
                    # if multiple acc is 0 , then select default sale account
                    purchaseAccount = con.execute(
                        select([accounts.c.accountcode]).where(
                            and_(
                                accounts.c.defaultflag == 16,
                                accounts.c.orgcode == orgcode,
                            )
                        )
                    )
                    purchaseAcc = purchaseAccount.fetchone()
                    drs[purchaseAcc["accountcode"]] = totalTaxableVal
                    vchProdAcc = purchaseAcc["accountcode"]
                if int(queryParams["taxflag"]) == 7 and queryParams.get("taxstate"):
                    abv = con.execute(
                        select([state.c.abbreviation]).where(
                            state.c.statename == queryParams["taxstate"]
                        )
                    )
                    abb = abv.fetchone()
                    taxName = queryParams["taxname"]
                    if taxName == "SGST":
                        for prod in queryParams["prodData"]:
                            taxRate = float(queryParams["taxes"][prod])
                            taxable = float(queryParams["reductionval"][prod])
                            if taxRate > 0.00:
                                tx = float(taxRate) / 2
                                taxHalf = taxRateDict[float(taxRate)]
                                # this is the value which is going to Dr/Cr
                                taxVal = taxable * (tx / 100) * float(queryParams["reductionval"]["quantities"][prod])
                                taxNameSGST = (
                                    "SGSTIN_"
                                    + str(abb["abbreviation"])
                                    + "@"
                                    + str(taxHalf)
                                    + "%"
                                )
                                taxNameCGST = (
                                    "CGSTIN_"
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
                            taxable = float(queryParams["reductionval"][prod])
                            if taxRate > 0.00:
                                tx = float(taxRate)
                                # this is the value which is going to Dr/Cr
                                taxVal = taxable * (tx / 100) * float(queryParams["reductionval"]["quantities"][prod])
                                taxNameIGST = (
                                    "IGSTIN_"
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
                                "CESSIN_"
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
                        drs[taxRow["accountcode"]] = "%.2f" % float(taxDict[Tax])
                else:
                    vatoutaccount = con.execute(
                        select([accounts.c.accountcode]).where(
                            and_(
                                accounts.c.accountname == "VAT_IN",
                                accounts.c.orgcode == orgcode,
                            )
                        )
                    )
                    vatoutaccountcode = vatoutaccount.fetchone()
                    for prod in queryParams["taxes"]:
                        taxAmount = taxAmount + float(queryParams["reductionval"][prod]) * (
                            float(queryParams["taxes"][prod]) / 100
                        ) * float(queryParams["reductionval"]["quantities"][prod])
                    drs[vatoutaccountcode["accountcode"]] = "%.2f" % float(taxAmount)

                Narration = (
                    "Received goods worth Rupees "
                    + "%.2f" % float(queryParams["totreduct"])
                    + " from "
                    + str(queryParams["custname"])
                    + " ref Credit Note No. "
                    + str(queryParams["drcrno"])
                )

                voucherDict = {
                    "drs": drs,
                    "crs": crs,
                    "voucherdate": queryParams["drcrdate"],
                    "narration": Narration,
                    "vouchertype": "creditnote",
                    "drcrid": queryParams["drcrid"],
                }
                vouchersList.append(voucherDict)

                # check whether amount paid is rounded off
                if "roundoffamt" in queryParams:
                    if float(queryParams["roundoffamt"]) < 0.00:
                        # user has spent rounded of amount
                        roundAcc = con.execute(
                            select([accounts.c.accountcode]).where(
                                and_(
                                    accounts.c.defaultflag == 180,
                                    accounts.c.orgcode == orgcode,
                                )
                            )
                        )
                        roundRow = roundAcc.fetchone()

                        try:
                            accCode = roundRow["accountcode"]
                        except:
                            a = createAccount(con, 18, "Round Off Paid", orgcode)
                            accCode = a["accountcode"]

                        rddrs[accCode] = "%.2f" % float(abs(queryParams["roundoffamt"]))
                        rdcrs[partyaccountcode["accountcode"]] = "%.2f" % float(
                            abs(queryParams["roundoffamt"])
                        )
                        rd_VoucherDict = {
                            "drs": rddrs,
                            "crs": rdcrs,
                            "voucherdate": queryParams["drcrdate"],
                            "narration": "Round off amount %.2f spent"
                            % float(abs(queryParams["roundoffamt"])),
                            "vouchertype": "journal",
                            "drcrid": queryParams["drcrid"],
                        }
                        vouchersList.append(rd_VoucherDict)

                    if float(queryParams["roundoffamt"]) > 0.00:
                        # user has earned rounded of amount
                        roundAcc = con.execute(
                            select([accounts.c.accountcode]).where(
                                and_(
                                    accounts.c.defaultflag == 181,
                                    accounts.c.orgcode == orgcode,
                                )
                            )
                        )
                        roundRow = roundAcc.fetchone()

                        try:
                            accCode = roundRow["accountcode"]
                        except:
                            a = createAccount(con, 18, "Round Off Received", orgcode)
                            accCode = a["accountcode"]

                        rdcrs[accCode] = "%.2f" % float(queryParams["roundoffamt"])
                        rddrs[partyaccountcode["accountcode"]] = "%.2f" % float(
                            queryParams["roundoffamt"]
                        )

                        rd_VoucherDict = {
                            "drs": rddrs,
                            "crs": rdcrs,
                            "voucherdate": queryParams["drcrdate"],
                            "narration": "Round off amount %.2f earned"
                            % float(queryParams["roundoffamt"]),
                            "vouchertype": "journal",
                            "drcrid": queryParams["drcrid"],
                        }
                        vouchersList.append(rd_VoucherDict)

            elif (
                int(queryParams["dctypeflag"]) == 4
                and int(queryParams["inoutflag"]) == 15
            ):
                drs[partyaccountcode["accountcode"]] = queryParams["totreduct"]
                if int(queryParams["maflag"]) == 1:
                    prodDataP = queryParams["product"]
                    for prod in prodDataP:
                        proN = str(prod) + " Sale"
                        prodAcc = con.execute(
                            select([accounts.c.accountcode]).where(
                                and_(
                                    accounts.c.accountname == proN,
                                    accounts.c.orgcode == orgcode,
                                )
                            )
                        )
                        prodAccount = prodAcc.fetchone()
                        crs[prodAccount["accountcode"]] = "%.2f" % float(
                            prodDataP[prod]
                        )
                        vchProdAcc = prodAccount["accountcode"]
                else:
                    # if multiple acc is 0 , then select default sale account
                    salesAccount = con.execute(
                        select([accounts.c.accountcode]).where(
                            and_(
                                accounts.c.defaultflag == 19,
                                accounts.c.orgcode == orgcode,
                            )
                        )
                    )
                    saleAcc = salesAccount.fetchone()
                    crs[saleAcc["accountcode"]] = totalTaxableVal
                    vchProdAcc = saleAcc["accountcode"]
                if int(queryParams["taxflag"]) == 7 and queryParams.get("taxstate"):
                    abv = con.execute(
                        select([state.c.abbreviation]).where(
                            state.c.statename == queryParams["taxstate"]
                        )
                    )
                    abb = abv.fetchone()
                    taxName = queryParams["taxname"]
                    if taxName == "SGST":
                        for prod in queryParams["prodData"]:
                            taxRate = float(queryParams["taxes"][prod])
                            taxable = float(queryParams["reductionval"][prod])
                            if taxRate > 0.00:
                                tx = float(taxRate) / 2
                                taxHalf = taxRateDict[float(taxRate)]
                                # this is the value which is going to Dr/Cr
                                taxVal = taxable * (tx / 100) * float(queryParams["reductionval"]["quantities"][prod])
                                taxNameSGST = (
                                    "SGSTOUT_"
                                    + str(abb["abbreviation"])
                                    + "@"
                                    + str(taxHalf)
                                    + "%"
                                )
                                taxNameCGST = (
                                    "CGSTOUT_"
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
                            taxable = float(queryParams["reductionval"][prod])
                            if taxRate > 0.00:
                                tx = float(taxRate)
                                # this is the value which is going to Dr/Cr
                                taxVal = taxable * (tx / 100) * float(queryParams["reductionval"]["quantities"][prod])
                                taxNameIGST = (
                                    "IGSTOUT_"
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
                                "CESSOUT_"
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
                        crs[taxRow["accountcode"]] = "%.2f" % float(taxDict[Tax])
                else:
                    vatoutaccount = con.execute(
                        select([accounts.c.accountcode]).where(
                            and_(
                                accounts.c.accountname == "VAT_OUT",
                                accounts.c.orgcode == orgcode,
                            )
                        )
                    )
                    vatoutaccountcode = vatoutaccount.fetchone()
                    for prod in queryParams["taxes"]:
                        taxAmount = taxAmount + float(queryParams["reductionval"][prod]) * (
                            float(queryParams["taxes"][prod]) / 100
                        ) * float(queryParams["reductionval"]["quantities"][prod])
                    crs[vatoutaccountcode["accountcode"]] = "%.2f" % float(taxAmount)

                Narration = (
                    "Sold goods worth Rupees "
                    + "%.2f" % float(queryParams["totreduct"])
                    + " to "
                    + str(queryParams["custname"])
                    + " ref Debit Note No. "
                    + str(queryParams["drcrno"])
                )

                voucherDict = {
                    "drs": drs,
                    "crs": crs,
                    "voucherdate": queryParams["drcrdate"],
                    "narration": Narration,
                    "vouchertype": "debitnote",
                    "drcrid": queryParams["drcrid"],
                }
                vouchersList.append(voucherDict)

                # check whether amount paid is rounded off
                if "roundoffamt" in queryParams:
                    if float(queryParams["roundoffamt"]) > 0.00:
                        # user has spent rounded of amount
                        roundAcc = con.execute(
                            select([accounts.c.accountcode]).where(
                                and_(
                                    accounts.c.defaultflag == 180,
                                    accounts.c.orgcode == orgcode,
                                )
                            )
                        )
                        roundRow = roundAcc.fetchone()

                        try:
                            accCode = roundRow["accountcode"]
                        except:
                            a = createAccount(con, 18, "Round Off Paid", orgcode)
                            accCode = a["accountcode"]

                        rddrs[accCode] = "%.2f" % float(queryParams["roundoffamt"])
                        rdcrs[partyaccountcode["accountcode"]] = "%.2f" % float(
                            queryParams["roundoffamt"]
                        )

                        rd_VoucherDict = {
                            "drs": rddrs,
                            "crs": rdcrs,
                            "voucherdate": queryParams["drcrdate"],
                            "narration": "Round off amount %.2f spent"
                            % float(queryParams["roundoffamt"]),
                            "vouchertype": "payment",
                            "drcrid": queryParams["drcrid"],
                        }
                        vouchersList.append(rd_VoucherDict)

                    if float(queryParams["roundoffamt"]) < 0.00:
                        # user has earned rounded of amount
                        roundAcc = con.execute(
                            select([accounts.c.accountcode]).where(
                                and_(
                                    accounts.c.defaultflag == 181,
                                    accounts.c.orgcode == orgcode,
                                )
                            )
                        )
                        roundRow = roundAcc.fetchone()

                        try:
                            accCode = roundRow["accountcode"]
                        except:
                            a = createAccount(con, 18, "Round Off Received", orgcode)
                            accCode = a["accountcode"]

                        rdcrs[accCode] = "%.2f" % float(abs(queryParams["roundoffamt"]))
                        rddrs[partyaccountcode["accountcode"]] = "%.2f" % float(
                            abs(queryParams["roundoffamt"])
                        )
                        rd_VoucherDict = {
                            "drs": rddrs,
                            "crs": rdcrs,
                            "voucherdate": queryParams["drcrdate"],
                            "narration": "Round off amount %.2f earned"
                            % float(abs(queryParams["roundoffamt"])),
                            "vouchertype": "journal",
                            "drcrid": queryParams["drcrid"],
                        }
                        vouchersList.append(rd_VoucherDict)

            elif (
                int(queryParams["dctypeflag"]) == 4
                and int(queryParams["inoutflag"]) == 9
            ):
                drs[partyaccountcode["accountcode"]] = queryParams["totreduct"]
                if int(queryParams["maflag"]) == 1:
                    prodDataP = queryParams["product"]
                    for prod in prodDataP:
                        proN = str(prod) + " Purchase"
                        prodAcc = con.execute(
                            select([accounts.c.accountcode]).where(
                                and_(
                                    accounts.c.accountname == proN,
                                    accounts.c.orgcode == orgcode,
                                )
                            )
                        )
                        prodAccount = prodAcc.fetchone()
                        crs[prodAccount["accountcode"]] = "%.2f" % float(
                            prodDataP[prod]
                        )
                        vchProdAcc = prodAccount["accountcode"]
                else:
                    # if multiple acc is 0 , then select default sale account
                    purchaseAccount = con.execute(
                        select([accounts.c.accountcode]).where(
                            and_(
                                accounts.c.defaultflag == 16,
                                accounts.c.orgcode == orgcode,
                            )
                        )
                    )
                    purchaseAcc = purchaseAccount.fetchone()
                    crs[purchaseAcc["accountcode"]] = totalTaxableVal
                    vchProdAcc = purchaseAcc["accountcode"]
                if int(queryParams["taxflag"]) == 7 and queryParams.get("taxstate"):
                    abv = con.execute(
                        select([state.c.abbreviation]).where(
                            state.c.statename == queryParams["taxstate"]
                        )
                    )
                    abb = abv.fetchone()
                    taxName = queryParams["taxname"]
                    if taxName == "SGST":
                        for prod in queryParams["prodData"]:
                            taxRate = float(queryParams["taxes"][prod])
                            taxable = float(queryParams["reductionval"][prod])
                            if taxRate > 0.00:
                                tx = float(taxRate) / 2
                                taxHalf = taxRateDict[float(taxRate)]
                                # this is the value which is going to Dr/Cr
                                taxVal = taxable * (tx / 100) * float(queryParams["reductionval"]["quantities"][prod])
                                taxNameSGST = (
                                    "SGSTIN_"
                                    + str(abb["abbreviation"])
                                    + "@"
                                    + str(taxHalf)
                                    + "%"
                                )
                                taxNameCGST = (
                                    "CGSTIN_"
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
                            taxable = float(queryParams["reductionval"][prod])
                            if taxRate > 0.00:
                                tx = float(taxRate)
                                # this is the value which is going to Dr/Cr
                                taxVal = taxable * (tx / 100) * float(queryParams["reductionval"]["quantities"][prod])
                                taxNameIGST = (
                                    "IGSTIN_"
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
                                "CESSIN_"
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
                        crs[taxRow["accountcode"]] = "%.2f" % float(taxDict[Tax])
                else:
                    vatoutaccount = con.execute(
                        select([accounts.c.accountcode]).where(
                            and_(
                                accounts.c.accountname == "VAT_IN",
                                accounts.c.orgcode == orgcode,
                            )
                        )
                    )
                    vatoutaccountcode = vatoutaccount.fetchone()
                    for prod in queryParams["taxes"]:
                        taxAmount = taxAmount + float(queryParams["reductionval"][prod]) * (
                            float(queryParams["taxes"][prod]) / 100
                        ) * float(queryParams["reductionval"]["quantities"][prod])
                    crs[vatoutaccountcode["accountcode"]] = "%.2f" % float(taxAmount)

                Narration = (
                    "Returned goods worth Rupees "
                    + "%.2f" % float(queryParams["totreduct"])
                    + " to "
                    + str(queryParams["custname"])
                    + " ref Debit Note No. "
                    + str(queryParams["drcrno"])
                )

                voucherDict = {
                    "drs": drs,
                    "crs": crs,
                    "voucherdate": queryParams["drcrdate"],
                    "narration": Narration,
                    "vouchertype": "debitnote",
                    "drcrid": queryParams["drcrid"],
                }
                vouchersList.append(voucherDict)

                # check whether amount paid is rounded off
                if "roundoffamt" in queryParams:
                    if float(queryParams["roundoffamt"]) > 0.00:
                        # user has spent rounded of amount
                        roundAcc = con.execute(
                            select([accounts.c.accountcode]).where(
                                and_(
                                    accounts.c.defaultflag == 180,
                                    accounts.c.orgcode == orgcode,
                                )
                            )
                        )
                        roundRow = roundAcc.fetchone()

                        try:
                            accCode = roundRow["accountcode"]
                        except:
                            a = createAccount(con, 18, "Round Off Paid", orgcode)
                            accCode = a["accountcode"]

                        rddrs[accCode] = "%.2f" % float(queryParams["roundoffamt"])
                        rdcrs[partyaccountcode["accountcode"]] = "%.2f" % float(
                            queryParams["roundoffamt"]
                        )

                        rd_VoucherDict = {
                            "drs": rddrs,
                            "crs": rdcrs,
                            "voucherdate": queryParams["drcrdate"],
                            "narration": "Round off amount %.2f spent"
                            % float(queryParams["roundoffamt"]),
                            "vouchertype": "journal",
                            "drcrid": queryParams["drcrid"],
                        }
                        vouchersList.append(rd_VoucherDict)

                    if float(queryParams["roundoffamt"]) < 0.00:
                        # user has earned rounded of amount
                        roundAcc = con.execute(
                            select([accounts.c.accountcode]).where(
                                and_(
                                    accounts.c.defaultflag == 181,
                                    accounts.c.orgcode == orgcode,
                                )
                            )
                        )
                        roundRow = roundAcc.fetchone()

                        try:
                            accCode = roundRow["accountcode"]
                        except:
                            a = createAccount(con, 18, "Round Off Received", orgcode)
                            accCode = a["accountcode"]

                        rdcrs[accCode] = "%.2f" % float(abs(queryParams["roundoffamt"]))
                        rddrs[partyaccountcode["accountcode"]] = "%.2f" % float(
                            abs(queryParams["roundoffamt"])
                        )
                        rd_VoucherDict = {
                            "drs": rddrs,
                            "crs": rdcrs,
                            "voucherdate": queryParams["drcrdate"],
                            "narration": "Round off amount %.2f earned"
                            % float(abs(queryParams["roundoffamt"])),
                            "vouchertype": "journal",
                            "drcrid": queryParams["drcrid"],
                        }
                        vouchersList.append(rd_VoucherDict)
    else:
        invData = con.execute(
            select([invoice.c.paymentmode]).where(
                and_(
                    invoice.c.invid == queryParams["invid"],
                    invoice.c.orgcode == orgcode,
                )
            )
        )
        paymentMode = invData.fetchone()
        if paymentMode[0] == 2:
            accountname = "Bank A/C"
        elif paymentMode[0] == 3:
            accountname = "Cash in hand"
        else:
            # If paymentMode[0] is neither 2 nor 3, handle it appropriately
            # For example, raise an error or assign a default value
            raise ValueError("Invalid payment mode")
        partyaccount = con.execute(
                select([accounts.c.accountcode]).where(
                    and_(
                        accounts.c.accountname == accountname,
                        accounts.c.orgcode == orgcode,
                    )
                )
            )
        partyaccountcode = partyaccount.fetchone()
        discountpaidaccount = con.execute(
                select([accounts.c.accountcode]).where(
                    and_(
                        accounts.c.accountname == "Discount Paid",
                        accounts.c.orgcode == orgcode,
                    )
                )
            )
        discountpaidaccountcode = discountpaidaccount.fetchone()
        discountreceivedaccount = con.execute(
                select([accounts.c.accountcode]).where(
                    and_(
                        accounts.c.accountname == "Discount Received",
                        accounts.c.orgcode == orgcode,
                    )
                )
            )
        discountreceivedaccountcode = discountreceivedaccount.fetchone()
        if int(queryParams["drcrmode"]) == 4:
            if (
                int(queryParams["dctypeflag"]) == 3
                and int(queryParams["inoutflag"]) == 15
            ):
                crs[partyaccountcode["accountcode"]] = queryParams["totreduct"]
                drs[discountpaidaccountcode["accountcode"]] = totalTaxableVal
                if int(queryParams["taxflag"]) == 7 and queryParams.get("taxstate"):
                    abv = con.execute(
                        select([state.c.abbreviation]).where(
                            state.c.statename == queryParams["taxstate"]
                        )
                    )
                    abb = abv.fetchone()
                    taxName = queryParams["taxname"]
                    if taxName == "SGST":
                        for prod in queryParams["prodData"]:
                            taxRate = float(queryParams["taxes"][prod])
                            taxable = float(queryParams["reductionval"][prod])
                            if taxRate > 0.00:
                                tx = float(taxRate) / 2
                                taxHalf = taxRateDict[float(taxRate)]
                                # this is the value which is going to Dr/Cr
                                taxVal = taxable * (tx / 100) * float(queryParams["reductionval"]["quantities"][prod])
                                taxNameSGST = (
                                    "SGSTOUT_"
                                    + str(abb["abbreviation"])
                                    + "@"
                                    + str(taxHalf)
                                    + "%"
                                )
                                taxNameCGST = (
                                    "CGSTOUT_"
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
                            taxable = float(queryParams["reductionval"][prod])
                            if taxRate > 0.00:
                                tx = float(taxRate)
                                # this is the value which is going to Dr/Cr
                                taxVal = taxable * (tx / 100) * float(queryParams["reductionval"]["quantities"][prod])
                                taxNameIGST = (
                                    "IGSTOUT_"
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
                                "CESSOUT_"
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
                        drs[taxRow["accountcode"]] = "%.2f" % float(taxDict[Tax])
                else:
                    vatoutaccount = con.execute(
                        select([accounts.c.accountcode]).where(
                            and_(
                                accounts.c.accountname == "VAT_OUT",
                                accounts.c.orgcode == orgcode,
                            )
                        )
                    )
                    vatoutaccountcode = vatoutaccount.fetchone()
                    for prod in queryParams["taxes"]:
                        taxAmount = taxAmount + float(queryParams["reductionval"][prod]) * (
                            float(queryParams["taxes"][prod]) / 100
                        ) * float(queryParams["reductionval"]["quantities"][prod])
                    drs[vatoutaccountcode["accountcode"]] = "%.2f" % float(taxAmount)

                Narration = (
                    "Paid Rupees "
                    + "%.2f" % float(queryParams["totreduct"])
                    + " to "
                    + str(queryParams["custname"])
                    + " ref Credit Note No. "
                    + str(queryParams["drcrno"])
                )

                voucherDict = {
                    "drs": drs,
                    "crs": crs,
                    "voucherdate": queryParams["drcrdate"],
                    "narration": Narration,
                    "vouchertype": "creditnote",
                    "drcrid": queryParams["drcrid"],
                }
                vouchersList.append(voucherDict)

                # check whether amount paid is rounded off
                if "roundoffamt" in queryParams:
                    if float(queryParams["roundoffamt"]) < 0.00:
                        # user has spent rounded of amount
                        roundAcc = con.execute(
                            select([accounts.c.accountcode]).where(
                                and_(
                                    accounts.c.defaultflag == 180,
                                    accounts.c.orgcode == orgcode,
                                )
                            )
                        )
                        roundRow = roundAcc.fetchone()

                        try:
                            accCode = roundRow["accountcode"]
                        except:
                            a = createAccount(con, 18, "Round Off Paid", orgcode)
                            accCode = a["accountcode"]

                        rddrs[accCode] = "%.2f" % float(abs(queryParams["roundoffamt"]))
                        rdcrs[partyaccountcode["accountcode"]] = "%.2f" % float(
                            abs(queryParams["roundoffamt"])
                        )
                        rd_VoucherDict = {
                            "drs": rddrs,
                            "crs": rdcrs,
                            "voucherdate": queryParams["drcrdate"],
                            "narration": "Round off amount %.2f spent"
                            % float(abs(queryParams["roundoffamt"])),
                            "vouchertype": "journal",
                            "drcrid": queryParams["drcrid"],
                        }
                        vouchersList.append(rd_VoucherDict)

                    if float(queryParams["roundoffamt"]) > 0.00:
                        # user has earned rounded of amount
                        roundAcc = con.execute(
                            select([accounts.c.accountcode]).where(
                                and_(
                                    accounts.c.defaultflag == 181,
                                    accounts.c.orgcode == orgcode,
                                )
                            )
                        )
                        roundRow = roundAcc.fetchone()

                        try:
                            accCode = roundRow["accountcode"]
                        except:
                            a = createAccount(con, 18, "Round Off Received", orgcode)
                            accCode = a["accountcode"]

                        rdcrs[accCode] = "%.2f" % float(queryParams["roundoffamt"])
                        rddrs[partyaccountcode["accountcode"]] = "%.2f" % float(
                            queryParams["roundoffamt"]
                        )

                        rd_VoucherDict = {
                            "drs": rddrs,
                            "crs": rdcrs,
                            "voucherdate": queryParams["drcrdate"],
                            "narration": "Round off amount %.2f earned"
                            % float(queryParams["roundoffamt"]),
                            "vouchertype": "journal",
                            "drcrid": queryParams["drcrid"],
                        }
                        vouchersList.append(rd_VoucherDict)

            elif (
                int(queryParams["dctypeflag"]) == 3
                and int(queryParams["inoutflag"]) == 9
            ):
                crs[partyaccountcode["accountcode"]] = queryParams["totreduct"]
                drs[discountpaidaccountcode["accountcode"]] = totalTaxableVal
                if int(queryParams["taxflag"]) == 7 and queryParams.get("taxstate"):
                    abv = con.execute(
                        select([state.c.abbreviation]).where(
                            state.c.statename == queryParams["taxstate"]
                        )
                    )
                    abb = abv.fetchone()
                    taxName = queryParams["taxname"]
                    if taxName == "SGST":
                        for prod in queryParams["prodData"]:
                            taxRate = float(queryParams["taxes"][prod])
                            taxable = float(queryParams["reductionval"][prod])
                            if taxRate > 0.00:
                                taxHalf = taxRateDict[float(taxRate)]
                                tx = float(taxRate) / 2
                                # this is the value which is going to Dr/Cr
                                taxVal = taxable * (tx / 100) * float(queryParams["reductionval"]["quantities"][prod])
                                taxNameSGST = (
                                    "SGSTIN_"
                                    + str(abb["abbreviation"])
                                    + "@"
                                    + str(taxHalf)
                                    + "%"
                                )
                                taxNameCGST = (
                                    "CGSTIN_"
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
                            taxable = float(queryParams["reductionval"][prod])
                            if taxRate > 0.00:
                                tx = float(taxRate)
                                # this is the value which is going to Dr/Cr
                                taxVal = taxable * (tx / 100) * float(queryParams["reductionval"]["quantities"][prod])
                                taxNameIGST = (
                                    "IGSTIN_"
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
                                "CESSIN_"
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
                        drs[taxRow["accountcode"]] = "%.2f" % float(taxDict[Tax])
                else:
                    vatoutaccount = con.execute(
                        select([accounts.c.accountcode]).where(
                            and_(
                                accounts.c.accountname == "VAT_IN",
                                accounts.c.orgcode == orgcode,
                            )
                        )
                    )
                    vatoutaccountcode = vatoutaccount.fetchone()
                    for prod in queryParams["taxes"]:
                        taxAmount = taxAmount + float(queryParams["reductionval"][prod]) * (
                            float(queryParams["taxes"][prod]) / 100
                        ) * float(queryParams["reductionval"]["quantities"][prod])
                    drs[vatoutaccountcode["accountcode"]] = "%.2f" % float(taxAmount)

                Narration = (
                    "Paid Rupees "
                    + "%.2f" % float(queryParams["totreduct"])
                    + " to "
                    + str(queryParams["custname"])
                    + " ref Credit Note No. "
                    + str(queryParams["drcrno"])
                )

                voucherDict = {
                    "drs": drs,
                    "crs": crs,
                    "voucherdate": queryParams["drcrdate"],
                    "narration": Narration,
                    "vouchertype": "creditnote",
                    "drcrid": queryParams["drcrid"],
                }
                vouchersList.append(voucherDict)

                # check whether amount paid is rounded off
                if "roundoffamt" in queryParams:
                    if float(queryParams["roundoffamt"]) < 0.00:
                        # user has spent rounded of amount
                        roundAcc = con.execute(
                            select([accounts.c.accountcode]).where(
                                and_(
                                    accounts.c.defaultflag == 180,
                                    accounts.c.orgcode == orgcode,
                                )
                            )
                        )
                        roundRow = roundAcc.fetchone()

                        try:
                            accCode = roundRow["accountcode"]
                        except:
                            a = createAccount(con, 18, "Round Off Paid", orgcode)
                            accCode = a["accountcode"]

                        rddrs[accCode] = "%.2f" % float(abs(queryParams["roundoffamt"]))
                        rdcrs[partyaccountcode["accountcode"]] = "%.2f" % float(
                            abs(queryParams["roundoffamt"])
                        )
                        rd_VoucherDict = {
                            "drs": rddrs,
                            "crs": rdcrs,
                            "voucherdate": queryParams["drcrdate"],
                            "narration": "Round off amount %.2f spent"
                            % float(abs(queryParams["roundoffamt"])),
                            "vouchertype": "journal",
                            "drcrid": queryParams["drcrid"],
                        }
                        vouchersList.append(rd_VoucherDict)

                    if float(queryParams["roundoffamt"]) > 0.00:
                        # user has earned rounded of amount
                        roundAcc = con.execute(
                            select([accounts.c.accountcode]).where(
                                and_(
                                    accounts.c.defaultflag == 181,
                                    accounts.c.orgcode == orgcode,
                                )
                            )
                        )
                        roundRow = roundAcc.fetchone()

                        try:
                            accCode = roundRow["accountcode"]
                        except:
                            a = createAccount(con, 18, "Round Off Received", orgcode)
                            accCode = a["accountcode"]

                        rdcrs[accCode] = "%.2f" % float(queryParams["roundoffamt"])
                        rddrs[partyaccountcode["accountcode"]] = "%.2f" % float(
                            queryParams["roundoffamt"]
                        )

                        rd_VoucherDict = {
                            "drs": rddrs,
                            "crs": rdcrs,
                            "voucherdate": queryParams["drcrdate"],
                            "narration": "Round off amount %.2f earned"
                            % float(queryParams["roundoffamt"]),
                            "vouchertype": "journal",
                            "drcrid": queryParams["drcrid"],
                        }
                        vouchersList.append(rd_VoucherDict)

            elif (
                int(queryParams["dctypeflag"]) == 4
                and int(queryParams["inoutflag"]) == 15
            ):
                drs[partyaccountcode["accountcode"]] = queryParams["totreduct"]
                crs[discountreceivedaccountcode["accountcode"]] = totalTaxableVal
                if int(queryParams["taxflag"]) == 7 and queryParams.get("taxstate"):
                    abv = con.execute(
                        select([state.c.abbreviation]).where(
                            state.c.statename == queryParams["taxstate"]
                        )
                    )
                    abb = abv.fetchone()
                    taxName = queryParams["taxname"]
                    if taxName == "SGST":
                        for prod in queryParams["prodData"]:
                            taxRate = float(queryParams["taxes"][prod])
                            taxable = float(queryParams["reductionval"][prod])
                            if taxRate > 0.00:
                                tx = float(taxRate) / 2
                                taxHalf = taxRateDict[float(taxRate)]
                                # this is the value which is going to Dr/Cr
                                taxVal = taxable * (tx / 100) * float(queryParams["reductionval"]["quantities"][prod])
                                taxNameSGST = (
                                    "SGSTOUT_"
                                    + str(abb["abbreviation"])
                                    + "@"
                                    + str(taxHalf)
                                    + "%"
                                )
                                taxNameCGST = (
                                    "CGSTOUT_"
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
                            taxable = float(queryParams["reductionval"][prod])
                            if taxRate > 0.00:
                                tx = float(taxRate)
                                # this is the value which is going to Dr/Cr
                                taxVal = taxable * (tx / 100) * float(queryParams["reductionval"]["quantities"][prod])
                                taxNameIGST = (
                                    "IGSTOUT_"
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
                                "CESSOUT_"
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
                        crs[taxRow["accountcode"]] = "%.2f" % float(taxDict[Tax])
                else:
                    vatoutaccount = con.execute(
                        select([accounts.c.accountcode]).where(
                            and_(
                                accounts.c.accountname == "VAT_OUT",
                                accounts.c.orgcode == orgcode,
                            )
                        )
                    )
                    vatoutaccountcode = vatoutaccount.fetchone()
                    for prod in queryParams["taxes"]:
                        taxAmount = taxAmount + float(queryParams["reductionval"][prod]) * (
                            float(queryParams["taxes"][prod]) / 100
                        ) * float(queryParams["reductionval"]["quantities"][prod])
                    crs[vatoutaccountcode["accountcode"]] = "%.2f" % float(taxAmount)

                Narration = (
                    "Received Rupees "
                    + "%.2f" % float(queryParams["totreduct"])
                    + " to "
                    + str(queryParams["custname"])
                    + " ref Debit Note No. "
                    + str(queryParams["drcrno"])
                )

                voucherDict = {
                    "drs": drs,
                    "crs": crs,
                    "voucherdate": queryParams["drcrdate"],
                    "narration": Narration,
                    "vouchertype": "debitnote",
                    "drcrid": queryParams["drcrid"],
                }
                vouchersList.append(voucherDict)

                # check whether amount paid is rounded off
                if "roundoffamt" in queryParams:
                    if float(queryParams["roundoffamt"]) > 0.00:
                        # user has spent rounded of amount
                        roundAcc = con.execute(
                            select([accounts.c.accountcode]).where(
                                and_(
                                    accounts.c.defaultflag == 180,
                                    accounts.c.orgcode == orgcode,
                                )
                            )
                        )
                        roundRow = roundAcc.fetchone()

                        try:
                            accCode = roundRow["accountcode"]
                        except:
                            a = createAccount(con, 18, "Round Off Paid", orgcode)
                            accCode = a["accountcode"]

                        rddrs[accCode] = "%.2f" % float(queryParams["roundoffamt"])
                        rdcrs[partyaccountcode["accountcode"]] = "%.2f" % float(
                            queryParams["roundoffamt"]
                        )
                        rd_VoucherDict = {
                            "drs": rddrs,
                            "crs": rdcrs,
                            "voucherdate": queryParams["drcrdate"],
                            "narration": "Round off amount %.2f spent"
                            % float(queryParams["roundoffamt"]),
                            "vouchertype": "journal",
                            "drcrid": queryParams["drcrid"],
                        }
                        vouchersList.append(rd_VoucherDict)

                    if float(queryParams["roundoffamt"]) < 0.00:
                        # user has earned rounded of amount
                        roundAcc = con.execute(
                            select([accounts.c.accountcode]).where(
                                and_(
                                    accounts.c.defaultflag == 181,
                                    accounts.c.orgcode == orgcode,
                                )
                            )
                        )
                        roundRow = roundAcc.fetchone()

                        try:
                            accCode = roundRow["accountcode"]
                        except:
                            a = createAccount(con, 18, "Round Off Received", orgcode)
                            accCode = a["accountcode"]

                        rdcrs[accCode] = "%.2f" % float(abs(queryParams["roundoffamt"]))
                        rddrs[partyaccountcode["accountcode"]] = "%.2f" % float(
                            abs(queryParams["roundoffamt"])
                        )

                        rd_VoucherDict = {
                            "drs": rddrs,
                            "crs": rdcrs,
                            "voucherdate": queryParams["drcrdate"],
                            "narration": "Round off amount %.2f earned"
                            % float(abs(queryParams["roundoffamt"])),
                            "vouchertype": "journal",
                            "drcrid": queryParams["drcrid"],
                        }
                        vouchersList.append(rd_VoucherDict)

            elif (
                int(queryParams["dctypeflag"]) == 4
                and int(queryParams["inoutflag"]) == 9
            ):
                drs[partyaccountcode["accountcode"]] = queryParams["totreduct"]
                crs[discountreceivedaccountcode["accountcode"]] = totalTaxableVal
                if int(queryParams["taxflag"]) == 7 and queryParams.get("taxstate"):
                    abv = con.execute(
                        select([state.c.abbreviation]).where(
                            state.c.statename == queryParams["taxstate"]
                        )
                    )
                    abb = abv.fetchone()
                    taxName = queryParams["taxname"]
                    if taxName == "SGST":
                        for prod in queryParams["prodData"]:
                            taxRate = float(queryParams["taxes"][prod])
                            taxable = float(queryParams["reductionval"][prod])
                            if taxRate > 0.00:
                                tx = float(taxRate) / 2
                                taxHalf = taxRateDict[float(taxRate)]
                                # this is the value which is going to Dr/Cr
                                taxVal = taxable * (tx / 100) * float(queryParams["reductionval"]["quantities"][prod])
                                taxNameSGST = (
                                    "SGSTIN_"
                                    + str(abb["abbreviation"])
                                    + "@"
                                    + str(taxHalf)
                                    + "%"
                                )
                                taxNameCGST = (
                                    "CGSTIN_"
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
                            taxable = float(queryParams["reductionval"][prod])
                            if taxRate > 0.00:
                                tx = float(taxRate)
                                # this is the value which is going to Dr/Cr
                                taxVal = taxable * (tx / 100) * float(queryParams["reductionval"]["quantities"][prod])
                                taxNameIGST = (
                                    "IGSTIN_"
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
                                "CESSIN_"
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
                        crs[taxRow["accountcode"]] = "%.2f" % float(taxDict[Tax])
                else:
                    vatoutaccount = con.execute(
                        select([accounts.c.accountcode]).where(
                            and_(
                                accounts.c.accountname == "VAT_IN",
                                accounts.c.orgcode == orgcode,
                            )
                        )
                    )
                    vatoutaccountcode = vatoutaccount.fetchone()
                    for prod in queryParams["taxes"]:
                        taxAmount = taxAmount + float(queryParams["reductionval"][prod]) * (
                            float(queryParams["taxes"][prod]) / 100
                        ) * float(queryParams["reductionval"]["quantities"][prod])
                    crs[vatoutaccountcode["accountcode"]] = "%.2f" % float(taxAmount)

                Narration = (
                    "Paid Rupees "
                    + "%.2f" % float(queryParams["totreduct"])
                    + " to "
                    + str(queryParams["custname"])
                    + " ref Debit Note No. "
                    + str(queryParams["drcrno"])
                )

                voucherDict = {
                    "drs": drs,
                    "crs": crs,
                    "voucherdate": queryParams["drcrdate"],
                    "narration": Narration,
                    "vouchertype": "debitnote",
                    "drcrid": queryParams["drcrid"],
                }
                vouchersList.append(voucherDict)

                # check whether amount paid is rounded off
                if "roundoffamt" in queryParams:
                    if float(queryParams["roundoffamt"]) > 0.00:
                        # user has spent rounded of amount
                        roundAcc = con.execute(
                            select([accounts.c.accountcode]).where(
                                and_(
                                    accounts.c.defaultflag == 180,
                                    accounts.c.orgcode == orgcode,
                                )
                            )
                        )
                        roundRow = roundAcc.fetchone()

                        try:
                            accCode = roundRow["accountcode"]
                        except:
                            a = createAccount(con, 18, "Round Off Paid", orgcode)
                            accCode = a["accountcode"]

                        rddrs[accCode] = "%.2f" % float(queryParams["roundoffamt"])
                        rdcrs[partyaccountcode["accountcode"]] = "%.2f" % float(
                            queryParams["roundoffamt"]
                        )
                        rd_VoucherDict = {
                            "drs": rddrs,
                            "crs": rdcrs,
                            "voucherdate": queryParams["drcrdate"],
                            "narration": "Round off amount %.2f spent"
                            % float(queryParams["roundoffamt"]),
                            "vouchertype": "journal",
                            "drcrid": queryParams["drcrid"],
                        }
                        vouchersList.append(rd_VoucherDict)

                    if float(queryParams["roundoffamt"]) < 0.00:
                        # user has earned rounded of amount
                        roundAcc = con.execute(
                            select([accounts.c.accountcode]).where(
                                and_(
                                    accounts.c.defaultflag == 181,
                                    accounts.c.orgcode == orgcode,
                                )
                            )
                        )
                        roundRow = roundAcc.fetchone()

                        try:
                            accCode = roundRow["accountcode"]
                        except:
                            a = createAccount(con, 18, "Round Off Received", orgcode)
                            accCode = a["accountcode"]

                        rdcrs[accCode] = "%.2f" % float(abs(queryParams["roundoffamt"]))
                        rddrs[partyaccountcode["accountcode"]] = "%.2f" % float(
                            abs(queryParams["roundoffamt"])
                        )

                        rd_VoucherDict = {
                            "drs": rddrs,
                            "crs": rdcrs,
                            "voucherdate": queryParams["drcrdate"],
                            "narration": "Round off amount %.2f earned"
                            % float(abs(queryParams["roundoffamt"])),
                            "vouchertype": "journal",
                            "drcrid": queryParams["drcrid"],
                        }
                        vouchersList.append(rd_VoucherDict)

        elif int(queryParams["drcrmode"]) == 18:
            vchProdAcc = ""
            if (
                int(queryParams["dctypeflag"]) == 3
                and int(queryParams["inoutflag"]) == 15
            ):
                crs[partyaccountcode["accountcode"]] = queryParams["totreduct"]
                drs[discountpaidaccountcode["accountcode"]] = totalTaxableVal
                if int(queryParams["taxflag"]) == 7 and queryParams.get("taxstate"):
                    abv = con.execute(
                        select([state.c.abbreviation]).where(
                            state.c.statename == queryParams["taxstate"]
                        )
                    )
                    abb = abv.fetchone()
                    taxName = queryParams["taxname"]
                    if taxName == "SGST":
                        for prod in queryParams["prodData"]:
                            taxRate = float(queryParams["taxes"][prod])
                            taxable = float(queryParams["reductionval"][prod])
                            if taxRate > 0.00:
                                tx = float(taxRate) / 2
                                taxHalf = taxRateDict[float(taxRate)]
                                # this is the value which is going to Dr/Cr
                                taxVal = taxable * (tx / 100) * float(queryParams["reductionval"]["quantities"][prod])
                                taxNameSGST = (
                                    "SGSTOUT_"
                                    + str(abb["abbreviation"])
                                    + "@"
                                    + str(taxHalf)
                                    + "%"
                                )
                                taxNameCGST = (
                                    "CGSTOUT_"
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
                            taxable = float(queryParams["reductionval"][prod])
                            if taxRate > 0.00:
                                tx = float(taxRate)
                                # this is the value which is going to Dr/Cr
                                taxVal = taxable * (tx / 100) * float(queryParams["reductionval"]["quantities"][prod])
                                taxNameIGST = (
                                    "IGSTOUT_"
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
                                "CESSOUT_"
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
                        drs[taxRow["accountcode"]] = "%.2f" % float(taxDict[Tax])
                else:
                    vatoutaccount = con.execute(
                        select([accounts.c.accountcode]).where(
                            and_(
                                accounts.c.accountname == "VAT_OUT",
                                accounts.c.orgcode == orgcode,
                            )
                        )
                    )
                    vatoutaccountcode = vatoutaccount.fetchone()
                    for prod in queryParams["taxes"]:
                        taxAmount = taxAmount + float(queryParams["reductionval"][prod]) * (
                            float(queryParams["taxes"][prod]) / 100
                        ) * float(queryParams["reductionval"]["quantities"][prod])
                    drs[vatoutaccountcode["accountcode"]] = "%.2f" % float(taxAmount)

                Narration = (
                    "Paid Rupees "
                    + "%.2f" % float(queryParams["totreduct"])
                    + " to "
                    + str(queryParams["custname"])
                    + " ref Credit Note No. "
                    + str(queryParams["drcrno"])
                )

                voucherDict = {
                    "drs": drs,
                    "crs": crs,
                    "voucherdate": queryParams["drcrdate"],
                    "narration": Narration,
                    "vouchertype": "creditnote",
                    "drcrid": queryParams["drcrid"],
                }
                vouchersList.append(voucherDict)

                # check whether amount paid is rounded off
                if "roundoffamt" in queryParams:
                    if float(queryParams["roundoffamt"]) < 0.00:
                        # user has spent rounded of amount
                        roundAcc = con.execute(
                            select([accounts.c.accountcode]).where(
                                and_(
                                    accounts.c.defaultflag == 180,
                                    accounts.c.orgcode == orgcode,
                                )
                            )
                        )
                        roundRow = roundAcc.fetchone()

                        try:
                            accCode = roundRow["accountcode"]
                        except:
                            a = createAccount(con, 18, "Round Off Paid", orgcode)
                            accCode = a["accountcode"]

                        rddrs[accCode] = "%.2f" % float(abs(queryParams["roundoffamt"]))
                        rdcrs[partyaccountcode["accountcode"]] = "%.2f" % float(
                            abs(queryParams["roundoffamt"])
                        )
                        rd_VoucherDict = {
                            "drs": rddrs,
                            "crs": rdcrs,
                            "voucherdate": queryParams["drcrdate"],
                            "narration": "Round off amount %.2f spent"
                            % float(abs(queryParams["roundoffamt"])),
                            "vouchertype": "journal",
                            "drcrid": queryParams["drcrid"],
                        }
                        vouchersList.append(rd_VoucherDict)

                    if float(queryParams["roundoffamt"]) > 0.00:
                        # user has earned rounded of amount
                        roundAcc = con.execute(
                            select([accounts.c.accountcode]).where(
                                and_(
                                    accounts.c.defaultflag == 181,
                                    accounts.c.orgcode == orgcode,
                                )
                            )
                        )
                        roundRow = roundAcc.fetchone()

                        try:
                            accCode = roundRow["accountcode"]
                        except:
                            a = createAccount(con, 18, "Round Off Received", orgcode)
                            accCode = a["accountcode"]

                        rdcrs[accCode] = "%.2f" % float(queryParams["roundoffamt"])
                        rddrs[partyaccountcode["accountcode"]] = "%.2f" % float(
                            queryParams["roundoffamt"]
                        )

                        rd_VoucherDict = {
                            "drs": rddrs,
                            "crs": rdcrs,
                            "voucherdate": queryParams["drcrdate"],
                            "narration": "Round off amount %.2f earned"
                            % float(queryParams["roundoffamt"]),
                            "vouchertype": "journal",
                            "drcrid": queryParams["drcrid"],
                        }
                        vouchersList.append(rd_VoucherDict)

            elif (
                int(queryParams["dctypeflag"]) == 3
                and int(queryParams["inoutflag"]) == 9
            ):
                crs[partyaccountcode["accountcode"]] = queryParams["totreduct"]
                drs[discountpaidaccountcode["accountcode"]] = totalTaxableVal
                if int(queryParams["taxflag"]) == 7 and queryParams.get("taxstate"):
                    abv = con.execute(
                        select([state.c.abbreviation]).where(
                            state.c.statename == queryParams["taxstate"]
                        )
                    )
                    abb = abv.fetchone()
                    taxName = queryParams["taxname"]
                    if taxName == "SGST":
                        for prod in queryParams["prodData"]:
                            taxRate = float(queryParams["taxes"][prod])
                            taxable = float(queryParams["reductionval"][prod])
                            if taxRate > 0.00:
                                taxHalf = taxRateDict[float(taxRate)]
                                tx = float(taxRate) / 2
                                # this is the value which is going to Dr/Cr
                                taxVal = taxable * (tx / 100) * float(queryParams["reductionval"]["quantities"][prod])
                                taxNameSGST = (
                                    "SGSTIN_"
                                    + str(abb["abbreviation"])
                                    + "@"
                                    + str(taxHalf)
                                    + "%"
                                )
                                taxNameCGST = (
                                    "CGSTIN_"
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
                            taxable = float(queryParams["reductionval"][prod])
                            if taxRate > 0.00:
                                tx = float(taxRate)
                                # this is the value which is going to Dr/Cr
                                taxVal = taxable * (tx / 100) * float(queryParams["reductionval"]["quantities"][prod])
                                taxNameIGST = (
                                    "IGSTIN_"
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
                                "CESSIN_"
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
                        drs[taxRow["accountcode"]] = "%.2f" % float(taxDict[Tax])
                else:
                    vatoutaccount = con.execute(
                        select([accounts.c.accountcode]).where(
                            and_(
                                accounts.c.accountname == "VAT_IN",
                                accounts.c.orgcode == orgcode,
                            )
                        )
                    )
                    vatoutaccountcode = vatoutaccount.fetchone()
                    for prod in queryParams["taxes"]:
                        taxAmount = taxAmount + float(queryParams["reductionval"][prod]) * (
                            float(queryParams["taxes"][prod]) / 100
                        ) * float(queryParams["reductionval"]["quantities"][prod])
                    drs[vatoutaccountcode["accountcode"]] = "%.2f" % float(taxAmount)

                Narration = (
                    "Paid Rupees "
                    + "%.2f" % float(queryParams["totreduct"])
                    + " to "
                    + str(queryParams["custname"])
                    + " ref Credit Note No. "
                    + str(queryParams["drcrno"])
                )

                voucherDict = {
                    "drs": drs,
                    "crs": crs,
                    "voucherdate": queryParams["drcrdate"],
                    "narration": Narration,
                    "vouchertype": "creditnote",
                    "drcrid": queryParams["drcrid"],
                }
                vouchersList.append(voucherDict)

                # check whether amount paid is rounded off
                if "roundoffamt" in queryParams:
                    if float(queryParams["roundoffamt"]) < 0.00:
                        # user has spent rounded of amount
                        roundAcc = con.execute(
                            select([accounts.c.accountcode]).where(
                                and_(
                                    accounts.c.defaultflag == 180,
                                    accounts.c.orgcode == orgcode,
                                )
                            )
                        )
                        roundRow = roundAcc.fetchone()

                        try:
                            accCode = roundRow["accountcode"]
                        except:
                            a = createAccount(con, 18, "Round Off Paid", orgcode)
                            accCode = a["accountcode"]

                        rddrs[accCode] = "%.2f" % float(abs(queryParams["roundoffamt"]))
                        rdcrs[partyaccountcode["accountcode"]] = "%.2f" % float(
                            abs(queryParams["roundoffamt"])
                        )
                        rd_VoucherDict = {
                            "drs": rddrs,
                            "crs": rdcrs,
                            "voucherdate": queryParams["drcrdate"],
                            "narration": "Round off amount %.2f spent"
                            % float(abs(queryParams["roundoffamt"])),
                            "vouchertype": "journal",
                            "drcrid": queryParams["drcrid"],
                        }
                        vouchersList.append(rd_VoucherDict)

                    if float(queryParams["roundoffamt"]) > 0.00:
                        # user has earned rounded of amount
                        roundAcc = con.execute(
                            select([accounts.c.accountcode]).where(
                                and_(
                                    accounts.c.defaultflag == 181,
                                    accounts.c.orgcode == orgcode,
                                )
                            )
                        )
                        roundRow = roundAcc.fetchone()

                        try:
                            accCode = roundRow["accountcode"]
                        except:
                            a = createAccount(con, 18, "Round Off Received", orgcode)
                            accCode = a["accountcode"]

                        rdcrs[accCode] = "%.2f" % float(queryParams["roundoffamt"])
                        rddrs[partyaccountcode["accountcode"]] = "%.2f" % float(
                            queryParams["roundoffamt"]
                        )

                        rd_VoucherDict = {
                            "drs": rddrs,
                            "crs": rdcrs,
                            "voucherdate": queryParams["drcrdate"],
                            "narration": "Round off amount %.2f earned"
                            % float(queryParams["roundoffamt"]),
                            "vouchertype": "journal",
                            "drcrid": queryParams["drcrid"],
                        }
                        vouchersList.append(rd_VoucherDict)

            elif (
                int(queryParams["dctypeflag"]) == 4
                and int(queryParams["inoutflag"]) == 15
            ):
                drs[partyaccountcode["accountcode"]] = queryParams["totreduct"]
                crs[discountreceivedaccountcode["accountcode"]] = totalTaxableVal
                if int(queryParams["taxflag"]) == 7 and queryParams.get("taxstate"):
                    abv = con.execute(
                        select([state.c.abbreviation]).where(
                            state.c.statename == queryParams["taxstate"]
                        )
                    )
                    abb = abv.fetchone()
                    taxName = queryParams["taxname"]
                    if taxName == "SGST":
                        for prod in queryParams["prodData"]:
                            taxRate = float(queryParams["taxes"][prod])
                            taxable = float(queryParams["reductionval"][prod])
                            if taxRate > 0.00:
                                tx = float(taxRate) / 2
                                taxHalf = taxRateDict[float(taxRate)]
                                # this is the value which is going to Dr/Cr
                                taxVal = taxable * (tx / 100) * float(queryParams["reductionval"]["quantities"][prod])
                                taxNameSGST = (
                                    "SGSTOUT_"
                                    + str(abb["abbreviation"])
                                    + "@"
                                    + str(taxHalf)
                                    + "%"
                                )
                                taxNameCGST = (
                                    "CGSTOUT_"
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
                            taxable = float(queryParams["reductionval"][prod])
                            if taxRate > 0.00:
                                tx = float(taxRate)
                                # this is the value which is going to Dr/Cr
                                taxVal = taxable * (tx / 100) * float(queryParams["reductionval"]["quantities"][prod])
                                taxNameIGST = (
                                    "IGSTOUT_"
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
                                "CESSOUT_"
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
                        crs[taxRow["accountcode"]] = "%.2f" % float(taxDict[Tax])
                else:
                    vatoutaccount = con.execute(
                        select([accounts.c.accountcode]).where(
                            and_(
                                accounts.c.accountname == "VAT_OUT",
                                accounts.c.orgcode == orgcode,
                            )
                        )
                    )
                    vatoutaccountcode = vatoutaccount.fetchone()
                    for prod in queryParams["taxes"]:
                        taxAmount = taxAmount + float(queryParams["reductionval"][prod]) * (
                            float(queryParams["taxes"][prod]) / 100
                        ) * float(queryParams["reductionval"]["quantities"][prod])
                    crs[vatoutaccountcode["accountcode"]] = "%.2f" % float(taxAmount)

                Narration = (
                    "Received Rupees "
                    + "%.2f" % float(queryParams["totreduct"])
                    + " to "
                    + str(queryParams["custname"])
                    + " ref Debit Note No. "
                    + str(queryParams["drcrno"])
                )

                voucherDict = {
                    "drs": drs,
                    "crs": crs,
                    "voucherdate": queryParams["drcrdate"],
                    "narration": Narration,
                    "vouchertype": "debitnote",
                    "drcrid": queryParams["drcrid"],
                }
                vouchersList.append(voucherDict)

                # check whether amount paid is rounded off
                if "roundoffamt" in queryParams:
                    if float(queryParams["roundoffamt"]) > 0.00:
                        # user has spent rounded of amount
                        roundAcc = con.execute(
                            select([accounts.c.accountcode]).where(
                                and_(
                                    accounts.c.defaultflag == 180,
                                    accounts.c.orgcode == orgcode,
                                )
                            )
                        )
                        roundRow = roundAcc.fetchone()

                        try:
                            accCode = roundRow["accountcode"]
                        except:
                            a = createAccount(con, 18, "Round Off Paid", orgcode)
                            accCode = a["accountcode"]

                        rddrs[accCode] = "%.2f" % float(queryParams["roundoffamt"])
                        rdcrs[partyaccountcode["accountcode"]] = "%.2f" % float(
                            queryParams["roundoffamt"]
                        )
                        rd_VoucherDict = {
                            "drs": rddrs,
                            "crs": rdcrs,
                            "voucherdate": queryParams["drcrdate"],
                            "narration": "Round off amount %.2f spent"
                            % float(queryParams["roundoffamt"]),
                            "vouchertype": "journal",
                            "drcrid": queryParams["drcrid"],
                        }
                        vouchersList.append(rd_VoucherDict)

                    if float(queryParams["roundoffamt"]) < 0.00:
                        # user has earned rounded of amount
                        roundAcc = con.execute(
                            select([accounts.c.accountcode]).where(
                                and_(
                                    accounts.c.defaultflag == 181,
                                    accounts.c.orgcode == orgcode,
                                )
                            )
                        )
                        roundRow = roundAcc.fetchone()

                        try:
                            accCode = roundRow["accountcode"]
                        except:
                            a = createAccount(con, 18, "Round Off Received", orgcode)
                            accCode = a["accountcode"]

                        rdcrs[accCode] = "%.2f" % float(abs(queryParams["roundoffamt"]))
                        rddrs[partyaccountcode["accountcode"]] = "%.2f" % float(
                            abs(queryParams["roundoffamt"])
                        )

                        rd_VoucherDict = {
                            "drs": rddrs,
                            "crs": rdcrs,
                            "voucherdate": queryParams["drcrdate"],
                            "narration": "Round off amount %.2f earned"
                            % float(abs(queryParams["roundoffamt"])),
                            "vouchertype": "journal",
                            "drcrid": queryParams["drcrid"],
                        }
                        vouchersList.append(rd_VoucherDict)

            elif (
                int(queryParams["dctypeflag"]) == 4
                and int(queryParams["inoutflag"]) == 9
            ):
                drs[partyaccountcode["accountcode"]] = queryParams["totreduct"]
                crs[discountreceivedaccountcode["accountcode"]] = totalTaxableVal
                if int(queryParams["taxflag"]) == 7 and queryParams.get("taxstate"):
                    abv = con.execute(
                        select([state.c.abbreviation]).where(
                            state.c.statename == queryParams["taxstate"]
                        )
                    )
                    abb = abv.fetchone()
                    taxName = queryParams["taxname"]
                    if taxName == "SGST":
                        for prod in queryParams["prodData"]:
                            taxRate = float(queryParams["taxes"][prod])
                            taxable = float(queryParams["reductionval"][prod])
                            if taxRate > 0.00:
                                tx = float(taxRate) / 2
                                taxHalf = taxRateDict[float(taxRate)]
                                # this is the value which is going to Dr/Cr
                                taxVal = taxable * (tx / 100) * float(queryParams["reductionval"]["quantities"][prod])
                                taxNameSGST = (
                                    "SGSTIN_"
                                    + str(abb["abbreviation"])
                                    + "@"
                                    + str(taxHalf)
                                    + "%"
                                )
                                taxNameCGST = (
                                    "CGSTIN_"
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
                            taxable = float(queryParams["reductionval"][prod])
                            if taxRate > 0.00:
                                tx = float(taxRate)
                                # this is the value which is going to Dr/Cr
                                taxVal = taxable * (tx / 100) * float(queryParams["reductionval"]["quantities"][prod])
                                taxNameIGST = (
                                    "IGSTIN_"
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
                                "CESSIN_"
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
                        crs[taxRow["accountcode"]] = "%.2f" % float(taxDict[Tax])
                else:
                    vatoutaccount = con.execute(
                        select([accounts.c.accountcode]).where(
                            and_(
                                accounts.c.accountname == "VAT_IN",
                                accounts.c.orgcode == orgcode,
                            )
                        )
                    )
                    vatoutaccountcode = vatoutaccount.fetchone()
                    for prod in queryParams["taxes"]:
                        taxAmount = taxAmount + float(queryParams["reductionval"][prod]) * (
                            float(queryParams["taxes"][prod]) / 100
                        ) * float(queryParams["reductionval"]["quantities"][prod])
                    crs[vatoutaccountcode["accountcode"]] = "%.2f" % float(taxAmount)

                Narration = (
                    "Paid Rupees "
                    + "%.2f" % float(queryParams["totreduct"])
                    + " to "
                    + str(queryParams["custname"])
                    + " ref Debit Note No. "
                    + str(queryParams["drcrno"])
                )

                voucherDict = {
                    "drs": drs,
                    "crs": crs,
                    "voucherdate": queryParams["drcrdate"],
                    "narration": Narration,
                    "vouchertype": "debitnote",
                    "drcrid": queryParams["drcrid"],
                }
                vouchersList.append(voucherDict)

                # check whether amount paid is rounded off
                if "roundoffamt" in queryParams:
                    if float(queryParams["roundoffamt"]) > 0.00:
                        # user has spent rounded of amount
                        roundAcc = con.execute(
                            select([accounts.c.accountcode]).where(
                                and_(
                                    accounts.c.defaultflag == 180,
                                    accounts.c.orgcode == orgcode,
                                )
                            )
                        )
                        roundRow = roundAcc.fetchone()

                        try:
                            accCode = roundRow["accountcode"]
                        except:
                            a = createAccount(con, 18, "Round Off Paid", orgcode)
                            accCode = a["accountcode"]

                        rddrs[accCode] = "%.2f" % float(queryParams["roundoffamt"])
                        rdcrs[partyaccountcode["accountcode"]] = "%.2f" % float(
                            queryParams["roundoffamt"]
                        )
                        rd_VoucherDict = {
                            "drs": rddrs,
                            "crs": rdcrs,
                            "voucherdate": queryParams["drcrdate"],
                            "narration": "Round off amount %.2f spent"
                            % float(queryParams["roundoffamt"]),
                            "vouchertype": "journal",
                            "drcrid": queryParams["drcrid"],
                        }
                        vouchersList.append(rd_VoucherDict)

                    if float(queryParams["roundoffamt"]) < 0.00:
                        # user has earned rounded of amount
                        roundAcc = con.execute(
                            select([accounts.c.accountcode]).where(
                                and_(
                                    accounts.c.defaultflag == 181,
                                    accounts.c.orgcode == orgcode,
                                )
                            )
                        )
                        roundRow = roundAcc.fetchone()

                        try:
                            accCode = roundRow["accountcode"]
                        except:
                            a = createAccount(con, 18, "Round Off Received", orgcode)
                            accCode = a["accountcode"]

                        rdcrs[accCode] = "%.2f" % float(abs(queryParams["roundoffamt"]))
                        rddrs[partyaccountcode["accountcode"]] = "%.2f" % float(
                            abs(queryParams["roundoffamt"])
                        )

                        rd_VoucherDict = {
                            "drs": rddrs,
                            "crs": rdcrs,
                            "voucherdate": queryParams["drcrdate"],
                            "narration": "Round off amount %.2f earned"
                            % float(abs(queryParams["roundoffamt"])),
                            "vouchertype": "journal",
                            "drcrid": queryParams["drcrid"],
                        }
                        vouchersList.append(rd_VoucherDict)

    for vch in vouchersList:
        vch["orgcode"] = orgcode

        # generate voucher number if it is not sent.

        if vch["vouchertype"] == "creditnote":
            initialType = "cr"
        if vch["vouchertype"] == "debitnote":
            initialType = "dr"
        if vch["vouchertype"] == "journal":
            initialType = "jr"
        vchCountResult = con.execute(
            "select count(vouchercode) as vcount from vouchers where orgcode = %d"
            % (int(orgcode))
        )
        vchCount = vchCountResult.fetchone()
        if vchCount["vcount"] == 0:
            initialType = initialType + "1"
        else:
            vchCodeResult = con.execute(
                "select max(vouchercode) as vcode from vouchers"
            )
            vchCode = vchCodeResult.fetchone()
            initialType = initialType + str(vchCode["vcode"])
        vch["vouchernumber"] = initialType

        result = con.execute(vouchers.insert(), [vch])
        for drkeys in list(vch["drs"].keys()):
            con.execute(
                "update accounts set vouchercount = vouchercount +1 where accountcode = %d"
                % (int(drkeys))
            )
        for crkeys in list(vch["crs"].keys()):
            con.execute(
                "update accounts set vouchercount = vouchercount +1 where accountcode = %d"
                % (int(crkeys))
            )
        vchCodes.append(initialType)
    return vchCodes
