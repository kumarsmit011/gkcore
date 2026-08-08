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
"Survesh" <123survesh@gmail.com>
"Sai Karthik"<kskarthik@disroot.org>

"""

from gkcore import eng, enumdict
from gkcore.models import gkdb
from sqlalchemy.sql import select
import json
from sqlalchemy.engine.base import Connection
from sqlalchemy import and_, exc
from sqlalchemy.sql.expression import text
from pyramid.request import Request
from pyramid.response import Response
from pyramid.view import view_defaults, view_config
from sqlalchemy.ext.baked import Result
import gkcore

# from gkcore.utils import authCheck
from gkcore.views.transaction.services import getInvVouchers
from gkcore.views.api_invoice import getDefaultAcc

import traceback  # for printing detailed exception logs

"""
The Dev API is used to perform tasks during development. 

Note: This API modifies tables directly and can cause unwanted behaviour during normal use or be misused. 
And hence must be commented out in __init__.py file outside this folder during production.
"""


def recalculateStock(con, data, data_type, flag):
    try:
        id_key = data_type + "id"
        for item in data:
            id = item[id_key]
            orgcode = item["orgcode"]
            new_fqty = {}
            for prod_code in item["contents"]:
                if prod_code and prod_code != "undefined":
                    # print("================")
                    p_qty = (
                        float(
                            item["contents"][prod_code][
                                list(item["contents"][prod_code].keys())[0]
                            ]
                        )
                        or 0
                    )
                    p_fqty = float(item["freeqty"][prod_code])

                    if p_fqty != p_fqty:
                        new_fqty[prod_code] = 0
                        p_fqty = 0

                    prod_qty = p_qty + p_fqty
                    stock_row = con.execute(
                        select([gkdb.stock.c.stockid, gkdb.stock.c.qty]).where(
                            and_(
                                gkdb.stock.c.orgcode == orgcode,
                                gkdb.stock.c.dcinvtnid == id,
                                gkdb.stock.c.productcode == prod_code,
                                gkdb.stock.c.dcinvtnflag == flag,
                            )
                        )
                    )
                    # print(
                    #     "gkdb.stock.c.orgcode == %s; gkdb.stock.c.dcinvtnid == %s; gkdb.stock.c.productcode == %s; gkdb.stock.c.dcinvtnflag == 3"
                    #     % (orgcode, invid, prod_code)
                    # )
                    if stock_row.rowcount > 0:
                        stock_data = stock_row.fetchone()
                        # print(id_key + ": " + str(id) + ", qty = " +str(stock_data["qty"])+ ", pqty = "+str(prod_qty))
                        if float(stock_data["qty"]) != prod_qty:
                            con.execute(
                                stock.update()
                                .where(gkdb.stock.c.stockid == stock_data["stockid"])
                                .values(qty=prod_qty)
                            )
                            # print(
                            #     "stockid = %s;  bad qty = %s;  good qty = %s"
                            #     % (
                            #         str(stock_data["stockid"]),
                            #         str(stock_data["qty"]),
                            #         str(prod_qty),
                            #     )
                            # )
            if len(new_fqty):
                if data_type == "inv":
                    con.execute(
                        invoice.update()
                        .where(gkdb.invoice.c.invid == item[id_key])
                        .values(freeqty=new_fqty)
                    )
                elif data_type == "dc":
                    con.execute(
                        delchal.update()
                        .where(gkdb.delchal.c.dcid == item[id_key])
                        .values(freeqty=new_fqty)
                    )
    except:
        print(traceback.format_exc())


def recalculateVoucher(con, orgcode, invid, maflag):
    try:
        inv_data = con.execute(
            select([invoice]).where(
                and_(gkdb.invoice.c.orgcode == orgcode, gkdb.invoice.c.invid == invid)
            )
        ).fetchone()
        vouchers = getInvVouchers(con, orgcode, invid)
        voucherData = {}
        if len(vouchers) > 0:
            # recalculate vouchers
            print("%s Has Voucher" % (str(invid)))
        else:
            # create vouchers
            avData = {
                "totaltaxable": 0,
                "product": {},
                "prodData": {},
                "taxpayment": 0,
                "avtax": {
                    "GSTName": "CGST"
                    if inv_data["taxstate"] == inv_data["sourcestate"]
                    else "IGST",
                    "CESSName": "CESS",
                },
            }
            for pid in inv_data["contents"]:
                prod_row = con.execute(
                    select([gkdb.product.c.productdesc]).where(
                        and_(
                            gkdb.product.c.productcode == pid,
                            gkdb.product.c.orgcode == orgcode,
                        )
                    )
                ).fetchone()
                pname = prod_row["productdesc"]
                price = float(list(inv_data["contents"][pid].keys())[0]) or 0
                qty = float(list(inv_data["contents"][pid].values())[0]) or 0
                discount = float(inv_data["discount"][pid]) or 0
                fqty = float(inv_data["freeqty"][pid]) or 0
                taxable = (price * (qty - fqty)) - discount
                avData["totaltaxable"] += taxable
                avData["prodData"][pid] = taxable
                avData["product"][pname] = taxable
            avData["taxpayment"] = avData["totaltaxable"]

            queryParams = {
                "invtype": inv_data["inoutflag"],
                "pmtmode": inv_data["paymentmode"],
                "taxType": inv_data["taxflag"],
                "destinationstate": inv_data["taxstate"],
                "totaltaxablevalue": avData["totaltaxable"],
                "maflag": maflag,
                "totalAmount": (inv_data["invoicetotal"]),
                "invoicedate": inv_data["invoicedate"],
                "invid": invid,
                "invoiceno": inv_data["invoiceno"],
                "taxes": inv_data["tax"],
                "cess": inv_data["cess"],
                "products": avData["product"],
                "prodData": avData["prodData"],
                "csname": "",
            }

            if inv_data["custid"]:
                csName = con.execute(
                    select([gkdb.customerandsupplier.c.custname]).where(
                        and_(
                            gkdb.customerandsupplier.c.orgcode == orgcode,
                            gkdb.customerandsupplier.c.custid
                            == int(inv_data["custid"]),
                        )
                    )
                ).fetchone()
                queryParams["csname"] = csName["custname"]

            # when invoice total is rounded off
            if inv_data["roundoffflag"] == 1:
                roundOffAmount = float(inv_data["invoicetotal"]) - round(
                    float(inv_data["invoicetotal"])
                )
                if float(roundOffAmount) != 0.00:
                    queryParams["roundoffamt"] = float(roundOffAmount)

            if int(inv_data["taxflag"]) == 7:
                queryParams["gstname"] = avData["avtax"]["GSTName"]
                queryParams["cessname"] = avData["avtax"]["CESSName"]

            if int(inv_data["taxflag"]) == 22:
                queryParams["taxpayment"] = avData["taxpayment"]

            # call getDefaultAcc
            av_Result = getDefaultAcc(con, queryParams, orgcode)

            if av_Result["gkstatus"] == 0:
                voucherData["status"] = 0
                voucherData["vchno"] = av_Result["vchNo"]
                voucherData["vchid"] = av_Result["vid"]
            else:
                voucherData["status"] = 1

        return voucherData
    except:
        print(traceback.format_exc())
        return {}


"""
    updateStockRate()

    For a given organisation, go through the stock table and calculate the value of items for every entry and 
    update the table accordingly

    step1: Fetch all entries in stock table for an orgcode
    step2: For each item in the list
    step3: Fetch the corresponding transaction document and calculate the value of the item
    step4: Update the value of the item in the table

    delivery chalan (flag = 4) or invoice (flag = 9 ) or cash memo (flag = 3) or transfernote (flag = 20), rejection note(flag = 18), quantity adjustments using Debit/Credit Note(flag = 7) or rejection of goods of bad quality(flag = 2).
"""


def updateStockRate(con, orgcode):
    try:
        stocks = con.execute(
            select([stock]).where(gkdb.stock.c.orgcode == orgcode)
        ).fetchall()
        for stockItem in stocks:
            productCode = str(stockItem["productcode"])
            trnId = stockItem["dcinvtnid"]
            prodRate = prodQty = prodValue = 0
            if stockItem.dcinvtnflag in [
                3,
                4,
                9,
                18,
            ]:  # if invoice/ cash memo/ delivery chalan / rejection note
                transaction = {}
                if stockItem.dcinvtnflag == 4:  # Delivery chalan
                    transaction = con.execute(
                        select(
                            [gkdb.delchal.c.contents]
                        ).where(  # , gkdb.delchal.c.freeqty
                            and_(
                                gkdb.delchal.c.orgcode == orgcode,
                                gkdb.delchal.c.dcid == trnId,
                            )
                        )
                    ).fetchone()
                elif stockItem.dcinvtnflag == 18:  # Rejection note
                    transaction = con.execute(
                        select(
                            [gkdb.rejectionnote.c.rejprods]
                        ).where(  # , gkdb.delchal.c.freeqty
                            and_(
                                gkdb.rejectionnote.c.orgcode == orgcode,
                                gkdb.rejectionnote.c.rnid == trnId,
                            )
                        )
                    ).fetchone()
                    print(stockItem.dcinvtnflag)
                    print(transaction["rejprods"])
                else:  # invoice / cash memo
                    transaction = con.execute(
                        select(
                            [gkdb.invoice.c.contents]
                        ).where(  # , gkdb.invoice.c.freeqty
                            and_(
                                gkdb.invoice.c.orgcode == orgcode,
                                gkdb.invoice.c.invid == trnId,
                            )
                        )
                    ).fetchone()
                productData = []
                if "contents" in transaction:
                    productData = list(transaction["contents"][productCode].items())[0]
                elif "rejprods" in transaction:
                    productData = list(transaction["rejprods"][productCode].items())[0]

                if len(productData) > 0:
                    prodRate = float(productData[0]) or 0
                    prodQty = float(productData[1]) or 0
                    # prodFreeQty = float(transaction.freeqty[productCode])
            elif stockItem.dcinvtnflag in [
                7,
                2,
            ]:  # if debit credit note, bad quality rejection
                transaction = con.execute(
                    select([gkdb.drcr.c.reductionval]).where(
                        and_(
                            gkdb.drcr.c.orgcode == orgcode,
                            gkdb.drcr.c.drcrid == trnId,
                        )
                    )
                ).fetchone()
                if "quantities" in transaction:
                    prodQty = float(transaction["quantities"][productCode]) or 0
                    prodRate = float(transaction[productCode]) or 0
            # elif stockItem.dcinvtnflag == 20: # transfer note
            # must use the stock on hand's value

            con.execute(
                stock.update()
                .where(gkdb.stock.c.stockid == stockItem["stockid"])
                .values(rate=prodRate)
            )
        return 1
    except:
        print(traceback.format_exc())
        return -1


@view_defaults(route_name="dev")
class api_dev(object):
    def __init__(self, request):
        self.request = Request
        self.request = request
        self.con = Connection
        print("Dev API is ON")

    @view_config(
        request_method="GET", request_param="task=stock_rectify", renderer="json"
    )
    def rectifyStock(self):
        """
        This methods recalculates the stock table data, using the invoice / delivery note of the respective stock table entry.
        """
        try:
            self.con = eng.connect()

            # Rectify all invoice
            invoices = self.con.execute(
                select(
                    [
                        gkdb.invoice.c.invid,
                        gkdb.invoice.c.contents,
                        gkdb.invoice.c.freeqty,
                        gkdb.invoice.c.orgcode,
                    ]
                ).where(gkdb.invoice.c.icflag == 9)
            ).fetchall()
            recalculateStock(self.con, invoices, "inv", 9)

            # Rectify all cash memos
            invoices = self.con.execute(
                select(
                    [
                        gkdb.invoice.c.invid,
                        gkdb.invoice.c.contents,
                        gkdb.invoice.c.freeqty,
                        gkdb.invoice.c.orgcode,
                    ]
                ).where(gkdb.invoice.c.icflag == 3)
            ).fetchall()
            recalculateStock(self.con, invoices, "inv", 3)

            # Rectify all Delivery Notes
            delnotes = self.con.execute(
                select(
                    [
                        gkdb.delchal.c.dcid,
                        gkdb.delchal.c.contents,
                        gkdb.delchal.c.freeqty,
                        gkdb.delchal.c.orgcode,
                    ]
                )
            ).fetchall()
            recalculateStock(self.con, delnotes, "dc", 4)

            # Rectify any remaining entries that are NaN
            # stocks = self.con.execute(
            #     select([gkdb.stock.c.dcinvtnid, gkdb.stock.c.dcinvtnflag, gkdb.stock.c.orgcode]).where(
            #         gkdb.stock.c.qty == "NaN"
            #     )
            # ).fetchall()
            # stock_map = {}
            # for item in stocks:
            #     if not item["dcinvtnflag"] in stock_map:
            #         stock_map[item["dcinvtnflag"]] = []
            #     if item["dcinvtnflag"] == 4:
            #         delnote = self.con.execute(
            #             select(
            #                 [
            #                     gkdb.delchal.c.dcid,
            #                     gkdb.delchal.c.contents,
            #                     gkdb.delchal.c.freeqty,
            #                     gkdb.delchal.c.orgcode,
            #                 ]
            #             ).where(
            #                 and_(
            #                     gkdb.delchal.c.dcid == item["dcinvtnid"],
            #                     gkdb.delchal.c.orgcode == item["orgcode"],
            #                 )
            #             )
            #         ).fetchone()
            #         stock_map[item["dcinvtnflag"]].append(delnote)
            # for stock_flag in stock_map:
            #     # print(stock_map[stock_flag])
            #     stock_type = "inv" if stock_flag == 9 else "dc"
            #     recalculateStock(self.con, stock_map[stock_flag], stock_type, stock_flag)

            # dcinvtnflag = 3 for cash memo, 9 for invoice and 4 for delchal
            self.con.close()
            return {
                "gkstatus": enumdict["Success"],
            }
        except Exception:
            print(traceback.format_exc())
            self.con.close()
            return {"gkstatus": enumdict["ConnectionFailed"]}

    @view_config(
        request_method="GET", request_param="task=voucher_rectify", renderer="json"
    )
    def rectifyVouchers(self):
        """
        This methods recalculates the vouchers, using the invoice data for a given orgcode.
        """
        try:
            self.con = eng.connect()

            orgcode = self.request.params["orgcode"]["orgcode"]

            # check automatic voucher flag  if it is 1 get maflag
            avfl = self.con.execute(
                select([gkdb.organisation.c.avflag]).where(
                    gkdb.organisation.c.orgcode == orgcode
                )
            )
            av = avfl.fetchone()
            if av["avflag"] == 1:
                mafl = self.con.execute(
                    select([gkdb.organisation.c.maflag]).where(
                        gkdb.organisation.c.orgcode == orgcode
                    )
                ).fetchone()
                maFlag = mafl["maflag"]

                invlist = self.con.execute(
                    select([gkdb.invoice.c.invid]).where(
                        gkdb.invoice.c.orgcode == orgcode
                    )
                ).fetchall()

                voucherData = {}
                for inv in invlist:
                    voucherData[inv["invid"]] = recalculateVoucher(
                        self.con, orgcode, inv["invid"], maFlag
                    )

                self.con.close()
                return {"gkstatus": enumdict["Success"], "gkresult": voucherData}
            else:
                self.con.close()
                return {
                    "gkstatus": enumdict["ActionDisallowed"],
                }

        except Exception:
            print(traceback.format_exc())
            self.con.close()
            return {"gkstatus": enumdict["ConnectionFailed"]}

    @view_config(
        request_method="GET", request_param="task=update_stock_rate", renderer="json"
    )
    def updateAllStockRate(self):
        """
        This methods checks the corresponding transaction table and updates the rate of stock in the stock table

        Note: Used for DB migration, after adding the column "rate" in stock table
        """
        try:
            self.con = eng.connect()
            orgs = self.con.execute(select([gkdb.organisation.c.orgcode])).fetchall()
            status = True
            for org in orgs:
                result = updateStockRate(self.con, org["orgcode"])
                if result < 0:
                    status = False
            if status:
                return {"gkstatus": enumdict["Success"]}
            else:
                return {"gkstatus": enumdict["ConnectionFailed"]}
        except:
            print(traceback.format_exc())
            self.con.close()
            return {"gkstatus": enumdict["ConnectionFailed"]}

    @view_config(request_method="GET", request_param="task=test", renderer="json")
    def test(self):
        """
        This methods is for testing out syntax and code
        """
        try:
            self.con = eng.connect()
            orgcode = self.request.params["orgcode"]
            userid = self.request.params["userid"]
            userOrgQuery = self.con.execute(
                text("select orgs->':orgcode' as data from gkusers where userid = :userid;"),
                orgcode = orgcode,
                userid = userid,
            )
            if userOrgQuery.rowcount < 1:
                return {"gkstatus": enumdict["ActionDisallowed"]}
            userOrgData = userOrgQuery.fetchone()
            print(userOrgData["data"])
            return {"gkstatus": enumdict["Success"]}
        except:
            print(traceback.format_exc())
            self.con.close()
            return {"gkstatus": enumdict["ConnectionFailed"]}
