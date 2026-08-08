"""
Copyright (C) 2013, 2014, 2015, 2016 Digital Freedom Foundation
Copyright (C) 2017, 2018, 2019, 2020, 2019 Digital Freedom Foundation & Accion Labs Pvt. Ltd.
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
   "Karan Kamdar" <kamdar.karan@gmail.com>
   "Prajkta Patkar" <prajkta@riseup.com>
   "Abhijith Balan" <abhijith@dff.org.in>
   "rohan khairnar" <rohankhairnar@gmail.com>
  
  This API is written for budgeting module. With this API budget add,edit,delete,list of budget and budget report calculation can be done.
  This api is related to "BUDGET TABLE".   
  """

from gkcore import eng, enumdict
from gkcore.models.gkdb import invoice, budget, accounts, groupsubgroups, users
from sqlalchemy.sql import select, func
import json
from sqlalchemy.engine.base import Connection
from sqlalchemy import and_, exc, desc
from pyramid.request import Request
from pyramid.response import Response
from pyramid.view import view_defaults, view_config
from datetime import datetime, date, timedelta
import jwt
import gkcore
from gkcore.utils import authCheck, getUserRole
from gkcore.models import gkdb
from gkcore.views.reports.helpers.balance import calculateBalance


@view_defaults(route_name="budget")
class api_budget(object):
    def __init__(self, request):
        self.request = Request
        self.request = request
        self.con = Connection

    @view_config(request_method="POST", renderer="json")
    def addBudget(self):
        try:
            token = self.request.headers["gktoken"]
        except:
            return {"gkstatus": gkcore.enumdict["UnauthorisedAccess"]}
        authDetails = authCheck(token)
        if authDetails["auth"] == False:
            return {"gkstatus": enumdict["UnauthorisedAccess"]}
        else:
            try:
                self.con = eng.connect()
                userRoleData = getUserRole(
                    authDetails["userid"], authDetails["orgcode"]
                )
                userrole = userRoleData["gkresult"]["userrole"]
                if userrole == -1 or userrole == 0:
                    budgetdataset = self.request.json_body
                    budgetdataset["orgcode"] = authDetails["orgcode"]
                    # Check for duplicate entry before insertion
                    result_duplicate_check = self.con.execute(
                        select([budget.c.budname])
                        .where(
                            and_(
                                budget.c.orgcode == authDetails["orgcode"],
                                func.lower(budget.c.budname) == func.lower(budgetdataset["budname"]),
                            )
                        )
                    )
                    
                    if result_duplicate_check.rowcount > 0:
                        # Duplicate entry found, handle accordingly
                        return {"gkstatus": enumdict["DuplicateEntry"]}
            
                    result = self.con.execute(budget.insert(), [budgetdataset])
                    return {"gkstatus": enumdict["Success"]}
                else:
                    return {"gkstatus": gkcore.enumdict["ActionDisallowed"]}
            except exc.IntegrityError:
                return {"gkstatus": enumdict["DuplicateEntry"]}
            except:
                return {"gkstatus": gkcore.enumdict["ConnectionFailed"]}
            finally:
                self.con.close()

    @view_config(request_method="GET", request_param="bud=all", renderer="json")
    def getlistofbudgets(self):
        """To get all budgets list"""
        try:
            token = self.request.headers["gktoken"]
        except:
            return {"gkstatus": gkcore.enumdict["UnauthorisedAccess"]}
        authDetails = authCheck(token)
        if authDetails["auth"] == False:
            return {"gkstatus": enumdict["UnauthorisedAccess"]}
        else:
            try:
                self.con = eng.connect()
                btype = self.request.params["btype"]
                result = self.con.execute(
                    select(
                        [
                            budget.c.budid,
                            budget.c.budname,
                            budget.c.budtype,
                            budget.c.contents,
                            budget.c.startdate,
                            budget.c.enddate,
                        ]
                    ).where(
                        and_(
                            budget.c.budtype == btype,
                            budget.c.orgcode == authDetails["orgcode"],
                        )
                    )
                )
                list = result.fetchall()
                budlist = []
                for l in list:
                    budlist.append(
                        {
                            "budid": l["budid"],
                            "budname": l["budname"],
                            "startdate": datetime.strftime(l["startdate"], "%d-%m-%Y"),
                            "enddate": datetime.strftime(l["enddate"], "%d-%m-%Y"),
                            "btype": l["budtype"],
                        }
                    )

                return {"gkstatus": gkcore.enumdict["Success"], "gkresult": budlist}
            except:
                return {"gkstatus": gkcore.enumdict["ConnectionFailed"]}
            finally:
                self.con.close()

    @view_config(request_method="GET", request_param="bud=details", renderer="json")
    def getbudgetdetails(self):
        """To get single budget details as per budget id 'budid'"""
        try:
            token = self.request.headers["gktoken"]
        except:
            return {"gkstatus": gkcore.enumdict["UnauthorisedAccess"]}
        authDetails = authCheck(token)
        if authDetails["auth"] == False:
            return {"gkstatus": enumdict["UnauthorisedAccess"]}
        else:
            try:
                self.con = eng.connect()
                result = self.con.execute(
                    select(
                        [
                            budget.c.budid,
                            budget.c.budname,
                            budget.c.budtype,
                            budget.c.contents,
                            budget.c.startdate,
                            budget.c.enddate,
                            budget.c.gaflag,
                        ]
                    ).where(
                        and_(
                            budget.c.orgcode == authDetails["orgcode"],
                            budget.c.budid == self.request.params["budid"],
                        )
                    )
                )
                budgetdata = result.fetchone()
                budlist = {
                    "budid": budgetdata["budid"],
                    "budname": budgetdata["budname"],
                    "startdate": datetime.strftime(budgetdata["startdate"], "%d-%m-%Y"),
                    "enddate": datetime.strftime(budgetdata["enddate"], "%d-%m-%Y"),
                    "btype": budgetdata["budtype"],
                    "contents": budgetdata["contents"],
                    "gaflag": budgetdata["gaflag"],
                }

                return {"gkstatus": gkcore.enumdict["Success"], "gkresult": budlist}
            except:
                return {"gkstatus": gkcore.enumdict["ConnectionFailed"]}
            finally:
                self.con.close()

    @view_config(request_method="GET", request_param="type=addtab", renderer="json")
    def getbalatbeginning(self):
        """For clossing balances of all acounts.It  will fetch all acounts balance from financial startdate to the previous date of budget startdate with their accountcode.
        It will take financial start and budget start date as input.
        Budget type = 3: (Cash Budget)
        It will fetch all accounts except accounts under Bank and Cash subgroups.
        Accounts under Direct,Indirect Expense and Current Liabilities are consider in Outflow
        Accounts under Direct,Indirect Income and Current Assets are consider in Inflow.
        Budget type = 16:(profit and loss Budget)
        It will fetch all accounts under Direct and Indirect Expense and Income groups and their subgroups.
        """
        try:
            token = self.request.headers["gktoken"]
        except:
            return {"gkstatus": gkcore.enumdict["UnauthorisedAccess"]}
        authDetails = authCheck(token)
        if authDetails["auth"] == False:
            return {"gkstatus": enumdict["UnauthorisedAccess"]}
        else:
            try:
                self.con = eng.connect()
                uptodate = self.request.params["uptodate"]
                financialStart = self.request.params["financialstart"]
                btype = self.request.params["btype"]
                # budget type 3: cash budget
                if btype == "3":
                    result = self.con.execute(
                        "select accountcode, openingbal, accountname from accounts where orgcode = %d order by accountname"
                        % (authDetails["orgcode"])
                    )
                    accounts = result.fetchall()

                    if uptodate != financialStart:
                        calculateToDate = datetime.strptime(uptodate, "%Y-%m-%d")
                        prevday = calculateToDate - timedelta(days=1)
                        prevday = str(prevday)[0:10]
                        inAccountdata = []
                        outAccountdata = []
                        openingBal = 0.00

                        for bal in accounts:
                            groupData = self.con.execute(
                                "select groupname from groupsubgroups where subgroupof is null and groupcode = (select groupcode from accounts where accountcode = %d) or groupcode = (select subgroupof from groupsubgroups where groupcode = (select groupcode from accounts where accountcode = %d))"
                                % (int(bal["accountcode"]), int(bal["accountcode"]))
                            )
                            groupRecord = groupData.fetchone()

                            # Outflow accounts
                            if (
                                groupRecord[0] == "Direct Expense"
                                or groupRecord[0] == "Indirect Expense"
                                or groupRecord[0] == "Current Liabilities"
                            ):
                                outAccountdata.append(
                                    {
                                        "accountname": bal["accountname"],
                                        "accountcode": bal["accountcode"],
                                    }
                                )

                            # Inflow accounts
                            if (
                                groupRecord[0] == "Direct Income"
                                or groupRecord[0] == "Indirect Income"
                                or groupRecord[0] == "Current Assets"
                            ):
                                subgroupname = self.con.execute(
                                    "select groupname from groupsubgroups where groupcode = (select groupcode from accounts where accountcode = %d)"
                                    % int(bal["accountcode"])
                                )
                                subgroup = subgroupname.fetchone()
                                # bank and cash accounts balance as opening balance of budget
                                if subgroup[0] == "Bank" or subgroup[0] == "Cash":
                                    calbaldata = calculateBalance(
                                        self.con,
                                        bal["accountcode"],
                                        str(financialStart),
                                        str(financialStart),
                                        prevday,
                                    )

                                    if calbaldata["baltype"] == "Cr":
                                        openingBal = float(openingBal) - float(
                                            calbaldata["curbal"]
                                        )
                                    if calbaldata["baltype"] == "Dr":
                                        openingBal = float(openingBal) + float(
                                            calbaldata["curbal"]
                                        )
                                else:
                                    inAccountdata.append(
                                        {
                                            "accountname": bal["accountname"],
                                            "accountcode": bal["accountcode"],
                                        }
                                    )

                        data = {
                            "inflow": inAccountdata,
                            "outflow": outAccountdata,
                            "openingbal": "%.2f" % float(openingBal),
                        }
                        return {
                            "gkstatus": gkcore.enumdict["Success"],
                            "gkresult": data,
                        }
                    else:
                        inAccountdata = []
                        outAccountdata = []
                        openingBal = 0.00
                        for bal in accounts:
                            groupData = self.con.execute(
                                "select groupname from groupsubgroups where subgroupof is null and groupcode = (select groupcode from accounts where accountcode = %d) or groupcode = (select subgroupof from groupsubgroups where groupcode = (select groupcode from accounts where accountcode = %d));"
                                % (int(bal["accountcode"]), int(bal["accountcode"]))
                            )
                            groupRecord = groupData.fetchone()
                            # Outflow accounts
                            if (
                                groupRecord[0] == "Direct Expense"
                                or groupRecord[0] == "Indirect Expense"
                                or groupRecord[0] == "Current Liabilities"
                            ):
                                outAccountdata.append(
                                    {
                                        "accountname": bal["accountname"],
                                        "accountcode": bal["accountcode"],
                                    }
                                )
                            # Inflow accounts
                            if (
                                groupRecord[0] == "Direct Income"
                                or groupRecord[0] == "Indirect Income"
                                or groupRecord[0] == "Current Assets"
                            ):
                                subgroupname = self.con.execute(
                                    "select groupname from groupsubgroups where groupcode = (select groupcode from accounts where accountcode = %d)"
                                    % int(bal["accountcode"])
                                )
                                subgroup = subgroupname.fetchone()
                                # cash and bank accounts balance as opening balance of budget
                                if subgroup[0] == "Bank" or subgroup[0] == "Cash":
                                    openingBal = float(openingBal) + float(
                                        bal["openingbal"]
                                    )
                                else:
                                    inAccountdata.append(
                                        {
                                            "accountname": bal["accountname"],
                                            "accountcode": bal["accountcode"],
                                        }
                                    )

                        data = {
                            "inflow": inAccountdata,
                            "outflow": outAccountdata,
                            "openingbal": "%.2f" % float(openingBal),
                        }
                        return {
                            "gkstatus": gkcore.enumdict["Success"],
                            "gkresult": data,
                        }

                # budget type 16: profit and loss budget
                if btype == "16":
                    expense = []
                    income = []
                    # accounts for expense
                    result = self.con.execute(
                        "select accountcode,accountname from accounts where orgcode = %d and (groupcode in (select groupcode from groupsubgroups where orgcode= %d and (groupname = 'Indirect Expense' or groupname = 'Direct Expense' or subgroupof in (select groupcode from groupsubgroups where orgcode= %d and (groupname='Indirect Expense' or groupname = 'Direct Expense')))))order by accountname;"
                        % (
                            authDetails["orgcode"],
                            authDetails["orgcode"],
                            authDetails["orgcode"],
                        )
                    )
                    expenseAccounts = result.fetchall()
                    for account in expenseAccounts:
                        expense.append(
                            {
                                "code": account["accountcode"],
                                "name": account["accountname"],
                            }
                        )

                    # accounts for income
                    result = self.con.execute(
                        "select accountcode,accountname from accounts where orgcode = %d and (groupcode in (select groupcode from groupsubgroups where orgcode= %d and (groupname = 'Indirect Income' or groupname = 'Direct Income' or subgroupof in (select groupcode from groupsubgroups where orgcode= %d and (groupname='Indirect Income' or groupname = 'Direct Income')))))order by accountname;"
                        % (
                            authDetails["orgcode"],
                            authDetails["orgcode"],
                            authDetails["orgcode"],
                        )
                    )
                    incomeAccounts = result.fetchall()
                    for account in incomeAccounts:
                        income.append(
                            {
                                "code": account["accountcode"],
                                "name": account["accountname"],
                            }
                        )
                    total = {"expense": expense, "income": income}
                    return {"gkstatus": gkcore.enumdict["Success"], "gkresult": total}
            except:
                return {"gkstatus": gkcore.enumdict["ConnectionFailed"]}
            finally:
                self.con.close()

    @view_config(request_method="PUT", renderer="json")
    def editbudgets(self):
        try:
            token = self.request.headers["gktoken"]
        except:
            return {"gkstatus": gkcore.enumdict["UnauthorisedAccess"]}
        authDetails = authCheck(token)
        if authDetails["auth"] == False:
            return {"gkstatus": enumdict["UnauthorisedAccess"]}
        else:
            try:
                self.con = eng.connect()
                userRoleData = getUserRole(
                    authDetails["userid"], authDetails["orgcode"]
                )
                userrole = userRoleData["gkresult"]["userrole"]
                if userrole == -1 or userrole == 0:
                    dataset = self.request.json_body
                    result = self.con.execute(
                        budget.update()
                        .where(budget.c.budid == dataset["budid"])
                        .values(dataset)
                    )
                    return {"gkstatus": enumdict["Success"]}
                else:
                    return {"gkstatus": gkcore.enumdict["ActionDisallowed"]}
            except:
                return {"gkstatus": gkcore.enumdict["ConnectionFailed"]}
            finally:
                self.con.close()

    @view_config(request_method="DELETE", renderer="json")
    def deletebudget(self):
        try:
            token = self.request.headers["gktoken"]
        except:
            return {"gkstatus": gkcore.enumdict["UnauthorisedAccess"]}
        authDetails = authCheck(token)
        if authDetails["auth"] == False:
            return {"gkstatus": enumdict["UnauthorisedAccess"]}
        else:
            try:
                dataset = self.request.json_body
                self.con = eng.connect()
                userRoleData = getUserRole(
                    authDetails["userid"], authDetails["orgcode"]
                )
                userrole = userRoleData["gkresult"]["userrole"]
                if userrole == -1 or userrole == 0:
                    result = self.con.execute(
                        budget.delete().where(budget.c.budid == dataset["budid"])
                    )
                    return {"gkstatus": enumdict["Success"]}
                else:
                    return {"gkstatus": gkcore.enumdict["ActionDisallowed"]}
            except exc.IntegrityError:
                return {"gkstatus": enumdict["ActionDisallowed"]}
            except:
                return {"gkstatus": enumdict["ConnectionFailed"]}
            finally:
                self.con.close()

    @view_config(request_method="GET", request_param="type=cashReport", renderer="json")
    def cashReport(self):
        """
        Purpose:
        To calculate complete budget for given time period.
        Input from webapp: financialstartdate,budgetperiod,budgetid
        contents field is Json field which have all accountcodes which used in budget as key and their budget amount as value.

        OutFlow accounts : which are from Direct & Indirect Expense and Current Liabilities groups.
        InFlow accounts : which are from Direct & Indirect Income and Current Assets groups.

        Here we need to consider all accounts under the Bank and Cash subgroups to get transaction details from vouchers.
        For each accounts of cash and bank we are getting opening and closing balance for budget using calculateBalance function.
        Opening balance = from financial start date to previous date of budget start date.
        Closing balance = from financial start date to end date of budget.
        Again actual opening balance and budgeted opening balance will be same.But the actual closing and bugdeted closing balances will e different.
        Budgeted closing bal. = Actual opening + total inflow - total outflow

        For Inflow and Outflow if any accounts which has transaction with cash and bank accounts but not used in budget, we also consider that accounts with budget 0.

        For transaction consider payment & receipt vouchers and only that sales and purchase vouchers which having transaction with Cash and Bank accounts.

        variance part will only for inflow and outflow accounts.
        variance inflow = actual - budgeted , variance outflow = budgeted - actuals
        variance in percent = (variance * 100)/ budgeted

        """
        try:
            token = self.request.headers["gktoken"]
        except:
            return {"gkstatus": gkcore.enumdict["UnauthorisedAccess"]}
        authDetails = authCheck(token)
        if authDetails["auth"] == False:
            return {"gkstatus": enumdict["UnauthorisedAccess"]}
        else:
            try:
                self.con = eng.connect()
                financialStart = self.request.params["financialstart"]
                result = self.con.execute(
                    select(
                        [budget.c.contents, budget.c.startdate, budget.c.enddate]
                    ).where(
                        and_(
                            budget.c.orgcode == authDetails["orgcode"],
                            budget.c.budid == self.request.params["budid"],
                        )
                    )
                )
                budgetdata = result.fetchone()
                startdate = str(budgetdata["startdate"])[0:10]
                enddate = str(budgetdata["enddate"])[0:10]
                content = budgetdata["contents"]
                accountslist = list(content.keys())

                # To calaculate total Outflow and Inflow
                totalBudgetInflow = 0.00
                totalBudgetOutflow = 0.00
                for acc in content:
                    groupData = self.con.execute(
                        "select groupname from groupsubgroups where subgroupof is null and groupcode = (select groupcode from accounts where accountcode = %d) or groupcode = (select subgroupof from groupsubgroups where groupcode = (select groupcode from accounts where accountcode = %d));"
                        % (int(acc), int(acc))
                    )
                    groupRecord = groupData.fetchone()
                    if (
                        groupRecord[0] == "Direct Expense"
                        or groupRecord[0] == "Indirect Expense"
                        or groupRecord[0] == "Current Liabilities"
                    ):
                        totalBudgetOutflow = float(totalBudgetOutflow) + float(
                            content[str(acc)]
                        )
                    if (
                        groupRecord[0] == "Direct Income"
                        or groupRecord[0] == "Indirect Income"
                        or groupRecord[0] == "Current Assets"
                    ):
                        totalBudgetInflow = float(totalBudgetInflow) + float(
                            content[str(acc)]
                        )

                # getting all accounts under cash and bank subgroups.
                cbAccountsData = self.con.execute(
                    "select accountcode, openingbal, accountname from accounts where orgcode = %d and groupcode in (select groupcode from groupsubgroups where orgcode = %d and groupname in ('Bank','Cash')) order by accountname"
                    % (authDetails["orgcode"], authDetails["orgcode"])
                )
                cbAccounts = cbAccountsData.fetchall()
                cbAccountscode = []
                totalopeningbal = 0.00
                actualClosingBal = 0.00

                openingacc = []
                closing = []
                if startdate != financialStart:
                    d = startdate
                    calculateToDate = datetime.strptime(d, "%Y-%m-%d")
                    prevday = calculateToDate - timedelta(days=1)
                    prevday = str(prevday)[0:10]
                else:
                    prevday = startdate
                # for all cash and bank accounts.
                for bal in cbAccounts:
                    cbAccountscode.append(bal["accountcode"])
                    calculate = calculateBalance(
                        self.con,
                        bal["accountcode"],
                        financialStart,
                        financialStart,
                        prevday,
                    )
                    closingdata = calculateBalance(
                        self.con,
                        bal["accountcode"],
                        financialStart,
                        financialStart,
                        enddate,
                    )
                    openaccountbal = 0.00
                    # To calculate opening balance.
                    if startdate != financialStart:
                        if calculate["baltype"] == "Cr":
                            totalopeningbal = float(totalopeningbal) - float(
                                calculate["curbal"]
                            )
                            openaccountbal = -float(calculate["curbal"])
                        if calculate["baltype"] == "Dr":
                            totalopeningbal = float(totalopeningbal) + float(
                                calculate["curbal"]
                            )
                            openaccountbal = float(calculate["curbal"])
                    else:
                        # Opening balances of accounts
                        totalopeningbal = float(totalopeningbal) + float(
                            bal["openingbal"]
                        )
                        openaccountbal = float(bal["openingbal"])
                    openingacc.append(
                        {
                            "accountname": bal["accountname"],
                            "balance": "%.2f" % float(openaccountbal),
                        }
                    )

                    # Actual Closing and Budgeted Closing Balance calculation for Cash and Bank accounts.
                    closingaccountbal = 0.00
                    if closingdata["baltype"] == "Cr":
                        actualClosingBal = float(actualClosingBal) - float(
                            closingdata["curbal"]
                        )
                        closingaccountbal = -float(closingdata["curbal"])
                    if closingdata["baltype"] == "Dr":
                        actualClosingBal = float(actualClosingBal) + float(
                            closingdata["curbal"]
                        )
                        closingaccountbal = float(closingdata["curbal"])
                    # closing budgeted balance for each account
                    accbudget = (
                        float(openaccountbal)
                        + float(totalBudgetInflow)
                        - float(totalBudgetOutflow)
                    )
                    try:
                        var = "%.2f" % float(
                            float(closingaccountbal) - float(accbudget)
                        )
                        varinpercent = "%.2f" % float(
                            (float(var) * 100) / float(accbudget)
                        )
                    except:
                        var = "-"
                        varinpercent = "-"
                    closing.append(
                        {
                            "accountname": bal["accountname"],
                            "balance": "%.2f" % float(closingaccountbal),
                            "budget": "%.2f" % float(accbudget),
                            "var": var,
                            "varinpercent": varinpercent,
                        }
                    )

                    # To get all accounts which having transaction with Bank and Cash accounts.
                    # If Cash or Bank account is present in drs then get accountcode present in crs and crs accounts are consider in inflow
                    # If Cash or Bank account is present in crs then get accountcode present in drs and drs accounts are consider in outflow
                    inflowAccData = self.con.execute(
                        "select crs from vouchers where voucherdate >= '%s'  and voucherdate <= '%s' and (drs ? '%d')  order by voucherdate DESC,vouchercode ;"
                        % (startdate, enddate, bal["accountcode"])
                    )
                    outflowAccData = self.con.execute(
                        "select drs from vouchers where voucherdate >= '%s'  and voucherdate <= '%s' and (crs ? '%d')  order by voucherdate DESC,vouchercode ;"
                        % (startdate, enddate, bal["accountcode"])
                    )

                    inAcc = inflowAccData.fetchall()
                    outAcc = outflowAccData.fetchall()

                    # here we making new list (accountslist) of all accountcodes for inflow and outflow.
                    # That accounts which are used in budget and that also which having transaction cash and bank accounts but not used in budget.
                    # accountlist already having accounts used in budget.
                    if len(inAcc) > 0:
                        for vch in inAcc:
                            for inAccode in list(vch[0].keys()):
                                if inAccode not in accountslist:
                                    accountslist.append(inAccode)
                    if len(outAcc) > 0:
                        for vch in outAcc:
                            for outAccCode in list(vch[0].keys()):
                                if outAccCode not in accountslist:
                                    accountslist.append(outAccCode)

                inflowAccounts = []
                outflowAccounts = []
                totalActualOutflow = 0.00
                totalActualInflow = 0.00
                # all inflow and outflow accountcodes are in accountslist

                for acc in accountslist:
                    # To get account name and their groupname.
                    result = self.con.execute(
                        select([accounts.c.accountname]).where(
                            accounts.c.accountcode == int(acc)
                        )
                    )
                    accountname = result.fetchone()
                    # Get all vouchers of related accountcode
                    vouchers = self.con.execute(
                        "select drs,crs from vouchers where voucherdate >= '%s'  and voucherdate <= '%s' and (drs ? '%d' or crs ? '%d') order by voucherdate DESC,vouchercode ;"
                        % (startdate, enddate, int(acc), int(acc))
                    )
                    vchOfAcc = vouchers.fetchall()
                    # vouchers crs/drs field will decide account should consider in Inflow or Outflow
                    accType = ""
                    accountbal = 0.00
                    if len(vchOfAcc) > 0:
                        # loop all vouchers of account
                        for vch in vchOfAcc:
                            # For Inflow field
                            # As account is in crs then that account is income for budget
                            if acc in list(vch["crs"].keys()):
                                accType = "Inflow"
                                # check wheather bank or cash account is in drs
                                accIncbAccounts = 0
                                for drs in list(vch["drs"].keys()):
                                    if int(drs) in cbAccountscode:
                                        accIncbAccounts = 1
                                # If bank or cash account is in drs
                                if accIncbAccounts == 1:
                                    accountbal += float(vch["crs"][str(int(acc))])
                                else:
                                    accountbal += 0.00

                            else:
                                accType = "Outflow"
                                accIncbAccounts = 0
                                for crs in list(vch["crs"].keys()):
                                    if int(crs) in cbAccountscode:
                                        accIncbAccounts = 1
                                if accIncbAccounts == 1:
                                    accountbal += float(vch["drs"][str(int(acc))])
                                else:
                                    accountbal += 0.00

                    if accType == "Inflow":
                        totalActualInflow = float(totalActualInflow) + float(accountbal)
                        if acc in content:
                            var = float(accountbal) - float(content[str(acc)])
                            varInPercent = (var * 100) / content[str(acc)]
                            inflowAccounts.append(
                                {
                                    "accountname": accountname[0],
                                    "actual": "%.2f" % float(accountbal),
                                    "budget": "%.2f" % float(content[str(acc)]),
                                    "var": "%.2f" % float(var),
                                    "varinpercent": "%.2f" % float(varInPercent),
                                }
                            )
                        else:
                            var = "-"
                            varInPercent = "-"
                            inflowAccounts.append(
                                {
                                    "accountname": accountname[0],
                                    "actual": "%.2f" % float(accountbal),
                                    "budget": "%.2f" % float(0),
                                    "var": var,
                                    "varinpercent": varInPercent,
                                }
                            )
                    if accType == "Outflow":
                        totalActualOutflow = float(totalActualOutflow) + float(
                            accountbal
                        )
                        if acc in content:
                            var = float(content[str(acc)]) - float(accountbal)
                            varInPercent = (var * 100) / content[str(acc)]
                            outflowAccounts.append(
                                {
                                    "accountname": accountname[0],
                                    "actual": "%.2f" % float(accountbal),
                                    "budget": "%.2f" % float(content[str(acc)]),
                                    "var": "%.2f" % float(var),
                                    "varinpercent": "%.2f" % float(varInPercent),
                                }
                            )
                        else:
                            var = "-"
                            varInPercent = "-"
                            outflowAccounts.append(
                                {
                                    "accountname": accountname[0],
                                    "actual": "%.2f" % float(accountbal),
                                    "budget": "%.2f" % float(0),
                                    "var": var,
                                    "varinpercent": varInPercent,
                                }
                            )
                    # If no transaction done, then this account should have budget amount.
                    if accType == "":
                        # Fetch groupname of account to check wheather it comes under Inflow or Outflow
                        groupData = self.con.execute(
                            "select groupname from groupsubgroups where subgroupof is null and groupcode = (select groupcode from accounts where accountcode = %d) or groupcode = (select subgroupof from groupsubgroups where groupcode = (select groupcode from accounts where accountcode = %d));"
                            % (int(acc), int(acc))
                        )
                        groupRecord = groupData.fetchone()
                        groupName = groupRecord["groupname"]

                        if (
                            groupName == "Direct Expense"
                            or groupName == "Indirect Expense"
                            or groupName == "Current Liabilities"
                        ):
                            var = float(content[str(acc)]) - float(accountbal)
                            varInPercent = (var * 100) / content[str(acc)]
                            outflowAccounts.append(
                                {
                                    "accountname": accountname[0],
                                    "actual": "%.2f" % float(accountbal),
                                    "budget": "%.2f" % float(content[str(acc)]),
                                    "var": "%.2f" % float(var),
                                    "varinpercent": "%.2f" % float(varInPercent),
                                }
                            )
                        else:
                            var = float(content[str(acc)]) - float(accountbal)
                            varInPercent = (var * 100) / content[str(acc)]
                            inflowAccounts.append(
                                {
                                    "accountname": accountname[0],
                                    "actual": "%.2f" % float(accountbal),
                                    "budget": "%.2f" % float(content[str(acc)]),
                                    "var": "%.2f" % float(var),
                                    "varinpercent": "%.2f" % float(varInPercent),
                                }
                            )

                total = {
                    "inflow": inflowAccounts,
                    "outflow": outflowAccounts,
                    "openingacc": openingacc,
                    "closing": closing,
                }
                total["opening"] = "%.2f" % float(totalopeningbal)
                total["actualclosing"] = "%.2f" % float(actualClosingBal)
                total["budgetclosing"] = "%.2f" % float(
                    float(totalBudgetInflow)
                    + float(totalopeningbal)
                    - float(totalBudgetOutflow)
                )
                total["budgetin"] = "%.2f" % float(totalBudgetInflow)
                total["budgetout"] = "%.2f" % float(totalBudgetOutflow)
                total["actualin"] = "%.2f" % float(totalActualInflow)
                total["actualout"] = "%.2f" % float(totalActualOutflow)
                total["varin"] = "%.2f" % float(
                    float(totalActualInflow) - float(totalBudgetInflow)
                )
                total["varout"] = "%.2f" % float(
                    float(totalBudgetOutflow) - float(totalActualOutflow)
                )
                total["varpercentin"] = "%.2f" % float(
                    float(total["varin"]) * 100 / totalBudgetInflow
                )
                total["varpercentout"] = "%.2f" % float(
                    float(total["varout"]) * 100 / totalBudgetOutflow
                )
                return {"gkstatus": gkcore.enumdict["Success"], "gkresult": total}
            except:
                return {"gkstatus": enumdict["ConnectionFailed"]}
            finally:
                self.con.close()

    @view_config(
        request_method="GET", request_param="type=profitlossReport", renderer="json"
    )
    def profitlossReport(self):
        """Purpose:
        This function is used to calculate Profit & Loss budget report.
        This will take financial start date and budget id as input.
        Using budget id it will fetch all data regarding that budget id.
        This budget considers all accounts under Direct Expense & Indirect Expense and  Direct Income & Indirect Income to calculate Net profit.
        Calculations:
        for expense variance : budget - actuals
        for income variance : actuals - budget
        Net budget : income budget - expense budget
        Net actual : income actual - expense actual
        Net profit variance : actual - budgeted
        Variance in percentage : (100 * variance) / budget
        In this those accounts not have budget but they have their balances means their transaction has done, so that accounts should consider
            in budget report and their budget amount will be consider 0.But their variance is not calculate.
        """
        try:
            token = self.request.headers["gktoken"]
        except:
            return {"gkstatus": gkcore.enumdict["UnauthorisedAccess"]}
        authDetails = authCheck(token)
        if authDetails["auth"] == False:
            return {"gkstatus": enumdict["UnauthorisedAccess"]}
        else:
            try:
                self.con = eng.connect()
                financialStart = self.request.params["financialstart"]
                result = self.con.execute(
                    select(
                        [budget.c.contents, budget.c.startdate, budget.c.enddate]
                    ).where(
                        and_(
                            budget.c.orgcode == authDetails["orgcode"],
                            budget.c.budid == self.request.params["budid"],
                        )
                    )
                )
                budgetdata = result.fetchone()
                startdate = str(budgetdata["startdate"])[0:10]
                enddate = str(budgetdata["enddate"])[0:10]
                accountsList = list(budgetdata["contents"].keys())

                directExpense = 0.00
                directIncome = 0.00
                indirectExpense = 0.00
                indirectIncome = 0.00

                expensedata = []
                incomedata = []
                budgetDirectIncome = 0.00
                budgetDirectExpense = 0.00
                budgetIndirectIncome = 0.00
                budgetIndirectExpense = 0.00
                total = {}
                # all accounts under Direct Expense and in Direct expense subgroups
                result = self.con.execute(
                    "select accountcode,accountname from accounts where orgcode = %d and (groupcode in (select groupcode from groupsubgroups where orgcode= %d and (groupname = 'Direct Expense' or subgroupof in (select groupcode from groupsubgroups where orgcode= %d and (groupname = 'Direct Expense')))))"
                    % (
                        authDetails["orgcode"],
                        authDetails["orgcode"],
                        authDetails["orgcode"],
                    )
                )
                DEAccounts = result.fetchall()
                for acc in DEAccounts:
                    calbalData = calculateBalance(
                        self.con, acc["accountcode"], financialStart, startdate, enddate
                    )
                    balance = 0.00
                    if calbalData["curbal"] == 0.00:
                        if str(acc["accountcode"]) not in accountsList:
                            continue
                    if calbalData["baltype"] == "Dr":
                        balance = "%.2f" % float(float(calbalData["curbal"]))
                        directExpense = directExpense + float(calbalData["curbal"])
                    if calbalData["baltype"] == "Cr":
                        balance = "%.2f" % float(-float(calbalData["curbal"]))
                        directExpense = directExpense - float(calbalData["curbal"])
                    # if account is in budget then it will have an budget amount
                    if str(acc["accountcode"]) in accountsList:
                        budgetDirectExpense = float(budgetDirectExpense) + float(
                            budgetdata["contents"][str(acc["accountcode"])]
                        )
                        var = float(
                            budgetdata["contents"][str(acc["accountcode"])]
                        ) - float(balance)
                        varinpercent = (100 * var) / float(
                            budgetdata["contents"][str(acc["accountcode"])]
                        )
                        expensedata.append(
                            {
                                "name": acc["accountname"],
                                "budget": "%.2f"
                                % float(
                                    budgetdata["contents"][str(acc["accountcode"])]
                                ),
                                "actual": "%.2f" % float(balance),
                                "var": "%.2f" % float(var),
                                "varinpercent": "%.2f" % float(varinpercent),
                            }
                        )
                    else:
                        expensedata.append(
                            {
                                "name": acc["accountname"],
                                "budget": "%.2f" % float(0),
                                "actual": "%.2f" % float(balance),
                                "var": "-",
                                "varinpercent": "-",
                            }
                        )
                # similar fro Indirect Expense
                result = self.con.execute(
                    "select accountcode,accountname from accounts where orgcode = %d and (groupcode in (select groupcode from groupsubgroups where orgcode= %d and (groupname = 'Indirect Expense' or subgroupof in (select groupcode from groupsubgroups where orgcode= %d and (groupname = 'Indirect Expense')))))"
                    % (
                        authDetails["orgcode"],
                        authDetails["orgcode"],
                        authDetails["orgcode"],
                    )
                )
                DEAccounts = result.fetchall()
                for acc in DEAccounts:
                    calbalData = calculateBalance(
                        self.con, acc["accountcode"], financialStart, startdate, enddate
                    )
                    balance = 0.00
                    if calbalData["curbal"] == 0.00:
                        if str(acc["accountcode"]) not in accountsList:
                            continue
                    if calbalData["baltype"] == "Dr":
                        balance = "%.2f" % float(float(calbalData["curbal"]))
                        indirectExpense = indirectExpense + float(calbalData["curbal"])
                    if calbalData["baltype"] == "Cr":
                        balance = "%.2f" % float(-float(calbalData["curbal"]))
                        indirectExpense = indirectExpense - float(calbalData["curbal"])
                    if str(acc["accountcode"]) in accountsList:
                        budgetIndirectExpense = float(budgetDirectExpense) + float(
                            budgetdata["contents"][str(acc["accountcode"])]
                        )
                        var = float(
                            budgetdata["contents"][str(acc["accountcode"])]
                        ) - float(balance)
                        varinpercent = (100 * var) / float(
                            budgetdata["contents"][str(acc["accountcode"])]
                        )
                        expensedata.append(
                            {
                                "name": acc["accountname"],
                                "budget": "%.2f"
                                % float(
                                    budgetdata["contents"][str(acc["accountcode"])]
                                ),
                                "actual": "%.2f" % float(balance),
                                "var": "%.2f" % float(var),
                                "varinpercent": "%.2f" % float(varinpercent),
                            }
                        )
                    else:
                        expensedata.append(
                            {
                                "name": acc["accountname"],
                                "budget": "%.2f" % float(0),
                                "actual": "%.2f" % float(balance),
                                "var": "-",
                                "varinpercent": "-",
                            }
                        )
                # Total Expense calculation
                total["expense"] = "%.2f" % float(directExpense + indirectExpense)
                total["budgetexpense"] = "%.2f" % float(
                    budgetIndirectExpense + budgetDirectExpense
                )
                total["varexpense"] = "%.2f" % float(
                    float(total["budgetexpense"]) - float(total["expense"])
                )
                total["varinpercentexp"] = "%.2f" % float(
                    (100 * float(total["varexpense"])) / float(total["budgetexpense"])
                )
                total["expenseacc"] = expensedata

                # all accounts under Direct income and Direct income subgroups
                result = self.con.execute(
                    "select accountcode,accountname from accounts where orgcode = %d and (groupcode in (select groupcode from groupsubgroups where orgcode= %d and (groupname = 'Direct Income' or subgroupof in (select groupcode from groupsubgroups where orgcode= %d and (groupname = 'Direct Income')))))"
                    % (
                        authDetails["orgcode"],
                        authDetails["orgcode"],
                        authDetails["orgcode"],
                    )
                )
                DIAccounts = result.fetchall()
                for acc in DIAccounts:
                    calbalData = calculateBalance(
                        self.con, acc["accountcode"], financialStart, startdate, enddate
                    )
                    balance = 0.00
                    if calbalData["curbal"] == 0.00:
                        if str(acc["accountcode"]) not in accountsList:
                            continue
                    if calbalData["baltype"] == "Dr":
                        balance = "%.2f" % float(-float(calbalData["curbal"]))
                        directIncome = directIncome - float(calbalData["curbal"])
                    if calbalData["baltype"] == "Cr":
                        balance = "%.2f" % float(float(calbalData["curbal"]))
                        directIncome = directIncome + float(calbalData["curbal"])
                    # If account in budget then it will have budget amount
                    if str(acc["accountcode"]) in accountsList:
                        budgetDirectIncome = float(budgetDirectIncome) + float(
                            budgetdata["contents"][str(acc["accountcode"])]
                        )
                        var = float(balance) - float(
                            budgetdata["contents"][str(acc["accountcode"])]
                        )
                        varinpercent = (100 * var) / float(
                            budgetdata["contents"][str(acc["accountcode"])]
                        )
                        incomedata.append(
                            {
                                "name": acc["accountname"],
                                "budget": "%.2f"
                                % float(
                                    budgetdata["contents"][str(acc["accountcode"])]
                                ),
                                "actual": "%.2f" % float(balance),
                                "var": "%.2f" % float(var),
                                "varinpercent": "%.2f" % float(varinpercent),
                            }
                        )
                    else:
                        incomedata.append(
                            {
                                "name": acc["accountname"],
                                "budget": "%.2f" % float(0),
                                "actual": "%.2f" % float(balance),
                                "var": "-",
                                "varinpercent": "-",
                            }
                        )
                # similar fro Indirect Income
                result = self.con.execute(
                    "select accountcode,accountname from accounts where orgcode = %d and (groupcode in (select groupcode from groupsubgroups where orgcode= %d and (groupname = 'Indirect Income' or subgroupof in (select groupcode from groupsubgroups where orgcode= %d and (groupname = 'Indirect Income')))))"
                    % (
                        authDetails["orgcode"],
                        authDetails["orgcode"],
                        authDetails["orgcode"],
                    )
                )
                DIAccounts = result.fetchall()
                for acc in DIAccounts:
                    calbalData = calculateBalance(
                        self.con, acc["accountcode"], financialStart, startdate, enddate
                    )
                    balance = 0.00
                    if calbalData["curbal"] == 0.00:
                        if str(acc["accountcode"]) not in accountsList:
                            continue
                    if calbalData["baltype"] == "Dr":
                        balance = "%.2f" % float(-float(calbalData["curbal"]))
                        indirectIncome = indirectIncome - float(calbalData["curbal"])
                    if calbalData["baltype"] == "Cr":
                        balance = "%.2f" % float(float(calbalData["curbal"]))
                        indirectIncome = indirectIncome + float(calbalData["curbal"])
                    if str(acc["accountcode"]) in accountsList:
                        budgetIndirectIncome = float(budgetIndirectIncome) + float(
                            budgetdata["contents"][str(acc["accountcode"])]
                        )
                        var = float(balance) - float(
                            budgetdata["contents"][str(acc["accountcode"])]
                        )
                        varinpercent = (100 * var) / float(
                            budgetdata["contents"][str(acc["accountcode"])]
                        )
                        incomedata.append(
                            {
                                "name": acc["accountname"],
                                "budget": "%.2f"
                                % float(
                                    budgetdata["contents"][str(acc["accountcode"])]
                                ),
                                "actual": "%.2f" % float(balance),
                                "var": "%.2f" % float(var),
                                "varinpercent": "%.2f" % float(varinpercent),
                            }
                        )
                    else:
                        incomedata.append(
                            {
                                "name": acc["accountname"],
                                "budget": "%.2f" % float(0),
                                "actual": "%.2f" % float(balance),
                                "var": "-",
                                "varinpercent": "-",
                            }
                        )
                # Total Income calculations

                total["income"] = "%.2f" % float(directIncome + indirectIncome)
                total["budgetincome"] = "%.2f" % float(
                    budgetIndirectIncome + budgetDirectIncome
                )
                total["varincome"] = "%.2f" % float(
                    float(total["income"]) - float(total["budgetincome"])
                )
                total["varinpercentincome"] = "%.2f" % float(
                    (100 * float(total["varincome"])) / float(total["budgetincome"])
                )
                total["incomeacc"] = incomedata
                # Profit calculations
                profit = float(total["income"]) - float(total["expense"])
                total["profit"] = "%.2f" % float(profit)
                budgetprofit = float(total["budgetincome"]) - float(
                    total["budgetexpense"]
                )
                total["budgetprofit"] = "%.2f" % float(budgetprofit)
                if float(total["budgetprofit"]) != 0:
                    total["varprofit"] = "%.2f" % float(
                        float(total["profit"]) - float(total["budgetprofit"])
                    )
                    total["varinpercentprofit"] = "%.2f" % float(
                        (100 * float(total["varprofit"])) / float(total["budgetprofit"])
                    )
                else:
                    total["varprofit"] = "-"
                    total["varinpercentprofit"] = "-"

                return {"gkstatus": gkcore.enumdict["Success"], "gkresult": total}
            except:
                return {"gkstatus": enumdict["ConnectionFailed"]}
            finally:
                self.con.close()
