from gkcore import eng, enumdict
from gkcore.utils import authCheck
from gkcore.models.gkdb import (
    accounts,
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
    categorysubcategories,
)
from gkcore.views.helpers.voucher import (
    generate_consolidated_voucher_data, get_org_vouchers
)
from sqlalchemy.sql import select
from sqlalchemy.engine.base import Connection
from sqlalchemy import and_, or_
from pyramid.request import Request
from pyramid.view import view_defaults, view_config
from datetime import datetime
from sqlalchemy.sql.functions import func
from gkcore.views.reports.helpers.stock import stockonhandfun


@view_defaults(request_method="GET")
class api_stock_register(object):
    def __init__(self, request):
        self.request = Request
        self.request = request
        self.con = Connection

    @view_config(route_name="registers", renderer="json_extended")
    def register(self):
        """
        purpose: Takes input: i.e. either sales/purchase register and time period.
        Returns a dictionary of all matched invoices.
        description:
        This function is used to see sales or purchase register of organisation.
        It means the total purchase and sales of different products. Also its amount,
        tax, etc.
        orderflag is checked in request params for sorting date in descending order.
        """
        try:
            token = self.request.headers["gktoken"]
        except:
            return {"gkstatus": enumdict["UnauthorisedAccess"]}
        authDetails = authCheck(token)
        if authDetails["auth"] == False:
            return {"gkstatus": enumdict["UnauthorisedAccess"]}
        account_flag = self.request.params["flag"]
        if account_flag == "0":
            default_account_flag = 19 # Sale
        elif account_flag == "1":
            default_account_flag = 16 # Purchase
        with eng.connect() as connection:
            account_details = connection.execute(
                select([accounts.c.accountcode]).where(
                    and_(
                        accounts.c.orgcode == authDetails["orgcode"],
                        accounts.c.defaultflag == default_account_flag,
                    )
                )
            ).fetchone()
            account_id = account_details["accountcode"]

            from_date = datetime.strptime(
                self.request.params.get("calculatefrom"),
                "%d-%m-%Y",
            )
            to_date = datetime.strptime(
                self.request.params.get("calculateto"),
                "%d-%m-%Y",
            )

            voucher_rows = get_org_vouchers(
                connection,
                authDetails["orgcode"],
                account_id,
                from_date,
                to_date,
            )
            vouchers_consolidated = generate_consolidated_voucher_data(
                connection, voucher_rows, account_id
            )
        return {
            "gkstatus": enumdict["Success"],
            "gkresult": vouchers_consolidated,
        }


    @view_config(route_name="stock-report", renderer="json")
    def stockReport(self):
        """
        Purpose:
        Return the structured data grid of stock report for given product.
        Input will be productcode,startdate,enddate.
        orgcode will be taken from header and startdate and enddate of fianancial year taken from organisation table .
        returns a list of dictionaries where every dictionary will be one row.
        description:
        This function returns the complete stock report,
        including opening stock every inward and outward quantity and running balance for every transaction along with transaction type.
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
            try:
                self.con = eng.connect()
                orgcode = authDetails["orgcode"]
                productCode = self.request.params["productcode"]
                startDate = datetime.strptime(
                    str(self.request.params["startdate"]), "%Y-%m-%d"
                )
                endDate = datetime.strptime(
                    str(self.request.params["enddate"]), "%Y-%m-%d"
                )
                stockReport = []
                totalinward = 0.00
                totaloutward = 0.00
                openingStockResult = self.con.execute(
                    select([product.c.openingstock]).where(
                        and_(
                            product.c.productcode == productCode,
                            product.c.orgcode == orgcode,
                        )
                    )
                )
                osRow = openingStockResult.fetchone()
                openingStock = osRow["openingstock"]
                stockRecords = self.con.execute(
                    select([stock])
                    .where(
                        and_(
                            stock.c.productcode == productCode,
                            stock.c.orgcode == orgcode,
                        )
                    )
                    .order_by(stock.c.stockdate)
                )
                stockData = stockRecords.fetchall()
                ysData = self.con.execute(
                    select([organisation.c.yearstart]).where(
                        organisation.c.orgcode == orgcode
                    )
                )
                ysRow = ysData.fetchone()
                yearStart = datetime.strptime(str(ysRow["yearstart"]), "%Y-%m-%d")
                enData = self.con.execute(
                    select([organisation.c.yearend]).where(
                        organisation.c.orgcode == orgcode
                    )
                )
                enRow = enData.fetchone()
                yearend = datetime.strptime(str(enRow["yearend"]), "%Y-%m-%d")
                if startDate > yearStart:
                    for stockRow in stockData:
                        if stockRow["dcinvtnflag"] == 3 or stockRow["dcinvtnflag"] == 9:
                            countresult = self.con.execute(
                                select(
                                    [func.count(invoice.c.invid).label("inv")]
                                ).where(
                                    and_(
                                        invoice.c.invoicedate >= yearStart,
                                        invoice.c.invoicedate < startDate,
                                        invoice.c.invid == stockRow["dcinvtnid"],
                                    )
                                )
                            )
                            countrow = countresult.fetchone()
                            if countrow["inv"] == 1:
                                if stockRow["inout"] == 9:
                                    openingStock = float(openingStock) + float(
                                        stockRow["qty"]
                                    )
                                if stockRow["inout"] == 15:
                                    openingStock = float(openingStock) - float(
                                        stockRow["qty"]
                                    )
                        if stockRow["dcinvtnflag"] == 4:
                            countresult = self.con.execute(
                                select([func.count(delchal.c.dcid).label("dc")]).where(
                                    and_(
                                        delchal.c.dcdate >= yearStart,
                                        delchal.c.dcdate < startDate,
                                        delchal.c.dcid == stockRow["dcinvtnid"],
                                    )
                                )
                            )
                            countrow = countresult.fetchone()
                            if countrow["dc"] == 1:
                                if stockRow["inout"] == 9:
                                    openingStock = float(openingStock) + float(
                                        stockRow["qty"]
                                    )
                                if stockRow["inout"] == 15:
                                    openingStock = float(openingStock) - float(
                                        stockRow["qty"]
                                    )
                        if stockRow["dcinvtnflag"] == 18:
                            if stockRow["inout"] == 9:
                                openingStock = float(openingStock) + float(
                                    stockRow["qty"]
                                )
                                totalinward = float(totalinward) + float(
                                    stockRow["qty"]
                                )
                            if stockRow["inout"] == 15:
                                openingStock = float(openingStock) - float(
                                    stockRow["qty"]
                                )
                                totaloutward = float(totaloutward) + float(
                                    stockRow["qty"]
                                )
                        if stockRow["dcinvtnflag"] == 7:
                            countresult = self.con.execute(
                                select([func.count(drcr.c.drcrid).label("dc")]).where(
                                    and_(
                                        drcr.c.drcrdate >= yearStart,
                                        drcr.c.drcrdate < startDate,
                                        drcr.c.drcrid == stockRow["dcinvtnid"],
                                    )
                                )
                            )
                            countrow = countresult.fetchone()
                            if countrow["dc"] == 1:
                                if stockRow["inout"] == 9:
                                    openingStock = float(openingStock) + float(
                                        stockRow["qty"]
                                    )
                                if stockRow["inout"] == 15:
                                    openingStock = float(openingStock) - float(
                                        stockRow["qty"]
                                    )
                stockReport.append(
                    {
                        "date": "",
                        "particulars": "opening stock",
                        "trntype": "",
                        "dcid": "",
                        "dcno": "",
                        "drcrno": "",
                        "drcrid": "",
                        "invid": "",
                        "invno": "",
                        "rnid": "",
                        "rnno": "",
                        "balance": "%.2f" % float(openingStock),
                        "inward": "%.2f" % float(openingStock),
                    }
                )
                totalinward = totalinward + float(openingStock)
                for finalRow in stockData:
                    if finalRow["dcinvtnflag"] == 3 or finalRow["dcinvtnflag"] == 9:
                        countresult = self.con.execute(
                            select(
                                [
                                    invoice.c.invoicedate,
                                    invoice.c.invoiceno,
                                    invoice.c.custid,
                                ]
                            ).where(
                                and_(
                                    invoice.c.invoicedate >= startDate,
                                    invoice.c.invoicedate <= endDate,
                                    invoice.c.invid == finalRow["dcinvtnid"],
                                )
                            )
                        )
                        if countresult.rowcount == 1:
                            countrow = countresult.fetchone()

                            custdata = self.con.execute(
                                select([customerandsupplier.c.custname]).where(
                                    customerandsupplier.c.custid == countrow["custid"]
                                )
                            )
                            custrow = custdata.fetchone()
                            if custrow != None:
                                custnamedata = custrow["custname"]
                            else:
                                custnamedata = "Cash Memo"
                            if finalRow["inout"] == 9:
                                openingStock = float(openingStock) + float(
                                    finalRow["qty"]
                                )
                                totalinward = float(totalinward) + float(
                                    finalRow["qty"]
                                )
                                stockReport.append(
                                    {
                                        "date": datetime.strftime(
                                            datetime.strptime(
                                                str(countrow["invoicedate"].date()),
                                                "%Y-%m-%d",
                                            ).date(),
                                            "%d-%m-%Y",
                                        ),
                                        "particulars": custnamedata,
                                        "trntype": "invoice",
                                        "dcid": "",
                                        "dcno": "",
                                        "drcrno": "",
                                        "drcrid": "",
                                        "rnid": "",
                                        "rnno": "",
                                        "invid": finalRow["dcinvtnid"],
                                        "invno": countrow["invoiceno"],
                                        "inwardqty": "%.2f" % float(finalRow["qty"]),
                                        "outwardqty": "",
                                        "balance": "%.2f" % float(openingStock),
                                    }
                                )
                            if finalRow["inout"] == 15:
                                openingStock = float(openingStock) - float(
                                    finalRow["qty"]
                                )
                                totaloutward = float(totaloutward) + float(
                                    finalRow["qty"]
                                )
                                stockReport.append(
                                    {
                                        "date": datetime.strftime(
                                            datetime.strptime(
                                                str(countrow["invoicedate"].date()),
                                                "%Y-%m-%d",
                                            ).date(),
                                            "%d-%m-%Y",
                                        ),
                                        "particulars": custnamedata,
                                        "trntype": "invoice",
                                        "dcid": "",
                                        "dcno": "",
                                        "rnid": "",
                                        "rnno": "",
                                        "invid": finalRow["dcinvtnid"],
                                        "invno": countrow["invoiceno"],
                                        "inwardqty": "",
                                        "outwardqty": "%.2f" % float(finalRow["qty"]),
                                        "balance": "%.2f" % float(openingStock),
                                    }
                                )

                    if finalRow["dcinvtnflag"] == 4:
                        countresult = self.con.execute(
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

                            custdata = self.con.execute(
                                select([customerandsupplier.c.custname]).where(
                                    customerandsupplier.c.custid == countrow["custid"]
                                )
                            )
                            custrow = custdata.fetchone()
                            dcinvresult = self.con.execute(
                                select([dcinv.c.invid]).where(
                                    dcinv.c.dcid == finalRow["dcinvtnid"]
                                )
                            )
                            if dcinvresult.rowcount == 1:
                                dcinvrow = dcinvresult.fetchone()
                                invresult = self.con.execute(
                                    select(
                                        [invoice.c.invoiceno, invoice.c.icflag]
                                    ).where(invoice.c.invid == dcinvrow["invid"])
                                )
                                """ No need to check if invresult has rowcount 1 since it must be 1 """
                                invrow = invresult.fetchone()
                                trntype = "delchal&invoice"
                            else:
                                dcinvrow = {"invid": ""}
                                invrow = {"invoiceno": "", "icflag": ""}
                                trntype = "delchal"

                            if finalRow["inout"] == 9:
                                openingStock = float(openingStock) + float(
                                    finalRow["qty"]
                                )
                                totalinward = float(totalinward) + float(
                                    finalRow["qty"]
                                )

                                stockReport.append(
                                    {
                                        "date": datetime.strftime(
                                            datetime.strptime(
                                                str(countrow["dcdate"].date()),
                                                "%Y-%m-%d",
                                            ).date(),
                                            "%d-%m-%Y",
                                        ),
                                        "particulars": custrow["custname"],
                                        "trntype": trntype,
                                        "dcid": finalRow["dcinvtnid"],
                                        "dcno": countrow["dcno"],
                                        "drcrno": "",
                                        "drcrid": "",
                                        "rnid": "",
                                        "rnno": "",
                                        "invid": dcinvrow["invid"],
                                        "invno": invrow["invoiceno"],
                                        "icflag": invrow["icflag"],
                                        "inwardqty": "%.2f" % float(finalRow["qty"]),
                                        "outwardqty": "",
                                        "balance": "%.2f" % float(openingStock),
                                    }
                                )
                            if finalRow["inout"] == 15:
                                openingStock = float(openingStock) - float(
                                    finalRow["qty"]
                                )
                                totaloutward = float(totaloutward) + float(
                                    finalRow["qty"]
                                )

                                stockReport.append(
                                    {
                                        "date": datetime.strftime(
                                            datetime.strptime(
                                                str(countrow["dcdate"].date()),
                                                "%Y-%m-%d",
                                            ).date(),
                                            "%d-%m-%Y",
                                        ),
                                        "particulars": custrow["custname"],
                                        "trntype": trntype,
                                        "dcid": finalRow["dcinvtnid"],
                                        "dcno": countrow["dcno"],
                                        "drcrno": "",
                                        "drcrid": "",
                                        "invid": dcinvrow["invid"],
                                        "invno": invrow["invoiceno"],
                                        "icflag": invrow["icflag"],
                                        "rnid": "",
                                        "rnno": "",
                                        "inwardqty": "",
                                        "outwardqty": "%.2f" % float(finalRow["qty"]),
                                        "balance": "%.2f" % float(openingStock),
                                    }
                                )

                    if finalRow["dcinvtnflag"] == 18:
                        countresult = self.con.execute(
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
                                custdata = self.con.execute(
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
                                custdata = self.con.execute(
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
                            if finalRow["inout"] == 9:
                                openingStock = float(openingStock) + float(
                                    finalRow["qty"]
                                )
                                totalinward = float(totalinward) + float(
                                    finalRow["qty"]
                                )
                                stockReport.append(
                                    {
                                        "date": datetime.strftime(
                                            datetime.strptime(
                                                str(countrow["rndate"].date()),
                                                "%Y-%m-%d",
                                            ).date(),
                                            "%d-%m-%Y",
                                        ),
                                        "particulars": custrow["custname"],
                                        "trntype": "Rejection Note",
                                        "rnid": finalRow["dcinvtnid"],
                                        "rnno": countrow["rnno"],
                                        "dcno": "",
                                        "invid": "",
                                        "invno": "",
                                        "tnid": "",
                                        "tnno": "",
                                        "inwardqty": "%.2f" % float(finalRow["qty"]),
                                        "outwardqty": "",
                                        "balance": "%.2f" % float(openingStock),
                                    }
                                )
                            if finalRow["inout"] == 15:
                                openingStock = float(openingStock) - float(
                                    finalRow["qty"]
                                )
                                totaloutward = float(totaloutward) + float(
                                    finalRow["qty"]
                                )
                                stockReport.append(
                                    {
                                        "date": datetime.strftime(
                                            datetime.strptime(
                                                str(countrow["rndate"].date()),
                                                "%Y-%m-%d",
                                            ).date(),
                                            "%d-%m-%Y",
                                        ),
                                        "particulars": custrow["custname"],
                                        "trntype": "Rejection Note",
                                        "rnid": finalRow["dcinvtnid"],
                                        "rnno": countrow["rnno"],
                                        "dcno": "",
                                        "drcrno": "",
                                        "drcrid": "",
                                        "invid": "",
                                        "invno": "",
                                        "tnid": "",
                                        "tnno": "",
                                        "inwardqty": "",
                                        "outwardqty": "%.2f" % float(finalRow["qty"]),
                                        "balance": "%.2f" % float(openingStock),
                                    }
                                )
                    if finalRow["dcinvtnflag"] == 7:
                        countresult = self.con.execute(
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
                            drcrinvdata = self.con.execute(
                                select([invoice.c.custid]).where(
                                    invoice.c.invid == countrow["invid"]
                                )
                            )
                            drcrinv = drcrinvdata.fetchone()
                            custdata = self.con.execute(
                                select([customerandsupplier.c.custname]).where(
                                    customerandsupplier.c.custid == drcrinv["custid"]
                                )
                            )
                            custrow = custdata.fetchone()
                            if int(countrow["dctypeflag"] == 3):
                                trntype = "Credit Note"
                            else:
                                trntype = "Debit Note"
                            if finalRow["inout"] == 9:
                                openingStock = float(openingStock) + float(
                                    finalRow["qty"]
                                )
                                totalinward = float(totalinward) + float(
                                    finalRow["qty"]
                                )

                                stockReport.append(
                                    {
                                        "date": datetime.strftime(
                                            datetime.strptime(
                                                str(countrow["drcrdate"].date()),
                                                "%Y-%m-%d",
                                            ).date(),
                                            "%d-%m-%Y",
                                        ),
                                        "particulars": custrow["custname"],
                                        "trntype": trntype,
                                        "drcrid": finalRow["dcinvtnid"],
                                        "drcrno": countrow["drcrno"],
                                        "dcno": "",
                                        "dcid": "",
                                        "rnid": "",
                                        "rnno": "",
                                        "invid": "",
                                        "invno": "",
                                        "inwardqty": "%.2f" % float(finalRow["qty"]),
                                        "outwardqty": "",
                                        "balance": "%.2f" % float(openingStock),
                                    }
                                )
                            if finalRow["inout"] == 15:
                                openingStock = float(openingStock) - float(
                                    finalRow["qty"]
                                )
                                totaloutward = float(totaloutward) + float(
                                    finalRow["qty"]
                                )

                                stockReport.append(
                                    {
                                        "date": datetime.strftime(
                                            datetime.strptime(
                                                str(countrow["drcrdate"].date()),
                                                "%Y-%m-%d",
                                            ).date(),
                                            "%d-%m-%Y",
                                        ),
                                        "particulars": custrow["custname"],
                                        "trntype": trntype,
                                        "drcrid": finalRow["dcinvtnid"],
                                        "drcrno": countrow["drcrno"],
                                        "dcid": "",
                                        "dcno": "",
                                        "invid": "",
                                        "invno": "",
                                        "rnid": "",
                                        "rnno": "",
                                        "inwardqty": "",
                                        "outwardqty": "%.2f" % float(finalRow["qty"]),
                                        "balance": "%.2f" % float(openingStock),
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
                        "drcrno": "",
                        "drcrid": "",
                        "trntype": "",
                        "totalinwardqty": "%.2f" % float(totalinward),
                        "totaloutwardqty": "%.2f" % float(totaloutward),
                    }
                )
                self.con.close()
                return {"gkstatus": enumdict["Success"], "gkresult": stockReport}
            except:
                self.con.close()
                return {"gkstatus": enumdict["ConnectionFailed"]}

    @view_config(route_name="stock-on-hand", renderer="json")
    def stockOnHandReport(self):
        """
        Purpose:
        Return the structured data grid of stock report for given product.
        Input will be productcode,startdate,enddate.
        orgcode will be taken from header and enddate
        returns a list of dictionaries where every dictionary will be one row.
        description:
        This function returns the complete stock report,
        including opening stock every inward and outward quantity and running balance for every transaction along with transaction type.
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
                productCode = self.request.params["productcode"]
                endDate = datetime.strptime(
                    str(self.request.params["enddate"]), "%Y-%m-%d"
                )
                stockresult = stockonhandfun(con, orgcode, productCode, endDate)
                return {
                    "gkstatus": enumdict["Success"],
                    "gkresult": stockresult["gkresult"],
                }


    @view_config(route_name="category-wise-stock-on-hand", renderer="json")
    def categorywiseStockOnHandReport(self):
        """
        Purpose:
        Return the structured data grid of stock report for all products in given category.
        Input will be categorycodecode, enddate.
        orgcode will be taken from header
        returns a list of dictionaries where every dictionary will be one row.
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
                goid = self.request.params["goid"]
                subcategorycode = self.request.params["subcategorycode"]
                speccode = self.request.params["speccode"]
                orgcode = authDetails["orgcode"]
                categorycode = self.request.params["categorycode"]
                endDate = datetime.strptime(
                    str(self.request.params["enddate"]), "%Y-%m-%d"
                )
                stockReport = []
                totalinward = 0.00
                totaloutward = 0.00
                """get its subcategories as well"""
                catdata = []
                # when there is some subcategory then get all N level categories of this category.
                if subcategorycode != "all":
                    catdata.append(int(subcategorycode))
                    for ccode in catdata:
                        result = self.con.execute(
                            select([categorysubcategories.c.categorycode]).where(
                                and_(
                                    categorysubcategories.c.orgcode == orgcode,
                                    categorysubcategories.c.subcategoryof == ccode,
                                )
                            )
                        )
                        result = result.fetchall()
                        for cat in result:
                            catdata.append(cat[0])
                # when subcategory is not there get all N level categories of main category.
                else:
                    catdata.append(int(categorycode))
                    for ccode in catdata:
                        result = self.con.execute(
                            select([categorysubcategories.c.categorycode]).where(
                                and_(
                                    categorysubcategories.c.orgcode == orgcode,
                                    categorysubcategories.c.subcategoryof == ccode,
                                )
                            )
                        )
                        result = result.fetchall()
                        for cat in result:
                            catdata.append(cat[0])
                # if godown wise report selected
                if goid != "-1" and goid != "all":
                    products = self.con.execute(
                        select(
                            [
                                goprod.c.goopeningstock.label("openingstock"),
                                product.c.productcode,
                                product.c.productdesc,
                            ]
                        ).where(
                            and_(
                                product.c.orgcode == orgcode,
                                goprod.c.orgcode == orgcode,
                                goprod.c.goid == int(goid),
                                product.c.productcode == goprod.c.productcode,
                                product.c.categorycode.in_(catdata),
                            )
                        )
                    )
                    prodDesc = products.fetchall()
                    srno = 1
                    for row in prodDesc:
                        totalinwardgo = 0.00
                        totaloutwardgo = 0.00
                        gopeningStock = row["openingstock"]
                        stockRecords = self.con.execute(
                            select([stock])
                            .where(
                                and_(
                                    stock.c.productcode == row["productcode"],
                                    stock.c.goid == int(goid),
                                    stock.c.orgcode == orgcode,
                                )
                            )
                            .order_by(stock.c.stockdate)
                        )
                        stockData = stockRecords.fetchall()
                        ysData = self.con.execute(
                            select([organisation.c.yearstart]).where(
                                organisation.c.orgcode == orgcode
                            )
                        )
                        ysRow = ysData.fetchone()
                        yearStart = datetime.strptime(
                            str(ysRow["yearstart"]), "%Y-%m-%d"
                        )
                        totalinwardgo = totalinwardgo + float(gopeningStock)
                        for finalRow in stockData:
                            if finalRow["dcinvtnflag"] == 4:
                                countresult = self.con.execute(
                                    select(
                                        [
                                            delchal.c.dcdate,
                                            delchal.c.dcno,
                                            delchal.c.custid,
                                        ]
                                    ).where(
                                        and_(
                                            delchal.c.dcdate <= endDate,
                                            delchal.c.dcid == finalRow["dcinvtnid"],
                                        )
                                    )
                                )
                                if countresult.rowcount == 1:
                                    countrow = countresult.fetchone()
                                    custdata = self.con.execute(
                                        select([customerandsupplier.c.custname]).where(
                                            customerandsupplier.c.custid
                                            == countrow["custid"]
                                        )
                                    )
                                    custrow = custdata.fetchone()
                                    dcinvresult = self.con.execute(
                                        select([dcinv.c.invid]).where(
                                            dcinv.c.dcid == finalRow["dcinvtnid"]
                                        )
                                    )
                                    if dcinvresult.rowcount == 1:
                                        dcinvrow = dcinvresult.fetchone()
                                        invresult = self.con.execute(
                                            select([invoice.c.invoiceno]).where(
                                                invoice.c.invid == dcinvrow["invid"]
                                            )
                                        )
                                        """ No need to check if invresult has rowcount 1 since it must be 1 """
                                        invrow = invresult.fetchone()
                                        trntype = "delchal&invoice"
                                    else:
                                        dcinvrow = {"invid": ""}
                                        invrow = {"invoiceno": ""}
                                        trntype = "delchal"
                                    if finalRow["inout"] == 9:
                                        gopeningStock = float(gopeningStock) + float(
                                            finalRow["qty"]
                                        )
                                        totalinwardgo = float(totalinwardgo) + float(
                                            finalRow["qty"]
                                        )

                                    if finalRow["inout"] == 15:
                                        gopeningStock = float(gopeningStock) - float(
                                            finalRow["qty"]
                                        )
                                        totaloutward = float(totaloutwardgo) + float(
                                            finalRow["qty"]
                                        )
                            if finalRow["dcinvtnflag"] == 20:
                                countresult = self.con.execute(
                                    select(
                                        [
                                            transfernote.c.transfernotedate,
                                            transfernote.c.transfernoteno,
                                        ]
                                    ).where(
                                        and_(
                                            transfernote.c.transfernotedate <= endDate,
                                            transfernote.c.transfernoteid
                                            == finalRow["dcinvtnid"],
                                        )
                                    )
                                )
                                if countresult.rowcount == 1:
                                    countrow = countresult.fetchone()
                                    if finalRow["inout"] == 9:
                                        gopeningStock = float(gopeningStock) + float(
                                            finalRow["qty"]
                                        )
                                        totalinwardgo = float(totalinwardgo) + float(
                                            finalRow["qty"]
                                        )

                                    if finalRow["inout"] == 15:
                                        gopeningStock = float(gopeningStock) - float(
                                            finalRow["qty"]
                                        )
                                        totaloutwardgo = float(totaloutwardgo) + float(
                                            finalRow["qty"]
                                        )
                            if finalRow["dcinvtnflag"] == 18:
                                if finalRow["inout"] == 9:
                                    gopeningStock = float(gopeningStock) + float(
                                        finalRow["qty"]
                                    )
                                    totalinward = float(totalinward) + float(
                                        finalRow["qty"]
                                    )
                                if finalRow["inout"] == 15:
                                    gopeningStock = float(gopeningStock) - float(
                                        finalRow["qty"]
                                    )
                                    totaloutward = float(totaloutward) + float(
                                        finalRow["qty"]
                                    )
                        stockReport.append(
                            {
                                "srno": srno,
                                "productname": row["productdesc"],
                                "totalinwardqty": "%.2f" % float(totalinwardgo),
                                "totaloutwardqty": "%.2f" % float(totaloutwardgo),
                                "balance": "%.2f" % float(gopeningStock),
                            }
                        )
                        srno += 1
                    self.con.close()
                    return {"gkstatus": enumdict["Success"], "gkresult": stockReport}
                # if godown wise report selected but all godowns selected
                elif goid == "all":
                    products = self.con.execute(
                        select(
                            [
                                goprod.c.goopeningstock.label("openingstock"),
                                goprod.c.goid,
                                product.c.productcode,
                                product.c.productdesc,
                            ]
                        ).where(
                            and_(
                                product.c.orgcode == orgcode,
                                goprod.c.orgcode == orgcode,
                                product.c.productcode == goprod.c.productcode,
                                product.c.categorycode.in_(catdata),
                            )
                        )
                    )
                    prodDesc = products.fetchall()
                    srno = 1
                    for row in prodDesc:
                        totalinwardgo = 0.00
                        totaloutwardgo = 0.00
                        gopeningStock = row["openingstock"]
                        godowns = self.con.execute(
                            select([godown.c.goname]).where(
                                and_(
                                    godown.c.goid == row["goid"],
                                    godown.c.orgcode == orgcode,
                                )
                            )
                        )
                        stockRecords = self.con.execute(
                            select([stock])
                            .where(
                                and_(
                                    stock.c.productcode == row["productcode"],
                                    stock.c.goid == int(row["goid"]),
                                    stock.c.orgcode == orgcode,
                                )
                            )
                            .order_by(stock.c.stockdate)
                        )
                        stockData = stockRecords.fetchall()
                        ysData = self.con.execute(
                            select([organisation.c.yearstart]).where(
                                organisation.c.orgcode == orgcode
                            )
                        )
                        ysRow = ysData.fetchone()
                        yearStart = datetime.strptime(
                            str(ysRow["yearstart"]), "%Y-%m-%d"
                        )
                        totalinwardgo = totalinwardgo + float(gopeningStock)
                        for finalRow in stockData:
                            if finalRow["dcinvtnflag"] == 4:
                                countresult = self.con.execute(
                                    select(
                                        [
                                            delchal.c.dcdate,
                                            delchal.c.dcno,
                                            delchal.c.custid,
                                        ]
                                    ).where(
                                        and_(
                                            delchal.c.dcdate <= endDate,
                                            delchal.c.dcid == finalRow["dcinvtnid"],
                                        )
                                    )
                                )
                                if countresult.rowcount == 1:
                                    countrow = countresult.fetchone()
                                    custdata = self.con.execute(
                                        select([customerandsupplier.c.custname]).where(
                                            customerandsupplier.c.custid
                                            == countrow["custid"]
                                        )
                                    )
                                    custrow = custdata.fetchone()
                                    dcinvresult = self.con.execute(
                                        select([dcinv.c.invid]).where(
                                            dcinv.c.dcid == finalRow["dcinvtnid"]
                                        )
                                    )
                                    if dcinvresult.rowcount == 1:
                                        dcinvrow = dcinvresult.fetchone()
                                        invresult = self.con.execute(
                                            select([invoice.c.invoiceno]).where(
                                                invoice.c.invid == dcinvrow["invid"]
                                            )
                                        )
                                        """ No need to check if invresult has rowcount 1 since it must be 1 """
                                        invrow = invresult.fetchone()
                                        trntype = "delchal&invoice"
                                    else:
                                        dcinvrow = {"invid": ""}
                                        invrow = {"invoiceno": ""}
                                        trntype = "delchal"
                                    if finalRow["inout"] == 9:
                                        gopeningStock = float(gopeningStock) + float(
                                            finalRow["qty"]
                                        )
                                        totalinwardgo = float(totalinwardgo) + float(
                                            finalRow["qty"]
                                        )

                                    if finalRow["inout"] == 15:
                                        gopeningStock = float(gopeningStock) - float(
                                            finalRow["qty"]
                                        )
                                        totaloutward = float(totaloutwardgo) + float(
                                            finalRow["qty"]
                                        )
                            if finalRow["dcinvtnflag"] == 20:
                                countresult = self.con.execute(
                                    select(
                                        [
                                            transfernote.c.transfernotedate,
                                            transfernote.c.transfernoteno,
                                        ]
                                    ).where(
                                        and_(
                                            transfernote.c.transfernotedate <= endDate,
                                            transfernote.c.transfernoteid
                                            == finalRow["dcinvtnid"],
                                        )
                                    )
                                )
                                if countresult.rowcount == 1:
                                    countrow = countresult.fetchone()
                                    if finalRow["inout"] == 9:
                                        gopeningStock = float(gopeningStock) + float(
                                            finalRow["qty"]
                                        )
                                        totalinwardgo = float(totalinwardgo) + float(
                                            finalRow["qty"]
                                        )

                                    if finalRow["inout"] == 15:
                                        gopeningStock = float(gopeningStock) - float(
                                            finalRow["qty"]
                                        )
                                        totaloutwardgo = float(totaloutwardgo) + float(
                                            finalRow["qty"]
                                        )

                            if finalRow["dcinvtnflag"] == 18:
                                if finalRow["inout"] == 9:
                                    gopeningStock = float(gopeningStock) + float(
                                        finalRow["qty"]
                                    )
                                    totalinward = float(totalinward) + float(
                                        finalRow["qty"]
                                    )
                                if finalRow["inout"] == 15:
                                    gopeningStock = float(gopeningStock) - float(
                                        finalRow["qty"]
                                    )
                                    totaloutward = float(totaloutward) + float(
                                        finalRow["qty"]
                                    )
                        stockReport.append(
                            {
                                "srno": srno,
                                "productname": row["productdesc"],
                                "godown": godowns.fetchone()["goname"],
                                "totalinwardqty": "%.2f" % float(totalinwardgo),
                                "totaloutwardqty": "%.2f" % float(totaloutwardgo),
                                "balance": "%.2f" % float(gopeningStock),
                            }
                        )
                        srno += 1
                    self.con.close()
                    return {"gkstatus": enumdict["Success"], "gkresult": stockReport}
                # No godown selected just categorywise stock on hand report
                else:
                    products = self.con.execute(
                        select(
                            [
                                product.c.openingstock,
                                product.c.productcode,
                                product.c.productdesc,
                            ]
                        ).where(
                            and_(
                                product.c.orgcode == orgcode,
                                product.c.categorycode.in_(catdata),
                            )
                        )
                    )
                    prodDesc = products.fetchall()
                    srno = 1
                    for row in prodDesc:
                        totalinward = 0.00
                        totaloutward = 0.00
                        openingStock = row["openingstock"]
                        productCd = row["productcode"]
                        prodName = row["productdesc"]
                        if goid != "-1" and goid != "all":
                            stockRecords = self.con.execute(
                                select([stock])
                                .where(
                                    and_(
                                        stock.c.productcode == productCd,
                                        stock.c.goid == int(goid),
                                        stock.c.orgcode == orgcode,
                                    )
                                )
                                .order_by(stock.c.stockdate)
                            )
                        else:
                            stockRecords = self.con.execute(
                                select([stock]).where(
                                    and_(
                                        stock.c.productcode == productCd,
                                        stock.c.orgcode == orgcode,
                                    )
                                )
                            )
                        stockData = stockRecords.fetchall()
                        totalinward = totalinward + float(openingStock)
                        for finalRow in stockData:
                            if (
                                finalRow["dcinvtnflag"] == 3
                                or finalRow["dcinvtnflag"] == 9
                            ):
                                countresult = self.con.execute(
                                    select(
                                        [
                                            invoice.c.invoicedate,
                                            invoice.c.invoiceno,
                                            invoice.c.custid,
                                        ]
                                    ).where(
                                        and_(
                                            invoice.c.invoicedate <= endDate,
                                            invoice.c.invid == finalRow["dcinvtnid"],
                                        )
                                    )
                                )
                                if countresult.rowcount == 1:
                                    countrow = countresult.fetchone()
                                    custdata = self.con.execute(
                                        select([customerandsupplier.c.custname]).where(
                                            customerandsupplier.c.custid
                                            == countrow["custid"]
                                        )
                                    )
                                    custrow = custdata.fetchone()
                                    if custrow != None:
                                        custnamedata = custrow["custname"]
                                    else:
                                        custnamedata = "Cash Memo"
                                    if finalRow["inout"] == 9:
                                        openingStock = float(openingStock) + float(
                                            finalRow["qty"]
                                        )
                                        totalinward = float(totalinward) + float(
                                            finalRow["qty"]
                                        )
                                    if finalRow["inout"] == 15:
                                        openingStock = float(openingStock) - float(
                                            finalRow["qty"]
                                        )
                                        totaloutward = float(totaloutward) + float(
                                            finalRow["qty"]
                                        )

                            if finalRow["dcinvtnflag"] == 4:
                                countresult = self.con.execute(
                                    select(
                                        [
                                            delchal.c.dcdate,
                                            delchal.c.dcno,
                                            delchal.c.custid,
                                        ]
                                    ).where(
                                        and_(
                                            delchal.c.dcdate <= endDate,
                                            delchal.c.dcid == finalRow["dcinvtnid"],
                                        )
                                    )
                                )
                                if countresult.rowcount == 1:
                                    countrow = countresult.fetchone()
                                    custdata = self.con.execute(
                                        select([customerandsupplier.c.custname]).where(
                                            customerandsupplier.c.custid
                                            == countrow["custid"]
                                        )
                                    )
                                    custrow = custdata.fetchone()
                                    dcinvresult = self.con.execute(
                                        select([dcinv.c.invid]).where(
                                            dcinv.c.dcid == finalRow["dcinvtnid"]
                                        )
                                    )
                                    if dcinvresult.rowcount == 1:
                                        dcinvrow = dcinvresult.fetchone()
                                        invresult = self.con.execute(
                                            select([invoice.c.invoiceno]).where(
                                                invoice.c.invid == dcinvrow["invid"]
                                            )
                                        )
                                        """ No need to check if invresult has rowcount 1 since it must be 1 """
                                        invrow = invresult.fetchone()
                                        trntype = "delchal&invoice"
                                    else:
                                        dcinvrow = {"invid": ""}
                                        invrow = {"invoiceno": ""}
                                        trntype = "delchal"
                                    if finalRow["inout"] == 9:
                                        openingStock = float(openingStock) + float(
                                            finalRow["qty"]
                                        )
                                        totalinward = float(totalinward) + float(
                                            finalRow["qty"]
                                        )
                                    if finalRow["inout"] == 15:
                                        openingStock = float(openingStock) - float(
                                            finalRow["qty"]
                                        )
                                        totaloutward = float(totaloutward) + float(
                                            finalRow["qty"]
                                        )

                            if finalRow["dcinvtnflag"] == 18:
                                if finalRow["inout"] == 9:
                                    openingStock = float(openingStock) + float(
                                        finalRow["qty"]
                                    )
                                    totalinward = float(totalinward) + float(
                                        finalRow["qty"]
                                    )
                                if finalRow["inout"] == 15:
                                    openingStock = float(openingStock) - float(
                                        finalRow["qty"]
                                    )
                                    totaloutward = float(totaloutward) + float(
                                        finalRow["qty"]
                                    )

                        stockReport.append(
                            {
                                "srno": srno,
                                "productname": prodName,
                                "totalinwardqty": "%.2f" % float(totalinward),
                                "totaloutwardqty": "%.2f" % float(totaloutward),
                                "balance": "%.2f" % float(openingStock),
                            }
                        )
                        srno = srno + 1
                    return {"gkstatus": enumdict["Success"], "gkresult": stockReport}
            except:
                return {"gkstatus": enumdict["ConnectionFailed"]}
            finally:
                self.con.close()
