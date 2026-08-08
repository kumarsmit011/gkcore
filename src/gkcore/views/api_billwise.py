"""
Copyright (C) 2013, 2014, 2015, 2016, 2017 Digital Freedom Foundation
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
'Abhijith Balan'<abhijith@dff.org.in>
"Krishnakant Mane" <kk@dff.org.in>
"Prajkta Patkar" <prajakta@dff.org.in>
"""

from gkcore import eng, enumdict
from gkcore.utils import authCheck
from gkcore.models import gkdb
from sqlalchemy.sql import select
import json
from sqlalchemy.engine.base import Connection
from sqlalchemy import and_, exc, alias, or_, func, desc
from pyramid.request import Request
from pyramid.response import Response
from pyramid.view import view_defaults, view_config
from sqlalchemy.sql.expression import null
from gkcore.models.gkdb import (
    billwise,
    invoice,
    customerandsupplier,
    vouchers,
    accounts,
    organisation,
)
from datetime import datetime, date
from operator import itemgetter
from natsort import natsorted


@view_defaults(route_name="billwise")
class api_billWise(object):
    """
        This class is a resource for billwise accounting.
    It will be used for creating entries in the billwise table and updating it as new entries are passed.
        The invoice table will also be updated every time an adjustment is made.
        We will have get and post methods.
    """

    def __init__(self, request):
        self.request = Request
        self.request = request
        self.con = Connection
        print("billwise initialized")

    @view_config(request_method="POST", renderer="json")
    def adjustBills(self):
        """
        purpose:
        adjustment of invoices using a given receipt.
        also purchase and sales voucher.
        Single receipt can be used for one or more invoices.
        description:
        this function takes a list of dictionaries containing,
        *vouchercode,
        * invid
        * amount.
        The amount key is also used to update the payed amount in invoice table.
        A for loop runs through the list of dictionaries.
        """
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
                dataSet = self.request.json_body
                adjBills = dataSet["adjbills"]
                for bill in adjBills:
                    bill["orgcode"] = authDetails["orgcode"]
                    result = self.con.execute(billwise.insert(), [bill])
                    updres = self.con.execute(
                        "update invoice set amountpaid = amountpaid + %f where invid = %d"
                        % (float(bill["adjamount"]), bill["invid"])
                    )
                return {"gkstatus": enumdict["Success"]}
                self.con.close()
            except:
                return {"gkstatus": enumdict["ConnectionFailed"]}
                self.con.close()
            finally:
                self.con.close()

    @view_config(request_method="GET", renderer="json")
    def getUnadjustedBills(self):
        """
        Purpose:
        Gets the list of unadjusted receipts and invoices.
        description:
        first we provide it a customerandsupplier code.
        Then get all the receipts vouchers for that customer or supplyer.
        now the receipts are filtered on the basis of 2 conditions.
        firstly the vouchers is unused at all.
        secondly if it is used then it's total should not be equal to the sum of all adjusted amounts of those invoices which have been adjusted using this vouchers.
        For this we loop through the list of vouchers.
        at the beginning of the loop we set a qualification flag to true.
        we will have a nested set of 2 if conditions.
        first we check if the given vouchers is present in the billwise table or not.
        if it is present then the secondly if conditions checks
        if the total amountpaid in the vouchers is equal to the sum of invoices as mentioned above.
        if this condition too is satisfied then the flag is set to false.
        if any of this conditions fail then flag remains true.
        finaly there will be a 3rd if condition which checks this flag.
        if it is true then the vouchers is added to the list to be returned.
        """
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
                csid = int(self.request.params["csid"])
                csFlag = int(self.request.params["csflag"])
                csn = self.con.execute(
                    select([customerandsupplier.c.custname]).where(
                        and_(
                            customerandsupplier.c.custid == csid,
                            customerandsupplier.c.orgcode == authDetails["orgcode"],
                        )
                    )
                )
                csName = csn.fetchone()
                accData = self.con.execute(
                    select([accounts.c.accountcode]).where(
                        and_(
                            accounts.c.accountname == csName["custname"],
                            accounts.c.orgcode == authDetails["orgcode"],
                        )
                    )
                )
                acccode = accData.fetchone()
                if csFlag == 3:
                    csReceiptData = self.con.execute(
                        "select vouchercode, vouchernumber, voucherdate, crs->>'%d' as amt from vouchers where crs ? '%d' and orgcode = %d and vouchertype = 'receipt'"
                        % (
                            acccode["accountcode"],
                            acccode["accountcode"],
                            authDetails["orgcode"],
                        )
                    )
                if csFlag == 19:
                    csReceiptData = self.con.execute(
                        "select vouchercode, vouchernumber, voucherdate, drs->>'%d' as amt from vouchers where drs ? '%d' and orgcode = %d and vouchertype = 'payment'"
                        % (
                            acccode["accountcode"],
                            acccode["accountcode"],
                            authDetails["orgcode"],
                        )
                    )
                csReceipts = csReceiptData.fetchall()
                unAdjReceipts = []
                unAdjInvoices = []
                for rcpt in csReceipts:
                    invs = self.con.execute(
                        select(
                            [
                                func.count(billwise.c.invid).label("invFound"),
                                func.sum(billwise.c.adjamount).label("amtAdjusted"),
                            ]
                        ).where(billwise.c.vouchercode == rcpt["vouchercode"])
                    )
                    invsData = invs.fetchone()
                    amtadj = 0.00
                    if int(invsData["invFound"]) > 0:
                        amtadj = invsData["amtAdjusted"]

                        if float(rcpt["amt"]) == float(invsData["amtAdjusted"]):
                            continue
                    unAdjReceipts.append(
                        {
                            "vouchercode": rcpt["vouchercode"],
                            "vouchernumber": rcpt["vouchernumber"],
                            "voucherdate": datetime.strftime(
                                rcpt["voucherdate"], "%d-%m-%Y"
                            ),
                            "amtadj": "%.2f"
                            % (float(float(rcpt["amt"]) - float(amtadj))),
                        }
                    )

                csInvoices = self.con.execute(
                    select(
                        [
                            invoice.c.invid,
                            invoice.c.invoiceno,
                            invoice.c.invoicedate,
                            invoice.c.invoicetotal,
                            invoice.c.amountpaid,
                        ]
                    ).where(
                        and_(
                            invoice.c.custid == csid,
                            invoice.c.invoicetotal > invoice.c.amountpaid,
                            invoice.c.orgcode == authDetails["orgcode"],
                        )
                    )
                )
                csInvoicesData = csInvoices.fetchall()
                for inv in csInvoicesData:
                    unAdjInvoices.append(
                        {
                            "invid": inv["invid"],
                            "invoiceno": inv["invoiceno"],
                            "invoicedate": datetime.strftime(
                                inv["invoicedate"], "%d-%m-%Y"
                            ),
                            "invoiceamount": "%.2f" % (float(inv["invoicetotal"])),
                            "balanceamount": "%.2f"
                            % (float(inv["invoicetotal"] - inv["amountpaid"])),
                        }
                    )
                return {
                    "gkstatus": enumdict["Success"],
                    "vouchers": unAdjReceipts,
                    "invoices": unAdjInvoices,
                }
                self.con.close()
            except:
                return {"gkstatus": enumdict["ConnectionFailed"]}
                self.con.close()
            finally:
                self.con.close()

    @view_config(request_method="GET", renderer="json", request_param="type=all")
    def getallUnadjustedBills(self):
        """
        Purpose:
        Gets the list of unadjusted invoices.
        Description:
        An invoice is considered unadjusted if it has not been paid or payment for it has not been received completely.
        These are adjusted either while creating vouchers or while doing bill wise accounting.
        This function returns a list of all unadjusted or partially adjusted bills of an organisation.
        """
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
                # An empty list into which unadjusted invoices shall be appended.
                unAdjInvoices = []
                # Fetching id, number, date, total amount and amount paid of all unpaid invoices.
                # It is unadjusted if invoice total is greater that amount paid.

                invoices = self.con.execute(
                    select(
                        [
                            invoice.c.invid,
                            invoice.c.invoiceno,
                            invoice.c.invoicedate,
                            invoice.c.inoutflag,
                            invoice.c.invoicetotal,
                            invoice.c.amountpaid,
                            invoice.c.custid,
                        ]
                    ).where(
                        and_(
                            invoice.c.invoicetotal > invoice.c.amountpaid,
                            invoice.c.icflag == 9,
                            invoice.c.orgcode == authDetails["orgcode"],
                        )
                    )
                )
                invoicesData = invoices.fetchall()
                # Appending dictionaries into empty list.
                # Each dictionary has details of an invoice viz. id, number, date, total amount, amount paid and balance.
                for inv in invoicesData:
                    custData = self.con.execute(
                        select(
                            [
                                customerandsupplier.c.custname,
                                customerandsupplier.c.csflag,
                                customerandsupplier.c.custid,
                            ]
                        ).where(customerandsupplier.c.custid == inv["custid"])
                    )
                    customerdata = custData.fetchone()
                    unAdjInvoices.append(
                        {
                            "invid": inv["invid"],
                            "invoiceno": inv["invoiceno"],
                            "invoicedate": datetime.strftime(
                                inv["invoicedate"], "%d-%m-%Y"
                            ),
                            "invoicetotal": "%.2f" % (float(inv["invoicetotal"])),
                            "balanceamount": "%.2f"
                            % (float(inv["invoicetotal"] - inv["amountpaid"])),
                            "custname": customerdata["custname"],
                            "custid": customerdata["custid"],
                            "inoutflag": inv["inoutflag"],
                        }
                    )
                return {"gkstatus": enumdict["Success"], "invoices": unAdjInvoices}
                self.con.close()
            except:
                return {"gkstatus": enumdict["ConnectionFailed"]}
                self.con.close()
            finally:
                self.con.close()

    @view_config(request_method="GET", renderer="json", request_param="type=pending")
    def getallPendingBills(self):
        """
        Purpose:
        Gets the list of pending invoices.
        Description:
        An invoice is considered pending if it has not been paid or no payment for it has been received.
        These are adjusted either while creating vouchers or while doing bill wise accounting.
        This function returns a list of all pending bills of an organisation.
        """
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
                # An empty list into which pending invoices shall be appended.
                unAdjInvoices = []
                # Fetching id, number, date, total amount and amount paid of all unpaid invoices.
                # It is pending if invoice total is greater that amount paid.

                invoices = self.con.execute(
                    select(
                        [
                            invoice.c.invid,
                            invoice.c.invoiceno,
                            invoice.c.invoicedate,
                            invoice.c.invoicetotal,
                            invoice.c.amountpaid,
                            invoice.c.custid,
                        ]
                    ).where(
                        and_(
                            invoice.c.amountpaid == 0,
                            invoice.c.icflag == 9,
                            invoice.c.orgcode == authDetails["orgcode"],
                        )
                    )
                )
                invoicesData = invoices.fetchall()
                # Appending dictionaries into empty list.
                # Each dictionary has details of an invoice viz. id, number, date, total amount, amount paid and balance.
                for inv in invoicesData:
                    custData = self.con.execute(
                        select(
                            [
                                customerandsupplier.c.custname,
                                customerandsupplier.c.csflag,
                                customerandsupplier.c.custid,
                            ]
                        ).where(customerandsupplier.c.custid == inv["custid"])
                    )
                    customerdata = custData.fetchone()
                    # If there is a invtype parameter then only sale/purchase invoices are returned depending on the value of type.
                    if "invtype" in self.request.params:
                        if (
                            str(self.request.params["invtype"]) == "sale"
                            and int(customerdata["csflag"]) == 3
                        ):
                            unAdjInvoices.append(
                                {
                                    "invid": inv["invid"],
                                    "invoiceno": inv["invoiceno"],
                                    "invoicedate": datetime.strftime(
                                        inv["invoicedate"], "%d-%m-%Y"
                                    ),
                                    "invoicetotal": "%.2f"
                                    % (float(inv["invoicetotal"])),
                                    "balanceamount": "%.2f"
                                    % (float(inv["invoicetotal"] - inv["amountpaid"])),
                                    "custname": customerdata["custname"],
                                    "custid": customerdata["custid"],
                                    "csflag": customerdata["csflag"],
                                }
                            )
                        elif (
                            str(self.request.params["invtype"]) == "purchase"
                            and int(customerdata["csflag"]) == 19
                        ):
                            unAdjInvoices.append(
                                {
                                    "invid": inv["invid"],
                                    "invoiceno": inv["invoiceno"],
                                    "invoicedate": datetime.strftime(
                                        inv["invoicedate"], "%d-%m-%Y"
                                    ),
                                    "invoicetotal": "%.2f"
                                    % (float(inv["invoicetotal"])),
                                    "balanceamount": "%.2f"
                                    % (float(inv["invoicetotal"] - inv["amountpaid"])),
                                    "custname": customerdata["custname"],
                                    "custid": customerdata["custid"],
                                    "csflag": customerdata["csflag"],
                                }
                            )
                    else:
                        unAdjInvoices.append(
                            {
                                "invid": inv["invid"],
                                "invoiceno": inv["invoiceno"],
                                "invoicedate": datetime.strftime(
                                    inv["invoicedate"], "%d-%m-%Y"
                                ),
                                "invoicetotal": "%.2f" % (float(inv["invoicetotal"])),
                                "balanceamount": "%.2f"
                                % (float(inv["invoicetotal"] - inv["amountpaid"])),
                                "custname": customerdata["custname"],
                                "custid": customerdata["custid"],
                                "csflag": customerdata["csflag"],
                            }
                        )
                return {"gkstatus": enumdict["Success"], "invoices": unAdjInvoices}
                self.con.close()
            except:
                return {"gkstatus": enumdict["ConnectionFailed"]}
                self.con.close()
            finally:
                self.con.close()

    @view_config(request_method="GET", renderer="json", request_param="type=onlybills")
    def getOnlyUnadjustedBills(self):
        """
        Purpose:
        Gets the list of invoices for a customer/supplier in the order of balance amount.
        Description:
        We receive customer id and orderflag. The value of orderflag is 1 for ascending order and 4 for descending.
        Data of invoices for the customer that are not fully paid are fetched in the order of balance amount.
        If orderflag is not 1 they are fetched in the descending order.
        A list of dictionaries is then returned where each dictionary contains data regarding an invoice.
        """
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
                csid = int(self.request.params["csid"])
                inoutflag = int(self.request.params["inoutflag"])
                orderflag = int(self.request.params["orderflag"])
                typeflag = int(self.request.params["typeflag"])
                # Period for which this report is created is determined by startdate and enddate. They are formatted as YYYY-MM-DD.
                startdate = datetime.strptime(
                    str(self.request.params["startdate"]), "%d-%m-%Y"
                ).strftime("%Y-%m-%d")
                enddate = datetime.strptime(
                    str(self.request.params["enddate"]), "%d-%m-%Y"
                ).strftime("%Y-%m-%d")
                # Empty list for storing incoices
                unAdjInvoices = []
                # Invoices in ascending order of amount.
                if orderflag == 1 and typeflag == 1:
                    csInvoices = self.con.execute(
                        select(
                            [
                                invoice.c.invid,
                                invoice.c.invoiceno,
                                invoice.c.invoicedate,
                                invoice.c.invoicetotal,
                                invoice.c.amountpaid,
                            ]
                        )
                        .where(
                            and_(
                                invoice.c.custid == csid,
                                invoice.c.invoicetotal > invoice.c.amountpaid,
                                invoice.c.icflag == 9,
                                invoice.c.orgcode == authDetails["orgcode"],
                                invoice.c.invoicedate >= startdate,
                                invoice.c.invoicedate <= enddate,
                                invoice.c.inoutflag == inoutflag,
                            )
                        )
                        .order_by(invoice.c.invoicetotal - invoice.c.amountpaid)
                    )
                # Invoices in descending order of amount.
                if orderflag == 4 and typeflag == 1:
                    csInvoices = self.con.execute(
                        select(
                            [
                                invoice.c.invid,
                                invoice.c.invoiceno,
                                invoice.c.invoicedate,
                                invoice.c.invoicetotal,
                                invoice.c.amountpaid,
                            ]
                        )
                        .where(
                            and_(
                                invoice.c.custid == csid,
                                invoice.c.invoicetotal > invoice.c.amountpaid,
                                invoice.c.icflag == 9,
                                invoice.c.orgcode == authDetails["orgcode"],
                                invoice.c.invoicedate >= startdate,
                                invoice.c.invoicedate <= enddate,
                                invoice.c.inoutflag == inoutflag,
                            )
                        )
                        .order_by(desc(invoice.c.invoicetotal - invoice.c.amountpaid))
                    )
                # Invoices in ascending order of due date.
                if orderflag == 1 and typeflag == 4:
                    csInvoices = self.con.execute(
                        select(
                            [
                                invoice.c.invid,
                                invoice.c.invoiceno,
                                invoice.c.invoicedate,
                                invoice.c.invoicetotal,
                                invoice.c.amountpaid,
                            ]
                        )
                        .where(
                            and_(
                                invoice.c.custid == csid,
                                invoice.c.invoicetotal > invoice.c.amountpaid,
                                invoice.c.icflag == 9,
                                invoice.c.orgcode == authDetails["orgcode"],
                                invoice.c.invoicedate >= startdate,
                                invoice.c.invoicedate <= enddate,
                                invoice.c.inoutflag == inoutflag,
                            )
                        )
                        .order_by(invoice.c.invoicedate)
                    )
                # Invoices in descending order of due date.
                if orderflag == 4 and typeflag == 4:
                    csInvoices = self.con.execute(
                        select(
                            [
                                invoice.c.invid,
                                invoice.c.invoiceno,
                                invoice.c.invoicedate,
                                invoice.c.invoicetotal,
                                invoice.c.amountpaid,
                            ]
                        )
                        .where(
                            and_(
                                invoice.c.custid == csid,
                                invoice.c.invoicetotal > invoice.c.amountpaid,
                                invoice.c.icflag == 9,
                                invoice.c.orgcode == authDetails["orgcode"],
                                invoice.c.invoicedate >= startdate,
                                invoice.c.invoicedate <= enddate,
                                invoice.c.inoutflag == inoutflag,
                            )
                        )
                        .order_by(desc(invoice.c.invoicedate))
                    )
                csInvoicesData = csInvoices.fetchall()
                for inv in csInvoicesData:
                    unAdjInvoices.append(
                        {
                            "invid": inv["invid"],
                            "invoiceno": inv["invoiceno"],
                            "invoicedate": datetime.strftime(
                                inv["invoicedate"], "%d-%m-%Y"
                            ),
                            "invoiceamount": "%.2f" % (float(inv["invoicetotal"])),
                            "balanceamount": "%.2f"
                            % (float(inv["invoicetotal"] - inv["amountpaid"])),
                        }
                    )
                return {"gkstatus": enumdict["Success"], "invoices": unAdjInvoices}
                self.con.close()
            except:
                return {"gkstatus": enumdict["ConnectionFailed"]}
                self.con.close()
            finally:
                self.con.close()

    @view_config(
        request_method="GET", renderer="json", request_param="type=onlybillsforall"
    )
    def getOnlyUnadjustedBillsForAll(self):
        """
        Purpose:
        Gets the list of invoices for all customers and suppliers in the order of balance amount and due date.
        Description:
        We receive orderflag and typeflag. The value of orderflag is 1 for ascending order and 4 for descending.
        If typeflag is 1 data of invoices for the  all customers and suppliers that are not fully paid are fetched in order of balance amount.
        If orderflag is 4 they are fetched in the descending order.
        If typeflag is 4 invoices are fetched in order of due date.
        If it is 3 invoices are fetched normally and sorted later in the order of customer/supplier name.
        This is done so because name of customer/supplier is not stored in invoice table but in customerandsupplier table.
        A list of dictionaries is then returned where each dictionary contains data regarding an invoice.
        """
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
                inoutflag = int(self.request.params["inoutflag"])
                orderflag = int(self.request.params["orderflag"])
                typeflag = int(self.request.params["typeflag"])
                # Dictionaries for inoutflag, orderflag and typeflag. Keys are integer values of flags and values corresponding strings.
                inouts = {9: "Purchase", 15: "Sale"}
                orders = {1: "Ascending", 4: "Descending"}
                types = {1: "Amount Wise", 3: "Party Wise", 4: "Due Wise"}
                # Period for which this report is created is determined by startdate and enddate. They are formatted as YYYY-MM-DD.
                startdate = datetime.strptime(
                    str(self.request.params["startdate"]), "%d-%m-%Y"
                ).strftime("%Y-%m-%d")
                enddate = datetime.strptime(
                    str(self.request.params["enddate"]), "%d-%m-%Y"
                ).strftime("%Y-%m-%d")
                # Empty list for storing incoices
                unAdjInvoices = []
                # Invoices in ascending order of amount.
                if orderflag == 1 and typeflag == 1:
                    csInvoices = self.con.execute(
                        select(
                            [
                                invoice.c.invid,
                                invoice.c.invoiceno,
                                invoice.c.invoicedate,
                                invoice.c.invoicetotal,
                                invoice.c.amountpaid,
                                invoice.c.custid,
                            ]
                        )
                        .where(
                            and_(
                                invoice.c.invoicetotal > invoice.c.amountpaid,
                                invoice.c.icflag == 9,
                                invoice.c.orgcode == authDetails["orgcode"],
                                invoice.c.invoicedate >= startdate,
                                invoice.c.invoicedate <= enddate,
                                invoice.c.inoutflag == inoutflag,
                            )
                        )
                        .order_by(invoice.c.invoicetotal - invoice.c.amountpaid)
                    )
                # Invoices in descending order of amount.
                if orderflag == 4 and typeflag == 1:
                    csInvoices = self.con.execute(
                        select(
                            [
                                invoice.c.invid,
                                invoice.c.invoiceno,
                                invoice.c.invoicedate,
                                invoice.c.invoicetotal,
                                invoice.c.amountpaid,
                                invoice.c.custid,
                            ]
                        )
                        .where(
                            and_(
                                invoice.c.invoicetotal > invoice.c.amountpaid,
                                invoice.c.icflag == 9,
                                invoice.c.orgcode == authDetails["orgcode"],
                                invoice.c.invoicedate >= startdate,
                                invoice.c.invoicedate <= enddate,
                                invoice.c.inoutflag == inoutflag,
                            )
                        )
                        .order_by(desc(invoice.c.invoicetotal - invoice.c.amountpaid))
                    )
                # Invoices in ascending order of due date.
                if orderflag == 1 and typeflag == 4:
                    csInvoices = self.con.execute(
                        select(
                            [
                                invoice.c.invid,
                                invoice.c.invoiceno,
                                invoice.c.invoicedate,
                                invoice.c.invoicetotal,
                                invoice.c.amountpaid,
                                invoice.c.custid,
                            ]
                        )
                        .where(
                            and_(
                                invoice.c.invoicetotal > invoice.c.amountpaid,
                                invoice.c.icflag == 9,
                                invoice.c.orgcode == authDetails["orgcode"],
                                invoice.c.invoicedate >= startdate,
                                invoice.c.invoicedate <= enddate,
                                invoice.c.inoutflag == inoutflag,
                            )
                        )
                        .order_by(invoice.c.invoicedate)
                    )
                # Invoices in descending order of due date.
                if orderflag == 4 and typeflag == 4:
                    csInvoices = self.con.execute(
                        select(
                            [
                                invoice.c.invid,
                                invoice.c.invoiceno,
                                invoice.c.invoicedate,
                                invoice.c.invoicetotal,
                                invoice.c.amountpaid,
                                invoice.c.custid,
                            ]
                        )
                        .where(
                            and_(
                                invoice.c.invoicetotal > invoice.c.amountpaid,
                                invoice.c.icflag == 9,
                                invoice.c.orgcode == authDetails["orgcode"],
                                invoice.c.invoicedate >= startdate,
                                invoice.c.invoicedate <= enddate,
                                invoice.c.inoutflag == inoutflag,
                            )
                        )
                        .order_by(desc(invoice.c.invoicedate))
                    )
                # Unsorted invoices to be sorted later in the order of customer/supplier name.
                if typeflag == 3:
                    csInvoices = self.con.execute(
                        select(
                            [
                                invoice.c.invid,
                                invoice.c.invoiceno,
                                invoice.c.invoicedate,
                                invoice.c.invoicetotal,
                                invoice.c.amountpaid,
                                invoice.c.custid,
                            ]
                        ).where(
                            and_(
                                invoice.c.invoicetotal > invoice.c.amountpaid,
                                invoice.c.icflag == 9,
                                invoice.c.orgcode == authDetails["orgcode"],
                                invoice.c.invoicedate >= startdate,
                                invoice.c.invoicedate <= enddate,
                                invoice.c.inoutflag == inoutflag,
                            )
                        )
                    )
                csInvoicesData = csInvoices.fetchall()
                for inv in csInvoicesData:
                    csd = self.con.execute(
                        select(
                            [
                                customerandsupplier.c.custname,
                                customerandsupplier.c.csflag,
                            ]
                        ).where(
                            and_(
                                customerandsupplier.c.custid == inv["custid"],
                                customerandsupplier.c.orgcode == authDetails["orgcode"],
                            )
                        )
                    )
                    csDetails = csd.fetchone()
                    unAdjInvoices.append(
                        {
                            "invid": inv["invid"],
                            "invoiceno": inv["invoiceno"],
                            "invoicedate": datetime.strftime(
                                inv["invoicedate"], "%d-%m-%Y"
                            ),
                            "invoiceamount": "%.2f" % (float(inv["invoicetotal"])),
                            "balanceamount": "%.2f"
                            % (float(inv["invoicetotal"] - inv["amountpaid"])),
                            "custname": csDetails["custname"],
                            "csflag": csDetails["csflag"],
                        }
                    )
                # List of dictionaries unAdjInvoices is sorted in order of key custname.
                if typeflag == 3 and orderflag == 1:
                    newlistofinvs = natsorted(unAdjInvoices, key=itemgetter("custname"))
                    unAdjInvoices = newlistofinvs
                if typeflag == 3 and orderflag == 4:
                    newlistofinvs = natsorted(
                        unAdjInvoices, key=itemgetter("custname"), reverse=True
                    )
                    unAdjInvoices = newlistofinvs
                # List of outstanding invoices is returned together with strings that appear in heading.
                return {
                    "gkstatus": enumdict["Success"],
                    "invoices": unAdjInvoices,
                    "inout": inouts[inoutflag],
                    "type": types[typeflag],
                    "order": orders[orderflag],
                }
                self.con.close()
            except:
                return {"gkstatus": enumdict["ConnectionFailed"]}
                self.con.close()
            finally:
                self.con.close()
