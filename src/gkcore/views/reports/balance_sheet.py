from gkcore import eng, enumdict
from gkcore.utils import authCheck
from sqlalchemy.engine.base import Connection
from pyramid.request import Request
from pyramid.view import view_defaults, view_config
from gkcore.views.reports.helpers.balance import getBalanceSheet


@view_defaults(route_name="balance-sheet", request_method="GET")
class api_balance_sheet(object):
    def __init__(self, request):
        self.request = Request
        self.request = request
        self.con = Connection

    @view_config(renderer="json")
    def balanceSheet(self):
        """
        Purpose:
        Gets the list of groups and their respective balances
        takes organisation code and end date as input parameter
        Description:
        This function is used to generate balance sheet for a given organisation and the given time period.
        This function takes orgcode and end date as the input parameters
        This function is called when the type=balancesheet is passed to the /report url.
        orgcode is extracted from the header
        end date is extracted from the request_params
        The accountcode is extracted from the database under  groupcode for groups relevent to balance sheet
        the  groupbalance will be initialized to 0.0 for each group.
        this accountcode is sent to the calculateBalance function along with financialstart, calculateTo
        the function will return the closing balance related to each account which will be later added or subtracted according to the accounting rules from the group balance
        Then the subgroups and their respective accounts will be fetched from the database and the detail will be sent to the calculatBalance function which will return the curbal.
        the amount will be added or subtracted from the subgroup balance accordingly.
        the above steps will be executed in loop to calculate balances of all subgroups.
        these balances will be added/subtracted from the group balance accordingly.
        the above statements will be running in a loop for each group.
        Later all the group balances for sources and application will be added
        the difference in the amounts of sourcetotal and applicationtotal will be found
        the function will return the gkstatus and gkresult which contains a list of dictionaries where every dictionary represents a row with two key-value pairs each representing columns

        """
        try:
            token = self.request.headers["gktoken"]
        except:
            return {"gkstatus": enumdict["UnauthorisedAccess"]}
        authDetails = authCheck(token)
        if authDetails["auth"] == False:
            return {"gkstatus": enumdict["UnauthorisedAccess"]}
        with eng.connect() as conn:
            balanceSheet = getBalanceSheet(
                conn,
                authDetails["orgcode"],
                self.request.params["calculateto"],
                self.request.params["calculatefrom"],
                int(self.request.params["baltype"]),
            )
            return {
                "gkstatus": enumdict["Success"],
                "gkresult": balanceSheet,
            }

    @view_config(request_param="type=conventionalbalancesheet", renderer="json")
    def conventionalbalanceSheet(self):
        """
        Purpose:
        Gets the list of groups and their respective balances
        takes organisation code and end date as input parameter
        Description:
        This function is used to generate balance sheet for a given organisation and the given time period.
        This function takes orgcode and end date as the input parameters
        This function is called when the type=conventionalbalancesheet is passed to the /report url.
        orgcode is extracted from the header
        end date is extracted from the request_params
        The accountcode is extracted from the database under  groupcode for groups relevent to balance sheet (meaning all groups except income and expence groups).
        the  groupbalance will be initialized to 0.0 for each group.
        this accountcode is sent to the calculateBalance function along with financialstart, calculateTo
        the function will return the closing balance related to each account which will be later added or subtracted according to the accounting rules from the group balance
        the above statements will be running in a loop for each group.
        Later all the group balances for sources and application will be added
        the difference in the amounts of sourcetotal and applicationtotal will be found
        the function will return the gkstatus and gkresult which contains a list of dictionaries where every dictionary represents a row with two key-value pairs each representing columns
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
                financialstart = self.con.execute(
                    "select yearstart, orgtype from organisation where orgcode = %d"
                    % int(orgcode)
                )
                financialstartRow = financialstart.fetchone()
                financialStart = financialstartRow["yearstart"]
                orgtype = financialstartRow["orgtype"]
                calculateTo = self.request.params["calculateto"]
                calculateTo = calculateTo
                balanceSheet = []
                sourcegroupWiseTotal = 0.00
                applicationgroupWiseTotal = 0.00
                sourcesTotal = 0.00
                applicationsTotal = 0.00
                difference = 0.00
                balanceSheet.append(
                    {
                        "sourcesgroupname": "Sources:",
                        "sourceamount": "",
                        "appgroupname": "Applications:",
                        "applicationamount": "",
                    }
                )
                capital_Corpus = ""
                if orgtype == "Profit Making":
                    capital_Corpus = "Capital"
                if orgtype == "Not For Profit":
                    capital_Corpus = "Corpus"

                # Calculate grouptotal for group Capital/Corpus
                accountcodeData = self.con.execute(
                    "select accountcode from accounts where orgcode = %d and groupcode in(select groupcode from groupsubgroups where orgcode =%d and groupname = '%s' or subgroupof = (select groupcode from groupsubgroups where orgcode = %d and groupname = '%s'));"
                    % (orgcode, orgcode, capital_Corpus, orgcode, capital_Corpus)
                )
                accountCodes = accountcodeData.fetchall()
                for accountRow in accountCodes:
                    accountDetails = calculateBalance(
                        self.con,
                        accountRow["accountcode"],
                        financialStart,
                        financialStart,
                        calculateTo,
                    )
                    if accountDetails["baltype"] == "Cr":
                        sourcegroupWiseTotal += accountDetails["curbal"]
                    if accountDetails["baltype"] == "Dr":
                        sourcegroupWiseTotal -= accountDetails["curbal"]
                sourcesTotal += sourcegroupWiseTotal

                # Calculate grouptotal for group "Fixed Assets"
                accountcodeData = self.con.execute(
                    "select accountcode from accounts where orgcode = %d and groupcode in(select groupcode from groupsubgroups where orgcode =%d and groupname = 'Fixed Assets' or subgroupof = (select groupcode from groupsubgroups where orgcode = %d and groupname = 'Fixed Assets'));"
                    % (orgcode, orgcode, orgcode)
                )
                accountCodes = accountcodeData.fetchall()
                for accountRow in accountCodes:
                    accountDetails = calculateBalance(
                        self.con,
                        accountRow["accountcode"],
                        financialStart,
                        financialStart,
                        calculateTo,
                    )
                    if accountDetails["baltype"] == "Dr":
                        applicationgroupWiseTotal += accountDetails["curbal"]
                    if accountDetails["baltype"] == "Cr":
                        applicationgroupWiseTotal -= accountDetails["curbal"]
                applicationsTotal += applicationgroupWiseTotal
                balanceSheet.append(
                    {
                        "sourcesgroupname": capital_Corpus,
                        "sourceamount": "%.2f" % (sourcegroupWiseTotal),
                        "appgroupname": "Fixed Assets",
                        "applicationamount": "%.2f" % (applicationgroupWiseTotal),
                    }
                )

                # Calculate grouptotal for group Loans(Liability)
                sourcegroupWiseTotal = 0.00
                accountcodeData = self.con.execute(
                    "select accountcode from accounts where orgcode = %d and groupcode in(select groupcode from groupsubgroups where orgcode =%d and groupname = 'Loans(Liability)' or subgroupof = (select groupcode from groupsubgroups where orgcode = %d and groupname = 'Loans(Liability)'));"
                    % (orgcode, orgcode, orgcode)
                )
                accountCodes = accountcodeData.fetchall()
                for accountRow in accountCodes:
                    accountDetails = calculateBalance(
                        self.con,
                        accountRow["accountcode"],
                        financialStart,
                        financialStart,
                        calculateTo,
                    )
                    if accountDetails["baltype"] == "Cr":
                        sourcegroupWiseTotal += accountDetails["curbal"]
                    if accountDetails["baltype"] == "Dr":
                        sourcegroupWiseTotal -= accountDetails["curbal"]
                sourcesTotal += sourcegroupWiseTotal

                # Calculate grouptotal for group "Investments"
                applicationgroupWiseTotal = 0.00
                accountcodeData = self.con.execute(
                    "select accountcode from accounts where orgcode = %d and groupcode in(select groupcode from groupsubgroups where orgcode =%d and groupname = 'Investments' or subgroupof = (select groupcode from groupsubgroups where orgcode = %d and groupname = 'Investments'));"
                    % (orgcode, orgcode, orgcode)
                )
                accountCodes = accountcodeData.fetchall()
                for accountRow in accountCodes:
                    accountDetails = calculateBalance(
                        self.con,
                        accountRow["accountcode"],
                        financialStart,
                        financialStart,
                        calculateTo,
                    )
                    if accountDetails["baltype"] == "Dr":
                        applicationgroupWiseTotal += accountDetails["curbal"]
                    if accountDetails["baltype"] == "Cr":
                        applicationgroupWiseTotal -= accountDetails["curbal"]
                applicationsTotal += applicationgroupWiseTotal
                balanceSheet.append(
                    {
                        "sourcesgroupname": "Loans(Liability)",
                        "sourceamount": "%.2f" % (sourcegroupWiseTotal),
                        "appgroupname": "Investments",
                        "applicationamount": "%.2f" % (applicationgroupWiseTotal),
                    }
                )

                # Calculate grouptotal for group Current Liabilities
                sourcegroupWiseTotal = 0.00
                accountcodeData = self.con.execute(
                    "select accountcode from accounts where orgcode = %d and groupcode in(select groupcode from groupsubgroups where orgcode =%d and groupname = 'Current Liabilities' or subgroupof = (select groupcode from groupsubgroups where orgcode = %d and groupname = 'Current Liabilities'));"
                    % (orgcode, orgcode, orgcode)
                )
                accountCodes = accountcodeData.fetchall()
                for accountRow in accountCodes:
                    accountDetails = calculateBalance(
                        self.con,
                        accountRow["accountcode"],
                        financialStart,
                        financialStart,
                        calculateTo,
                    )
                    if accountDetails["baltype"] == "Cr":
                        sourcegroupWiseTotal += accountDetails["curbal"]
                    if accountDetails["baltype"] == "Dr":
                        sourcegroupWiseTotal -= accountDetails["curbal"]
                sourcesTotal += sourcegroupWiseTotal

                # Calculate grouptotal for group "Current Assets"
                applicationgroupWiseTotal = 0.00
                accountcodeData = self.con.execute(
                    "select accountcode from accounts where orgcode = %d and groupcode in(select groupcode from groupsubgroups where orgcode =%d and groupname = 'Current Assets' or subgroupof = (select groupcode from groupsubgroups where orgcode = %d and groupname = 'Current Assets'));"
                    % (orgcode, orgcode, orgcode)
                )
                accountCodes = accountcodeData.fetchall()
                for accountRow in accountCodes:
                    accountDetails = calculateBalance(
                        self.con,
                        accountRow["accountcode"],
                        financialStart,
                        financialStart,
                        calculateTo,
                    )
                    if accountDetails["baltype"] == "Dr":
                        applicationgroupWiseTotal += accountDetails["curbal"]
                    if accountDetails["baltype"] == "Cr":
                        applicationgroupWiseTotal -= accountDetails["curbal"]
                applicationsTotal += applicationgroupWiseTotal
                balanceSheet.append(
                    {
                        "sourcesgroupname": "Current Liabilities",
                        "sourceamount": "%.2f" % (sourcegroupWiseTotal),
                        "appgroupname": "Current Assets",
                        "applicationamount": "%.2f" % (applicationgroupWiseTotal),
                    }
                )

                # Calculate grouptotal for group "Reserves"
                sourcegroupWiseTotal = 0.00
                incomeTotal = 0.00
                expenseTotal = 0.00
                # Calculate all income(Direct and Indirect Income)
                accountcodeData = self.con.execute(
                    "select accountcode from accounts where orgcode = %d and groupcode in(select groupcode from groupsubgroups where orgcode =%d and groupname in ('Direct Income','Indirect Income') or subgroupof in (select groupcode from groupsubgroups where orgcode = %d and groupname in ('Direct Income','Indirect Income')));"
                    % (orgcode, orgcode, orgcode)
                )
                accountCodes = accountcodeData.fetchall()
                for accountRow in accountCodes:
                    accountDetails = calculateBalance(
                        self.con,
                        accountRow["accountcode"],
                        financialStart,
                        financialStart,
                        calculateTo,
                    )
                    if accountDetails["baltype"] == "Cr":
                        incomeTotal += accountDetails["curbal"]
                    if accountDetails["baltype"] == "Dr":
                        incomeTotal -= accountDetails["curbal"]

                # Calculate all expense(Direct and Indirect Expense)
                accountcodeData = self.con.execute(
                    "select accountcode from accounts where orgcode = %d and groupcode in(select groupcode from groupsubgroups where orgcode =%d and groupname in ('Direct Expense','Indirect Expense') or subgroupof in (select groupcode from groupsubgroups where orgcode = %d and groupname in ('Direct Expense','Indirect Expense')));"
                    % (orgcode, orgcode, orgcode)
                )
                accountCodes = accountcodeData.fetchall()
                for accountRow in accountCodes:
                    accountDetails = calculateBalance(
                        self.con,
                        accountRow["accountcode"],
                        financialStart,
                        financialStart,
                        calculateTo,
                    )
                    if accountDetails["baltype"] == "Dr":
                        expenseTotal += accountDetails["curbal"]
                    if accountDetails["baltype"] == "Cr":
                        expenseTotal -= accountDetails["curbal"]

                # Calculate total of all accounts in Reserves (except Direct and Indirect Income, Expense)
                accountcodeData = self.con.execute(
                    "select accountcode from accounts where orgcode = %d and groupcode in(select groupcode from groupsubgroups where orgcode =%d and groupname = 'Reserves' or subgroupof = (select groupcode from groupsubgroups where orgcode = %d and groupname = 'Reserves'));"
                    % (orgcode, orgcode, orgcode)
                )
                accountCodes = accountcodeData.fetchall()
                for accountRow in accountCodes:
                    accountDetails = calculateBalance(
                        self.con,
                        accountRow["accountcode"],
                        financialStart,
                        financialStart,
                        calculateTo,
                    )
                    if accountDetails["baltype"] == "Cr":
                        sourcegroupWiseTotal += accountDetails["curbal"]
                    if accountDetails["baltype"] == "Dr":
                        sourcegroupWiseTotal -= accountDetails["curbal"]

                # Calculate Profit/Loss for the year
                profit = 0.00

                if expenseTotal > incomeTotal:
                    profit = expenseTotal - incomeTotal
                    sourcegroupWiseTotal -= profit
                if expenseTotal < incomeTotal:
                    profit = incomeTotal - expenseTotal
                    sourcegroupWiseTotal += profit

                sourcesTotal += sourcegroupWiseTotal

                # Calculate grouptotal for group Loans(Asset)
                applicationgroupWiseTotal = 0.00
                accountcodeData = self.con.execute(
                    "select accountcode from accounts where orgcode = %d and groupcode in(select groupcode from groupsubgroups where orgcode =%d and groupname = 'Loans(Asset)' or subgroupof = (select groupcode from groupsubgroups where orgcode = %d and groupname = 'Loans(Asset)'));"
                    % (orgcode, orgcode, orgcode)
                )
                accountCodes = accountcodeData.fetchall()
                for accountRow in accountCodes:
                    accountDetails = calculateBalance(
                        self.con,
                        accountRow["accountcode"],
                        financialStart,
                        financialStart,
                        calculateTo,
                    )
                    if accountDetails["baltype"] == "Dr":
                        applicationgroupWiseTotal += accountDetails["curbal"]
                    if accountDetails["baltype"] == "Cr":
                        applicationgroupWiseTotal -= accountDetails["curbal"]
                applicationsTotal += applicationgroupWiseTotal
                balanceSheet.append(
                    {
                        "sourcesgroupname": "Reserves",
                        "sourceamount": "%.2f" % (sourcegroupWiseTotal),
                        "appgroupname": "Loans(Asset)",
                        "applicationamount": "%.2f" % (applicationgroupWiseTotal),
                    }
                )

                # Calculate grouptotal for group "Miscellaneous Expenses(Asset)"
                applicationgroupWiseTotal = 0.00
                accountcodeData = self.con.execute(
                    "select accountcode from accounts where orgcode = %d and groupcode in(select groupcode from groupsubgroups where orgcode =%d and groupname = 'Miscellaneous Expenses(Asset)' or subgroupof = (select groupcode from groupsubgroups where orgcode = %d and groupname = 'Miscellaneous Expenses(Asset)'));"
                    % (orgcode, orgcode, orgcode)
                )
                accountCodes = accountcodeData.fetchall()
                for accountRow in accountCodes:
                    accountDetails = calculateBalance(
                        self.con,
                        accountRow["accountcode"],
                        financialStart,
                        financialStart,
                        calculateTo,
                    )
                    if accountDetails["baltype"] == "Dr":
                        applicationgroupWiseTotal += accountDetails["curbal"]
                    if accountDetails["baltype"] == "Cr":
                        applicationgroupWiseTotal -= accountDetails["curbal"]
                applicationsTotal += applicationgroupWiseTotal

                if expenseTotal > incomeTotal:
                    balanceSheet.append(
                        {
                            "sourcesgroupname": "Loss for the Year:",
                            "sourceamount": "%.2f" % (profit),
                            "appgroupname": "Miscellaneous Expenses(Asset)",
                            "applicationamount": "%.2f" % (applicationgroupWiseTotal),
                        }
                    )
                if expenseTotal < incomeTotal:
                    balanceSheet.append(
                        {
                            "sourcesgroupname": "Profit for the Year",
                            "sourceamount": "%.2f" % (profit),
                            "appgroupname": "Miscellaneous Expenses(Asset)",
                            "applicationamount": "%.2f" % (applicationgroupWiseTotal),
                        }
                    )
                if expenseTotal == incomeTotal:
                    balanceSheet.append(
                        {
                            "sourcesgroupname": "",
                            "sourceamount": "",
                            "appgroupname": "Miscellaneous Expenses(Asset)",
                            "applicationamount": "%.2f" % (applicationgroupWiseTotal),
                        }
                    )

                # Total of Sources and Applications
                balanceSheet.append(
                    {
                        "sourcesgroupname": "Total",
                        "sourceamount": "%.2f" % (sourcesTotal),
                        "appgroupname": "Total",
                        "applicationamount": "%.2f" % (applicationsTotal),
                    }
                )

                # Difference
                difference = abs(sourcesTotal - applicationsTotal)
                balanceSheet.append(
                    {
                        "sourcesgroupname": "Difference",
                        "sourceamount": "%.2f" % (difference),
                        "appgroupname": "",
                        "applicationamount": "",
                    }
                )
                return balanceSheet
                self.con.close()
            except:
                self.con.close()
                return {"gkstatus": enumdict["ConnectionFailed"]}

    @view_config(request_param="type=consolidatedbalancesheet", renderer="json")
    def consolidatedbalanceSheet(self):
        """
        Purpose:
        Gets the list of groups and their respective balances
        takes organisations code and end date as input parameter
        Description:
        This function is used to generate consolidated balance sheet for a given organisations and the given time period.
        This function takes orgcode and end date as the input parameters
        This function is called and type=consolidatedbalancesheet is passed to the /report url.
        orgcode is extracted from the header
        end date is extracted from the request_params
        The accountcode is extracted from the database under  groupcode for groups relevent to balance sheet (meaning all groups except income and expence groups).
        the  groupbalance will be initialized to 0.0 for each group.
        this accountcode is sent to the calculateBalance function along with financialstart, calculateTo
        the function will return the closing balance related to each account which will be later added or subtracted according to the accounting rules from the group balance
        the above statements will be running in a loop for each group.
        Later all the group balances for sources and application will be added
        the difference in the amounts of sourcetotal and applicationtotal will be found
        the function will return the gkstatus and gkresult which contains a list of dictionaries where every dictionary represents a row with two key-value pairs each representing columns
        """
        try:
            token = self.request.headers["gktoken"]
        except:
            return {"gkstatus": enumdict["UnauthorisedAccess"]}
        authDetails = authCheck(token)
        if authDetails["auth"] == False:
            return {"gkstatus": enumdict["UnauthorisedAccess"]}
        else:
            # try:
            self.con = eng.connect()
            orgcode = authDetails["orgcode"]
            orgtype = self.request.params["orgtype"]
            financialStart = self.request.params["financialStart"]
            calculateTo = self.request.params["calculateto"]
            data = self.request.json_body
            orgs = data["listoforg"]
            sbalanceSheet = []
            abalanceSheet = []
            sourcesTotal = 0.00
            applicationsTotal = 0.00
            difference = 0.00
            sourcesTotal1 = 0.00
            applicationsTotal1 = 0.00
            sbalanceSheet.append(
                {
                    "groupAccname": "Sources:",
                    "amount": "",
                    "groupAcccode": "",
                    "subgroupof": "",
                    "accountof": "",
                    "groupAccflag": "",
                    "advflag": "",
                }
            )
            capital_Corpus = ""
            if orgtype == "Profit Making":
                capital_Corpus = "Capital"
            if orgtype == "Not For Profit":
                capital_Corpus = "Corpus"
            groupWiseTotal = 0.00

            # Calculate grouptotal for group Capital/Corpus
            for i in orgs:
                orgcode = int(i)
                accountcodeData = self.con.execute(
                    "select accountcode, accountname from accounts where orgcode = %d and groupcode = (select groupcode from groupsubgroups where orgcode =%d and groupname = '%s') order by accountname;"
                    % (orgcode, orgcode, capital_Corpus)
                )
                accountCodes = accountcodeData.fetchall()
                subgroupDataRow = self.con.execute(
                    "select groupcode, groupname  from groupsubgroups where orgcode = %d and subgroupof = (select groupcode from groupsubgroups where orgcode = %d and subgroupof is null and groupname ='%s');"
                    % (orgcode, orgcode, capital_Corpus)
                )
                subgroupData = subgroupDataRow.fetchall()
                groupCode = self.con.execute(
                    "select groupcode from groupsubgroups where (orgcode=%d and groupname='%s');"
                    % (orgcode, capital_Corpus)
                )
                groupcode = groupCode.fetchone()["groupcode"]
                groupAccSubgroup = []

                for accountRow in accountCodes:
                    accountTotal = 0.00
                    adverseflag = 0
                    accountDetails = calculateBalance(
                        self.con,
                        accountRow["accountcode"],
                        financialStart,
                        financialStart,
                        calculateTo,
                    )
                    if accountDetails["baltype"] == "Cr":
                        groupWiseTotal += accountDetails["curbal"]
                        accountTotal += accountDetails["curbal"]
                    if (
                        accountDetails["baltype"] == "Dr"
                        and accountDetails["curbal"] != 0
                    ):
                        adverseflag = 1
                        accountTotal -= accountDetails["curbal"]
                        groupWiseTotal -= accountDetails["curbal"]

                for subgroup in subgroupData:
                    subgroupTotal = 0.00
                    accounts = []
                    subgroupAccDataRow = self.con.execute(
                        "select accountcode, accountname from accounts where orgcode = %d and groupcode = %d order by accountname"
                        % (orgcode, subgroup["groupcode"])
                    )
                    subgroupAccData = subgroupAccDataRow.fetchall()
                    for account in subgroupAccData:
                        accountTotal = 0.00
                        adverseflag = 0
                        accountDetails = calculateBalance(
                            self.con,
                            account["accountcode"],
                            financialStart,
                            financialStart,
                            calculateTo,
                        )
                        if accountDetails["baltype"] == "Cr":
                            subgroupTotal += accountDetails["curbal"]
                            accountTotal += accountDetails["curbal"]
                        if (
                            accountDetails["baltype"] == "Dr"
                            and accountDetails["curbal"] != 0
                        ):
                            adverseflag = 1
                            subgroupTotal -= accountDetails["curbal"]
                            accountTotal -= accountDetails["curbal"]
                        if accountDetails["curbal"] != 0:
                            dummy = 0
                            # accounts.append({"groupAccname":account["accountname"],"amount":"%.2f"%(accountTotal), "groupAcccode":account["accountcode"],"subgroupof":groupcode , "accountof":subgroup["groupcode"], "groupAccflag":2, "advflag":adverseflag})
                    groupWiseTotal += subgroupTotal
                    # groupAccSubgroup.append({"groupAccname":subgroup["groupname"],"amount":"%.2f"%(subgroupTotal), "groupAcccode":subgroup["groupcode"],"subgroupof":groupcode , "accountof":"", "groupAccflag":"", "advflag":""})
                    groupAccSubgroup += accounts
                sourcesTotal += groupWiseTotal
            sbalanceSheet.append(
                {
                    "groupAccname": capital_Corpus,
                    "amount": "%.2f" % (groupWiseTotal),
                    "groupAcccode": groupcode,
                    "subgroupof": "",
                    "accountof": "",
                    "groupAccflag": "",
                    "advflag": "",
                }
            )
            sourcesTotal1 += groupWiseTotal
            sbalanceSheet += groupAccSubgroup

            # Calculate grouptotal for group Loans(Liability)
            groupWiseTotal = 0.00
            for i in orgs:
                orgcode = int(i)
                accountcodeData = self.con.execute(
                    "select accountcode, accountname from accounts where orgcode = %d and groupcode = (select groupcode from groupsubgroups where orgcode =%d and groupname = 'Loans(Liability)') order by accountname;"
                    % (orgcode, orgcode)
                )
                accountCodes = accountcodeData.fetchall()
                subgroupDataRow = self.con.execute(
                    "select groupcode, groupname  from groupsubgroups where orgcode = %d and subgroupof = (select groupcode from groupsubgroups where orgcode = %d and subgroupof is null and groupname ='Loans(Liability)');"
                    % (orgcode, orgcode)
                )
                subgroupData = subgroupDataRow.fetchall()
                groupCode = self.con.execute(
                    "select groupcode from groupsubgroups where (orgcode=%d and groupname='Loans(Liability)');"
                    % (orgcode)
                )
                groupcode = groupCode.fetchone()["groupcode"]
                groupAccSubgroup = []

                for accountRow in accountCodes:
                    accountTotal = 0.00
                    adverseflag = 0
                    accountDetails = calculateBalance(
                        self.con,
                        accountRow["accountcode"],
                        financialStart,
                        financialStart,
                        calculateTo,
                    )
                    if accountDetails["baltype"] == "Cr":
                        groupWiseTotal += accountDetails["curbal"]
                        accountTotal += accountDetails["curbal"]
                    if (
                        accountDetails["baltype"] == "Dr"
                        and accountDetails["curbal"] != 0
                    ):
                        adverseflag = 1
                        accountTotal -= accountDetails["curbal"]
                        groupWiseTotal -= accountDetails["curbal"]
                    groupAccSubgroup.append(
                        {
                            "groupAccname": accountRow["accountname"],
                            "amount": "%.2f" % (accountTotal),
                            "groupAcccode": accountRow["accountcode"],
                            "subgroupof": "",
                            "accountof": groupcode,
                            "groupAccflag": 1,
                            "advflag": adverseflag,
                        }
                    )

                for subgroup in subgroupData:
                    subgroupTotal = 0.00
                    accounts = []
                    subgroupAccDataRow = self.con.execute(
                        "select accountcode, accountname from accounts where orgcode = %d and groupcode = %d order by accountname"
                        % (orgcode, subgroup["groupcode"])
                    )
                    subgroupAccData = subgroupAccDataRow.fetchall()
                    for account in subgroupAccData:
                        accountTotal = 0.00
                        adverseflag = 0
                        accountDetails = calculateBalance(
                            self.con,
                            account["accountcode"],
                            financialStart,
                            financialStart,
                            calculateTo,
                        )
                        if accountDetails["baltype"] == "Cr":
                            subgroupTotal += accountDetails["curbal"]
                            accountTotal += accountDetails["curbal"]
                        if (
                            accountDetails["baltype"] == "Dr"
                            and accountDetails["curbal"] != 0
                        ):
                            adverseflag = 1
                            subgroupTotal -= accountDetails["curbal"]
                            accountTotal -= accountDetails["curbal"]
                        if accountDetails["curbal"] != 0:
                            dummy = 0
                            # accounts.append({"groupAccname":account["accountname"],"amount":"%.2f"%(accountTotal), "groupAcccode":account["accountcode"],"subgroupof":groupcode , "accountof":subgroup["groupcode"], "groupAccflag":2, "advflag":adverseflag})
                    groupWiseTotal += subgroupTotal
                    # groupAccSubgroup.append({"groupAccname":subgroup["groupname"],"amount":"%.2f"%(subgroupTotal), "groupAcccode":subgroup["groupcode"],"subgroupof":groupcode , "accountof":"", "groupAccflag":"", "advflag":""})
                    groupAccSubgroup += accounts

                sourcesTotal += groupWiseTotal
            sbalanceSheet.append(
                {
                    "groupAccname": "Loans(Liability)",
                    "amount": "%.2f" % (groupWiseTotal),
                    "groupAcccode": groupcode,
                    "subgroupof": "",
                    "accountof": "",
                    "groupAccflag": "",
                    "advflag": "",
                }
            )
            sourcesTotal1 += groupWiseTotal
            sbalanceSheet += groupAccSubgroup

            # Calculate grouptotal for group Current Liabilities
            groupWiseTotal = 0.00
            for i in orgs:
                orgcode = int(i)
                accountcodeData = self.con.execute(
                    "select accountcode, accountname from accounts where orgcode = %d and groupcode = (select groupcode from groupsubgroups where orgcode =%d and groupname = 'Current Liabilities') order by accountname;"
                    % (orgcode, orgcode)
                )
                accountCodes = accountcodeData.fetchall()
                subgroupDataRow = self.con.execute(
                    "select groupcode, groupname  from groupsubgroups where orgcode = %d and subgroupof = (select groupcode from groupsubgroups where orgcode = %d and subgroupof is null and groupname ='Current Liabilities');"
                    % (orgcode, orgcode)
                )
                subgroupData = subgroupDataRow.fetchall()
                groupCode = self.con.execute(
                    "select groupcode from groupsubgroups where (orgcode=%d and groupname='Current Liabilities');"
                    % (orgcode)
                )
                groupcode = groupCode.fetchone()["groupcode"]
                groupAccSubgroup = []

                for accountRow in accountCodes:
                    accountTotal = 0.00
                    adverseflag = 0
                    accountDetails = calculateBalance(
                        self.con,
                        accountRow["accountcode"],
                        financialStart,
                        financialStart,
                        calculateTo,
                    )
                    if accountDetails["baltype"] == "Cr":
                        groupWiseTotal += accountDetails["curbal"]
                        accountTotal += accountDetails["curbal"]
                    if (
                        accountDetails["baltype"] == "Dr"
                        and accountDetails["curbal"] != 0
                    ):
                        adverseflag = 1
                        accountTotal -= accountDetails["curbal"]
                        groupWiseTotal -= accountDetails["curbal"]

                for subgroup in subgroupData:
                    subgroupTotal = 0.00
                    accounts = []
                    subgroupAccDataRow = self.con.execute(
                        "select accountcode, accountname from accounts where orgcode = %d and groupcode = %d order by accountname"
                        % (orgcode, subgroup["groupcode"])
                    )
                    subgroupAccData = subgroupAccDataRow.fetchall()
                    for account in subgroupAccData:
                        accountTotal = 0.00
                        adverseflag = 0
                        accountDetails = calculateBalance(
                            self.con,
                            account["accountcode"],
                            financialStart,
                            financialStart,
                            calculateTo,
                        )
                        if accountDetails["baltype"] == "Cr":
                            subgroupTotal += accountDetails["curbal"]
                            accountTotal += accountDetails["curbal"]
                        if (
                            accountDetails["baltype"] == "Dr"
                            and accountDetails["curbal"] != 0
                        ):
                            adverseflag = 1
                            subgroupTotal -= accountDetails["curbal"]
                            accountTotal -= accountDetails["curbal"]
                        if accountDetails["curbal"] != 0:
                            dummy = 0
                            # accounts.append({"groupAccname":account["accountname"],"amount":"%.2f"%(accountTotal), "groupAcccode":account["accountcode"],"subgroupof":groupcode , "accountof":subgroup["groupcode"], "groupAccflag":2, "advflag":adverseflag})
                    groupWiseTotal += subgroupTotal
                    # groupAccSubgroup.append({"groupAccname":subgroup["groupname"],"amount":"%.2f"%(subgroupTotal), "groupAcccode":subgroup["groupcode"],"subgroupof":groupcode , "accountof":"", "groupAccflag":"", "advflag":""})
                    groupAccSubgroup += accounts

                sourcesTotal += groupWiseTotal
            sbalanceSheet.append(
                {
                    "groupAccname": "Current Liabilities",
                    "amount": "%.2f" % (groupWiseTotal),
                    "groupAcccode": groupcode,
                    "subgroupof": "",
                    "accountof": "",
                    "groupAccflag": "",
                    "advflag": "",
                }
            )
            sourcesTotal1 += groupWiseTotal
            sbalanceSheet += groupAccSubgroup

            # Calculate grouptotal for group "Reserves"
            groupWiseTotal = 0.00
            incomeTotal = 0.00
            expenseTotal = 0.00
            for i in orgs:
                orgcode = int(i)
                accountcodeData = self.con.execute(
                    "select accountcode, accountname from accounts where orgcode = %d and groupcode = (select groupcode from groupsubgroups where orgcode =%d and groupname = 'Reserves') order by accountname;"
                    % (orgcode, orgcode)
                )
                accountCodes = accountcodeData.fetchall()
                subgroupDataRow = self.con.execute(
                    "select groupcode, groupname  from groupsubgroups where orgcode = %d and subgroupof = (select groupcode from groupsubgroups where orgcode = %d and subgroupof is null and groupname ='Reserves');"
                    % (orgcode, orgcode)
                )
                subgroupData = subgroupDataRow.fetchall()
                groupCode = self.con.execute(
                    "select groupcode from groupsubgroups where (orgcode=%d and groupname='Reserves');"
                    % (orgcode)
                )
                groupcode = groupCode.fetchone()["groupcode"]
                groupAccSubgroup = []

                for accountRow in accountCodes:
                    accountTotal = 0.00
                    adverseflag = 0
                    accountDetails = calculateBalance(
                        self.con,
                        accountRow["accountcode"],
                        financialStart,
                        financialStart,
                        calculateTo,
                    )
                    if accountDetails["baltype"] == "Cr":
                        groupWiseTotal += accountDetails["curbal"]
                        accountTotal += accountDetails["curbal"]
                    if (
                        accountDetails["baltype"] == "Dr"
                        and accountDetails["curbal"] != 0
                    ):
                        adverseflag = 1
                        accountTotal -= accountDetails["curbal"]
                        groupWiseTotal -= accountDetails["curbal"]

                for subgroup in subgroupData:
                    subgroupTotal = 0.00
                    accounts = []
                    subgroupAccDataRow = self.con.execute(
                        "select accountcode, accountname from accounts where orgcode = %d and groupcode = %d order by accountname"
                        % (orgcode, subgroup["groupcode"])
                    )
                    subgroupAccData = subgroupAccDataRow.fetchall()
                    for account in subgroupAccData:
                        accountTotal = 0.00
                        adverseflag = 0
                        accountDetails = calculateBalance(
                            self.con,
                            account["accountcode"],
                            financialStart,
                            financialStart,
                            calculateTo,
                        )
                        if accountDetails["baltype"] == "Cr":
                            subgroupTotal += accountDetails["curbal"]
                            accountTotal += accountDetails["curbal"]
                        if (
                            accountDetails["baltype"] == "Dr"
                            and accountDetails["curbal"] != 0
                        ):
                            adverseflag = 1
                            subgroupTotal -= accountDetails["curbal"]
                            accountTotal -= accountDetails["curbal"]
                        if accountDetails["curbal"] != 0:
                            dummy = 0
                            # accounts.append({"groupAccname":account["accountname"],"amount":"%.2f"%(accountTotal), "groupAcccode":account["accountcode"],"subgroupof":groupcode , "accountof":subgroup["groupcode"], "groupAccflag":2, "advflag":adverseflag})
                    groupWiseTotal += subgroupTotal
            # groupAccSubgroup.append({"groupAccname":subgroup["groupname"],"amount":"%.2f"%(subgroupTotal), "groupAcccode":subgroup["groupcode"],"subgroupof":groupcode , "accountof":"", "groupAccflag":"", "advflag":""})
            groupAccSubgroup += accounts

            # Calculate all income(Direct and Indirect Income)
            for i in orgs:
                orgcode = int(i)
                accountcodeData = self.con.execute(
                    "select accountcode from accounts where orgcode = %d and groupcode in(select groupcode from groupsubgroups where orgcode =%d and groupname in ('Direct Income','Indirect Income') or subgroupof in (select groupcode from groupsubgroups where orgcode = %d and groupname in ('Direct Income','Indirect Income')));"
                    % (orgcode, orgcode, orgcode)
                )
                accountCodes = accountcodeData.fetchall()
                for accountRow in accountCodes:
                    accountDetails = calculateBalance(
                        self.con,
                        accountRow["accountcode"],
                        financialStart,
                        financialStart,
                        calculateTo,
                    )
                    if accountDetails["baltype"] == "Cr":
                        incomeTotal += accountDetails["curbal"]
                    if accountDetails["baltype"] == "Dr":
                        incomeTotal -= accountDetails["curbal"]

            # Calculate all expense(Direct and Indirect Expense)
            for i in orgs:
                orgcode = int(i)
                accountcodeData = self.con.execute(
                    "select accountcode from accounts where orgcode = %d and groupcode in(select groupcode from groupsubgroups where orgcode =%d and groupname in ('Direct Expense','Indirect Expense') or subgroupof in (select groupcode from groupsubgroups where orgcode = %d and groupname in ('Direct Expense','Indirect Expense')));"
                    % (orgcode, orgcode, orgcode)
                )
                accountCodes = accountcodeData.fetchall()
                for accountRow in accountCodes:
                    accountDetails = calculateBalance(
                        self.con,
                        accountRow["accountcode"],
                        financialStart,
                        financialStart,
                        calculateTo,
                    )
                    if accountDetails["baltype"] == "Dr":
                        expenseTotal += accountDetails["curbal"]
                    if accountDetails["baltype"] == "Cr":
                        expenseTotal -= accountDetails["curbal"]

            # Calculate Profit/Loss for the year
            profit = 0
            if expenseTotal > incomeTotal:
                profit = expenseTotal - incomeTotal
                groupWiseTotal -= profit
                sbalanceSheet.append(
                    {
                        "groupAccname": "Reserves",
                        "amount": "%.2f" % (groupWiseTotal),
                        "groupAcccode": groupcode,
                        "subgroupof": "",
                        "accountof": "",
                        "groupAccflag": "",
                        "advflag": "",
                    }
                )
                if orgtype == "Profit Making":
                    sbalanceSheet.append(
                        {
                            "groupAccname": "Loss for the Year:",
                            "amount": "%.2f" % (profit),
                            "groupAcccode": "",
                            "subgroupof": groupcode,
                            "accountof": "",
                            "groupAccflag": 2,
                            "advflag": "",
                        }
                    )
                else:
                    sbalanceSheet.append(
                        {
                            "groupAccname": "Deficit for the Year:",
                            "amount": "%.2f" % (profit),
                            "groupAcccode": "",
                            "subgroupof": groupcode,
                            "accountof": "",
                            "groupAccflag": 2,
                            "advflag": "",
                        }
                    )

            if expenseTotal < incomeTotal:
                profit = incomeTotal - expenseTotal
                groupWiseTotal += profit
                sbalanceSheet.append(
                    {
                        "groupAccname": "Reserves",
                        "amount": "%.2f" % (groupWiseTotal),
                        "groupAcccode": groupcode,
                        "subgroupof": "",
                        "accountof": "",
                        "groupAccflag": "",
                        "advflag": "",
                    }
                )
                if orgtype == "Profit Making":
                    sbalanceSheet.append(
                        {
                            "groupAccname": "Profit for the Year:",
                            "amount": "%.2f" % (profit),
                            "groupAcccode": "",
                            "subgroupof": groupcode,
                            "accountof": "",
                            "groupAccflag": 2,
                            "advflag": "",
                        }
                    )
                else:
                    sbalanceSheet.append(
                        {
                            "groupAccname": "Surplus for the Year:",
                            "amount": "%.2f" % (profit),
                            "groupAcccode": "",
                            "subgroupof": groupcode,
                            "accountof": "",
                            "groupAccflag": 2,
                            "advflag": "",
                        }
                    )
            if expenseTotal == incomeTotal:
                sbalanceSheet.append(
                    {
                        "groupAccname": "Reserves",
                        "amount": "%.2f" % (groupWiseTotal),
                        "groupAcccode": groupcode,
                        "subgroupof": "",
                        "accountof": "",
                        "groupAccflag": "",
                        "advflag": "",
                    }
                )

            sbalanceSheet += groupAccSubgroup
            sourcesTotal += groupWiseTotal
            sourcesTotal1 += groupWiseTotal
            sbalanceSheet.append(
                {
                    "groupAccname": "Total",
                    "amount": "%.2f" % (sourcesTotal1),
                    "groupAcccode": "",
                    "subgroupof": "",
                    "accountof": "",
                    "groupAccflag": "",
                    "advflag": "",
                }
            )

            # Applications:
            abalanceSheet.append(
                {
                    "groupAccname": "Applications:",
                    "amount": "",
                    "groupAcccode": "",
                    "subgroupof": "",
                    "accountof": "",
                    "groupAccflag": "",
                    "advflag": "",
                }
            )

            # Calculate grouptotal for group "Fixed Assets"
            groupWiseTotal = 0.00
            for i in orgs:
                orgcode = int(i)
                accountcodeData = self.con.execute(
                    "select accountcode, accountname from accounts where orgcode = %d and groupcode = (select groupcode from groupsubgroups where orgcode =%d and groupname = 'Fixed Assets') order by accountname;"
                    % (orgcode, orgcode)
                )
                accountCodes = accountcodeData.fetchall()
                subgroupDataRow = self.con.execute(
                    "select groupcode, groupname  from groupsubgroups where orgcode = %d and subgroupof = (select groupcode from groupsubgroups where orgcode = %d and subgroupof is null and groupname ='Fixed Assets');"
                    % (orgcode, orgcode)
                )
                subgroupData = subgroupDataRow.fetchall()
                groupCode = self.con.execute(
                    "select groupcode from groupsubgroups where (orgcode=%d and groupname='Fixed Assets');"
                    % (orgcode)
                )
                groupcode = groupCode.fetchone()["groupcode"]
                groupAccSubgroup = []

                for accountRow in accountCodes:
                    accountTotal = 0.00
                    adverseflag = 0
                    accountDetails = calculateBalance(
                        self.con,
                        accountRow["accountcode"],
                        financialStart,
                        financialStart,
                        calculateTo,
                    )
                    if accountDetails["baltype"] == "Dr":
                        groupWiseTotal += accountDetails["curbal"]
                        accountTotal += accountDetails["curbal"]
                    if (
                        accountDetails["baltype"] == "Cr"
                        and accountDetails["curbal"] != 0
                    ):
                        adverseflag = 1
                        accountTotal -= accountDetails["curbal"]
                        groupWiseTotal -= accountDetails["curbal"]

                for subgroup in subgroupData:
                    subgroupTotal = 0.00
                    accounts = []
                    subgroupAccDataRow = self.con.execute(
                        "select accountcode, accountname from accounts where orgcode = %d and groupcode = %d order by accountname"
                        % (orgcode, subgroup["groupcode"])
                    )
                    subgroupAccData = subgroupAccDataRow.fetchall()

                    for account in subgroupAccData:
                        accountTotal = 0.00
                        adverseflag = 0
                        accountDetails = calculateBalance(
                            self.con,
                            account["accountcode"],
                            financialStart,
                            financialStart,
                            calculateTo,
                        )
                        if accountDetails["baltype"] == "Dr":
                            subgroupTotal += accountDetails["curbal"]
                            accountTotal += accountDetails["curbal"]
                        if (
                            accountDetails["baltype"] == "Cr"
                            and accountDetails["curbal"] != 0
                        ):
                            adverseflag = 1
                            subgroupTotal -= accountDetails["curbal"]
                            accountTotal -= accountDetails["curbal"]
                        if accountDetails["curbal"] != 0:
                            dummy = 0
                            # accounts.append({"groupAccname":account["accountname"],"amount":"%.2f"%(accountTotal), "groupAcccode":account["accountcode"],"subgroupof":groupcode , "accountof":subgroup["groupcode"], "groupAccflag":2,"advflag":adverseflag})
                    groupWiseTotal += subgroupTotal
                    # groupAccSubgroup.append({"groupAccname":subgroup["groupname"],"amount":"%.2f"%(subgroupTotal), "groupAcccode":subgroup["groupcode"],"subgroupof":groupcode , "accountof":"", "groupAccflag":"","advflag":""})
                    groupAccSubgroup += accounts

                applicationsTotal += groupWiseTotal
            abalanceSheet.append(
                {
                    "groupAccname": "Fixed Assets",
                    "amount": "%.2f" % (groupWiseTotal),
                    "groupAcccode": groupcode,
                    "subgroupof": "",
                    "accountof": "",
                    "groupAccflag": "",
                    "advflag": "",
                }
            )
            applicationsTotal1 += groupWiseTotal
            abalanceSheet += groupAccSubgroup

            # Calculate grouptotal for group "Investments"
            groupWiseTotal = 0.00
            for i in orgs:
                orgcode = int(i)
                accountcodeData = self.con.execute(
                    "select accountcode, accountname from accounts where orgcode = %d and groupcode = (select groupcode from groupsubgroups where orgcode =%d and groupname = 'Investments') order by accountname;"
                    % (orgcode, orgcode)
                )
                accountCodes = accountcodeData.fetchall()
                subgroupDataRow = self.con.execute(
                    "select groupcode, groupname  from groupsubgroups where orgcode = %d and subgroupof = (select groupcode from groupsubgroups where orgcode = %d and subgroupof is null and groupname ='Investments');"
                    % (orgcode, orgcode)
                )
                subgroupData = subgroupDataRow.fetchall()
                groupCode = self.con.execute(
                    "select groupcode from groupsubgroups where (orgcode=%d and groupname='Investments');"
                    % (orgcode)
                )
                groupcode = groupCode.fetchone()["groupcode"]
                groupAccSubgroup = []

                for accountRow in accountCodes:
                    accountTotal = 0.00
                    adverseflag = 0
                    accountDetails = calculateBalance(
                        self.con,
                        accountRow["accountcode"],
                        financialStart,
                        financialStart,
                        calculateTo,
                    )
                    if accountDetails["baltype"] == "Dr":
                        groupWiseTotal += accountDetails["curbal"]
                        accountTotal += accountDetails["curbal"]
                    if (
                        accountDetails["baltype"] == "Cr"
                        and accountDetails["curbal"] != 0
                    ):
                        adverseflag = 1
                        accountTotal -= accountDetails["curbal"]
                        groupWiseTotal -= accountDetails["curbal"]

                for subgroup in subgroupData:
                    subgroupTotal = 0.00
                    accounts = []
                    subgroupAccDataRow = self.con.execute(
                        "select accountcode, accountname from accounts where orgcode = %d and groupcode = %d order by accountname"
                        % (orgcode, subgroup["groupcode"])
                    )
                    subgroupAccData = subgroupAccDataRow.fetchall()
                    for account in subgroupAccData:
                        accountTotal = 0.00
                        adverseflag = 0
                        accountDetails = calculateBalance(
                            self.con,
                            account["accountcode"],
                            financialStart,
                            financialStart,
                            calculateTo,
                        )
                        if accountDetails["baltype"] == "Dr":
                            subgroupTotal += accountDetails["curbal"]
                            accountTotal += accountDetails["curbal"]
                        if (
                            accountDetails["baltype"] == "Cr"
                            and accountDetails["curbal"] != 0
                        ):
                            adverseflag = 1
                            subgroupTotal -= accountDetails["curbal"]
                            accountTotal -= accountDetails["curbal"]
                        if accountDetails["curbal"] != 0:
                            dummy = 0
                            # accounts.append({"groupAccname":account["accountname"],"amount":"%.2f"%(accountTotal), "groupAcccode":account["accountcode"],"subgroupof":groupcode , "accountof":subgroup["groupcode"], "groupAccflag":2, "advflag":adverseflag})
                    groupWiseTotal += subgroupTotal
                    # groupAccSubgroup.append({"groupAccname":subgroup["groupname"],"amount":"%.2f"%(subgroupTotal), "groupAcccode":subgroup["groupcode"],"subgroupof":groupcode , "accountof":"", "groupAccflag":"","advflag":""})
                    groupAccSubgroup += accounts

                applicationsTotal += groupWiseTotal
            abalanceSheet.append(
                {
                    "groupAccname": "Investments",
                    "amount": "%.2f" % (groupWiseTotal),
                    "groupAcccode": groupcode,
                    "subgroupof": "",
                    "accountof": "",
                    "groupAccflag": "",
                    "advflag": "",
                }
            )
            applicationsTotal1 += groupWiseTotal
            abalanceSheet += groupAccSubgroup

            # Calculate grouptotal for group "Current Assets"
            groupWiseTotal = 0.00
            for i in orgs:
                orgcode = int(i)
                accountcodeData = self.con.execute(
                    "select accountcode, accountname from accounts where orgcode = %d and groupcode = (select groupcode from groupsubgroups where orgcode =%d and groupname = 'Current Assets') order by accountname;"
                    % (orgcode, orgcode)
                )
                accountCodes = accountcodeData.fetchall()
                subgroupDataRow = self.con.execute(
                    "select groupcode, groupname  from groupsubgroups where orgcode = %d and subgroupof = (select groupcode from groupsubgroups where orgcode = %d and subgroupof is null and groupname ='Current Assets');"
                    % (orgcode, orgcode)
                )
                subgroupData = subgroupDataRow.fetchall()
                groupCode = self.con.execute(
                    "select groupcode from groupsubgroups where (orgcode=%d and groupname='Current Assets');"
                    % (orgcode)
                )
                groupcode = groupCode.fetchone()["groupcode"]
                groupAccSubgroup = []

                for accountRow in accountCodes:
                    accountTotal = 0.00
                    adverseflag = 0
                    accountDetails = calculateBalance(
                        self.con,
                        accountRow["accountcode"],
                        financialStart,
                        financialStart,
                        calculateTo,
                    )
                    if accountDetails["baltype"] == "Dr":
                        groupWiseTotal += accountDetails["curbal"]
                        accountTotal += accountDetails["curbal"]
                    if (
                        accountDetails["baltype"] == "Cr"
                        and accountDetails["curbal"] != 0
                    ):
                        adverseflag = 1
                        accountTotal -= accountDetails["curbal"]
                        groupWiseTotal -= accountDetails["curbal"]

                for subgroup in subgroupData:
                    subgroupTotal = 0.00
                    accounts = []
                    subgroupAccDataRow = self.con.execute(
                        "select accountcode, accountname from accounts where orgcode = %d and groupcode = %d order by accountname"
                        % (orgcode, subgroup["groupcode"])
                    )
                    subgroupAccData = subgroupAccDataRow.fetchall()
                    for account in subgroupAccData:
                        accountTotal = 0.00
                        adverseflag = 0
                        accountDetails = calculateBalance(
                            self.con,
                            account["accountcode"],
                            financialStart,
                            financialStart,
                            calculateTo,
                        )
                        if accountDetails["baltype"] == "Dr":
                            subgroupTotal += accountDetails["curbal"]
                            accountTotal += accountDetails["curbal"]
                        if (
                            accountDetails["baltype"] == "Cr"
                            and accountDetails["curbal"] != 0
                        ):
                            adverseflag = 1
                            subgroupTotal -= accountDetails["curbal"]
                            accountTotal -= accountDetails["curbal"]
                        if accountDetails["curbal"] != 0:
                            dummy = 0
                            # accounts.append({"groupAccname":account["accountname"],"amount":"%.2f"%(accountTotal), "groupAcccode":account["accountcode"],"subgroupof":groupcode , "accountof":subgroup["groupcode"], "groupAccflag":2, "advflag":adverseflag})
                    groupWiseTotal += subgroupTotal
                    # groupAccSubgroup.append({"groupAccname":subgroup["groupname"],"amount":"%.2f"%(subgroupTotal), "groupAcccode":subgroup["groupcode"],"subgroupof":groupcode , "accountof":"", "groupAccflag":"","advflag":""})
                    groupAccSubgroup += accounts

                applicationsTotal += groupWiseTotal
            abalanceSheet.append(
                {
                    "groupAccname": "Current Assets",
                    "amount": "%.2f" % (groupWiseTotal),
                    "groupAcccode": groupcode,
                    "subgroupof": "",
                    "accountof": "",
                    "groupAccflag": "",
                    "advflag": "",
                }
            )
            applicationsTotal1 += groupWiseTotal
            abalanceSheet += groupAccSubgroup

            # Calculate grouptotal for group Loans(Asset)
            groupWiseTotal = 0.00
            for i in orgs:
                orgcode = int(i)
                accountcodeData = self.con.execute(
                    "select accountcode, accountname from accounts where orgcode = %d and groupcode = (select groupcode from groupsubgroups where orgcode =%d and groupname = 'Loans(Asset)') order by accountname;"
                    % (orgcode, orgcode)
                )
                accountCodes = accountcodeData.fetchall()
                subgroupDataRow = self.con.execute(
                    "select groupcode, groupname  from groupsubgroups where orgcode = %d and subgroupof = (select groupcode from groupsubgroups where orgcode = %d and subgroupof is null and groupname ='Loans(Asset)');"
                    % (orgcode, orgcode)
                )
                subgroupData = subgroupDataRow.fetchall()
                groupCode = self.con.execute(
                    "select groupcode from groupsubgroups where (orgcode=%d and groupname='Loans(Asset)');"
                    % (orgcode)
                )
                groupcode = groupCode.fetchone()["groupcode"]
                groupAccSubgroup = []

                for accountRow in accountCodes:
                    accountTotal = 0.00
                    adverseflag = 0
                    accountDetails = calculateBalance(
                        self.con,
                        accountRow["accountcode"],
                        financialStart,
                        financialStart,
                        calculateTo,
                    )
                    if accountDetails["baltype"] == "Dr":
                        groupWiseTotal += accountDetails["curbal"]
                        accountTotal += accountDetails["curbal"]
                    if (
                        accountDetails["baltype"] == "Cr"
                        and accountDetails["curbal"] != 0
                    ):
                        adverseflag = 1
                        accountTotal -= accountDetails["curbal"]
                        groupWiseTotal -= accountDetails["curbal"]

                for subgroup in subgroupData:
                    subgroupTotal = 0.00
                    accounts = []
                    subgroupAccDataRow = self.con.execute(
                        "select accountcode, accountname from accounts where orgcode = %d and groupcode = %d order by accountname"
                        % (orgcode, subgroup["groupcode"])
                    )
                    subgroupAccData = subgroupAccDataRow.fetchall()
                    for account in subgroupAccData:
                        accountTotal = 0.00
                        adverseflag = 0
                        accountDetails = calculateBalance(
                            self.con,
                            account["accountcode"],
                            financialStart,
                            financialStart,
                            calculateTo,
                        )
                        if accountDetails["baltype"] == "Dr":
                            subgroupTotal += accountDetails["curbal"]
                            accountTotal += accountDetails["curbal"]
                        if (
                            accountDetails["baltype"] == "Cr"
                            and accountDetails["curbal"] != 0
                        ):
                            adverseflag = 1
                            subgroupTotal -= accountDetails["curbal"]
                            accountTotal -= accountDetails["curbal"]
                        if accountDetails["curbal"] != 0:
                            dummy = 0
                            # accounts.append({"groupAccname":account["accountname"],"amount":"%.2f"%(accountTotal), "groupAcccode":account["accountcode"],"subgroupof":groupcode , "accountof":subgroup["groupcode"], "groupAccflag":2, "advflag":adverseflag})
                    groupWiseTotal += subgroupTotal
                    # groupAccSubgroup.append({"groupAccname":subgroup["groupname"],"amount":"%.2f"%(subgroupTotal), "groupAcccode":subgroup["groupcode"],"subgroupof":groupcode , "accountof":"", "groupAccflag":"", "advflag":""})
                    groupAccSubgroup += accounts

                applicationsTotal += groupWiseTotal
            abalanceSheet.append(
                {
                    "groupAccname": "Loans(Asset)",
                    "amount": "%.2f" % (groupWiseTotal),
                    "groupAcccode": groupcode,
                    "subgroupof": "",
                    "accountof": "",
                    "groupAccflag": "",
                    "advflag": "",
                }
            )
            applicationsTotal1 += groupWiseTotal
            abalanceSheet += groupAccSubgroup

            if orgtype == "Profit Making":
                # Calculate grouptotal for group "Miscellaneous Expenses(Asset)"
                groupWiseTotal = 0.00
                for i in orgs:
                    orgcode = int(i)
                    accountcodeData = self.con.execute(
                        "select accountcode, accountname from accounts where orgcode = %d and groupcode = (select groupcode from groupsubgroups where orgcode =%d and groupname = 'Miscellaneous Expenses(Asset)') order by accountname;"
                        % (orgcode, orgcode)
                    )
                    accountCodes = accountcodeData.fetchall()
                    subgroupDataRow = self.con.execute(
                        "select groupcode, groupname  from groupsubgroups where orgcode = %d and subgroupof = (select groupcode from groupsubgroups where orgcode = %d and subgroupof is null and groupname ='Miscellaneous Expenses(Asset)');"
                        % (orgcode, orgcode)
                    )
                    subgroupData = subgroupDataRow.fetchall()
                    groupCode = self.con.execute(
                        "select groupcode from groupsubgroups where (orgcode=%d and groupname='Miscellaneous Expenses(Asset)');"
                        % (orgcode)
                    )
                    groupcode = groupCode.fetchone()["groupcode"]
                    groupAccSubgroup = []

                    for accountRow in accountCodes:
                        accountTotal = 0.00
                        adverseflag = 0
                        accountDetails = calculateBalance(
                            self.con,
                            accountRow["accountcode"],
                            financialStart,
                            financialStart,
                            calculateTo,
                        )
                        if accountDetails["baltype"] == "Dr":
                            groupWiseTotal += accountDetails["curbal"]
                            accountTotal += accountDetails["curbal"]
                        if (
                            accountDetails["baltype"] == "Cr"
                            and accountDetails["curbal"] != 0
                        ):
                            adverseflag = 1
                            accountTotal -= accountDetails["curbal"]
                            groupWiseTotal -= accountDetails["curbal"]

                    for subgroup in subgroupData:
                        subgroupTotal = 0.00
                        accounts = []
                        subgroupAccDataRow = self.con.execute(
                            "select accountcode, accountname from accounts where orgcode = %d and groupcode = %d order by accountname"
                            % (orgcode, subgroup["groupcode"])
                        )
                        subgroupAccData = subgroupAccDataRow.fetchall()
                        for account in subgroupAccData:
                            accountTotal = 0.00
                            adverseflag = 0
                            accountDetails = calculateBalance(
                                self.con,
                                account["accountcode"],
                                financialStart,
                                financialStart,
                                calculateTo,
                            )
                            if accountDetails["baltype"] == "Dr":
                                subgroupTotal += accountDetails["curbal"]
                                accountTotal += accountDetails["curbal"]
                            if (
                                accountDetails["baltype"] == "Cr"
                                and accountDetails["curbal"] != 0
                            ):
                                adverseflag = 1
                                subgroupTotal -= accountDetails["curbal"]
                                accountTotal -= accountDetails["curbal"]
                            if accountDetails["curbal"] != 0:
                                dummy = 0
                                # accounts.append({"groupAccname":account["accountname"],"amount":"%.2f"%(accountTotal), "groupAcccode":account["accountcode"],"subgroupof":groupcode , "accountof":subgroup["groupcode"], "groupAccflag":2, "advflag": adverseflag})
                        groupWiseTotal += subgroupTotal
                        # groupAccSubgroup.append({"groupAccname":subgroup["groupname"],"amount":"%.2f"%(subgroupTotal), "groupAcccode":subgroup["groupcode"],"subgroupof":groupcode , "accountof":"", "groupAccflag":"","advflag":""})
                        groupAccSubgroup += accounts

                    applicationsTotal += groupWiseTotal
                abalanceSheet.append(
                    {
                        "groupAccname": "Miscellaneous Expenses(Asset)",
                        "amount": "%.2f" % (groupWiseTotal),
                        "groupAcccode": groupcode,
                        "subgroupof": "",
                        "accountof": "",
                        "groupAccflag": "",
                        "advflag": "",
                    }
                )
                applicationsTotal1 += groupWiseTotal
                abalanceSheet += groupAccSubgroup

                abalanceSheet.append(
                    {
                        "groupAccname": "Total",
                        "amount": "%.2f" % (applicationsTotal1),
                        "groupAcccode": "",
                        "subgroupof": "",
                        "accountof": "",
                        "groupAccflag": "",
                        "advflag": "",
                    }
                )

            self.con.close()
            return {
                "gkstatus": enumdict["Success"],
                "gkresult": {"leftlist": sbalanceSheet, "rightlist": abalanceSheet},
            }
