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
"Ankita Chakrabarti"<chakrabarti.ankita94@gmail.com>
"Sai Karthik"<kskarthik@disrot.org>

"""
from gkcore import eng, enumdict
from gkcore.utils import authCheck
from .schemas import GodownRegister
from pyramid.view import view_defaults, view_config
from gkcore.models.gkdb import (
    organisation,
    delchal,
    invoice,
    customerandsupplier,
    stock,
    product,
    transfernote,
    goprod,
    dcinv,
    rejectionnote,
    drcr,
    godown,
)
from sqlalchemy.sql import select, and_, or_
from datetime import datetime
from sqlalchemy.sql.functions import func
from gkcore.views.reports.helpers.stock import (
    calculateStockValue,
    stockonhandfun,
    godownwise_stock_on_hand,
)

@view_defaults(request_method="GET", renderer="json_extended")
class api_godownregister(object):
    def __init__(self, request):
        self.request = request

    @view_config(route_name="godown-register")
    def godown_register(self):
        # Check whether the user is registered & valid
        try:
            token = self.request.headers["gktoken"]
        except:
            return {"gkstatus": enumdict["UnauthorisedAccess"]}

        auth_details = authCheck(token)

        if auth_details["auth"] == False:
            return {"gkstatus": enumdict["UnauthorisedAccess"]}

        goproddetails = None
        godownstock = []
        godown_items = []
        goid = self.request.matchdict["goid"]

        # Connecting to the DB table goprod & filtering the data for required org & godown
        with eng.connect() as con:
            result = con.execute(
                select([goprod]).where(
                    and_(
                        goprod.c.orgcode == auth_details["orgcode"],
                        goprod.c.goid == goid,
                    )
                )
            )
            goproddetails = result.fetchall()

        # Connecting to the DB table product & filtering the data for the required productcode

            for productid in goproddetails:
                result = eng.connect().execute(
                    select([product]).where(
                        product.c.productcode == productid["productcode"]
                    )
                )
                godownstock.append(result.fetchone())

        # Formatting the fetched data

            for p in godownstock:
                temp_dict = dict()
                for name, val in p.items():
                    value_type = str(type(val))
                    if value_type == "<class 'decimal.Decimal'>":
                        temp_dict[name] = str(val)
                    else:
                        temp_dict[name] = val
                godown_items.append(temp_dict)

        return {"gkstatus": enumdict["Success"], "gkresult": godown_items}


    @view_config(route_name="product-register")
    def godownStockReport(self):
        """
        Purpose:
        Return the structured data grid of stock report for given product.
        Input will be productcode,startdate,enddate and goid.
        orgcode will be taken from header and startdate and enddate of fianancial year taken from organisation table .
        returns a list of dictionaries where every dictionary will be one row.
        description:
        This function returns the complete stock report,
        including opening stock every inward and outward quantity and running balance for every transaction along with transaction type for a selected product and godown.
        at the end we get total inward and outward quantity.
        This report will be on the basis of productcode, startdate and enddate given from the client.
        The orgcode is taken from the header.
        The report will query database to get all in and out records for the given product where the dcinvtn flag is not 20.
        For every iteration of this list with a for loop we will find out the date of transaction from the delchal or invoice table depending on the flag being 4 or 9.
        Cash memo is in the invoice table so even 3 will qualify.
        Then we wil find the customer or supplyer name on the basis of given data.
        Note that if the startdate is same as the yearstart of the organisation then opening stock can be directly taken from the product table.
        if it is later than the startyear then we will have to come to the closing balance of the day before startdate given by client and use it as the opening balance.
        The row will be represented in this grid with every key denoting a column.
        The columns (keys) will be,
        date,particulars,invoice/dcno, transaction type (invoice /delchal),inward quantity,outward quantity ,total inward quantity , total outwrd quanity and balance.
        """
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
                dataset = GodownRegister(**self.request.params).model_dump()
                productCode = dataset["productcode"]
                godownCode = dataset["goid"]
                # Following date to datetime convert hack exists because other related
                # queries were using datetime format.
                startDate = datetime.strptime(str(dataset["startdate"]), "%Y-%m-%d")
                endDate = datetime.strptime(str(dataset["enddate"]), "%Y-%m-%d")
                stockReport = []
                totalinward = 0.00
                totaloutward = 0.00
                gopeningStock = 0.00
                godown_stock_value = 0.00
                goopeningStockResult = con.execute(
                    select([goprod.c.goopeningstock, goprod.c.openingstockvalue]).where(
                        and_(
                            goprod.c.productcode == productCode,
                            goprod.c.goid == godownCode,
                            goprod.c.orgcode == orgcode,
                        )
                    )
                ).fetchone()
                if goopeningStockResult:
                    gopeningStock = goopeningStockResult["goopeningstock"]
                    godown_stock_value = goopeningStockResult["openingstockvalue"]

                gopeningStock = float(gopeningStock)
                godown_stock_value = float(godown_stock_value)

                # inoutflag query param is used to filter entries by sales and purchases
                # 9 -> purchase, 15 -> sales, 0 -> all.
                inoutflag = [dataset.get("inoutflag")]
                if not dataset.get("inoutflag"):
                    inoutflag = [9, 15]
                stockRecords = con.execute(
                    select([stock])
                    .where(
                        and_(
                            stock.c.productcode == productCode,
                            stock.c.goid == godownCode,
                            stock.c.orgcode == orgcode,
                            stock.c.inout.in_(inoutflag),
                        )
                    )
                    .order_by(stock.c.stockdate)
                )
                stockData = stockRecords.fetchall()
                ysData = con.execute(
                    select([organisation.c.yearstart]).where(
                        organisation.c.orgcode == orgcode
                    )
                )
                ysRow = ysData.fetchone()
                yearStart = datetime.strptime(str(ysRow["yearstart"]), "%Y-%m-%d")
                if startDate > yearStart:
                    for stockRow in stockData:
                        if stockRow["inout"] == 9:
                            gopeningStock += float(stockRow["qty"])
                            godown_stock_value += float(stockRow["qty"] * stockRow["rate"])
                        if stockRow["inout"] == 15:
                            gopeningStock -= float(stockRow["qty"])
                            godown_stock_value -= float(stockRow["qty"] * stockRow["rate"])
                        if stockRow["dcinvtnflag"] in [2, 18]:
                            if stockRow["inout"] == 9:
                                totalinward = float(totalinward) + float(
                                    stockRow["qty"]
                                )
                            if stockRow["inout"] == 15:
                                totaloutward = float(totaloutward) + float(
                                    stockRow["qty"]
                                )
                stockReport.append(
                    {
                        "date": "",
                        "particulars": "opening stock",
                        "trntype": "",
                        "dcid": "",
                        "dcno": "",
                        "invid": "",
                        "invno": "",
                        "tnid": "",
                        "tnno": "",
                        "rnid": "",
                        "rnno": "",
                        "inward": "%.2f" % float(gopeningStock),
                        "balance": "%.2f" % float(gopeningStock),
                        "balance_value": godown_stock_value,
                    }
                )
                totalinward = totalinward + float(gopeningStock)

                for finalRow in stockData:
                    date = ""
                    particulars = ""
                    trntype = ""
                    dcid = ""
                    dcno = ""
                    rnid = ""
                    rnno = ""
                    invid = ""
                    invno = ""
                    drcrid = ""
                    drcrno = ""
                    icflag = ""
                    tnid = ""
                    tnno = ""
                    inwardqty = ""
                    outwardqty = ""
                    balance = ""
                    balance_value = ""
                    if finalRow["inout"] == 9:
                        gopeningStock += float(finalRow["qty"])
                        godown_stock_value += float(finalRow["qty"] * finalRow["rate"])
                        inwardqty = finalRow["qty"]
                        totalinward += float(inwardqty)
                    if finalRow["inout"] == 15:
                        gopeningStock -= float(finalRow["qty"])
                        godown_stock_value -= float(finalRow["qty"] * finalRow["rate"])
                        outwardqty = finalRow["qty"]
                        totaloutward += float(outwardqty)
                    balance = "%.2f" % float(gopeningStock)
                    balance_value = "%.2f" % float(godown_stock_value)
                    if finalRow["dcinvtnflag"] == 4:
                        countresult = con.execute(
                            select(
                                [delchal.c.dcdate, delchal.c.dcno, delchal.c.custid]
                            ).where(
                                and_(
                                    delchal.c.dcdate >= startDate,
                                    delchal.c.dcdate <= endDate,
                                    delchal.c.dcid == finalRow["dcinvtnid"],
                                )
                            )
                        )
                        if countresult.rowcount == 1:
                            countrow = countresult.fetchone()
                            custdata = con.execute(
                                select([customerandsupplier.c.custname]).where(
                                    customerandsupplier.c.custid == countrow["custid"]
                                )
                            )
                            custrow = custdata.fetchone()
                            dcinvresult = con.execute(
                                select([dcinv.c.invid]).where(
                                    dcinv.c.dcid == finalRow["dcinvtnid"]
                                )
                            )
                            date = countrow["dcdate"]
                            particulars = custrow["custname"]
                            dcid = finalRow["dcinvtnid"]
                            dcno = countrow["dcno"]
                            if dcinvresult.rowcount == 1:
                                dcinvrow = dcinvresult.fetchone()
                                invresult = con.execute(
                                    select(
                                        [invoice.c.invoiceno, invoice.c.icflag]
                                    ).where(invoice.c.invid == dcinvrow["invid"])
                                )
                                """ No need to check if invresult has rowcount 1 since it must be 1 """
                                invrow = invresult.fetchone()
                                invid = dcinvrow["invid"]
                                invno = invrow["invoiceno"]
                                icflag = invrow["icflag"]
                                trntype = "delchal&invoice"
                            else:
                                trntype = "delchal"

                    if finalRow["dcinvtnflag"] == 20:
                        countresult = con.execute(
                            select(
                                [
                                    transfernote.c.transfernotedate,
                                    transfernote.c.transfernoteno,
                                    transfernote.c.fromgodown,
                                    transfernote.c.togodown,
                                ]
                            ).where(
                                and_(
                                    transfernote.c.transfernotedate >= startDate,
                                    transfernote.c.transfernotedate <= endDate,
                                    transfernote.c.transfernoteid
                                    == finalRow["dcinvtnid"],
                                )
                            )
                        )
                        trntype = "transfer note"
                        tnid = finalRow["dcinvtnid"]
                        if countresult.rowcount == 1:
                            countrow = countresult.fetchone()

                            from_godown_id = countrow["fromgodown"]
                            to_godown_id = countrow["togodown"]
                            from_godown, to_godown = con.execute(
                                    select([godown.c.goname])
                                    .where(godown.c.goid.in_([from_godown_id, to_godown_id]))
                                ).fetchall()

                            particulars = (
                                f"Transfer from {from_godown['goname']} to {to_godown['goname']}"
                            )

                            tnno = countrow["transfernoteno"]
                            date = countrow["transfernotedate"]

                    if finalRow["dcinvtnflag"] == 18:
                        countresult = con.execute(
                            select(
                                [
                                    rejectionnote.c.rndate,
                                    rejectionnote.c.rnno,
                                    rejectionnote.c.dcid,
                                    rejectionnote.c.invid,
                                ]
                            ).where(
                                and_(
                                    rejectionnote.c.rndate >= startDate,
                                    rejectionnote.c.rndate <= endDate,
                                    rejectionnote.c.rnid == finalRow["dcinvtnid"],
                                )
                            )
                        )
                        if countresult.rowcount == 1:
                            countrow = countresult.fetchone()
                            if countrow["dcid"] != None:
                                custdata = con.execute(
                                    select([customerandsupplier.c.custname]).where(
                                        customerandsupplier.c.custid
                                        == (
                                            select([delchal.c.custid]).where(
                                                delchal.c.dcid == countrow["dcid"]
                                            )
                                        )
                                    )
                                )
                            elif countrow["invid"] != None:
                                custdata = con.execute(
                                    select([customerandsupplier.c.custname]).where(
                                        customerandsupplier.c.custid
                                        == (
                                            select([invoice.c.custid]).where(
                                                invoice.c.invid == countrow["invid"]
                                            )
                                        )
                                    )
                                )
                            custrow = custdata.fetchone()
                            date = countrow["rndate"]
                            particulars = custrow["custname"]
                            trntype = "Rejection Note"
                            rnid = finalRow["dcinvtnid"]
                            rnno = countrow["rnno"]
                    if finalRow["dcinvtnflag"] == 7:
                        countresult = con.execute(
                            select(
                                [
                                    drcr.c.drcrdate,
                                    drcr.c.drcrno,
                                    drcr.c.invid,
                                    drcr.c.dctypeflag,
                                ]
                            ).where(
                                and_(
                                    drcr.c.drcrdate >= startDate,
                                    drcr.c.drcrdate <= endDate,
                                    drcr.c.drcrid == finalRow["dcinvtnid"],
                                )
                            )
                        )
                        if countresult.rowcount == 1:
                            countrow = countresult.fetchone()
                            drcrinvdata = con.execute(
                                select([invoice.c.custid]).where(
                                    invoice.c.invid == countrow["invid"]
                                )
                            )
                            drcrinv = drcrinvdata.fetchone()
                            custdata = con.execute(
                                select([customerandsupplier.c.custname]).where(
                                    customerandsupplier.c.custid == drcrinv["custid"]
                                )
                            )
                            custrow = custdata.fetchone()
                            if int(countrow["dctypeflag"] == 3):
                                trntype = "Credit Note"
                            else:
                                trntype = "Debit Note"
                            particulars = custrow["custname"]
                            drcrid = finalRow["dcinvtnid"]
                            drcrno = countrow["drcrno"]
                            date = countrow["drcrdate"]
                    stockReport.append(
                        {
                            "date": date,
                            "particulars": particulars,
                            "trntype": trntype,
                            "dcid": dcid,
                            "dcno": dcno,
                            "rnid": rnid,
                            "rnno": rnno,
                            "invid": invid,
                            "invno": invno,
                            "icflag": icflag,
                            "tnid": tnid,
                            "tnno": tnno,
                            "drcrid": drcrid,
                            "drcrno": drcrno,
                            "inwardqty": "%.2f" % float(inwardqty) if inwardqty else "",
                            "outwardqty": (
                                "%.2f" % float(outwardqty) if outwardqty else ""
                            ),
                            "balance": "%.2f" % float(balance) if balance else "",
                            "balance_value": (
                                "%.2f" % float(balance_value) if balance_value else ""
                            ),
                        }
                    )
                stockReport.append(
                    {
                        "date": "",
                        "particulars": "Total",
                        "dcid": "",
                        "dcno": "",
                        "invid": "",
                        "invno": "",
                        "rnid": "",
                        "rnno": "",
                        "tnid": "",
                        "tnno": "",
                        "trntype": "",
                        "totalinwardqty": "%.2f" % float(totalinward),
                        "totaloutwardqty": "%.2f" % float(totaloutward),
                    }
                )
                return {"gkstatus": enumdict["Success"], "gkresult": stockReport}


    @view_config(route_name="godown-stock-godownincharge")
    def godownwisestockforgodownincharge(self):
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

                startDate = ""

                if "startdate" in self.request.params:
                    startDate = datetime.strptime(
                        str(self.request.params["startdate"]), "%Y-%m-%d"
                    )

                endDate = datetime.strptime(
                    str(self.request.params["enddate"]), "%Y-%m-%d"
                )
                stocktype = self.request.params["type"]
                godownCode = int(self.request.params["goid"])

                prodcode = con.execute(
                    "select productcode as productcode from goprod where goid=%d and orgcode=%d"
                    % (godownCode, orgcode)
                )
                prodcodelist = prodcode.fetchall()

                if prodcodelist == None:
                    return {"gkstatus": enumdict["Success"], "gkresult": prodcodelist}
                else:
                    stocklist = []
                    prodcodedesclist = []
                    for productcode in prodcodelist:
                        productCode = productcode["productcode"]
                        result = godownwise_stock_on_hand(
                            con,
                            orgcode,
                            startDate,
                            endDate,
                            productCode,
                            godownCode,
                        )
                        result["prodid"] = productCode
                        stocklist.append(result)

                    allprodstocklist = sorted(
                        stocklist, key=lambda x: float(x["balance"])
                    )[0:5]
                    for prodcode in allprodstocklist:
                        proddesc = con.execute(
                            "select productdesc as proddesc from product where productcode=%d"
                            % (prodcode["prodid"])
                        )
                        proddesclist = proddesc.fetchone()
                        prodcodedesclist.append(
                            {
                                "prodcode": prodcode["prodid"],
                                "proddesc": proddesclist["proddesc"],
                            }
                        )
                    return {
                        "gkstatus": enumdict["Success"],
                        "gkresult": allprodstocklist,
                        "proddesclist": prodcodedesclist,
                    }


    @view_config(route_name="godownwise-stock-value")
    def godownwise_stock_value(self):
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

                endDate = datetime.strptime(
                    str(self.request.params["enddate"]), "%Y-%m-%d"
                )
                godownCode = int(self.request.params["goid"])
                productCode = int(self.request.params["productcode"])

                valueOnHand = calculateStockValue(
                    con, orgcode, endDate, productCode, godownCode
                )

                return {
                    "gkstatus": enumdict["Success"],
                    "gkresult": valueOnHand,
                }


    @view_config(route_name="godownwise-stock-on-hand")
    def godownwise_stock_on_hand(self):
        """
        Purpose:
        Return the structured data grid of godown wise stock on hand report for given product.
        Input will be productcode,enddate and goid(for specific godown) also type(mention at last).
        orgcode will be taken from header .
        returns a list of dictionaries where every dictionary will be one row.
        description:
        This function returns the complete godown wise stock on hand report,
        including opening stock every inward and outward quantity and running balance  for  selected product and godown.
        at the end we get total inward and outward quantity and balance.
        godownwise opening stock can be taken from goprod table . and godown name can be taken from godown
        The report will query database to get all in and out records for the given product where the dcinvtn flag 4 & 20.
        For every iteration of this list with a for loop we will find out the date of transaction from the delchal or transfernote table depending on the flag being 4 or 20.
        closing balance of the day before startdate given by client and use it as the opening balance.
        The row will be represented in this grid with every key denoting a column.
        The columns (keys) will be,
        total inward quantity , total outwrd quanity and balance , product name ,godownname.

        *product and godown = pg
        *all product and all godown = apag
        *all product and single godown = apg
        *product and all godown = pag
        """
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
                start_date = self.request.params.get("startdate", "")
                end_date = self.request.params.get("enddate", "")
                stock_type = self.request.params["type"]
                product_code = self.request.params.get("productcode")

                ## Gkapp sometimes send productcode "0" for all products.
                if product_code and int(product_code) == 0:
                    product_code = None

                if stock_type in ["pg", "apg"]:
                    godown_codes = [self.request.params["goid"]]
                else:
                    godown_codes = [godown["goid"] for godown in con.execute(
                        select([godown.c.goid]).where(godown.c.orgcode == orgcode)
                    ).fetchall()]


                product_query = select([product.c.productcode, product.c.productdesc]).where(
                    and_(
                        product.c.orgcode == orgcode,
                        product.c.gsflag == 7,
                    )
                )

                if product_code:
                    product_query = product_query.where(product.c.productcode == product_code)
                products = con.execute(product_query).fetchall()

                pmap = {}
                for prod in products:
                    pmap[prod["productcode"]] = prod["productdesc"]

                goprod_query = select([goprod.c.productcode, goprod.c.goid]).where(
                    and_(
                        goprod.c.goid.in_(godown_codes),
                        goprod.c.orgcode == orgcode,
                    )
                )

                if product_code:
                    goprod_query = goprod_query.where(goprod.c.productcode == product_code)

                godown_products = con.execute(goprod_query).fetchall()

                stock_data = {}
                srno = 1
                for gpcode in godown_products:
                    pcode = gpcode["productcode"]
                    if not stock_data.get(pcode):
                        stock_data[pcode] = {
                            "srno": srno,
                            "productcode": pcode,
                            "productname": pmap[pcode],
                            "totalinwardqty": 0.0,
                            "totaloutwardqty": 0.0,
                            "balance": 0.0,
                            "value": 0.0,
                        }
                    godown_product_data = godownwise_stock_on_hand(
                        con,
                        orgcode,
                        start_date,
                        end_date,
                        pcode,
                        gpcode["goid"],
                    )
                    stock_data[pcode]["totalinwardqty"] = (
                        stock_data[pcode]["totalinwardqty"] + godown_product_data["totalinwardqty"]
                    )
                    stock_data[pcode]["totaloutwardqty"] = (
                        stock_data[pcode]["totaloutwardqty"] + godown_product_data["totaloutwardqty"]
                    )
                    stock_data[pcode]["balance"] = (
                        stock_data[pcode]["balance"] + godown_product_data["balance"]
                    )
                    stock_data[pcode]["value"] = (
                        stock_data[pcode]["value"] + godown_product_data["value"]
                    )

                stock_entries = list(stock_data.values())
                for entry in stock_entries:
                    for string in ["totalinwardqty", "totaloutwardqty", "balance", "value"]:
                        entry[string] = "%.2f" % float(entry[string])
                return {"gkstatus": enumdict["Success"], "gkresult": stock_entries}
