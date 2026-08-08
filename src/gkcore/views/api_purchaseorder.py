"""
Copyright (C) 2013, 2014, 2015, 2016 Digital Freedom Foundation
Copyright (C) 2017, 2018, 2019, 2020 Digital Freedom Foundation & Accion Labs Pvt. Ltd.
This file is part of GNUKhata:A modular,robust anhd Free Accounting System.

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
"Abhijith Balan" <abhijith@dff.org.in>
"Pornima Kolte <pornima@openmailbox.org>"
"Prajkta Patkar<prajkta.patkar007@gmail.com>"
"Pravin Dake" <pravindake24@gmail.com>
"""

from pyramid.view import view_defaults, view_config
from gkcore.utils import authCheck
from gkcore import eng, enumdict
from gkcore.models.gkdb import (
    purchaseorder,
    transaction,
    stock,
    product,
    customerandsupplier,
    unitofmeasurement,
    godown,
    tax,
    state,
    users,
)
from gkcore.views.organisation.services import get_organisation_profile
from sqlalchemy.sql import select, distinct
from sqlalchemy import func, desc
import json
from sqlalchemy import and_, exc
from datetime import datetime, date
import jwt
import gkcore


def getStateCode(StateName, con):
    stateData = con.execute(
        select([state.c.statecode]).where(state.c.statename == StateName)
    )
    staterow = stateData.fetchone()
    return {"statecode": staterow["statecode"]}


@view_defaults(route_name="purchaseorder", request_method="GET", renderer="json")
class api_purchaseorder(object):
    def __init__(self, request):
        self.request = request
        print("Purchase order initialized")

    @view_config(request_method="POST")
    def addPoSo(self):
        try:
            token = self.request.headers["gktoken"]
        except:
            return {"gkstatus": enumdict["UnauthorisedAccess"]}
        authDetails = authCheck(token)
        if authDetails["auth"] == False:
            return {"gkstatus": enumdict["UnauthorisedAccess"]}
        with eng.begin() as con:
            dataset = self.request.json_body
            dataset["orgcode"] = authDetails["orgcode"]
            godown_id = dataset["togodown"]
            godown_details = con.execute(
                select([godown])
                .where(godown.c.goid==godown_id)
            ).fetchone()
            contact_id = dataset["csid"]
            contact_details = con.execute(
                select([customerandsupplier])
                .where(customerandsupplier.c.custid == contact_id)
            ).fetchone()
            product_id_values = list(dataset["schedule"].keys())
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
            dataset["immutable_data_id"] = transaction_id[0]
            con.execute(purchaseorder.insert(), [dataset])
            orderIdData = con.execute(
                select([purchaseorder.c.orderid]).where(
                    and_(
                        purchaseorder.c.orderno == dataset["orderno"],
                        purchaseorder.c.orderdate == dataset["orderdate"],
                        purchaseorder.c.orgcode == dataset["orgcode"] ,
                    )
                )
            )
            orderIdRow = orderIdData.fetchone()
            return {
                "gkstatus": enumdict["Success"],
                "gkresult": orderIdRow["orderid"],
            }

    @view_config(route_name="purchaseorder")
    def getAllPoSoData(self):
        """This function returns all existing PO and SO"""
        try:
            token = self.request.headers["gktoken"]
        except:
            return {"gkstatus": enumdict["UnauthorisedAccess"]}
        authDetails = authCheck(token)
        if authDetails["auth"] == False:
            return {"gkstatus": enumdict["UnauthorisedAccess"]}
        with eng.connect() as con:
            query = select([
                purchaseorder.c.orderid,
                purchaseorder.c.orderdate,
                purchaseorder.c.orderno,
                purchaseorder.c.csid,
                purchaseorder.c.attachmentcount,
                purchaseorder.c.purchaseordertotal,
                purchaseorder.c.immutable_data_id,
            ])
            if "psflag" in self.request.params:
                query = query.where(and_(
                    purchaseorder.c.orgcode == authDetails["orgcode"],
                    purchaseorder.c.psflag
                    == "%d" % int(self.request.params["psflag"]),
                )).order_by(purchaseorder.c.orderdate)
            else:
                query = query.where(
                    purchaseorder.c.orgcode == authDetails["orgcode"]
                ).order_by(purchaseorder.c.orderdate)
            result = con.execute(query)
            allposo = []
            for row in result:
                custdata = con.execute(
                    select([customerandsupplier.c.custname, customerandsupplier.c.csflag]).where(
                        customerandsupplier.c.custid == row["csid"]
                    )
                )
                custrow = custdata.fetchone()
                immutable_data = con.execute(
                    select([transaction.c.transaction_details])
                    .where(transaction.c.transaction_id == row["immutable_data_id"])
                ).scalar()
                allposo.append(
                    {
                        "orderid": row["orderid"],
                        "orderno": row["orderno"],
                        "orderdate": datetime.strftime(
                            row["orderdate"], "%d-%m-%Y"
                        ),
                        "attachmentcount": row["attachmentcount"],
                        "immutable_data": immutable_data,
                        "customer": custrow["custname"],
                        "ordertotal": float(row["purchaseordertotal"]),
                        "csflag":  custrow["csflag"],
                    }
                )
            return {"gkstatus": enumdict["Success"], "gkresult": allposo}

    @view_config(request_param="poso=single")
    def getSingleposo(self):
        try:
            token = self.request.headers["gktoken"]
        except:
            return {"gkstatus": gkcore.enumdict["UnauthorisedAccess"]}
        authDetails = authCheck(token)
        if authDetails["auth"] == False:
            return {"gkstatus": gkcore.enumdict["UnauthorisedAccess"]}
        with eng.connect() as con:
            result = con.execute(
                select([purchaseorder]).where(
                    purchaseorder.c.orderid == self.request.params["orderid"]
                )
            )
            podata = result.fetchone()
            purchaseorderdetails = {
                "orderno": podata["orderno"],
                "orderdate": datetime.strftime(podata["orderdate"], "%d-%m-%Y"),
                "creditperiod": podata["creditperiod"],
                "payterms": podata["payterms"],
                "modeoftransport": podata["modeoftransport"],
                "psflag": podata["psflag"],
                "csid": podata["csid"],
                "taxflag": podata["taxflag"],
                "tax": podata["tax"],
                "purchaseordertotal": "%.2f" % float(podata["purchaseordertotal"]),
                "pototalwords": podata["pototalwords"],
                "orgstategstin": podata["orgstategstin"],
                "consignee": podata["consignee"],
                "reversecharge": podata["reversecharge"],
                "bankdetails": podata["bankdetails"],
                "vehicleno": podata["vehicleno"],
                "paymentmode": podata["paymentmode"],
                "orgcode": podata["orgcode"],
                "roundoffflag": podata["roundoffflag"],
                "roundedoffvalue": "%.2f"
                % float(round(podata["purchaseordertotal"])),
            }
            if podata["address"] != None:
                purchaseorderdetails["address"] = podata["address"]
            if podata["pincode"] != None:
                purchaseorderdetails["pincode"] = podata["pincode"]
            if podata["dateofsupply"] != None:
                purchaseorderdetails["dateofsupply"] = datetime.strftime(
                    podata["dateofsupply"], "%d-%m-%Y"
                )
            if podata["psflag"] == 16:
                purchaseorderdetails["issuername"] = podata["issuername"]
                purchaseorderdetails["designation"] = podata["designation"]
                purchaseorderdetails["address"] = podata["address"]

            # If sourcestate and taxstate are present.
            if podata["sourcestate"]:
                purchaseorderdetails["sourcestate"] = podata["sourcestate"]
                purchaseorderdetails["sourcestatecode"] = getStateCode(
                    podata["sourcestate"], con
                )["statecode"]
                sourceStateCode = getStateCode(podata["sourcestate"], con)[
                    "statecode"
                ]
            if podata["taxstate"]:
                purchaseorderdetails["destinationstate"] = podata["taxstate"]
                taxStateCode = getStateCode(podata["taxstate"], con)[
                    "statecode"
                ]
                purchaseorderdetails["taxstatecode"] = taxStateCode
            if podata["togodown"] != None:
                godowndata = con.execute(
                    select([godown.c.goname, godown.c.goaddr]).where(
                        and_(
                            godown.c.goid == podata["togodown"],
                            godown.c.orgcode == authDetails["orgcode"],
                        )
                    )
                )
                godowndetails = godowndata.fetchone()
                purchaseorderdetails["goname"] = godowndetails["goname"]
                purchaseorderdetails["goaddr"] = godowndetails["goaddr"]
            # Customer And Supplier details
            custandsup = con.execute(
                select(
                    [
                        customerandsupplier.c.custname,
                        customerandsupplier.c.state,
                        customerandsupplier.c.custaddr,
                        customerandsupplier.c.custtan,
                        customerandsupplier.c.pincode,
                        customerandsupplier.c.gstin,
                        customerandsupplier.c.csflag,
                    ]
                ).where(customerandsupplier.c.custid == podata["csid"])
            )
            custData = custandsup.fetchone()
            custsupstatecode = None
            if custData["state"]:
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
                            str(custsupstatecode)
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
            purchaseorderdetails["custSupDetails"] = custSupDetails
            schedule = podata["schedule"]
            details = {}  # Stores schedule
            totalDisc = 0.00
            totalTaxableVal = 0.00
            totalTaxAmt = 0.00
            totalCessAmt = 0.00
            discounts = podata["discount"]
            freeqtys = podata["freeqty"]
            for productCode in schedule:
                if discounts != None:
                    discount = discounts[productCode]
                else:
                    discount = 0.00

                if freeqtys != None:
                    freeqty = freeqtys[productCode]
                else:
                    freeqty = 0.00
                # Productname and unitofMeasurement depending on productcode.
                prod = con.execute(
                    select(
                        [
                            product.c.productdesc,
                            product.c.uomid,
                            product.c.gsflag,
                            product.c.gscode,
                            product.c.productcode,
                        ]
                    ).where(product.c.productcode == productCode)
                )
                prodrow = prod.fetchone()
                goid_result = con.execute(
                        select([stock.c.goid]).where(
                            and_(
                                stock.c.productcode == productCode,
                                stock.c.orgcode == authDetails["orgcode"],
                            )
                        )
                    )
                goid = goid_result.scalar()
                if int(prodrow["gsflag"]) == 7:
                    um = con.execute(
                        select([unitofmeasurement.c.unitname]).where(
                            unitofmeasurement.c.uomid == int(prodrow["uomid"])
                        )
                    )
                    unitrow = um.fetchone()
                    unitofMeasurement = unitrow["unitname"]
                    taxableAmount = (
                        (float(schedule[productCode]["rateperunit"]))
                        * float(schedule[productCode]["quantity"])
                    ) - float(discount)
                else:
                    unitofMeasurement = ""
                    taxableAmount = float(
                        schedule[productCode]["rateperunit"]
                    ) - float(discount)
                taxRate = 0.00
                totalAmount = 0.00
                taxRate = float(podata["tax"][productCode])
                if int(podata["taxflag"]) == 22:
                    taxRate = float(podata["tax"][productCode])
                    taxAmount = taxableAmount * float(taxRate / 100)
                    taxname = "VAT"
                    totalAmount = float(taxableAmount) + (
                        float(taxableAmount) * float(taxRate / 100)
                    )
                    totalDisc = totalDisc + float(podata["discount"][productCode])
                    totalTaxableVal = totalTaxableVal + taxableAmount
                    totalTaxAmt = totalTaxAmt + taxAmount
                    details[productCode] = {
                        "proddesc": prodrow["productdesc"],
                        "gscode": prodrow["gscode"],
                        "uom": unitofMeasurement,
                        "qty": "%.2f" % (float(schedule[productCode]["quantity"])),
                        "freeqty": "%.2f" % (float(freeqty)),
                        "priceperunit": "%.2f"
                        % (float(schedule[productCode]["rateperunit"])),
                        "discount": "%.2f" % (float(discount)),
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
                    if podata["cess"]:
                        cessVal = float(podata["cess"][productCode])
                        cessAmount = taxableAmount * (cessVal / 100)
                        totalCessAmt = totalCessAmt + cessAmount

                    if podata["sourcestate"] != podata["taxstate"]:
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

                    totalDisc = totalDisc + float(podata["discount"][productCode])
                    totalTaxableVal = totalTaxableVal + taxableAmount
                    totalTaxAmt = totalTaxAmt + taxAmount

                    details[productCode] = {
                        "proddesc": prodrow["productdesc"],
                        "gscode": prodrow["gscode"],
                        "gsflag": prodrow["gsflag"],
                        "uom": unitofMeasurement,
                        "qty": "%.2f" % (float(schedule[productCode]["quantity"])),
                        "freeqty": "%.2f" % (float(freeqty)),
                        "priceperunit": "%.2f"
                        % (float(schedule[productCode]["rateperunit"])),
                        "discount": "%.2f" % (float(discount)),
                        "taxableamount": "%.2f" % (float(taxableAmount)),
                        "totalAmount": "%.2f" % (float(totalAmount)),
                        "taxname": taxname,
                        "taxrate": "%.2f" % (float(taxRate)),
                        "taxamount": "%.2f" % (float(taxAmount)),
                        "cess": "%.2f" % (float(cessAmount)),
                        "cessrate": "%.2f" % (float(cessVal)),
                        "productCode": prodrow["productcode"],
                        "gsflag": prodrow["gsflag"],
                        "goid": goid,
                    }
                if "staggered" in schedule[productCode]:
                    details[productCode]["staggered"] = schedule[productCode][
                        "staggered"
                    ]
            purchaseorderdetails["totaldiscount"] = "%.2f" % (float(totalDisc))
            purchaseorderdetails["totaltaxablevalue"] = "%.2f" % (
                float(totalTaxableVal)
            )
            purchaseorderdetails["totaltaxamt"] = "%.2f" % (float(totalTaxAmt))
            purchaseorderdetails["totalcessamt"] = "%.2f" % (float(totalCessAmt))
            purchaseorderdetails["taxname"] = taxname
            purchaseorderdetails["schedule"] = details
            purchaseorderdetails["psnarration"] = podata["psnarration"]
            immutable_data = con.execute(
                select([transaction.c.transaction_details])
                .where(transaction.c.transaction_id == podata["immutable_data_id"])
            ).scalar()
            purchaseorderdetails["immutable_data"] = immutable_data
            return {
                "gkstatus": enumdict["Success"],
                "gkresult": purchaseorderdetails,
            }

    @view_config(request_param="attach=image")
    def getattachment(self):
        try:
            token = self.request.headers["gktoken"]
        except:
            return {"gkstatus": enumdict["UnauthorisedAccess"]}
        authDetails = authCheck(token)
        if authDetails["auth"] == False:
            return {"gkstatus": enumdict["UnauthorisedAccess"]}
        with eng.connect() as con:
            orderid = self.request.params["orderid"]
            purchaseorderData = con.execute(
                select([purchaseorder.c.orderno, purchaseorder.c.attachment]).where(
                    and_(purchaseorder.c.orderid == orderid)
                )
            )
            attachment = purchaseorderData.fetchone()
            return {
                "gkstatus": enumdict["Success"],
                "gkresult": attachment["attachment"],
                "orderno": attachment["orderno"],
            }

    @view_config(request_method="PUT")
    def editPurchaseOrder(self):
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
                purchaseorder.update()
                .where(purchaseorder.c.orderid == dataset["orderid"])
                .values(dataset)
            )
            return {"gkstatus": enumdict["Success"]}

    @view_config(request_method="DELETE")
    def deletePurchaseOrder(self):
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
                purchaseorder.delete().where(
                    purchaseorder.c.orderid == dataset["orderid"]
                )
            )
            return {"gkstatus": enumdict["Success"]}
