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
"Reshma Bhatawade" <reshma_b@riseup.net>
"Sanket Kolnoorkar" <sanketf123@gmail.com>
"Rupali Badgujar" <rupalibadgujar1234@gmail.com>

"""

from gkcore import eng, enumdict
from gkcore.models.gkdb import (
    delchal,
    transaction,
    stock,
    customerandsupplier,
    godown,
    product,
    unitofmeasurement,
    dcinv,
    goprod,
    rejectionnote,
    delchalbin,
    invoice,
    invoicebin,
    log,
)
from sqlalchemy.sql import select
import json
from sqlalchemy import and_, exc, func
from pyramid.response import Response
from pyramid.view import view_defaults, view_config
from datetime import datetime, date
import jwt
import gkcore
from gkcore.utils import authCheck, getUserRole
from gkcore.views.godown.services import getusergodowns
from gkcore.views.api_invoice import getStateCode


@view_defaults(request_method="GET", renderer="json")
class api_delchal(object):
    def __init__(self, request):
        self.request = request

    @view_config(route_name="delchal")
    def getAlldelchal(self):
        try:
            token = self.request.headers["gktoken"]
        except:
            return {"gkstatus": gkcore.enumdict["UnauthorisedAccess"]}
        authDetails = authCheck(token)
        if authDetails["auth"] == False:
            return {"gkstatus": gkcore.enumdict["UnauthorisedAccess"]}

        with eng.connect() as con:
            """
            given below is the condition to check the values is delivery in,out or all.
            if inoutflag is there then it will perform the following if condition for delivery in or out. otherwise it will perform else condition
            """
            query = select([
                delchal.c.dcid,
                delchal.c.dcno,
                delchal.c.custid,
                delchal.c.dcdate,
                delchal.c.delchaltotal,
                delchal.c.roundoffflag,
                delchal.c.noofpackages,
                delchal.c.modeoftransport,
                delchal.c.attachmentcount,
                delchal.c.orgcode,
            ])
            if "inoutflag" in self.request.params:
                query = query.where(and_(
                    delchal.c.inoutflag
                    == int(self.request.params["inoutflag"]),
                    delchal.c.orgcode == authDetails["orgcode"],
                ))
            else:
                query = query.where(
                    delchal.c.orgcode == authDetails["orgcode"]
                ).order_by(delchal.c.dcno)
            result = con.execute(query)

            # Creating a godown id to godown data map, to add godown details to the delchal list data
            godata = con.execute(
                "select goid, goname from godown where orgcode = %d"
                % (authDetails["orgcode"])
            )
            gorows = godata.fetchall()
            godownMap = {}
            for gorow in gorows:
                godownMap[gorow["goid"]] = {"goname": gorow["goname"]}

            """
            An empty list is created. Details of each delivery note and customer/supplier associated with it is stored in it.
            Loop is used to go through the result, fetch customer/supplier data and append them to the list.
            Each entry in the list is in the form of a dictionary.
            """
            delchals = []
            """
            A list of all godowns assigned to a user is retreived from API for godowns using the method usergodowmns.
            If user is not a godown keeper this list will be empty.
            If user has godowns assigned, only those delivery notes for moving goods into those godowns are appended into the above list.
            """
            usergodowmns = getusergodowns(con, authDetails["userid"])["gkresult"]
            godowns = []
            for godown in usergodowmns:
                godowns.append(godown["goid"])
            for row in result:
                # if delchal is linked to invoice, it shouldn't be cancelled. canceldelchal = 1 (if cancellable), 0 (if uncancellable)
                canceldelchal = 1
                invid = con.execute(
                    select([dcinv.c.invid])
                    .where(and_(
                        dcinv.c.dcid == row["dcid"],
                        dcinv.c.orgcode == authDetails["orgcode"],
                    ))
                ).scalar()
                immutable_data = {}
                if invid:
                    canceldelchal = 0
                    immutable_data_id = con.execute(
                        select([invoice.c.immutable_data_id])
                        .where(invoice.c.invid == invid)
                    ).scalar()
                    immutable_data = con.execute(
                        select([transaction.c.transaction_details])
                        .where(transaction.c.transaction_id == immutable_data_id)
                    ).scalar()

                delchalgodown = con.execute(
                    select([stock.c.goid]).where(
                        and_(
                            stock.c.dcinvtnid == row["dcid"],
                            stock.c.dcinvtnflag == 4,
                        )
                    )
                )
                delchalgodata = delchalgodown.fetchone()
                delchalgoid = delchalgodata["goid"]
                proceed = False
                if usergodowmns:
                    if delchalgoid in godowns:
                        # If the user has godowns assigned, then only those delchals mapped to the user godowns will be returned
                        proceed = True
                else:
                    # If the user has no godowns assigned to them, then all delivery challans will be returned
                    proceed = True
                if proceed:
                    custdata = con.execute(
                        select(
                            [
                                customerandsupplier.c.custname,
                                customerandsupplier.c.csflag,
                            ]
                        ).where(customerandsupplier.c.custid == row["custid"])
                    )
                    custrow = custdata.fetchone()
                    delchaltotal = float(row["delchaltotal"])
                    if row["roundoffflag"]:
                        delchaltotal = round(delchaltotal)
                    delchals.append(
                        {
                            "dcid": row["dcid"],
                            "dcno": row["dcno"],
                            "total": delchaltotal,
                            "custname": custrow["custname"],
                            "csflag": custrow["csflag"],
                            "dcdate": datetime.strftime(row["dcdate"], "%d-%m-%Y"),
                            "attachmentcount": row["attachmentcount"],
                            "goname": godownMap[delchalgoid]["goname"] or "",
                            "canceldelchal": canceldelchal,
                            "immutable_data": immutable_data,
                        }
                    )
            return {"gkstatus": gkcore.enumdict["Success"], "gkresult": delchals}

    """
    create method for delchal resource.
    stock table is also updated after delchal entry is made.
        -delchal id goes in dcinvtnid column of stock table.
        -dcinvtnflag column will be set to 4 for delivery challan entry.
    If stock table insert fails then the delchal entry will be deleted.
    It also returns 'dcid' to front end.
    """
    @view_config(route_name="delchal", request_method="POST")
    def adddelchal(self):
        try:
            token = self.request.headers["gktoken"]
        except:
            return {"gkstatus": gkcore.enumdict["UnauthorisedAccess"]}
        authDetails = authCheck(token)
        if authDetails["auth"] == False:
            return {"gkstatus": enumdict["UnauthorisedAccess"]}
        with eng.begin() as con:
            dataset = self.request.json_body
            delchaldata = dataset["delchaldata"]
            stockdata = dataset["stockdata"]
            freeqty = delchaldata["freeqty"]
            inoutflag = stockdata["inout"]
            items = delchaldata["contents"]
            delchaldata["orgcode"] = authDetails["orgcode"]
            stockdata["orgcode"] = authDetails["orgcode"]
            if delchaldata["dcflag"] == 19:
                delchaldata["issuerid"] = authDetails["userid"]
            result = con.execute(delchal.insert(), [delchaldata])
            if result.rowcount != 1:
                return {"gkstatus": gkcore.enumdict["ConnectionFailed"]}

            dciddata = con.execute(
                select([delchal.c.dcid, delchal.c.dcdate]).where(
                    and_(
                        delchal.c.orgcode == authDetails["orgcode"],
                        delchal.c.dcno == delchaldata["dcno"],
                        delchal.c.custid == delchaldata["custid"],
                    )
                )
            )
            dcidrow = dciddata.fetchone()
            stockdata["dcinvtnid"] = dcidrow["dcid"]
            stockdata["dcinvtnflag"] = 4
            stockdata["stockdate"] = dcidrow["dcdate"]
            for key in list(items.keys()):
                itemQty = float(list(items[key].values())[0])
                itemRate = float(list(items[key].keys())[0])
                stockdata["rate"] = itemRate
                stockdata["productcode"] = key
                stockdata["qty"] = itemQty + float(freeqty[key])
                result = con.execute(stock.insert(), [stockdata])
                if "goid" in stockdata:
                    resultgoprod = con.execute(
                        select([goprod]).where(
                            and_(
                                goprod.c.goid == stockdata["goid"],
                                goprod.c.productcode == key,
                            )
                        )
                    )
                    if resultgoprod.rowcount == 0:
                        result = con.execute(
                            goprod.insert(),
                            [
                                {
                                    "goid": stockdata["goid"],
                                    "productcode": key,
                                    "goopeningstock": 0.00,
                                    "orgcode": authDetails["orgcode"],
                                }
                            ],
                        )
            return {
                "gkstatus": enumdict["Success"],
                "gkresult": dcidrow["dcid"],
            }

    @view_config(route_name="delchal_dcid", request_method="PUT")
    def editdelchal(self):
        try:
            token = self.request.headers["gktoken"]
        except:
            return {"gkstatus": gkcore.enumdict["UnauthorisedAccess"]}
        authDetails = authCheck(token)
        if authDetails["auth"] == False:
            return {"gkstatus": enumdict["UnauthorisedAccess"]}
        with eng.begin() as con:
            dcid = self.request.matchdict["dcid"]
            dataset = self.request.json_body
            delchaldata = dataset["delchaldata"]
            discount = delchaldata["discount"]
            stockdata = dataset["stockdata"]
            delchaldata["orgcode"] = authDetails["orgcode"]
            stockdata["orgcode"] = authDetails["orgcode"]
            stockdata["dcinvtnid"] = dcid
            stockdata["stockdate"] = delchaldata["dcdate"]
            freeqty = delchaldata["freeqty"]
            stockdata["dcinvtnflag"] = 4
            result = con.execute(
                delchal.update().where(delchal.c.dcid == dcid).values(delchaldata)
            )
            if result.rowcount != 1:
                return {"gkstatus": gkcore.enumdict["ConnectionFailed"]}

            result = con.execute(
                stock.delete().where(
                    and_(
                        stock.c.dcinvtnid == dcid,
                        stock.c.dcinvtnflag == 4,
                    )
                )
            )
            items = delchaldata["contents"]
            for key in list(items.keys()):
                itemQty = float(list(items[key].values())[0])
                itemRate = float(list(items[key].keys())[0])
                itemTotalDiscount = float(discount.get(key, 0))
                itemDiscount = 0
                if itemQty:
                    itemDiscount = itemTotalDiscount / itemQty
                stockdata["rate"] = itemRate - itemDiscount
                stockdata["productcode"] = key
                stockdata["qty"] = itemQty + float(freeqty[key])
                result = con.execute(stock.insert(), [stockdata])
            return {"gkstatus": enumdict["Success"]}

    # Below function is used to cancel the delivery note entry from delchal table using dcid and stored in delchalbin table. Also delete stock entry for same dcid.
    @view_config(route_name="delchal_dcid", request_method="DELETE")
    def cancelDelchal(self):
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
                dcid = self.request.matchdict["dcid"]
                # To fetch data of all data of cancel delivery note.
                delchalData = self.con.execute(
                    select([delchal]).where(delchal.c.dcid == dcid)
                )
                delchaldata = delchalData.fetchone()
                # Add all data of cancel delivery note into delchalbin
                delchalbinData = {
                    "dcid": delchaldata["dcid"],
                    "dcno": delchaldata["dcno"],
                    "dcdate": delchaldata["dcdate"],
                    "dcflag": delchaldata["dcflag"],
                    "taxflag": delchaldata["taxflag"],
                    "contents": delchaldata["contents"],
                    "tax": delchaldata["tax"],
                    "cess": delchaldata["cess"],
                    "issuername": delchaldata["issuername"],
                    "designation": delchaldata["designation"],
                    "noofpackages": delchaldata["noofpackages"],
                    "modeoftransport": delchaldata["modeoftransport"],
                    "consignee": delchaldata["consignee"],
                    "taxstate": delchaldata["taxstate"],
                    "sourcestate": delchaldata["sourcestate"],
                    "orgstategstin": delchaldata["orgstategstin"],
                    "freeqty": delchaldata["freeqty"],
                    "discount": delchaldata["discount"],
                    "vehicleno": delchaldata["vehicleno"],
                    "dateofsupply": delchaldata["dateofsupply"],
                    "delchaltotal": delchaldata["delchaltotal"],
                    "attachmentcount": delchaldata["attachmentcount"],
                    "orgcode": delchaldata["orgcode"],
                    "custid": delchaldata["custid"],
                    "orderid": delchaldata["orderid"],
                    "inoutflag": delchaldata["inoutflag"],
                    "roundoffflag": delchaldata["roundoffflag"],
                    "discflag": delchaldata["discflag"],
                    "dcnarration": delchaldata["dcnarration"],
                    "totalinword": delchaldata["totalinword"],
                }
                if delchaldata["attachment"] != None:
                    delchalbinData["attachment"] = delchaldata["attachment"]
                try:
                    # To add goid for cancelled delivery note in delchalbin table before deleting stock entry.
                    delgodown = self.con.execute(
                        "select goid from stock where dcinvtnid = %d and orgcode=%d and dcinvtnflag=4"
                        % (int(dcid), authDetails["orgcode"])
                    )
                    degodowninfo = delgodown.fetchone()
                    if degodowninfo != None:
                        delchalbinData["goid"] = degodowninfo["goid"]
                except:
                    pass
                try:
                    # To delete stock entry of cancel delivery note.
                    self.con.execute(
                        "delete from stock  where dcinvtnid = %d and orgcode=%d and dcinvtnflag=4"
                        % (int(dcid), authDetails["orgcode"])
                    )
                except:
                    pass
                try:
                    logdata = {}
                    logdata["orgcode"] = authDetails["orgcode"]
                    logdata["userid"] = authDetails["userid"]
                    logdata["time"] = datetime.today().strftime("%Y-%m-%d")
                    logdata["activity"] = (
                        str(delchaldata["dcno"]) + " Delivery Note Cancelled"
                    )
                    result = self.con.execute(log.insert(), [logdata])
                except:
                    pass

                dcbin = self.con.execute(delchalbin.insert(), [delchalbinData])

                # To delete delivery note enrty from delchal table
                self.con.execute(
                    "delete from delchal  where dcid = %d and orgcode=%d"
                    % (int(dcid), authDetails["orgcode"])
                )
                return {"gkstatus": enumdict["Success"]}

            except:
                try:
                    dcid = self.request.matchdict["dcid"]
                    # if delivery note entry is not deleted then delete that delivery note from delchalbin table
                    self.con.execute(
                        "delete from delchalbin  where dcid = %d and orgcode=%d"
                        % (int(dcid), authDetails["orgcode"])
                    )
                    return {"gkstatus": enumdict["ConnectionFailed"]}
                except:
                    self.con.close()
                    return {"gkstatus": enumdict["ConnectionFailed"]}
            finally:
                self.con.close()

    @view_config(route_name="delchal_dcid")
    def getdelchal(self):
        """
        This function returns the single delivery challan data to frontend depending on 'dcid;.
        if for given dcid 'contents' field not available then 'stockdata' will be returned, else 'delchalContents' will be returned.
        we also return the 'delchalflag' for 'Old' and 'new' deliverychallan. for 'Old deliverychallan' delchalflag is '15',
        and for 'New deliverychallan' delchalflag is '14'.
        """
        try:
            token = self.request.headers["gktoken"]
        except:
            return {"gkstatus": gkcore.enumdict["UnauthorisedAccess"]}
        authDetails = authCheck(token)
        if authDetails["auth"] == False:
            return {"gkstatus": gkcore.enumdict["UnauthorisedAccess"]}
        with eng.connect() as con:
            if not self.request.matchdict["dcid"]:
                return {"gkstatus": gkcore.enumdict["ConnectionFailed"]}
            dcid = self.request.matchdict["dcid"]
            result = con.execute(
                select([delchal]).where(delchal.c.dcid == dcid)
            )
            delchaldata = result.fetchone()
            items = {}
            if delchaldata["cancelflag"] == 1:
                flag = 40
            else:
                flag = 4
            stockdata = con.execute(
                select(
                    [stock.c.productcode, stock.c.qty, stock.c.inout, stock.c.goid]
                ).where(
                    and_(
                        stock.c.dcinvtnflag == flag,
                        stock.c.dcinvtnid == dcid,
                    )
                )
            )
            for stockrow in stockdata:
                stockinout = stockrow["inout"]
                goiddata = stockrow["goid"]
            if stockdata.rowcount == 0:
                return {
                    "gkstatus": gkcore.enumdict["Success"],
                    "gkresult": {},
                }
            singledelchal = {
                "delchaldata": {
                    "dcid": delchaldata["dcid"],
                    "dcno": delchaldata["dcno"],
                    "dcflag": delchaldata["dcflag"],
                    "issuername": delchaldata["issuername"],
                    "designation": delchaldata["designation"],
                    "orggstin": delchaldata["orgstategstin"],
                    "dcdate": datetime.strftime(delchaldata["dcdate"], "%d-%m-%Y"),
                    "taxflag": delchaldata["taxflag"],
                    "cancelflag": delchaldata["cancelflag"],
                    "noofpackages": delchaldata["noofpackages"],
                    "modeoftransport": delchaldata["modeoftransport"],
                    "vehicleno": delchaldata["vehicleno"],
                    "attachmentcount": delchaldata["attachmentcount"],
                    "inoutflag": delchaldata["inoutflag"],
                    "inout": stockinout,
                    "dcnarration": delchaldata["dcnarration"],
                    "roundoffflag": delchaldata["roundoffflag"],
                    "totalinword": delchaldata["totalinword"],
                    "dcnarration": delchaldata["dcnarration"],
                }
            }

            if delchaldata["consignee"] != None:
                singledelchal["delchaldata"]["consignee"] = delchaldata["consignee"]
            if delchaldata["delchaltotal"] != None:
                singledelchal["delchaldata"]["delchaltotal"] = "%.2f" % (
                    float(delchaldata["delchaltotal"])
                )
                singledelchal["delchaldata"]["roundedoffvalue"] = "%.2f" % (
                    float(round(delchaldata["delchaltotal"]))
                )

            if delchaldata["cancelflag"] == 1:
                singledelchal["delchaldata"]["canceldate"] = datetime.strftime(
                    delchaldata["canceldate"], "%d-%m-%Y"
                )

            if goiddata != None:
                godata = con.execute(
                    select(
                        [godown.c.goname, godown.c.state, godown.c.goaddr]
                    ).where(godown.c.goid == goiddata)
                )
                goname = godata.fetchone()
                singledelchal["delchaldata"]["goid"] = goiddata
                singledelchal["delchaldata"]["goname"] = goname["goname"]
                singledelchal["delchaldata"]["gostate"] = goname["state"]
                singledelchal["delchaldata"]["goaddr"] = goname["goaddr"]
            else:
                singledelchal["delchaldata"]["goid"] = ""

            if delchaldata["taxstate"]:
                singledelchal["destinationstate"] = delchaldata["taxstate"]
                taxStateCode = getStateCode(delchaldata["taxstate"], con)[
                    "statecode"
                ]
                singledelchal["taxstatecode"] = taxStateCode

            if delchaldata["sourcestate"]:
                singledelchal["sourcestate"] = delchaldata["sourcestate"]
                singledelchal["sourcestatecode"] = getStateCode(
                    delchaldata["sourcestate"], con
                )["statecode"]
                sourceStateCode = getStateCode(
                    delchaldata["sourcestate"], con
                )["statecode"]

            if delchaldata["dateofsupply"] != None:
                singledelchal["dateofsupply"] = datetime.strftime(
                    delchaldata["dateofsupply"], "%d-%m-%Y"
                )
            else:
                singledelchal["dateofsupply"] = ""

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
                ).where(customerandsupplier.c.custid == delchaldata["custid"])
            )
            custData = custandsup.fetchone()
            custsupstatecode = None
            if custData["state"]:
                custsupstatecode = getStateCode(custData["state"], con)[
                    "statecode"
                ]
            singledelchal["custSupDetails"] = {
                "custname": custData["custname"],
                "custsupstate": custData["state"],
                "custaddr": custData["custaddr"],
                "csflag": custData["csflag"],
                "pincode": custData["pincode"],
                "custsupstatecode": custsupstatecode,
            }
            singledelchal["custSupDetails"]["custid"] = delchaldata["custid"]
            if custData["custtan"] != None:
                singledelchal["custSupDetails"]["custtin"] = custData["custtan"]
                if custData["gstin"] != None:
                    if int(delchaldata["inoutflag"]) == 15:
                        try:
                            singledelchal["custSupDetails"]["custgstin"] = custData[
                                "gstin"
                            ][str(taxStateCode)]
                        except:
                            singledelchal["custSupDetails"]["custgstin"] = None
                    else:
                        try:
                            singledelchal["custSupDetails"]["custgstin"] = custData[
                                "gstin"
                            ][str(sourceStateCode)]
                        except:
                            singledelchal["custSupDetails"]["custgstin"] = None

            # ..........................................Delchal ProductCode Info....................
            # contents is a nested dictionary from invoice table.
            # It contains productcode as the key with a value as a dictionary.
            # this dictionary has two key value pairs, priceperunit and quantity.
            if delchaldata["contents"] == None:
                singledelchal["delchalflag"] = 15
                stockdata = con.execute(
                    select(
                        [
                            stock.c.productcode,
                            stock.c.qty,
                            stock.c.inout,
                            stock.c.goid,
                        ]
                    ).where(
                        and_(
                            stock.c.dcinvtnflag == flag,
                            stock.c.dcinvtnid == dcid,
                        )
                    )
                )
            for stockrow in stockdata:
                productdata = con.execute(
                    select([product.c.productdesc, product.c.uomid]).where(
                        and_(
                            product.c.productcode == stockrow["productcode"],
                            product.c.gsflag == 7,
                        )
                    )
                )
                productdesc = productdata.fetchone()
                uomresult = con.execute(
                    select([unitofmeasurement.c.unitname]).where(
                        unitofmeasurement.c.uomid == productdesc["uomid"]
                    )
                )
                unitnamrrow = uomresult.fetchone()
                items[stockrow["productcode"]] = {
                    "qty": "%.2f" % float(stockrow["qty"]),
                    "productdesc": productdesc["productdesc"],
                    "unitname": unitnamrrow["unitname"],
                }
            singledelchal["stockdata"] = items
            if delchaldata["contents"] != None:
                singledelchal["delchalflag"] = 14
                contentsData = delchaldata["contents"]
                # delchalContents is the final dictionary which will not just have the dataset from original contents,
                # but also productdesc,unitname,freeqty,discount,taxname,taxrate,amount and taxamount
                delchalContents = {}
                # get the dictionary of discount and access it inside the loop for one product each.
                # do the same with freeqty.
                totalDisc = 0.00
                totalTaxableVal = 0.00
                totalTaxAmt = 0.00
                totalCessAmt = 0.00
                discounts = delchaldata["discount"]
                freeqtys = delchaldata["freeqty"]
                # now looping through the contents.
                # pc will have the productcode which will be the key in delchalContents.
                for pc in list(contentsData.keys()):
                    # freeqty and discount can be 0 as these field were not present in previous version of 4.25 hence we have to check if it is None or not and have to pass values accordingly for code optimization.
                    if discounts != None:
                        # discflag is for discount type: 16=Percent, 1=Amount
                        # here we convert percent discount in to amount.
                        if delchaldata["discflag"] == 16:
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
                    # uomid=unit of measurement
                    prod = con.execute(
                        select(
                            [
                                product.c.productdesc,
                                product.c.uomid,
                                product.c.gsflag,
                                product.c.gscode,
                                product.c.productcode,
                            ]
                        ).where(product.c.productcode == pc)
                    )
                    prodrow = prod.fetchone()
                    goid_result = con.execute(
                        select([stock.c.goid]).where(
                            and_(
                                stock.c.productcode == pc,
                                stock.c.orgcode == authDetails["orgcode"],
                            )
                        )
                    )
                    goid = goid_result.scalar()
                    # For 'Goods'
                    if int(prodrow["gsflag"]) == 7:
                        um = con.execute(
                            select([unitofmeasurement.c.unitname]).where(
                                unitofmeasurement.c.uomid == int(prodrow["uomid"])
                            )
                        )
                        unitrow = um.fetchone()
                        unitofMeasurement = unitrow["unitname"]
                        taxableAmount = (
                            (
                                float(
                                    contentsData[pc][
                                        list(contentsData[pc].keys())[0]
                                    ]
                                )
                            )
                            * float(list(contentsData[pc].keys())[0])
                        ) - float(discount)
                    # For 'Service'
                    else:
                        unitofMeasurement = ""
                        taxableAmount = float(
                            list(contentsData[pc].keys())[0]
                        ) - float(discount)

                    taxRate = 0.00
                    totalAmount = 0.00
                    taxRate = float(delchaldata["tax"][pc])
                    if int(delchaldata["taxflag"]) == 22:
                        taxRate = float(delchaldata["tax"][pc])
                        taxAmount = taxableAmount * float(taxRate / 100)
                        taxname = "VAT"
                        totalAmount = float(taxableAmount) + (
                            float(taxableAmount) * float(taxRate / 100)
                        )
                        totalDisc = totalDisc + float(discount)
                        totalTaxableVal = totalTaxableVal + taxableAmount
                        totalTaxAmt = totalTaxAmt + taxAmount
                        delchalContents[pc] = {
                            "proddesc": prodrow["productdesc"],
                            "gscode": prodrow["gscode"],
                            "uom": unitofMeasurement,
                            "qty": "%.2f"
                            % (
                                float(
                                    contentsData[pc][
                                        list(contentsData[pc].keys())[0]
                                    ]
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
                            "productCode": prodrow["productcode"],
                            "gsflag": prodrow["gsflag"],
                            "goid": goid,
                        }

                    else:
                        cessRate = 0.00
                        cessAmount = 0.00
                        cessVal = 0.00
                        taxname = ""
                        if delchaldata["cess"]:
                            cessVal = float(delchaldata["cess"][pc])
                            cessAmount = taxableAmount * (cessVal / 100)
                            totalCessAmt = totalCessAmt + cessAmount

                        if delchaldata["sourcestate"] != delchaldata["taxstate"]:
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

                        delchalContents[pc] = {
                            "proddesc": prodrow["productdesc"],
                            "gscode": prodrow["gscode"],
                            "uom": unitofMeasurement,
                            "qty": "%.2f"
                            % (
                                float(
                                    contentsData[pc][
                                        list(contentsData[pc].keys())[0]
                                    ]
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
                            "productCode": prodrow["productcode"],
                            "gsflag": prodrow["gsflag"],
                            "goid": goid,
                        }
                singledelchal["totaldiscount"] = "%.2f" % (float(totalDisc))
                singledelchal["totaltaxablevalue"] = "%.2f" % (
                    float(totalTaxableVal)
                )
                singledelchal["totaltaxamt"] = "%.2f" % (float(totalTaxAmt))
                singledelchal["totalcessamt"] = "%.2f" % (float(totalCessAmt))
                singledelchal["taxname"] = taxname
                singledelchal["delchalContents"] = delchalContents
                singledelchal["discflag"] = delchaldata["discflag"]
            invoice_id = con.execute(
                select([dcinv.c.invid])
                .where(dcinv.c.dcid == dcid)
            ).scalar()
            immutable_data_id = con.execute(
                select([invoice.c.immutable_data_id])
                .where(invoice.c.invid == invoice_id)
            ).scalar()
            immutable_data = con.execute(
                select([transaction.c.transaction_details])
                .where(transaction.c.transaction_id == immutable_data_id)
            ).scalar()
            singledelchal["immutable_data"] = immutable_data
            return {
                "gkstatus": gkcore.enumdict["Success"],
                "gkresult": singledelchal,
            }

    @view_config(route_name="delchal_cancel_dcid")
    def getcanceldelchal(self):
        """
        This function returns the single delivery challan data to frontend depending on 'dcid'.
        if for given dcid 'contents' field not available then 'stockdata' will be returned, else 'delchalContents' will be returned.
        we also return the 'delchalflag' for 'Old' and 'new' deliverychallan. for 'Old deliverychallan' delchalflag is '15',
        and for 'New deliverychallan' delchalflag is '14'.
        """
        try:
            token = self.request.headers["gktoken"]
        except:
            return {"gkstatus": gkcore.enumdict["UnauthorisedAccess"]}
        authDetails = authCheck(token)
        if authDetails["auth"] == False:
            return {"gkstatus": gkcore.enumdict["UnauthorisedAccess"]}
        with eng.connect() as con:
            result = con.execute(
                select([delchalbin]).where(
                    delchalbin.c.dcid == self.request.matchdict["dcid"]
                )
            )
            delchaldata = result.fetchone()
            items = {}
            goiddata = delchaldata["goid"]
            singledelchal = {
                "delchaldata": {
                    "dcid": delchaldata["dcid"],
                    "dcno": delchaldata["dcno"],
                    "dcflag": delchaldata["dcflag"],
                    "issuername": delchaldata["issuername"],
                    "designation": delchaldata["designation"],
                    "orggstin": delchaldata["orgstategstin"],
                    "dcdate": datetime.strftime(delchaldata["dcdate"], "%d-%m-%Y"),
                    "taxflag": delchaldata["taxflag"],
                    "noofpackages": delchaldata["noofpackages"],
                    "modeoftransport": delchaldata["modeoftransport"],
                    "vehicleno": delchaldata["vehicleno"],
                    "attachmentcount": delchaldata["attachmentcount"],
                    "dcnarration": delchaldata["dcnarration"],
                    "inoutflag": delchaldata["inoutflag"],
                    "roundoffflag": delchaldata["roundoffflag"],
                    "totalinword": delchaldata["totalinword"],
                }
            }

            if delchaldata["consignee"] != None:
                singledelchal["delchaldata"]["consignee"] = delchaldata["consignee"]
            if delchaldata["delchaltotal"] != None:
                singledelchal["delchaldata"]["delchaltotal"] = "%.2f" % float(
                    delchaldata["delchaltotal"]
                )
                singledelchal["delchaldata"]["roundedoffvalue"] = "%.2f" % float(
                    round(delchaldata["delchaltotal"])
                )

            if goiddata != None:
                godata = con.execute(
                    select(
                        [godown.c.goname, godown.c.state, godown.c.goaddr]
                    ).where(godown.c.goid == goiddata)
                )
                goname = godata.fetchone()
                singledelchal["delchaldata"]["goid"] = goiddata
                singledelchal["delchaldata"]["goname"] = goname["goname"]
                singledelchal["delchaldata"]["gostate"] = goname["state"]
                singledelchal["delchaldata"]["goaddr"] = goname["goaddr"]
            else:
                singledelchal["delchaldata"]["goid"] = ""

            if delchaldata["taxstate"]:
                singledelchal["destinationstate"] = delchaldata["taxstate"]
                taxStateCode = getStateCode(delchaldata["taxstate"], con)[
                    "statecode"
                ]
                singledelchal["taxstatecode"] = taxStateCode

            if delchaldata["sourcestate"]:
                singledelchal["sourcestate"] = delchaldata["sourcestate"]
                singledelchal["sourcestatecode"] = getStateCode(
                    delchaldata["sourcestate"], con
                )["statecode"]
                sourceStateCode = getStateCode(
                    delchaldata["sourcestate"], con
                )["statecode"]

            if delchaldata["dateofsupply"] != None:
                singledelchal["dateofsupply"] = datetime.strftime(
                    delchaldata["dateofsupply"], "%d-%m-%Y"
                )
            else:
                singledelchal["dateofsupply"] = ""

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
                ).where(customerandsupplier.c.custid == delchaldata["custid"])
            )
            custData = custandsup.fetchone()
            custsupstatecode = getStateCode(custData["state"], con)[
                "statecode"
            ]
            singledelchal["custSupDetails"] = {
                "custname": custData["custname"],
                "custsupstate": custData["state"],
                "custaddr": custData["custaddr"],
                "csflag": custData["csflag"],
                "pincode": custData["pincode"],
                "custsupstatecode": custsupstatecode,
            }
            singledelchal["custSupDetails"]["custid"] = delchaldata["custid"]
            if custData["custtan"] != None:
                singledelchal["custSupDetails"]["custtin"] = custData["custtan"]
                if custData["gstin"] != None:
                    if int(delchaldata["inoutflag"]) == 15:
                        try:
                            singledelchal["custSupDetails"]["custgstin"] = custData[
                                "gstin"
                            ][str(taxStateCode)]
                        except:
                            singledelchal["custSupDetails"]["custgstin"] = None
                    else:
                        try:
                            singledelchal["custSupDetails"]["custgstin"] = custData[
                                "gstin"
                            ][str(sourceStateCode)]
                        except:
                            singledelchal["custSupDetails"]["custgstin"] = None



            immutable_data_id = con.execute(
                select([invoicebin.c.immutable_data_id])
                .where(
                    invoicebin.c.dcinfo["dcno"].astext == delchaldata["dcno"]
                )
            ).scalar()
            immutable_data = {}
            if immutable_data_id:
                immutable_data = con.execute(
                    select([transaction.c.transaction_details])
                    .where(transaction.c.transaction_id == immutable_data_id)
                ).scalar()
            singledelchal["immutable_data"] = immutable_data

            # ..........................................Delchal ProductCode Info....................
            if delchaldata["contents"] != None:
                singledelchal["delchalflag"] = 14
                contentsData = delchaldata["contents"]

                delchalContents = {}

                totalDisc = 0.00
                totalTaxableVal = 0.00
                totalTaxAmt = 0.00
                totalCessAmt = 0.00
                discounts = delchaldata["discount"]
                freeqtys = delchaldata["freeqty"]
                # now looping through the contents.
                # pc will have the productcode which will be the key in delchalContents.
                for pc in list(contentsData.keys()):
                    if discounts != None:
                        discount = discounts[pc]
                    else:
                        discount = 0.00

                    if freeqtys != None:
                        freeqty = freeqtys[pc]
                    else:
                        freeqty = 0.00
                    # uomid=unit of measurement
                    prod = con.execute(
                        select(
                            [
                                product.c.productdesc,
                                product.c.productcode,
                                product.c.uomid,
                                product.c.gsflag,
                                product.c.gscode,
                            ]
                        ).where(product.c.productcode == pc)
                    )
                    prodrow = prod.fetchone()
                    # For 'Goods'
                    if int(prodrow["gsflag"]) == 7:
                        um = con.execute(
                            select([unitofmeasurement.c.unitname]).where(
                                unitofmeasurement.c.uomid == int(prodrow["uomid"])
                            )
                        )
                        unitrow = um.fetchone()
                        unitofMeasurement = unitrow["unitname"]
                        taxableAmount = (
                            (
                                float(
                                    contentsData[pc][
                                        list(contentsData[pc].keys())[0]
                                    ]
                                )
                            )
                            * float(list(contentsData[pc].keys())[0])
                        ) - float(discount)
                    # For 'Service'
                    else:
                        unitofMeasurement = ""
                        taxableAmount = float(
                            list(contentsData[pc].keys())[0]
                        ) - float(discount)

                    taxRate = 0.00
                    totalAmount = 0.00
                    taxRate = float(delchaldata["tax"][pc])
                    if int(delchaldata["taxflag"]) == 22:
                        taxRate = float(delchaldata["tax"][pc])
                        taxAmount = taxableAmount * float(taxRate / 100)
                        taxname = "VAT"
                        totalAmount = float(taxableAmount) + (
                            float(taxableAmount) * float(taxRate / 100)
                        )
                        totalDisc = totalDisc + float(discount)
                        totalTaxableVal = totalTaxableVal + taxableAmount
                        totalTaxAmt = totalTaxAmt + taxAmount
                        delchalContents[pc] = {
                            "proddesc": prodrow["productdesc"],
                            "gscode": prodrow["gscode"],
                            "uom": unitofMeasurement,
                            "qty": "%.2f"
                            % (
                                float(
                                    contentsData[pc][
                                        list(contentsData[pc].keys())[0]
                                    ]
                                )
                            ),
                            "freeqty": "%.2f" % (float(freeqty)),
                            "priceperunit": "%.2f"
                            % (float(list(contentsData[pc].keys())[0])),
                            "discount": "%.2f" % (float(discount)),
                            "taxableamount": "%.2f" % (float(taxableAmount)),
                            "totalAmount": "%.2f" % (float(totalAmount)),
                            "taxname": "VAT",
                            "productCode": prodrow["productcode"],
                            "taxrate": "%.2f" % (float(taxRate)),
                            "taxamount": "%.2f" % (float(taxAmount)),
                        }

                    else:
                        cessRate = 0.00
                        cessAmount = 0.00
                        cessVal = 0.00
                        taxname = ""
                        if delchaldata["cess"]:
                            cessVal = float(delchaldata["cess"][pc])
                            cessAmount = taxableAmount * (cessVal / 100)
                            totalCessAmt = totalCessAmt + cessAmount

                        if delchaldata["sourcestate"] != delchaldata["taxstate"]:
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

                        delchalContents[pc] = {
                            "proddesc": prodrow["productdesc"],
                            "gscode": prodrow["gscode"],
                            "uom": unitofMeasurement,
                            "qty": "%.2f"
                            % (
                                float(
                                    contentsData[pc][
                                        list(contentsData[pc].keys())[0]
                                    ]
                                )
                            ),
                            "freeqty": "%.2f" % (float(freeqty)),
                            "priceperunit": "%.2f"
                            % (float(list(contentsData[pc].keys())[0])),
                            "discount": "%.2f" % (float(discount)),
                            "taxableamount": "%.2f" % (float(taxableAmount)),
                            "totalAmount": "%.2f" % (float(totalAmount)),
                            "taxname": taxname,
                            "taxrate": "%.2f" % (float(taxRate)),
                            "taxamount": "%.2f" % (float(taxAmount)),
                            "productCode": prodrow["productcode"],
                            "cess": "%.2f" % (float(cessAmount)),
                            "cessrate": "%.2f" % (float(cessVal)),
                        }
                singledelchal["totaldiscount"] = "%.2f" % (float(totalDisc))
                singledelchal["totaltaxablevalue"] = "%.2f" % (
                    float(totalTaxableVal)
                )
                singledelchal["totaltaxamt"] = "%.2f" % (float(totalTaxAmt))
                singledelchal["totalcessamt"] = "%.2f" % (float(totalCessAmt))
                singledelchal["taxname"] = taxname
                singledelchal["delchalContents"] = delchalContents
                singledelchal["discflag"] = delchaldata["discflag"]

            return {
                "gkstatus": gkcore.enumdict["Success"],
                "gkresult": singledelchal,
            }

    # This function returns list of cancelled delivery notes.
    @view_config(route_name="delchal_cancel")
    def listofCancelDelchal(self):
        try:
            token = self.request.headers["gktoken"]
        except:
            return {"gkstatus": enumdict["UnauthorisedAccess"]}
        authDetails = authCheck(token)
        if authDetails["auth"] == False:
            return {"gkstatus": enumdict["UnauthorisedAccess"]}
        with eng.connect() as con:
            orgcode = authDetails["orgcode"]
            if "inputdate" in self.request.params:
                dataset = {
                    "inputdate": self.request.params["inputdate"],
                    "del_cancelled_type": self.request.params["del_cancelled_type"],
                }
            else:
                dataset = self.request.json_body
            inout = self.request.params["inout"]
            inputdate = dataset["inputdate"]
            del_cancelled_type = dataset["del_cancelled_type"]
            new_inputdate = dataset["inputdate"]
            new_inputdate = datetime.strptime(new_inputdate, "%Y-%m-%d")
            dc_unbilled = []
            alldcids = None
            # Adding the query here only, which will select the dcids either with "delivery-out" type or "delivery-in".
            if inout == "i":  # in
                if del_cancelled_type == "0":
                    alldcids = con.execute(
                        select([delchalbin])
                        .where(
                            and_(
                                delchalbin.c.orgcode == orgcode,
                                delchalbin.c.inoutflag == 9,
                                delchalbin.c.dcdate <= new_inputdate,
                            )
                        )
                        .order_by(delchalbin.c.dcdate)
                    )
                else:
                    alldcids = con.execute(
                        select([delchalbin])
                        .where(
                            and_(
                                delchalbin.c.orgcode == orgcode,
                                delchalbin.c.inoutflag == 9,
                                delchalbin.c.dcflag == int(del_cancelled_type),
                                delchalbin.c.dcdate <= new_inputdate,
                            )
                        )
                        .order_by(delchalbin.c.dcdate)
                    )
            if inout == "o":  # out
                if del_cancelled_type == "0":
                    alldcids = con.execute(
                        select([delchalbin])
                        .where(
                            and_(
                                delchalbin.c.orgcode == orgcode,
                                delchalbin.c.inoutflag == 15,
                                delchalbin.c.dcdate <= new_inputdate,
                            )
                        )
                        .order_by(delchalbin.c.dcdate)
                    )
                else:
                    alldcids = con.execute(
                        select([delchalbin])
                        .where(
                            and_(
                                delchalbin.c.orgcode == orgcode,
                                delchalbin.c.inoutflag == 15,
                                delchalbin.c.dcflag == int(del_cancelled_type),
                                delchalbin.c.dcdate <= new_inputdate,
                            )
                        )
                        .order_by(delchalbin.c.dcdate)
                    )
            alldcids = alldcids.fetchall()
            dcdata = []
            srno = 1
            for row in alldcids:
                immutable_data_id = con.execute(
                    select([invoicebin.c.immutable_data_id])
                    .where(
                        invoicebin.c.dcinfo["dcno"].astext == row["dcno"]
                    )
                ).scalar()
                immutable_data = {}
                if immutable_data_id:
                    immutable_data = con.execute(
                        select([transaction.c.transaction_details])
                        .where(transaction.c.transaction_id == immutable_data_id)
                    ).scalar()
                godown = ""
                cresult = con.execute(
                    select(
                        [
                            customerandsupplier.c.custname,
                            customerandsupplier.c.csflag,
                        ]
                    ).where(customerandsupplier.c.custid == row["custid"])
                )
                customerdetails = cresult.fetchone()
                if row["goid"] != None:
                    godownres = con.execute(
                        "select goname, goaddr from godown where goid = %d"
                        % int(row["goid"])
                    )
                    godownresult = godownres.fetchone()
                    if godownresult != None:
                        godownname = godownresult["goname"]
                        godownaddrs = godownresult["goaddr"]
                        godown = godownname + "(" + godownaddrs + ")"
                    else:
                        godownname = ""
                        godownaddrs = ""
                        godown = ""
                if row["dcflag"] == 1:
                    dcflag = "Approval"
                elif row["dcflag"] == 3:
                    dcflag = "Consignment"
                elif row["dcflag"] == 4:
                    dcflag = "Sale"
                elif row["dcflag"] == 16:
                    dcflag = "Purchase"
                elif row["dcflag"] == 19:
                    # We don't have to consider sample.
                    dcflag = "Sample"
                elif row["dcflag"] == 6:
                    # we ignore this as well
                    dcflag = "Free Replacement"
                else:
                    dcflag = "Bad Input"
                singledcdata = {
                    "dcid": row["dcid"],
                    "dcno": row["dcno"],
                    "total": float(row["delchaltotal"]),
                    "dcdate": datetime.strftime(row["dcdate"], "%d-%m-%Y"),
                    "dcflag": dcflag,
                    "inoutflag": row["inoutflag"],
                    "custname": customerdetails["custname"],
                    "goname": godown,
                    "srno": srno,
                    "immutable_data": immutable_data,
                }
                dcdata.append(singledcdata)
                srno += 1
            return {"gkstatus": enumdict["Success"], "gkresult": dcdata}

    @view_config(route_name="delchal_last")
    def getLastDelChalDetails(self):
        try:
            """
            Purpose:
            returns a last created note no. of Deliverychallan.
            Returns a json dictionary containing that Deliverychallan.
            """
            token = self.request.headers["gktoken"]
        except:
            return {"gkstatus": enumdict["UnauthorisedAccess"]}
        authDetails = authCheck(token)
        if authDetails["auth"] == False:
            return {"gkstatus": enumdict["UnauthorisedAccess"]}
        with eng.connect() as con:
            deliverychallandata = {"dcdate": "", "dcno": ""}
            dcstatus = int(self.request.params["status"])
            result = con.execute(
                select([delchal.c.dcno, delchal.c.dcdate]).where(
                    delchal.c.dcid
                    == (
                        select([func.max(stock.c.dcinvtnid)]).where(
                            and_(
                                stock.c.inout == dcstatus,
                                stock.c.dcinvtnflag == 4,
                                stock.c.orgcode == authDetails["orgcode"],
                            )
                        )
                    )
                )
            )
            row = result.fetchone()
            if row != None:
                deliverychallandata["dcdate"] = datetime.strftime(
                    (row["dcdate"]), "%d-%m-%Y"
                )
                deliverychallandata["dcno"] = row["dcno"]
            return {
                "gkstatus": enumdict["Success"],
                "gkresult": deliverychallandata,
            }

    @view_config(route_name="delchal_next_id")
    def getdelchalid(self):
        try:
            token = self.request.headers["gktoken"]
        except:
            return {"gkstatus": gkcore.enumdict["UnauthorisedAccess"]}
        authDetails = authCheck(token)
        if authDetails["auth"] == False:
            return {"gkstatus": gkcore.enumdict["UnauthorisedAccess"]}
        with eng.connect() as con:
            dcstatus = int(self.request.params["status"])
            dc_count = con.execute(
                select([func.count(delchal.c.dcid)]).where(
                    and_(
                        delchal.c.inoutflag == dcstatus,
                        delchal.c.orgcode == authDetails["orgcode"],
                    )
                )
            ).scalar()
            dcbin_count = con.execute(
                select([func.count(delchalbin.c.dcid)]).where(
                    and_(
                        delchalbin.c.inoutflag == dcstatus,
                        delchalbin.c.orgcode == authDetails["orgcode"],
                    )
                )
            ).scalar()
            dcid = int(dc_count) + int(dcbin_count) + 1
            return {"gkstatus": 0, "dcid": dcid}

    @view_config(route_name="delchal_invid")
    def getinviddetails(self):
        try:
            token = self.request.headers["gktoken"]
        except:
            return {"gkstatus": gkcore.enumdict["UnauthorisedAccess"]}
        authDetails = authCheck(token)
        if authDetails["auth"] == False:
            return {"gkstatus": gkcore.enumdict["UnauthorisedAccess"]}
        with eng.connect() as con:
            dcid = self.request.matchdict["dcid"]
            delchalresult = con.execute(
                select([dcinv.c.invid]).where(
                    dcinv.c.dcid == dcid
                )
            )
            deliveryinfo = delchalresult.scalar()
            return {"gkstatus": 0, "data": deliveryinfo}

    @view_config(route_name="delchal_attachment")
    def getdelchalattachment(self):
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
            dcid = self.request.matchdict["dcid"]
            delchalData = con.execute(
                select(
                    [delchal.c.dcno, delchal.c.attachment, delchal.c.cancelflag]
                ).where(and_(delchal.c.dcid == dcid))
            )
            attachment = delchalData.fetchone()
            return {
                "gkstatus": enumdict["Success"],
                "gkresult": attachment["attachment"],
                "dcno": attachment["dcno"],
                "cancelflag": attachment["cancelflag"],
                "userrole": urole["userrole"],
            }

    @view_config(route_name="delchal", request_param="action=getdcinvprods")
    def getdcinvproducts(self):
        try:
            token = self.request.headers["gktoken"]
        except:
            return {"gkstatus": enumdict["UnauthorisedAccess"]}
        authDetails = authCheck(token)
        if authDetails["auth"] == False:
            return {"gkstatus": enumdict["UnauthorisedAccess"]}
        with eng.connect() as con:
            dcid = self.request.params["dcid"]
            items = {}
            delchalresult = con.execute(
                select([delchal.c.contents, delchal.c.freeqty]).where(
                    delchal.c.dcid == dcid
                )
            )
            deliveryinfo = delchalresult.fetchone()
            freeprod = deliveryinfo["freeqty"]
            proddata = deliveryinfo["contents"]
            for pc in list(proddata.keys()):
                productdata = con.execute(
                    select(
                        [product.c.productdesc, product.c.uomid, product.c.gscode]
                    ).where(
                        and_(product.c.productcode == pc, product.c.gsflag == 7)
                    )
                )
                productdesc = productdata.fetchone()
                uomresult = con.execute(
                    select([unitofmeasurement.c.unitname]).where(
                        unitofmeasurement.c.uomid == productdesc["uomid"]
                    )
                )
                unitnamrrow = uomresult.fetchone()
                items[int(pc)] = {
                    "qty": float(
                        "%.2f" % float(proddata[pc][list(proddata[pc].keys())[0]])
                    ),
                    "productdesc": productdesc["productdesc"],
                    "unitname": unitnamrrow["unitname"],
                    "gscode": productdesc["gscode"],
                }
            for frep in list(freeprod.keys()):
                items[int(frep)]["freeqty"] = float("%.2f" % float(freeprod[frep]))

            result = con.execute(
                select([dcinv.c.invid, dcinv.c.invprods]).where(
                    dcinv.c.dcid == dcid
                )
            )
            linkedinvoices = result.fetchall()
            # linkedinvoices refers to the invoices which are associated with the delivery challan whose id = dcid.
            for invoiceid in linkedinvoices:
                invresult = con.execute(
                    select([invoice.c.contents, invoice.c.freeqty]).where(
                        invoice.c.invid == invoiceid["invid"]
                    )
                )
                invoiceinfo = invresult.fetchone()
                freeprodinv = invoiceinfo["freeqty"]
                proddatainv = invoiceinfo["contents"]
                for pc in list(proddatainv.keys()):
                    try:
                        items[int(pc)]["qty"] -= float(
                            "%.2f"
                            % float(
                                proddatainv[pc][list(proddatainv[pc].keys())[0]]
                            )
                        )
                    except:
                        pass
                for pc in list(freeprodinv.keys()):
                    try:
                        items[int(pc)]["freeqty"] -= float(
                            "%.2f" % float(freeprodinv[pc])
                        )
                    except:
                        pass

            allrnidres = con.execute(
                select([rejectionnote.c.rnid])
                .distinct()
                .where(
                    and_(
                        rejectionnote.c.orgcode == authDetails["orgcode"],
                        rejectionnote.c.dcid == dcid,
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
                            stock.c.orgcode == authDetails["orgcode"],
                            stock.c.dcinvtnflag == 18,
                            stock.c.dcinvtnid == rnid[0],
                        )
                    )
                )
                temp = temp.fetchall()
                rnprodresult.append(temp)
            for row in rnprodresult:
                try:
                    for prodc, qty in row:
                        items[int(prodc)]["qty"] -= float(qty)
                except:
                    pass
            if len(linkedinvoices) != 0 or len(rnprodresult) != 0:
                for productcode in list(items.keys()):
                    if items[productcode]["qty"] == 0:
                        del items[productcode]
            return {"gkstatus": enumdict["Success"], "gkresult": items}
