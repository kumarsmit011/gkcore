from gkcore import eng, enumdict
from gkcore.utils import authCheck, getUserRole
from gkcore.models.gkdb import (
    accounts,
    projects,
    organisation,
)
from sqlalchemy.sql import select
from sqlalchemy.sql.expression import text
from pyramid.view import view_defaults, view_config
from datetime import datetime, date
import calendar
from monthdelta import monthdelta
from gkcore.views.helpers.invoice import billwiseEntryLedger
from gkcore.views.reports.helpers.balance import calculateBalance


@view_defaults(request_method="GET")
class api_ledger(object):
    def __init__(self, request):
        self.request = request

    @view_config(route_name="ledger-monthly", renderer="json")
    def monthlyLedger(self):
        """
        Purpose:
        Gets the list of all months with their respective closing balance for the given account.
        takes accountcode as input parameter.
        description:
        This function is used to produce a monthly ledger report for a given account.
        This is a useful report from which the accountant can choose
        a month for which the entire ledger can be displayed.
        In this report just the closing balance at end of every month is displayed.
        Takes accountcode as input parameter.
        This function is called when type=monthlyledger is passed to the /reports url.
        accountcode is extracted from json_body from request.
        Orgcode is procured from the jwt header.
        The list returned is a grid containing set of dictionaries.
        For each month calculatebalance will be called to get the closing balnace for that range.
        each dictionary will have 2 keys with their respective values,
        month and balance will be the 2 key value pares.
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
                accountCode = self.request.params["accountcode"]
                accNameData = con.execute(
                    select([accounts.c.accountname]).where(
                        accounts.c.accountcode == accountCode
                    )
                )
                row = accNameData.fetchone()
                accname = row["accountname"]
                finStartData = con.execute(
                    select([organisation.c.yearstart]).where(
                        organisation.c.orgcode == orgcode
                    )
                )
                finRow = finStartData.fetchone()
                financialStart = finRow["yearstart"]
                finEndData = con.execute(
                    select([organisation.c.yearend]).where(
                        organisation.c.orgcode == orgcode
                    )
                )
                finEndrow = finEndData.fetchone()
                financialEnd = finEndrow["yearend"]
                monthCounter = 1
                startMonthDate = financialStart
                endMonthDate = date(
                    startMonthDate.year,
                    startMonthDate.month,
                    (calendar.monthrange(startMonthDate.year, startMonthDate.month)[1]),
                )
                monthlyBal = []
                while endMonthDate <= financialEnd:
                    count = con.execute(
                        text("select count(vouchercode) as vcount from vouchers where voucherdate<=:end_month_date and voucherdate>=:start_month_date and orgcode=orgcode and (drs ? :accountcode or crs ? :accountcode) "),
                            end_month_date = endMonthDate,
                            start_month_date = startMonthDate,
                            orgcode = orgcode,
                            accountcode = accountCode,
                    )
                    count = count.fetchone()
                    countDr = con.execute(
                        text("select count(vouchercode) as vcount from vouchers where voucherdate<=:end_month_date and  voucherdate>=:start_month_date and orgcode=:orgcode and (drs ? :accountcode) "),
                        end_month_date = endMonthDate,
                        start_month_date = startMonthDate,
                        orgcode = orgcode,
                        accountcode = accountCode,
                    )
                    countDr = countDr.fetchone()
                    countCr = con.execute(
                        text("select count(vouchercode) as vcount from vouchers where voucherdate<=:end_month_date and voucherdate>=:start_month_date and orgcode=:orgcode and (crs ? :accountcode) "),
                        end_month_date = endMonthDate,
                        start_month_date = startMonthDate,
                        orgcode = orgcode,
                        accountcode = accountCode,
                    )
                    countCr = countCr.fetchone()
                    countLock = con.execute(
                        text("select count(vouchercode) as vcount from vouchers where voucherdate<=:end_month_date and voucherdate>=:start_month_date and orgcode=:orgcode and lockflag='t' and (drs ? :accountcode or crs ? :accountcode) "),
                        end_month_date = endMonthDate,
                        start_month_date = startMonthDate,
                        orgcode = orgcode,
                        accountcode = accountCode,
                    )
                    countLock = countLock.fetchone()
                    adverseflag = 0
                    monthClBal = calculateBalance(
                        con,
                        accountCode,
                        str(financialStart),
                        str(financialStart),
                        str(endMonthDate),
                    )
                    if monthClBal["baltype"] == "Dr":
                        if (
                            monthClBal["grpname"] == "Corpus"
                            or monthClBal["grpname"] == "Capital"
                            or monthClBal["grpname"] == "Current Liabilities"
                            or monthClBal["grpname"] == "Loans(Liability)"
                            or monthClBal["grpname"] == "Reserves"
                            or monthClBal["grpname"] == "Indirect Income"
                            or monthClBal["grpname"] == "Direct Income"
                        ) and monthClBal["curbal"] != 0:
                            adverseflag = 1
                        clBal = {
                            "month": calendar.month_name[startMonthDate.month],
                            "Dr": "%.2f" % float(monthClBal["curbal"]),
                            "Cr": "",
                            "period": str(startMonthDate) + ":" + str(endMonthDate),
                            "vcount": count["vcount"],
                            "vcountDr": countDr["vcount"],
                            "vcountCr": countCr["vcount"],
                            "vcountLock": countLock["vcount"],
                            "advflag": adverseflag,
                        }
                        monthlyBal.append(clBal)
                    if monthClBal["baltype"] == "Cr":
                        if (
                            monthClBal["grpname"] == "Current Assets"
                            or monthClBal["grpname"] == "Fixed Assets"
                            or monthClBal["grpname"] == "Investments"
                            or monthClBal["grpname"] == "Loans(Asset)"
                            or monthClBal["grpname"] == "Miscellaneous Expenses(Asset)"
                            or monthClBal["grpname"] == "Indirect Expense"
                            or monthClBal["grpname"] == "Direct Expense"
                        ) and monthClBal["curbal"] != 0:
                            adverseflag = 1
                        clBal = {
                            "month": calendar.month_name[startMonthDate.month],
                            "Dr": "",
                            "Cr": "%.2f" % float(monthClBal["curbal"]),
                            "period": str(startMonthDate) + ":" + str(endMonthDate),
                            "vcount": count["vcount"],
                            "vcountDr": countDr["vcount"],
                            "vcountCr": countCr["vcount"],
                            "vcountLock": countLock["vcount"],
                            "advflag": adverseflag,
                        }
                        monthlyBal.append(clBal)
                    if monthClBal["baltype"] == "":
                        if (
                            monthClBal["grpname"] == "Corpus"
                            or monthClBal["grpname"] == "Capital"
                            or monthClBal["grpname"] == "Current Liabilities"
                            or monthClBal["grpname"] == "Loans(Liability)"
                            or monthClBal["grpname"] == "Reserves"
                            or monthClBal["grpname"] == "Indirect Income"
                            or monthClBal["grpname"] == "Direct Income"
                        ) and count["vcount"] != 0:
                            clBal = {
                                "month": calendar.month_name[startMonthDate.month],
                                "Dr": "",
                                "Cr": "%.2f" % float(monthClBal["curbal"]),
                                "period": str(startMonthDate) + ":" + str(endMonthDate),
                                "vcount": count["vcount"],
                                "vcountDr": countDr["vcount"],
                                "vcountCr": countCr["vcount"],
                                "vcountLock": countLock["vcount"],
                                "advflag": adverseflag,
                            }
                        if (
                            monthClBal["grpname"] == "Current Assets"
                            or monthClBal["grpname"] == "Fixed Assets"
                            or monthClBal["grpname"] == "Investments"
                            or monthClBal["grpname"] == "Loans(Asset)"
                            or monthClBal["grpname"] == "Miscellaneous Expenses(Asset)"
                            or monthClBal["grpname"] == "Indirect Expense"
                            or monthClBal["grpname"] == "Direct Expense"
                        ) and count["vcount"] != 0:
                            clBal = {
                                "month": calendar.month_name[startMonthDate.month],
                                "Dr": "%.2f" % float(monthClBal["curbal"]),
                                "Cr": "",
                                "period": str(startMonthDate) + ":" + str(endMonthDate),
                                "vcount": count["vcount"],
                                "vcountDr": countDr["vcount"],
                                "vcountCr": countCr["vcount"],
                                "vcountLock": countLock["vcount"],
                                "advflag": adverseflag,
                            }
                        if count["vcount"] == 0:
                            clBal = {
                                "month": calendar.month_name[startMonthDate.month],
                                "Dr": "",
                                "Cr": "",
                                "period": str(startMonthDate) + ":" + str(endMonthDate),
                                "vcount": count["vcount"],
                                "vcountDr": countDr["vcount"],
                                "vcountCr": countCr["vcount"],
                                "vcountLock": countLock["vcount"],
                                "advflag": adverseflag,
                            }
                        monthlyBal.append(clBal)
                    startMonthDate = date(
                        financialStart.year, financialStart.month, financialStart.day
                    ) + monthdelta(monthCounter)
                    endMonthDate = date(
                        startMonthDate.year,
                        startMonthDate.month,
                        calendar.monthrange(startMonthDate.year, startMonthDate.month)[
                            1
                        ],
                    )
                    monthCounter += 1
                return {
                    "gkstatus": enumdict["Success"],
                    "gkresult": monthlyBal,
                    "accountcode": accountCode,
                    "accountname": accname,
                }


    @view_config(route_name="ledger", renderer="json")
    def ledger(self):
        """
        Purpose:
        Creates a grid containing complete ledger.
        Takes calculatefrom,calculateto and accountcode.
        Returns success as status and the grid containing ledger.
        description:
        this function returns a grid containing ledger.
        The first row contains opening balance of the account.
        subsequent rows contain all the transactions for an account given it's account code.
        Further, it gives the closing balance at the end of all cr and dr transactions.
        in addition it also provides a flag to indicate if the balance is adverce.
        In addition to all this, there are 2 other columns containing running total Dr and Cr,
        this is used in Printing.
        If the closing balance is Dr then the amount will be shown at the cr side and other way round.
        Then finally grand total is displayed.
        This method is called when the report url is called with type=ledger request_param.
        The columns  in the grid include:
        *Date,Particular,voucher Number, Dr,Cr and balance at end of transaction.
        orderflag is checked in request params for sorting date in descending order.
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
                ur = getUserRole(authDetails["userid"], authDetails["orgcode"])
                urole = ur["gkresult"]
                orgcode = authDetails["orgcode"]
                accountCode = self.request.params["accountcode"]
                calculateFrom = self.request.params["calculatefrom"]
                calculateTo = self.request.params["calculateto"]
                projectCode = self.request.params["projectcode"]
                financialStart = self.request.params["financialstart"]
                calbalDict = calculateBalance(
                    con, accountCode, financialStart, calculateFrom, calculateTo
                )
                vouchergrid = []
                bal = 0.00
                adverseflag = 0
                accnamerow = con.execute(
                    select([accounts.c.accountname]).where(
                        accounts.c.accountcode == int(accountCode)
                    )
                )
                accname = accnamerow.fetchone()
                headerrow = {
                    "accountname": "".join(accname),
                    "projectname": "",
                    "calculateto": datetime.strftime(
                        datetime.strptime(str(calculateTo), "%Y-%m-%d").date(),
                        "%d-%m-%Y",
                    ),
                    "calculatefrom": datetime.strftime(
                        datetime.strptime(str(calculateFrom), "%Y-%m-%d").date(),
                        "%d-%m-%Y",
                    ),
                }
                if projectCode != "":
                    prjnamerow = con.execute(
                        select([projects.c.projectname]).where(
                            projects.c.projectcode == int(projectCode)
                        )
                    )
                    prjname = prjnamerow.fetchone()
                    headerrow["projectname"] = "".join(prjname)

                if projectCode == "" and calbalDict["balbrought"] > 0:
                    openingrow = {
                        "vouchercode": "",
                        "vouchernumber": "",
                        "voucherdate": datetime.strftime(
                            datetime.strptime(str(calculateFrom), "%Y-%m-%d").date(),
                            "%d-%m-%Y",
                        ),
                        "balance": "",
                        "narration": "",
                        "status": "",
                        "vouchertype": "",
                        "advflag": "",
                    }
                    vfrom = datetime.strptime(str(calculateFrom), "%Y-%m-%d")
                    fstart = datetime.strptime(str(financialStart), "%Y-%m-%d")
                    if vfrom == fstart:
                        openingrow["particulars"] = [{"accountname": "Opening Balance"}]
                    if vfrom > fstart:
                        openingrow["particulars"] = [{"accountname": "Balance B/F"}]
                    if calbalDict["openbaltype"] == "Dr":
                        openingrow["Dr"] = "%.2f" % float(calbalDict["balbrought"])
                        openingrow["Cr"] = ""
                        bal = float(calbalDict["balbrought"])
                    if calbalDict["openbaltype"] == "Cr":
                        openingrow["Dr"] = ""
                        openingrow["Cr"] = "%.2f" % float(calbalDict["balbrought"])
                        bal = float(-calbalDict["balbrought"])
                    vouchergrid.append(openingrow)
                transactionsRecords = ""
                if projectCode == "":
                    if "orderflag" in self.request.params:
                        transactionsRecords = con.execute(
                            text("select * from vouchers where voucherdate >= :from_date  and voucherdate <= :to_date and (drs ? :accountcode or crs ? :accountcode) order by voucherdate DESC,vouchercode ;"),
                            from_date = calculateFrom,
                            to_date = calculateTo,
                            accountcode = accountCode,
                        )
                    else:
                        transactionsRecords = con.execute(
                            text("select * from vouchers where voucherdate >= :from_date  and voucherdate <= :to_date and (drs ? :accountcode or crs ? :accountcode) order by voucherdate,vouchercode ;"),
                            from_date = calculateFrom,
                            to_date = calculateTo,
                            accountcode = accountCode,
                        )
                else:
                    if "orderflag" in self.request.params:
                        transactionsRecords = con.execute(
                            text("select vouchercode,vouchernumber,voucherdate,narration,drs,crs,prjcrs,prjdrs,vouchertype,lockflag,delflag,projectcode,orgcode,invid,drcrid  from vouchers where voucherdate >= :from_date  and voucherdate <= :to_date and projectcode=:projectcode and (drs ? :accountcode or crs ? :accountcode) order by voucherdate DESC, vouchercode;"),
                            from_date = calculateFrom,
                            to_date = calculateTo,
                            accountcode = accountCode,
                            projectcode = projectCode,
                        )
                    else:
                        transactionsRecords = con.execute(
                            text("select vouchercode,vouchernumber,voucherdate,narration,drs,crs,prjcrs,prjdrs,vouchertype,lockflag,delflag,projectcode,orgcode,invid,drcrid  from vouchers where voucherdate >= :from_date  and voucherdate <= :to_date and projectcode=:projectcode and (drs ? :accountcode or crs ? :accountcode) order by voucherdate, vouchercode;"),
                            from_date = calculateFrom,
                            to_date = calculateTo,
                            accountcode = accountCode,
                            projectcode = projectCode,
                        )

                transactions = transactionsRecords.fetchall()

                crtotal = 0.00
                drtotal = 0.00
                for transaction in transactions:
                    ledgerRecord = {
                        "vouchercode": transaction["vouchercode"],
                        "vouchernumber": transaction["vouchernumber"],
                        "voucherdate": str(
                            transaction["voucherdate"].date().strftime("%d-%m-%Y")
                        ),
                        "narration": transaction["narration"],
                        "status": transaction["lockflag"],
                        "vouchertype": transaction["vouchertype"],
                        "advflag": "",
                        "Cr": "",
                        "Dr": "",
                    }
                    if accountCode in transaction["drs"]:
                        ledgerRecord["Dr"] = "%.2f" % float(
                            transaction["drs"][accountCode]
                        )
                        drtotal += float(transaction["drs"][accountCode])
                        par = []
                        for cr in list(transaction["crs"].keys()):
                            accountnameRow = con.execute(
                                select([accounts.c.accountname]).where(
                                    accounts.c.accountcode == int(cr)
                                )
                            )
                            accountname = accountnameRow.fetchone()
                            if len(transaction["crs"]) > 1:
                                par.append(
                                    {
                                        "accountname": accountname["accountname"],
                                        "amount": transaction["crs"][cr],
                                    }
                                )
                            else:
                                par.append({"accountname": accountname["accountname"]})
                        ledgerRecord["particulars"] = par
                        bal = bal + float(transaction["drs"][accountCode])

                    if accountCode in transaction["crs"]:
                        ledgerRecord["Cr"] = "%.2f" % float(
                            transaction["crs"][accountCode]
                        )
                        crtotal += float(transaction["crs"][accountCode])
                        par = []
                        for dr in list(transaction["drs"].keys()):
                            accountnameRow = con.execute(
                                select([accounts.c.accountname]).where(
                                    accounts.c.accountcode == int(dr)
                                )
                            )
                            accountname = accountnameRow.fetchone()
                            if len(transaction["drs"]) > 1:
                                par.append(
                                    {
                                        "accountname": accountname["accountname"],
                                        "amount": transaction["drs"][dr],
                                    }
                                )
                            else:
                                par.append({"accountname": accountname["accountname"]})
                        ledgerRecord["particulars"] = par
                        bal = bal - float(transaction["crs"][accountCode])
                    if bal > 0:
                        ledgerRecord["balance"] = "%.2f(Dr)" % (bal)
                    elif bal < 0:
                        ledgerRecord["balance"] = "%.2f(Cr)" % (abs(bal))
                    else:
                        ledgerRecord["balance"] = "%.2f" % (0.00)
                    ledgerRecord["ttlRunDr"] = "%.2f" % (drtotal)
                    ledgerRecord["ttlRunCr"] = "%.2f" % (crtotal)
                    # get related document details
                    dcinfo = billwiseEntryLedger(
                        con,
                        orgcode,
                        transaction["vouchercode"],
                        transaction["invid"],
                        transaction["drcrid"],
                    )
                    if dcinfo != "":
                        ledgerRecord["dcinfo"] = dcinfo
                    vouchergrid.append(ledgerRecord)

                if projectCode == "":
                    if calbalDict["openbaltype"] == "Cr":
                        calbalDict["totalcrbal"] -= calbalDict["balbrought"]
                    if calbalDict["openbaltype"] == "Dr":
                        calbalDict["totaldrbal"] -= calbalDict["balbrought"]
                    ledgerRecord = {
                        "vouchercode": "",
                        "vouchernumber": "",
                        "voucherdate": "",
                        "narration": "",
                        "Dr": "%.2f" % (calbalDict["totaldrbal"]),
                        "Cr": "%.2f" % (calbalDict["totalcrbal"]),
                        "particulars": [{"accountname": "Total of Transactions"}],
                        "balance": "",
                        "status": "",
                        "vouchertype": "",
                        "advflag": "",
                    }
                    vouchergrid.append(ledgerRecord)

                    if calbalDict["curbal"] != 0:
                        ledgerRecord = {
                            "vouchercode": "",
                            "vouchernumber": "",
                            "voucherdate": datetime.strftime(
                                datetime.strptime(str(calculateTo), "%Y-%m-%d").date(),
                                "%d-%m-%Y",
                            ),
                            "narration": "",
                            "particulars": [{"accountname": "Closing Balance C/F"}],
                            "balance": "",
                            "status": "",
                            "vouchertype": "",
                        }
                        if calbalDict["baltype"] == "Cr":
                            if (
                                calbalDict["grpname"] == "Current Assets"
                                or calbalDict["grpname"] == "Fixed Assets"
                                or calbalDict["grpname"] == "Investments"
                                or calbalDict["grpname"] == "Loans(Asset)"
                                or calbalDict["grpname"]
                                == "Miscellaneous Expenses(Asset)"
                            ) and calbalDict["curbal"] != 0:
                                adverseflag = 1
                            ledgerRecord["Dr"] = "%.2f" % (calbalDict["curbal"])
                            ledgerRecord["Cr"] = ""

                        if calbalDict["baltype"] == "Dr":
                            if (
                                calbalDict["grpname"] == "Corpus"
                                or calbalDict["grpname"] == "Capital"
                                or calbalDict["grpname"] == "Current Liabilities"
                                or calbalDict["grpname"] == "Loans(Liability)"
                                or calbalDict["grpname"] == "Reserves"
                            ) and calbalDict["curbal"] != 0:
                                adverseflag = 1
                            ledgerRecord["Cr"] = "%.2f" % (calbalDict["curbal"])
                            ledgerRecord["Dr"] = ""
                        ledgerRecord["advflag"] = adverseflag
                        vouchergrid.append(ledgerRecord)

                    if (
                        (calbalDict["curbal"] == 0 and calbalDict["balbrought"] != 0)
                        or calbalDict["curbal"] != 0
                        or calbalDict["balbrought"] != 0
                    ):
                        ledgerRecord = {
                            "vouchercode": "",
                            "vouchernumber": "",
                            "voucherdate": "",
                            "narration": "",
                            "particulars": [{"accountname": "Grand Total"}],
                            "balance": "",
                            "status": "",
                            "vouchertype": "",
                            "advflag": "",
                        }
                        if projectCode == "" and calbalDict["balbrought"] > 0:
                            if calbalDict["openbaltype"] == "Dr":
                                calbalDict["totaldrbal"] += float(
                                    calbalDict["balbrought"]
                                )

                            if calbalDict["openbaltype"] == "Cr":
                                calbalDict["totalcrbal"] += float(
                                    calbalDict["balbrought"]
                                )
                            if calbalDict["baltype"] == "Cr":
                                calbalDict["totaldrbal"] += float(calbalDict["curbal"])

                            if calbalDict["baltype"] == "Dr":
                                calbalDict["totalcrbal"] += float(calbalDict["curbal"])
                            ledgerRecord["Dr"] = "%.2f" % (calbalDict["totaldrbal"])
                            ledgerRecord["Cr"] = "%.2f" % (calbalDict["totaldrbal"])
                            vouchergrid.append(ledgerRecord)
                        else:
                            if calbalDict["totaldrbal"] > calbalDict["totalcrbal"]:
                                ledgerRecord["Dr"] = "%.2f" % (calbalDict["totaldrbal"])
                                ledgerRecord["Cr"] = "%.2f" % (calbalDict["totaldrbal"])

                            if calbalDict["totaldrbal"] < calbalDict["totalcrbal"]:
                                ledgerRecord["Dr"] = "%.2f" % (calbalDict["totalcrbal"])
                                ledgerRecord["Cr"] = "%.2f" % (calbalDict["totalcrbal"])
                            vouchergrid.append(ledgerRecord)
                else:
                    ledgerRecord = {
                        "vouchercode": "",
                        "vouchernumber": "",
                        "voucherdate": "",
                        "narration": "",
                        "Dr": "%.2f" % (drtotal),
                        "Cr": "%.2f" % (crtotal),
                        "particulars": [{"accountname": "Total of Transactions"}],
                        "balance": "",
                        "status": "",
                        "vouchertype": "",
                        "advflag": "",
                    }

                    vouchergrid.append(ledgerRecord)
                return {
                    "gkstatus": enumdict["Success"],
                    "gkresult": vouchergrid,
                    "userrole": urole["userrole"],
                    "ledgerheader": headerrow,
                }


    @view_config(route_name="ledger-crdr", renderer="json")
    def crdrledger(self):
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
                orgcode = authDetails["orgcode"]
                accountCode = self.request.params["accountcode"]
                side = self.request.params["side"]
                calculateFrom = self.request.params["calculatefrom"]
                calculateTo = self.request.params["calculateto"]
                projectCode = self.request.params["projectcode"]
                financialStart = self.request.params["financialstart"]
                vouchergrid = []
                bal = 0.00
                accnamerow = con.execute(
                    select([accounts.c.accountname]).where(
                        accounts.c.accountcode == int(accountCode)
                    )
                )
                accname = accnamerow.fetchone()
                headerrow = {
                    "accountname": accname["accountname"],
                    "projectname": "",
                    "calculateto": datetime.strftime(
                        datetime.strptime(str(calculateTo), "%Y-%m-%d").date(),
                        "%d-%m-%Y",
                    ),
                    "calculatefrom": datetime.strftime(
                        datetime.strptime(str(calculateFrom), "%Y-%m-%d").date(),
                        "%d-%m-%Y",
                    ),
                }
                if projectCode != "":
                    prjnamerow = con.execute(
                        select([projects.c.projectname]).where(
                            projects.c.projectcode == int(projectCode)
                        )
                    )
                    prjname = prjnamerow.fetchone()
                    headerrow["projectname"] = prjname["projectname"]
                if side == "dr":
                    if projectCode == "":
                        if "orderflag" in self.request.params:
                            transactionsRecords = con.execute(
                                text("select vouchercode,vouchernumber,voucherdate,narration,drs,crs,prjcrs,prjdrs,vouchertype,lockflag,delflag,projectcode,orgcode,invid,drcrid from vouchers where voucherdate >= :from_date  and voucherdate <= :to_date and (drs ? :accountcode) order by voucherdate DESC;"),
                                from_date = calculateFrom,
                                to_date = calculateTo,
                                accountcode = accountCode,
                            )
                        else:
                            transactionsRecords = con.execute(
                                text("select vouchercode,vouchernumber,voucherdate,narration,drs,crs,prjcrs,prjdrs,vouchertype,lockflag,delflag,projectcode,orgcode,invid,drcrid from vouchers where voucherdate >= :from_date  and voucherdate <= :to_date and (drs ? :accountcode) order by voucherdate;"),
                                from_date = calculateFrom,
                                to_date = calculateTo,
                                accountcode = accountCode,
                            )
                    else:
                        if "orderflag" in self.request.params:
                            transactionsRecords = con.execute(
                                text("select vouchercode,vouchernumber,voucherdate,narration,drs,crs,prjcrs,prjdrs,vouchertype,lockflag,delflag,projectcode,orgcode,invid,drcrid from vouchers where voucherdate >= :from_date  and voucherdate <= :to_date  and projectcode = :projectcode and (drs ? :accountcode) order by voucherdate DESC;"),
                                from_date = calculateFrom,
                                to_date = calculateTo,
                                accountcode = accountCode,
                                productcode = projectCode,
                            )
                        else:
                            transactionsRecords = con.execute(
                                text("select vouchercode,vouchernumber,voucherdate,narration,drs,crs,prjcrs,prjdrs,vouchertype,lockflag,delflag,projectcode,orgcode,invid,drcrid from vouchers where voucherdate >= :from_date  and voucherdate <= :to_date  and projectcode = :projectcode and (drs ? :accountcode) order by voucherdate;"),
                                from_date = calculateFrom,
                                to_date = calculateTo,
                                accountcode = accountCode,
                                productcode = projectCode,
                            )

                    transactions = transactionsRecords.fetchall()
                    for transaction in transactions:
                        ledgerRecord = {
                            "vouchercode": transaction["vouchercode"],
                            "vouchernumber": transaction["vouchernumber"],
                            "voucherdate": str(
                                transaction["voucherdate"].date().strftime("%d-%m-%Y")
                            ),
                            "narration": transaction["narration"],
                            "status": transaction["lockflag"],
                            "vouchertype": transaction["vouchertype"],
                        }
                        ledgerRecord["Dr"] = "%.2f" % float(
                            transaction["drs"][accountCode]
                        )
                        ledgerRecord["Cr"] = ""
                        par = []
                        for cr in list(transaction["crs"].keys()):
                            accountnameRow = con.execute(
                                select([accounts.c.accountname]).where(
                                    accounts.c.accountcode == int(cr)
                                )
                            )
                            accountname = accountnameRow.fetchone()
                            if len(transaction["crs"]) > 1:
                                par.append(
                                    {
                                        "accountname": accountname["accountname"],
                                        "amount": transaction["crs"][cr],
                                    }
                                )
                            else:
                                par.append({"accountname": accountname["accountname"]})
                        ledgerRecord["particulars"] = par
                        # get deatils of related documents
                        dcinfo = billwiseEntryLedger(
                            con,
                            orgcode,
                            transaction["vouchercode"],
                            transaction["invid"],
                            transaction["drcrid"],
                        )
                        if dcinfo != "":
                            ledgerRecord["dcinfo"] = dcinfo

                        vouchergrid.append(ledgerRecord)
                    con.close()
                    return {
                        "gkstatus": enumdict["Success"],
                        "gkresult": vouchergrid,
                        "userrole": urole["userrole"],
                        "ledgerheader": headerrow,
                    }

                if side == "cr":
                    if projectCode == "":
                        if "orderflag" in self.request.params:
                            transactionsRecords = con.execute(
                                text("select vouchercode,vouchernumber,voucherdate,narration,drs,crs,prjcrs,prjdrs,vouchertype,lockflag,delflag,projectcode,orgcode,invid,drcrid from vouchers where voucherdate >= :from_date  and voucherdate <= :to_date and (crs ? :accountcode) order by voucherdate DESC;"),
                                from_date = calculateFrom,
                                to_date = calculateTo,
                                accountcode = accountCode,
                            )
                        else:
                            transactionsRecords = con.execute(
                                text("select vouchercode,vouchernumber,voucherdate,narration,drs,crs,prjcrs,prjdrs,vouchertype,lockflag,delflag,projectcode,orgcode,invid,drcrid from vouchers where voucherdate >= :from_date  and voucherdate <= :to_date and (crs ? :accountcode) order by voucherdate;"),
                                from_date = calculateFrom,
                                to_date = calculateTo,
                                accountcode = accountCode,
                            )
                    else:
                        if "orderflag" in self.request.params:
                            transactionsRecords = con.execute(
                                text("select vouchercode,vouchernumber,voucherdate,narration,drs,crs,prjcrs,prjdrs,vouchertype,lockflag,delflag,projectcode,orgcode,invid,drcrid from vouchers where voucherdate >= :from_date  and voucherdate <= :to_date  and projectcode = :projectcode and (crs ? :accountcode) order by voucherdate DESC;"),
                                from_date = calculateFrom,
                                to_date = calculateTo,
                                accountcode = accountCode,
                                productcode = projectCode,
                            )
                        else:
                            transactionsRecords = con.execute(
                                text("select vouchercode,vouchernumber,voucherdate,narration,drs,crs,prjcrs,prjdrs,vouchertype,lockflag,delflag,projectcode,orgcode,invid,drcrid from vouchers where voucherdate >= :from_date  and voucherdate <= :to_date  and projectcode = :projectcode and (crs ? :accountcode) order by voucherdate;"),
                                from_date = calculateFrom,
                                to_date = calculateTo,
                                accountcode = accountCode,
                                productcode = projectCode,
                            )

                    transactions = transactionsRecords.fetchall()
                    for transaction in transactions:
                        ledgerRecord = {
                            "vouchercode": transaction["vouchercode"],
                            "vouchernumber": transaction["vouchernumber"],
                            "voucherdate": str(
                                transaction["voucherdate"].date().strftime("%d-%m-%Y")
                            ),
                            "narration": transaction["narration"],
                            "status": transaction["lockflag"],
                            "vouchertype": transaction["vouchertype"],
                        }
                        ledgerRecord["Cr"] = "%.2f" % float(
                            transaction["crs"][accountCode]
                        )
                        ledgerRecord["Dr"] = ""
                        par = []
                        for dr in list(transaction["drs"].keys()):
                            accountnameRow = con.execute(
                                select([accounts.c.accountname]).where(
                                    accounts.c.accountcode == int(dr)
                                )
                            )
                            accountname = accountnameRow.fetchone()
                            if len(transaction["drs"]) > 1:
                                par.append(
                                    {
                                        "accountname": accountname["accountname"],
                                        "amount": transaction["drs"][dr],
                                    }
                                )
                            else:
                                par.append({"accountname": accountname["accountname"]})
                        ledgerRecord["particulars"] = par
                        # get documents details
                        dcinfo = billwiseEntryLedger(
                            con,
                            orgcode,
                            transaction["vouchercode"],
                            transaction["invid"],
                            transaction["drcrid"],
                        )
                        if dcinfo != "":
                            ledgerRecord["dcinfo"] = dcinfo

                        vouchergrid.append(ledgerRecord)
                    return {
                        "gkstatus": enumdict["Success"],
                        "gkresult": vouchergrid,
                        "userrole": urole["userrole"],
                        "ledgerheader": headerrow,
                    }
