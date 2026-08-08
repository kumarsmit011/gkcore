from gkcore import eng, enumdict
from gkcore.utils import authCheck
from gkcore.models.gkdb import accounts
from sqlalchemy.sql import select
from sqlalchemy.engine.base import Connection
from pyramid.request import Request
from pyramid.view import view_defaults, view_config
from gkcore.views.reports.helpers.balance import calculateBalance


@view_defaults(request_method="GET")
class api_trial_balance(object):
    def __init__(self, request):
        self.request = Request
        self.request = request
        self.con = Connection
    @view_config(route_name="net-trial-balance", renderer="json")
    def netTrialBalance(self):
        """
        Purpose:
        Returns a grid containing net trial balance for all accounts started from financial start till the end date provided by the user.
        Description:
        This method has type=nettrialbalance as request_param in view_config.
        the method takes financial start and calculateto as parameters.
        Then it calls calculateBalance in a loop after retriving list of accountcode and account names.
        For every iteration financialstart is passed twice to calculateBalance because in trial balance start date is always the financial start.
        Then all dR balances and all Cr balances are added to get total balance for each side.
        Finally if balances are different then that difference is calculated and shown on the lower side followed by a row containing grand total.
        In addition to this data we have 2 other columns,
        Total Running total for Dr and Cr useful for printing.
        Same applies to the following methods in this class for gross and extended trial balances.
        All rows in the ntbGrid are dictionaries.
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
                accountData = self.con.execute(
                    select([accounts.c.accountcode, accounts.c.accountname])
                    .where(accounts.c.orgcode == authDetails["orgcode"])
                    .order_by(accounts.c.accountname)
                )
                accountRecords = accountData.fetchall()
                ntbGrid = []
                financialStart = self.request.params["financialstart"]
                calculateTo = self.request.params["calculateto"]
                srno = 0
                totalDr = 0.00
                totalCr = 0.00
                for account in accountRecords:
                    adverseflag = 0
                    calbalData = calculateBalance(
                        self.con,
                        account["accountcode"],
                        financialStart,
                        financialStart,
                        calculateTo,
                    )
                    if calbalData["baltype"] == "":
                        continue
                    srno += 1
                    ntbRow = {
                        "accountcode": account["accountcode"],
                        "accountname": account["accountname"],
                        "groupname": calbalData["grpname"],
                        "srno": srno,
                    }
                    if calbalData["baltype"] == "Dr":
                        if (
                            calbalData["grpname"] == "Corpus"
                            or calbalData["grpname"] == "Capital"
                            or calbalData["grpname"] == "Current Liabilities"
                            or calbalData["grpname"] == "Loans(Liability)"
                            or calbalData["grpname"] == "Reserves"
                        ) and calbalData["curbal"] != 0:
                            adverseflag = 1
                        ntbRow["Dr"] = "%.2f" % (calbalData["curbal"])
                        ntbRow["Cr"] = ""
                        ntbRow["advflag"] = adverseflag
                        totalDr = totalDr + calbalData["curbal"]
                    if calbalData["baltype"] == "Cr":
                        if (
                            calbalData["grpname"] == "Current Assets"
                            or calbalData["grpname"] == "Fixed Assets"
                            or calbalData["grpname"] == "Investments"
                            or calbalData["grpname"] == "Loans(Asset)"
                            or calbalData["grpname"] == "Miscellaneous Expenses(Asset)"
                        ) and calbalData["curbal"] != 0:
                            adverseflag = 1
                        ntbRow["Dr"] = ""
                        ntbRow["Cr"] = "%.2f" % (calbalData["curbal"])
                        ntbRow["advflag"] = adverseflag
                        totalCr = totalCr + calbalData["curbal"]
                    ntbRow["ttlRunDr"] = "%.2f" % (totalDr)
                    ntbRow["ttlRunCr"] = "%.2f" % (totalCr)
                    ntbGrid.append(ntbRow)
                ntbGrid.append(
                    {
                        "accountcode": "",
                        "accountname": "Total",
                        "groupname": "",
                        "srno": "",
                        "Dr": "%.2f" % (totalDr),
                        "Cr": "%.2f" % (totalCr),
                        "advflag": "",
                    }
                )
                if totalDr > totalCr:
                    baldiff = totalDr - totalCr
                    ntbGrid.append(
                        {
                            "accountcode": "",
                            "accountname": "Difference in Trial balance",
                            "groupname": "",
                            "srno": "",
                            "Cr": "%.2f" % (baldiff),
                            "Dr": "",
                            "advflag": "",
                        }
                    )
                    ntbGrid.append(
                        {
                            "accountcode": "",
                            "accountname": "",
                            "groupname": "",
                            "srno": "",
                            "Cr": "%.2f" % (totalDr),
                            "Dr": "%.2f" % (totalDr),
                            "advflag": "",
                        }
                    )
                if totalDr < totalCr:
                    baldiff = totalCr - totalDr
                    ntbGrid.append(
                        {
                            "accountcode": "",
                            "accountname": "Difference in Trial balance",
                            "groupname": "",
                            "srno": "",
                            "Dr": "%.2f" % (baldiff),
                            "Cr": "",
                            "advflag": "",
                        }
                    )
                    ntbGrid.append(
                        {
                            "accountcode": "",
                            "accountname": "",
                            "groupname": "",
                            "srno": "",
                            "Cr": "%.2f" % (totalCr),
                            "Dr": "%.2f" % (totalCr),
                            "advflag": "",
                        }
                    )
                self.con.close()

                return {"gkstatus": enumdict["Success"], "gkresult": ntbGrid}
            except:
                self.con.close()
                return {"gkstatus": enumdict["ConnectionFailed"]}

    @view_config(route_name="gross-trial-balance", renderer="json")
    def grossTrialBalance(self):
        """
        Purpose:
        Returns a grid containing gross trial balance for all accounts started from financial start till the end date provided by the user.
        Description:
        This method has type=nettrialbalance as request_param in view_config.
        the method takes financial start and calculateto as parameters.
        Then it calls calculateBalance in a loop after retriving list of accountcode and account names.
        For every iteration financialstart is passed twice to calculateBalance because in trial balance start date is always the financial start.
        Then all dR balances and all Cr balances are added to get total balance for each side.
        Finally if balances are different then that difference is calculated and shown on the lower side followed by a row containing grand total.
        All rows in the ntbGrid are dictionaries.
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
                accountData = self.con.execute(
                    select([accounts.c.accountcode, accounts.c.accountname])
                    .where(accounts.c.orgcode == authDetails["orgcode"])
                    .order_by(accounts.c.accountname)
                )
                accountRecords = accountData.fetchall()
                gtbGrid = []
                financialStart = self.request.params["financialstart"]
                calculateTo = self.request.params["calculateto"]
                srno = 0
                totalDr = 0.00
                totalCr = 0.00
                for account in accountRecords:
                    adverseflag = 0
                    calbalData = calculateBalance(
                        self.con,
                        account["accountcode"],
                        financialStart,
                        financialStart,
                        calculateTo,
                    )
                    if (
                        float(calbalData["totaldrbal"]) == 0
                        and float(calbalData["totalcrbal"]) == 0
                    ):
                        continue
                    srno += 1
                    if (
                        (calbalData["baltype"] == "Dr")
                        and (
                            calbalData["grpname"] == "Corpus"
                            or calbalData["grpname"] == "Capital"
                            or calbalData["grpname"] == "Current Liabilities"
                            or calbalData["grpname"] == "Loans(Liability)"
                            or calbalData["grpname"] == "Reserves"
                        )
                        and calbalData["curbal"] != 0
                    ):
                        adverseflag = 1
                    if (
                        (calbalData["baltype"] == "Cr")
                        and (
                            calbalData["grpname"] == "Current Assets"
                            or calbalData["grpname"] == "Fixed Assets"
                            or calbalData["grpname"] == "Investments"
                            or calbalData["grpname"] == "Loans(Asset)"
                            or calbalData["grpname"] == "Miscellaneous Expenses(Asset)"
                        )
                        and calbalData["curbal"] != 0
                    ):
                        adverseflag = 1
                    gtbRow = {
                        "accountcode": account["accountcode"],
                        "accountname": account["accountname"],
                        "groupname": calbalData["grpname"],
                        "Dr balance": "%.2f" % (calbalData["totaldrbal"]),
                        "Cr balance": "%.2f" % (calbalData["totalcrbal"]),
                        "srno": srno,
                        "advflag": adverseflag,
                    }
                    totalDr += calbalData["totaldrbal"]
                    totalCr += calbalData["totalcrbal"]
                    gtbRow["ttlRunDr"] = "%.2f" % (totalDr)
                    gtbRow["ttlRunCr"] = "%.2f" % (totalCr)
                    gtbGrid.append(gtbRow)
                gtbGrid.append(
                    {
                        "accountcode": "",
                        "accountname": "Total",
                        "groupname": "",
                        "Dr balance": "%.2f" % (totalDr),
                        "Cr balance": "%.2f" % (totalCr),
                        "srno": "",
                        "advflag": "",
                    }
                )
                if totalDr > totalCr:
                    baldiff = totalDr - totalCr
                    gtbGrid.append(
                        {
                            "accountcode": "",
                            "accountname": "Difference in Trial balance",
                            "groupname": "",
                            "srno": "",
                            "Cr balance": "%.2f" % (baldiff),
                            "Dr balance": "",
                            "advflag": "",
                        }
                    )
                    gtbGrid.append(
                        {
                            "accountcode": "",
                            "accountname": "",
                            "groupname": "",
                            "srno": "",
                            "Cr balance": "%.2f" % (totalDr),
                            "Dr balance": "%.2f" % (totalDr),
                            "advflag": "",
                        }
                    )
                if totalDr < totalCr:
                    baldiff = totalCr - totalDr
                    gtbGrid.append(
                        {
                            "accountcode": "",
                            "accountname": "Difference in Trial balance",
                            "groupname": "",
                            "srno": "",
                            "Dr balance": "%.2f" % (baldiff),
                            "Cr balance": "",
                            "advflag": "",
                        }
                    )
                    gtbGrid.append(
                        {
                            "accountcode": "",
                            "accountname": "",
                            "groupname": "",
                            "srno": "",
                            "Cr balance": "%.2f" % (totalCr),
                            "Dr balance": "%.2f" % (totalCr),
                            "advflag": "",
                        }
                    )
                self.con.close()

                return {"gkstatus": enumdict["Success"], "gkresult": gtbGrid}
            except:
                self.con.close()
                return {"gkstatus": enumdict["ConnectionFailed"]}

    @view_config(route_name="extended-trial-balance", renderer="json")
    def extendedTrialBalance(self):
        """
        Purpose:
        Returns a grid containing extended trial balance for all accounts started from financial start till the end date provided by the user.
        Description:
        This method has type=nettrialbalance as request_param in view_config.
        the method takes financial start and calculateto as parameters.
        Then it calls calculateBalance in a loop after retriving list of accountcode and account names.
        For every iteration financialstart is passed twice to calculateBalance because in trial balance start date is always the financial start.
        Then all dR balances and all Cr balances are added to get total balance for each side.
        After this all closing balances are added either on Dr or Cr side depending on the baltype.
        Finally if balances are different then that difference is calculated and shown on the lower side followed by a row containing grand total.
        All rows in the extbGrid are dictionaries.
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
                accountData = self.con.execute(
                    select([accounts.c.accountcode, accounts.c.accountname])
                    .where(accounts.c.orgcode == authDetails["orgcode"])
                    .order_by(accounts.c.accountname)
                )
                accountRecords = accountData.fetchall()
                extbGrid = []
                financialStart = self.request.params["financialstart"]
                calculateTo = self.request.params["calculateto"]
                srno = 0
                totalDr = 0.00
                totalCr = 0.00
                totalDrBal = 0.00
                totalCrBal = 0.00
                difftb = 0.00
                for account in accountRecords:
                    adverseflag = 0
                    calbalData = calculateBalance(
                        self.con,
                        account["accountcode"],
                        financialStart,
                        financialStart,
                        calculateTo,
                    )
                    if (
                        float(calbalData["balbrought"]) == 0
                        and float(calbalData["totaldrbal"]) == 0
                        and float(calbalData["totalcrbal"]) == 0
                    ):
                        continue
                    srno += 1
                    if calbalData["openbaltype"] == "Cr":
                        calbalData["totalcrbal"] -= calbalData["balbrought"]
                    if calbalData["openbaltype"] == "Dr":
                        calbalData["totaldrbal"] -= calbalData["balbrought"]
                    extbrow = {
                        "accountcode": account["accountcode"],
                        "accountname": account["accountname"],
                        "groupname": calbalData["grpname"],
                        "totaldr": "%.2f" % (calbalData["totaldrbal"]),
                        "totalcr": "%.2f" % (calbalData["totalcrbal"]),
                        "srno": srno,
                    }
                    if calbalData["balbrought"] > 0:
                        extbrow["openingbalance"] = "%.2f(%s)" % (
                            calbalData["balbrought"],
                            calbalData["openbaltype"],
                        )
                    else:
                        extbrow["openingbalance"] = "0.00"
                    totalDr += calbalData["totaldrbal"]
                    totalCr += calbalData["totalcrbal"]
                    if calbalData["baltype"] == "Dr":
                        if (
                            calbalData["grpname"] == "Corpus"
                            or calbalData["grpname"] == "Capital"
                            or calbalData["grpname"] == "Current Liabilities"
                            or calbalData["grpname"] == "Loans(Liability)"
                            or calbalData["grpname"] == "Reserves"
                        ) and calbalData["curbal"] != 0:
                            adverseflag = 1
                        extbrow["curbaldr"] = "%.2f" % (calbalData["curbal"])
                        extbrow["curbalcr"] = ""
                        totalDrBal += calbalData["curbal"]
                    if calbalData["baltype"] == "Cr":
                        if (
                            calbalData["grpname"] == "Current Assets"
                            or calbalData["grpname"] == "Fixed Assets"
                            or calbalData["grpname"] == "Investments"
                            or calbalData["grpname"] == "Loans(Asset)"
                            or calbalData["grpname"] == "Miscellaneous Expenses(Asset)"
                        ) and calbalData["curbal"] != 0:
                            adverseflag = 1
                        extbrow["curbaldr"] = ""
                        extbrow["curbalcr"] = "%.2f" % (calbalData["curbal"])
                        totalCrBal += calbalData["curbal"]
                    if calbalData["baltype"] == "":
                        extbrow["curbaldr"] = ""
                        extbrow["curbalcr"] = ""
                    extbrow["ttlRunDr"] = "%.2f" % (totalDrBal)
                    extbrow["ttlRunCr"] = "%.2f" % (totalCrBal)
                    extbrow["advflag"] = adverseflag
                    extbGrid.append(extbrow)
                extbrow = {
                    "accountcode": "",
                    "accountname": "Total",
                    "groupname": "",
                    "openingbalance": "",
                    "totaldr": "%.2f" % (totalDr),
                    "totalcr": "%.2f" % (totalCr),
                    "curbaldr": "%.2f" % (totalDrBal),
                    "curbalcr": "%.2f" % (totalCrBal),
                    "srno": "",
                    "advflag": "",
                }
                extbGrid.append(extbrow)

                if totalDrBal > totalCrBal:
                    extbGrid.append(
                        {
                            "accountcode": "",
                            "accountname": "Difference in Trial Balance",
                            "groupname": "",
                            "openingbalance": "",
                            "totaldr": "",
                            "totalcr": "",
                            "srno": "",
                            "curbalcr": "%.2f" % (totalDrBal - totalCrBal),
                            "curbaldr": "",
                            "advflag": "",
                        }
                    )
                    extbGrid.append(
                        {
                            "accountcode": "",
                            "accountname": "",
                            "groupname": "",
                            "openingbalance": "",
                            "totaldr": "",
                            "totalcr": "",
                            "curbaldr": "%.2f" % (totalDrBal),
                            "curbalcr": "%.2f" % (totalDrBal),
                            "srno": "",
                            "advflag": "",
                        }
                    )
                if totalCrBal > totalDrBal:
                    extbGrid.append(
                        {
                            "accountcode": "",
                            "accountname": "Difference in Trial Balance",
                            "groupname": "",
                            "openingbalance": "",
                            "totaldr": "",
                            "totalcr": "",
                            "srno": "",
                            "curbaldr": "%.2f" % (totalCrBal - totalDrBal),
                            "curbalcr": "",
                            "advflag": "",
                        }
                    )
                    extbGrid.append(
                        {
                            "accountcode": "",
                            "accountname": "",
                            "groupname": "",
                            "openingbalance": "",
                            "totaldr": "",
                            "totalcr": "",
                            "curbaldr": "%.2f" % (totalCrBal),
                            "curbalcr": "%.2f" % (totalCrBal),
                            "srno": "",
                            "advflag": "",
                        }
                    )
                self.con.close()
                return {"gkstatus": enumdict["Success"], "gkresult": extbGrid}
            except:
                self.con.close()
                return {"gkstatus": enumdict["ConnectionFailed"]}
