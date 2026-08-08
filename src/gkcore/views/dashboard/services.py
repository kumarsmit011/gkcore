from typing import Tuple
from gkcore import eng, enumdict
from gkcore.utils import generate_month_start_end_dates
from gkcore.views.helpers.invoice import get_business_item_invoice_data, get_invoice_details
from sqlalchemy.sql import select
from sqlalchemy import and_, desc
from sqlalchemy.engine import ResultProxy
from sqlalchemy.engine.base import Connection
from sqlalchemy.sql.expression import text
from gkcore.models.gkdb import (
    invoice,
    customerandsupplier,
    organisation,
    stock,
    accounts,
)
from datetime import datetime, date
from monthdelta import monthdelta
import calendar
from gkcore.views.reports.helpers.balance import calculateBalance, get_current_balance


# This function is use to show amount wise top five unpaid invoice list at dashboard
def amountwiseinvoice(inoutflag, orgcode):
    try:
        con = eng.connect()
        fiveInvoiceslistdata = []
        # Invoices in descending order of amount.
        fiveinvoices = con.execute(
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
                    invoice.c.orgcode == orgcode,
                    invoice.c.inoutflag == inoutflag,
                )
            )
            .order_by(desc(invoice.c.invoicetotal - invoice.c.amountpaid))
            .limit(5)
        )
        fiveInvoiceslist = fiveinvoices.fetchall()
        for inv in fiveInvoiceslist:
            # for fetch customer or supplier name using cust id in invoice.
            csd = con.execute(
                select(
                    [customerandsupplier.c.custname, customerandsupplier.c.csflag]
                ).where(
                    and_(
                        customerandsupplier.c.custid == inv["custid"],
                        customerandsupplier.c.orgcode == orgcode,
                    )
                )
            )
            csDetails = csd.fetchone()
            fiveInvoiceslistdata.append(
                {
                    "invid": inv["invid"],
                    "invoiceno": inv["invoiceno"],
                    "invoicedate": datetime.strftime(inv["invoicedate"], "%d-%m-%Y"),
                    "balanceamount": "%.2f"
                    % (float(inv["invoicetotal"] - inv["amountpaid"])),
                    "custname": csDetails["custname"],
                    "csflag": csDetails["csflag"],
                }
            )
        con.close()
        return {
            "gkstatus": enumdict["Success"],
            "fiveInvoiceslistdata": fiveInvoiceslistdata,
        }
    except:
        con.close()
        return {"gkstatus": enumdict["ConnectionFailed"]}
    finally:
        con.close()


# This function is use to show date wise top five unpaid invoice list at dashboard
def datewiseinvoice(inoutflag, orgcode):
    try:
        con = eng.connect()
        fiveInvoiceslistdata = []
        # Invoices in ascending order of date.
        fiveinvoices = con.execute(
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
                    invoice.c.orgcode == orgcode,
                    invoice.c.inoutflag == inoutflag,
                )
            )
            .order_by(invoice.c.invoicedate)
            .limit(5)
        )
        fiveInvoiceslist = fiveinvoices.fetchall()

        for inv in fiveInvoiceslist:
            # for fetch customer or supplier name using cust id in invoice.
            csd = con.execute(
                select(
                    [customerandsupplier.c.custname, customerandsupplier.c.csflag]
                ).where(
                    and_(
                        customerandsupplier.c.custid == inv["custid"],
                        customerandsupplier.c.orgcode == orgcode,
                    )
                )
            )
            csDetails = csd.fetchone()
            fiveInvoiceslistdata.append(
                {
                    "invid": inv["invid"],
                    "invoiceno": inv["invoiceno"],
                    "invoicedate": datetime.strftime(inv["invoicedate"], "%d-%m-%Y"),
                    "balanceamount": "%.2f"
                    % (float(inv["invoicetotal"] - inv["amountpaid"])),
                    "custname": csDetails["custname"],
                    "csflag": csDetails["csflag"],
                }
            )
        con.close()
        return {
            "gkstatus": enumdict["Success"],
            "fiveInvoiceslistdata": fiveInvoiceslistdata,
        }
    except:
        con.close()
        return {"gkstatus": enumdict["ConnectionFailed"]}
    finally:
        con.close()


def get_invoice_monthly_balance(inoutflag, orgcode):
    """Generates monthly consolidated balances for sales and purchase for the financial
    year. Takes inoutflag (9 for sales, 15 for purchases) and org code as input.

    Output format: `[{"month": "month string", "balance": 0}, ...]`
    """
    with eng.connect() as conn:
        start_date, end_date = conn.execute(
            select([organisation.c.yearstart, organisation.c.yearend]).where(
                organisation.c.orgcode == orgcode
            )
        ).fetchone()
        month_start_end_dates = generate_month_start_end_dates(
            start_date,
            end_date,
        )
        if inoutflag not in [9,15]:
            raise AttributeError("inoutflag should be either 9 or 15.")

        account_name = "Sale A/C" if inoutflag == 15 else "Purchase A/C"
        account_code = conn.execute(
            select([accounts.c.accountcode]).where(
                and_(accounts.c.orgcode == orgcode, accounts.c.accountname == account_name)
            )
        ).fetchone()[0]

        monthly_balance = []
        for month in month_start_end_dates:
            if month[1] > date.today():
                monthly_balance.append({"month": month[0], "balance":0})
            else:
                balance = calculateBalance(
                    conn, account_code, f"{month[1]}", f"{month[1]}", f"{month[2]}",
                )
                monthly_balance.append({"month": month[0], "balance": balance["curbal"]})
        return monthly_balance


# this function use to show top five customer/supplier at dashbord in most valued costomer and supplier div
def topfivecustsup(con, inoutflag, orgcode):
    # this is to fetch top five customer which is sort by total amount.
    if inoutflag == 15:
        topfivecust = con.execute(
            "select custid as custid, sum(invoicetotal) as invoicetotal, array_agg(invid) as invids from invoice where inoutflag=15 and orgcode= %d and icflag=9 group by custid order by invoicetotal desc limit(5)"
            % (orgcode)
        )
        topfivecustlist = topfivecust.fetchall()
    # this is to fetch top five suppplier which is sort by total invoice.
    else:
        topfivecust = con.execute(
            "select custid as custid, sum(invoicetotal) as invoicetotal, array_agg(invid) as invids from invoice where inoutflag=9 and orgcode=%d and icflag=9  group by custid order by invoicetotal desc limit(5)"
            % (orgcode)
        )
        topfivecustlist = topfivecust.fetchall()

    topfivecustdetails = []
    for inv in topfivecustlist:
        # for fetch customer or supplier name using cust id in invoice.
        csd = con.execute(
            select([customerandsupplier.c.custname]).where(
                and_(
                    customerandsupplier.c.custid == inv["custid"],
                    customerandsupplier.c.orgcode == orgcode,
                )
            )
        )
        invoice_total = 0
        for invid in inv["invids"]:
            invoice_total += float(get_invoice_details(con, invid)["taxfree"])
        csDetails = csd.fetchone()
        topfivecustdetails.append(
            {
                "custname": csDetails["custname"],
                "custid": inv["custid"],
                "invoice_total": "%.2f" % invoice_total,
            }
        )

    return {
        "gkstatus": enumdict["Success"],
        "topfivecustdetails": topfivecustdetails,
    }


# this function use to show top five most bought product and service at dashbord in most bought product/service div
def topfiveprodsev(orgcode):
    try:
        con = eng.connect()
        # this is to fetch top five product/service  which is sort by  invoice count.
        topfiveprod = con.execute(
            "select ky as productcode, count(*) as numkeys from invoice cross join lateral jsonb_object_keys(contents) as t(ky) where orgcode=%d and invoice.inoutflag=9 group by ky order by count(*) desc limit(5)"
            % (orgcode)
        )
        topfiveprodlist = topfiveprod.fetchall()

        prodinfolist = []
        for prodinfo in topfiveprodlist:
            purchase = get_business_item_invoice_data(
                con, int(prodinfo["productcode"])
            )[0]
            proddesc = con.execute(
                "select productdesc as proddesc, gsflag as gs from product where productcode=%d and orgcode=%d"
                % (int(prodinfo["productcode"]), orgcode)
            )
            proddesclist = proddesc.fetchone()
            goid_result = con.execute(
                            select([stock.c.goid]).where(
                                and_(
                                    stock.c.productcode == int(prodinfo["productcode"]),
                                    stock.c.orgcode == orgcode,
                                )
                            )
                        )
            goid = goid_result.scalar()
            prodinfolist.append(
                {
                    "prodcode": prodinfo["productcode"],
                    "count": prodinfo["numkeys"],
                    "purchase": f"{purchase:.2f}",
                    "proddesc": proddesclist["proddesc"],
                    "goid": goid,
                    "gsflag": proddesclist['gs'],
                }
            )
        con.close()
        return {"gkstatus": enumdict["Success"], "prodinfolist": prodinfolist}
    except Exception as e:
        print(e)
        return {"gkstatus": enumdict["ConnectionFailed"]}


# this function use to show delchal count by month at dashbord in bar chart
def delchalcountbymonth(inoutflag, orgcode):
    try:
        con = eng.connect()
        # this is to fetch startdate and enddate
        startenddate = con.execute(
            select([organisation.c.yearstart, organisation.c.yearend]).where(
                organisation.c.orgcode == orgcode
            )
        )
        startenddateprint = startenddate.fetchone()

        # this is to fetch delchal count month wise
        monthlysortdata = con.execute(
            text("select extract(month from stockdate) as month, sum(qty) as total_qty from stock where stockdate BETWEEN ':yearstart' AND ':yearend' and inout=:inoutflag and orgcode=:orgcode and dcinvtnflag=4 group by month order by month"),
            yearstart = datetime.strftime(startenddateprint["yearstart"], "%Y-%m-%d"),
            yearend = datetime.strftime(startenddateprint["yearend"], "%Y-%m-%d"),
            inoutflag = inoutflag,
            orgcode = orgcode,
        )
        monthlysortdataset = monthlysortdata.fetchall()
        # this is use to send 0 if month have 0 delchal count
        totalamount = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
        for count in monthlysortdataset:
            totalamount[int(count["month"]) - 1] = float(count["total_qty"])
        con.close()
        return {"gkstatus": enumdict["Success"], "totalamount": totalamount}
    except:
        con.close()
        return {"gkstatus": enumdict["ConnectionFailed"]}
    finally:
        con.close()


# this fuction returns most sold product and stock on hand count for daashboard
def stockonhanddashboard(orgcode):
    try:
        con = eng.connect()
        # this is use to fetch top five product/service  which is order by  invoice count.
        topfiveprod = con.execute(
            "select ky as productcode from invoice cross join lateral jsonb_object_keys(contents) as t(ky) where orgcode=%d and invoice.inoutflag=15 group by ky order by count(*) desc limit(5)"
            % (orgcode)
        )
        topfiveprodlist = topfiveprod.fetchall()
        prodcodedesclist = []
        for prodcode in topfiveprodlist:
            proddesc = con.execute(
                "select productdesc as proddesc from product where productcode=%d"
                % (int(prodcode["productcode"]))
            )
            sale = get_business_item_invoice_data(
                con, int(prodcode["productcode"])
            )[1]
            proddesclist = proddesc.fetchone()
            prodcodedesclist.append(
                {
                    "prodcode": prodcode["productcode"],
                    "proddesc": proddesclist["proddesc"],
                    "sale": f"{sale:.2f}",
                }
            )

        con.close()
        # return {
        #     "gkstatus": enumdict["Success"],
        #     "stockresultlist": stockresultlist,
        #     "productname": prodname,
        # }
        return prodcodedesclist
    except Exception as e:
        return {"gkstatus": enumdict["ConnectionFailed"]}


# this fuction returns month wise bank and cash sub account  balance on daashboard
def cashbankbalance(orgcode):
    try:
        con = eng.connect()
        # below query is fetch account code for bank account
        accountcodebank = con.execute(
            "select accountcode as accountcode from accounts where groupcode = (select groupcode from groupsubgroups where groupname = 'Bank' and orgcode=%d) and orgcode =%d"
            % (orgcode, orgcode)
        )
        accountCodeBank = accountcodebank.fetchall()
        # below query is fetch account code for cash account
        accountcodecash = con.execute(
            "select accountcode as accountcode from accounts where groupcode = (select groupcode from groupsubgroups where groupname = 'Cash' and orgcode=%d) and orgcode =%d"
            % (orgcode, orgcode)
        )
        accountCodeCash = accountcodecash.fetchall()
        # below query is fetch finantial yearstart and yearend date
        financialstart = con.execute(
            "select yearstart as financialstart, yearend as financialend from organisation where orgcode=%d"
            % orgcode
        )
        financialStartresult = financialstart.fetchone()
        financialStart = datetime.strftime(
            financialStartresult["financialstart"], "%Y-%m-%d"
        )
        financialEnd = financialStartresult["financialend"]
        monthCounter = 1
        monthname = []
        bankbalancedata = []
        cashbalancedata = []
        balancedata = {}

        startMonthDate = financialStartresult["financialstart"]
        # endMonthDate gives last date of month
        endMonthDate = date(
            startMonthDate.year,
            startMonthDate.month,
            (calendar.monthrange(startMonthDate.year, startMonthDate.month)[1]),
        )
        while endMonthDate <= financialEnd:
            month = calendar.month_abbr[startMonthDate.month]
            monthname.append(month)
            bankbalance = 0.00
            cashbalance = 0.00
            # below code give calculate balance for bank account
            for bal in accountCodeBank:
                calbaldata = calculateBalance(
                    con,
                    bal["accountcode"],
                    str(financialStart),
                    str(startMonthDate),
                    str(endMonthDate),
                )
                if calbaldata["baltype"] == "Cr":
                    bankbalance = float(bankbalance) - float(calbaldata["curbal"])
                if calbaldata["baltype"] == "Dr":
                    bankbalance = float(bankbalance) + float(calbaldata["curbal"])
            bankbalancedata.append(bankbalance)
            # below code give calculate balance for cash account
            for bal in accountCodeCash:
                calbaldata = calculateBalance(
                    con,
                    bal["accountcode"],
                    str(financialStart),
                    str(financialStart),
                    str(endMonthDate),
                )
                if calbaldata["baltype"] == "Cr":
                    cashbalance = float(cashbalance) - float(calbaldata["curbal"])
                if calbaldata["baltype"] == "Dr":
                    cashbalance = float(cashbalance) + float(calbaldata["curbal"])
            cashbalancedata.append(cashbalance)

            startMonthDate = date(
                financialStartresult["financialstart"].year,
                financialStartresult["financialstart"].month,
                financialStartresult["financialstart"].day,
            ) + monthdelta(monthCounter)
            endMonthDate = date(
                startMonthDate.year,
                startMonthDate.month,
                calendar.monthrange(startMonthDate.year, startMonthDate.month)[1],
            )

            monthCounter += 1
        balancedata["monthname"] = monthname
        balancedata["bankbalancedata"] = bankbalancedata
        balancedata["cashbalancedata"] = cashbalancedata
        con.close()
        return {"gkstatus": enumdict["Success"], "balancedata": balancedata}
    except:
        con.close()
        return {"gkstatus": enumdict["ConnectionFailed"]}
    finally:
        con.close()

def group_accounts_by_name_balance(
        connection: Connection, accounts: ResultProxy
) -> Tuple:
    """Function to group accounts into two lists, one with account names and one with
    Account balances.
    """
    names, balances = [], []
    accounts_list = [
        {
            **dict(account),
            "current_balance": get_current_balance(connection, account)
        } for account in accounts
    ]
    sorted_accounts_list = sorted(
        accounts_list, key=lambda account: account["current_balance"], reverse=True
    )
    for account in sorted_accounts_list[:5]:
        if account["current_balance"]:
            names.append(account["accountname"])
            balances.append(account["current_balance"])
    return names, balances
