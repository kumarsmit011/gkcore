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
"Rupali Badgujar" <rupalibadgujar1234@gmail.com>
'Prajkta Patkar' <prajkta@riseup.net>
"Abhijith Balan" <abhijithb21@openmailbox.org>
"""
from gkcore import eng, enumdict
from gkcore.utils import authCheck, getUserRole
from gkcore.views.dashboard.services import (
    amountwiseinvoice,
    cashbankbalance,
    datewiseinvoice,
    delchalcountbymonth,
    get_invoice_monthly_balance,
    group_accounts_by_name_balance,
    stockonhanddashboard,
    topfivecustsup,
    topfiveprodsev,
)
from sqlalchemy import and_, or_
from sqlalchemy.sql import select
from sqlalchemy.engine.base import Connection
from sqlalchemy.sql.expression import text
from pyramid.request import Request
from pyramid.view import view_defaults, view_config
from gkcore.models.meta import gk_api
from gkcore.models.gkdb import (
    organisation,
    groupsubgroups,
    accounts,
)
from datetime import datetime
from gkcore.views.reports.helpers.balance import calculateBalance, get_groupwise_accounts_balances


@view_defaults(route_name="dashboard")
class api_dashboard(object):
    def __init__(self, request):
        self.request = Request
        self.request = request
        self.con = Connection
        print("dashboard initialize")

    # This function is use to send user wise data for dashboard divs
    @view_config(
        request_method="GET", renderer="json", request_param="type=dashboarddata"
    )
    def dashboarddata(self):
        try:
            token = self.request.headers["gktoken"]
        except:
            return {"gkstatus": enumdict["UnauthorisedAccess"]}
        authDetails = authCheck(token)
        if authDetails["auth"] == False:
            return {"gkstatus": enumdict["UnauthorisedAccess"]}
        else:
            with eng.connect() as con:
                userinfo = getUserRole(authDetails["userid"], authDetails["orgcode"])
                userrole: int = userinfo["gkresult"]["userrole"]
                orgcode = authDetails["orgcode"]
                monthly_balance = {
                    "purchase": get_invoice_monthly_balance(9, orgcode),
                    "sale": get_invoice_monthly_balance(15, orgcode),
                }
                org_details = con.execute(
                    select(
                        [
                            organisation.c.orgaddr,
                            organisation.c.orgpincode,
                        ]
                    )
                    .where(
                        organisation.c.orgcode == orgcode
                    )
                ).fetchone()
                org_contact_list = []
                if org_details["orgaddr"]:
                    org_contact_list.append(org_details["orgaddr"])
                if org_details["orgpincode"]:
                    org_contact_list.append(org_details["orgpincode"])
                org_contact = ", ".join(org_contact_list)
                # for admin & manager
                if userrole == -1 or userrole == 0:
                    amountwiise_purchaseinv = amountwiseinvoice(9, orgcode)
                    datewise_purchaseinv = datewiseinvoice(9, orgcode)
                    amountwiise_saleinv = amountwiseinvoice(15, orgcode)
                    datewise_saleinv = datewiseinvoice(15, orgcode)
                    sup_data = topfivecustsup(con, 9, orgcode)
                    cust_data = topfivecustsup(con, 15, orgcode)
                    mostbought_prodsev = topfiveprodsev(orgcode)
                    stockonhanddata = stockonhanddashboard(orgcode)
                    balancedata = cashbankbalance(orgcode)
                    return {
                        "gkstatus": enumdict["Success"],
                        "userrole": userrole,
                        "gkresult": {
                            "amtwisepurinv": amountwiise_purchaseinv[
                                "fiveInvoiceslistdata"
                            ],
                            "datewisepurinv": datewise_purchaseinv[
                                "fiveInvoiceslistdata"
                            ],
                            "amtwisesaleinv": amountwiise_saleinv[
                                "fiveInvoiceslistdata"
                            ],
                            "datewisesaleinv": datewise_saleinv["fiveInvoiceslistdata"],
                            "monthly_balance": monthly_balance,
                            "topfivecustlist": cust_data["topfivecustdetails"],
                            "topfivesuplist": sup_data["topfivecustdetails"],
                            "mostboughtprodsev": mostbought_prodsev["prodinfolist"],
                            "stockonhanddata": stockonhanddata,
                            "balancedata": balancedata["balancedata"],
                            "contact": org_contact,
                        },
                    }
                if userrole == 1:
                    amountwiise_purchaseinv = amountwiseinvoice(9, orgcode)
                    datewise_purchaseinv = datewiseinvoice(9, orgcode)
                    amountwiise_saleinv = amountwiseinvoice(15, orgcode)
                    datewise_saleinv = datewiseinvoice(15, orgcode)
                    delchal_out = delchalcountbymonth(15, orgcode)
                    delchal_in = delchalcountbymonth(9, orgcode)
                    sup_data = topfivecustsup(con, 9, orgcode)
                    cust_data = topfivecustsup(con, 15, orgcode)
                    mostbought_prodsev = topfiveprodsev(orgcode)
                    stockonhanddata = stockonhanddashboard(orgcode)
                    balancedata = cashbankbalance(orgcode)
                    return {
                        "gkstatus": enumdict["Success"],
                        "userrole": userrole,
                        "gkresult": {
                            "amtwisepurinv": amountwiise_purchaseinv[
                                "fiveInvoiceslistdata"
                            ],
                            "datewisepurinv": datewise_purchaseinv[
                                "fiveInvoiceslistdata"
                            ],
                            "amtwisesaleinv": amountwiise_saleinv[
                                "fiveInvoiceslistdata"
                            ],
                            "datewisesaleinv": datewise_saleinv["fiveInvoiceslistdata"],
                            "monthly_balance": monthly_balance,
                            "delchalout": delchal_out["totalamount"],
                            "delchalin": delchal_in["totalamount"],
                            "topfivesuplist": sup_data["topfivecustdetails"],
                            "topfivecustlist": cust_data["topfivecustdetails"],
                            "mostboughtprodsev": mostbought_prodsev["prodinfolist"],
                            "stockonhanddata": stockonhanddata,
                            "balancedata": balancedata["balancedata"],
                            "contact": org_contact,
                        },
                    }
                if userrole == 2:
                    delchal_out = delchalcountbymonth(15, orgcode)
                    delchal_in = delchalcountbymonth(9, orgcode)
                    return {
                        "gkstatus": enumdict["Success"],
                        "userrole": userrole,
                        "gkresult": {
                            "monthly_balance": monthly_balance,
                            "delchalout": delchal_out["totalamount"],
                            "delchalin": delchal_in["totalamount"],
                            "contact": org_contact,
                        },
                    }
                if userrole == 3:
                    delchal_out = delchalcountbymonth(15, orgcode)
                    delchal_in = delchalcountbymonth(9, orgcode)
                    return {
                        "gkstatus": enumdict["Success"],
                        "userrole": userrole,
                        "gkresult": {
                            "delchalout": delchal_out["totalamount"],
                            "delchalin": delchal_in["totalamount"],
                            "contact": org_contact,
                        },
                    }


    # this function use to show transfer note count by month at dashbord in bar chart
    @view_config(
        request_method="GET",
        renderer="json",
        request_param="type=transfernotecountbymonth",
    )
    def transferNoteCountbyMonth(self):
        try:
            token = self.request.headers["gktoken"]
        except:
            return {"gkstatus": enumdict["UnauthorisedAccess"]}
        authDetails = authCheck(token)
        if authDetails["auth"] == False:
            return {"gkstatus": enumdict["UnauthorisedAccess"]}
        else:
            try:
                goid = self.request.params["goid"]
                self.con = eng.connect()
                # this is to fetch startdate and enddate
                startenddate = self.con.execute(
                    select([organisation.c.yearstart, organisation.c.yearend]).where(
                        organisation.c.orgcode == authDetails["orgcode"]
                    )
                )
                startenddateprint = startenddate.fetchone()
                # this is to fetch in transfer note count month wise
                monthlysortindata = self.con.execute(
                    text("select extract(month from stockdate) as month, sum(qty) as count from stock where stockdate BETWEEN ':yearstart' AND ':yearend' and orgcode=:orgcode and goid=:goid and dcinvtnflag=20 and inout=9 group by month order by month"),
                    yearstart = datetime.strftime(startenddateprint["yearstart"], "%Y-%m-%d"),
                    yearend = datetime.strftime(startenddateprint["yearend"], "%Y-%m-%d"),
                    orgcode = authDetails["orgcode"],
                    goid = goid,
                )
                monthlysortindataset = monthlysortindata.fetchall()

                # this is to fetch out transfer note count month wise
                monthlysortoutdata = self.con.execute(
                    text("select extract(month from stockdate) as month, sum(qty) as count from stock where stockdate BETWEEN ':yearstart' AND ':yearend' and orgcode=:orgcode and goid=:goid and dcinvtnflag=20 and inout=15 group by month order by month"),
                    yearstart = datetime.strftime(startenddateprint["yearstart"], "%Y-%m-%d"),
                    yearend = datetime.strftime(startenddateprint["yearend"], "%Y-%m-%d"),
                    orgcode = authDetails["orgcode"],
                    goid = goid,
                )
                monthlysortoutdataset = monthlysortoutdata.fetchall()
                # this is use to send 0 if month have 0 invoice count
                innotecount = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
                outnotecount = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
                for count in monthlysortindataset:
                    innotecount[int(count["month"]) - 1] = "%.2f" % count["count"]
                for count in monthlysortoutdataset:
                    outnotecount[int(count["month"]) - 1] = "%.2f" % count["count"]
                return {
                    "gkstatus": enumdict["Success"],
                    "innotecount": innotecount,
                    "outnotecount": outnotecount,
                }
                self.con.close()
            except Exception as e:
                print(e)
                return {"gkstatus": enumdict["ConnectionFailed"]}
                self.con.close()

    # this function use to godwn name assign to godown incharge
    @view_config(request_method="GET", renderer="json", request_param="type=godowndesc")
    def godowndesc(self):
        try:
            token = self.request.headers["gktoken"]
        except:
            return {"gkstatus": enumdict["UnauthorisedAccess"]}
        authDetails = authCheck(token)
        if authDetails["auth"] == False:
            return {"gkstatus": enumdict["UnauthorisedAccess"]}
        else:
            try:
                userid = authDetails["userid"]
                orgcode = authDetails["orgcode"]
                self.con = eng.connect()
                godownid = self.con.execute(
                    "select goid from usergodown where orgcode=%d and userid=%d"
                    % (authDetails["orgcode"], authDetails["userid"])
                )
                godownidresult = godownid.fetchall()
                goname = []
                for goid in godownidresult:
                    godownname = self.con.execute(
                        "select goname as goname from godown where goid =%d and orgcode=%d"
                        % (goid["goid"], authDetails["orgcode"])
                    )
                    godownnameresult = godownname.fetchone()
                    goname.append({"goid": goid["goid"], "goname": godownnameresult[0]})
                return {"gkstatus": enumdict["Success"], "goname": goname}
                self.con.close()
            except:
                return {"gkstatus": enumdict["ConnectionFailed"]}
                self.con.close()
            finally:
                self.con.close()

    # this fuction returns bank and cash sub account balance
    @view_config(
        request_method="GET", renderer="json", request_param="type=cashbankaccountdata"
    )
    def cashbankaccountdata(self):
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
                # below query is fetch account code and name for bank account
                accountcodebank = self.con.execute(
                    "select accountcode as accountcode, accountname as accountname from accounts where groupcode = (select groupcode from groupsubgroups where groupname = 'Bank' and orgcode=%d) and orgcode =%d"
                    % (orgcode, orgcode)
                )
                accountCodeBank = accountcodebank.fetchall()
                # below query is fetch account code and name for cash account
                accountcodecash = self.con.execute(
                    "select accountcode as accountcode, accountname as accountname from accounts where groupcode = (select groupcode from groupsubgroups where groupname = 'Cash' and orgcode=%d) and orgcode =%d"
                    % (orgcode, orgcode)
                )
                accountCodeCash = accountcodecash.fetchall()

                # below query is fetch finantial yearstart and yearend date
                financialstart = self.con.execute(
                    "select yearstart as financialstart, yearend as financialend from organisation where orgcode=%d"
                    % orgcode
                )
                financialStartresult = financialstart.fetchone()
                financialStart = datetime.strftime(
                    financialStartresult["financialstart"], "%Y-%m-%d"
                )
                financialEnd = datetime.strftime(
                    financialStartresult["financialend"], "%Y-%m-%d"
                )
                bankbalance = 0.00
                cashbalance = 0.00
                bankaccdata = []
                cashaccdata = []
                # below code give calculate balance for bank account
                for bankbal in accountCodeBank:
                    bankbalancedata = {}
                    calbaldata = calculateBalance(
                        self.con,
                        bankbal["accountcode"],
                        str(financialStart),
                        str(financialStart),
                        str(financialEnd),
                    )
                    bankbalancedata["bankbalance"] = "%.2f" % calbaldata["curbal"]
                    bankbalancedata["bankaccname"] = bankbal["accountname"]
                    bankbalancedata["baltype"] = calbaldata["baltype"]
                    bankaccdata.append(bankbalancedata)
                # below code give calculate balance for cash account
                for cashbal in accountCodeCash:
                    cashbalancedata = {}
                    calbaldata = calculateBalance(
                        self.con,
                        cashbal["accountcode"],
                        str(financialStart),
                        str(financialStart),
                        str(financialEnd),
                    )
                    cashbalancedata["cashbalance"] = "%.2f" % calbaldata["curbal"]
                    cashbalancedata["cashaccname"] = cashbal["accountname"]
                    cashbalancedata["baltype"] = calbaldata["baltype"]
                    cashaccdata.append(cashbalancedata)
                self.con.close()
                return {
                    "gkstatus": enumdict["Success"],
                    "bankaccdata": bankaccdata,
                    "cashaccdata": cashaccdata,
                }
            except:
                self.con.close()
                return {"gkstatus": enumdict["ConnectionFailed"]}
            finally:
                self.con.close()

    @view_config(
        request_method="GET", renderer="json", request_param="type=profit-loss"
    )
    def profit_loss_report(self):
        """Profit Loss Report Chat data for given date range

        `params`

        calculatefrom: string
        calculateto: string
        """
        try:
            token = self.request.headers["gktoken"]
        except:
            return {"gkstatus": enumdict["UnauthorisedAccess"]}
        auth_details = authCheck(token)
        if auth_details["auth"] == False:
            return {"gkstatus": enumdict["UnauthorisedAccess"]}

        with eng.connect() as con:
            orgcode = auth_details["orgcode"]
            calculate_from = self.request.params["calculatefrom"]
            calculate_to = self.request.params["calculateto"]

            direct_expense = get_groupwise_accounts_balances(
                con, orgcode, "Direct Expense", calculate_from, calculate_to
            )[1]
            direct_income = get_groupwise_accounts_balances(
                con, orgcode, "Direct Income", calculate_from, calculate_to
            )[1]
            indirect_expense = get_groupwise_accounts_balances(
                con, orgcode, "Indirect Expense", calculate_from, calculate_to
            )[1]
            indirect_income = get_groupwise_accounts_balances(
                con, orgcode, "Indirect Income", calculate_from, calculate_to
            )[1]

            return {
                "gkstatus": enumdict["Success"],
                "gkresult": {
                    "direct_income": direct_income,
                    "indirect_income": indirect_income,
                    "direct_expense": direct_expense,
                    "indirect_expense": indirect_expense,
                },
            }


    @view_config(
        route_name="dashboard",
        request_param="type=balancesheet",
        renderer="json",
    )
    def balance_sheet_report(self):
        """Profit Loss Report Chat data for given date range

        `params`

        calculatefrom: string
        calculateto: string
        """
        calculateto = self.request.params["calculateto"]
        calculatefrom = self.request.params["calculatefrom"]
        header = {"gktoken": self.request.headers["gktoken"]}
        result = gk_api(
            url="/reports/balance-sheet?calculateto=%s&baltype=1&calculatefrom=%s"
            % (calculateto, calculatefrom),
            header=header,
            request=self.request,
        )
        data1 = []
        data2 = []
        for content in result["gkresult"]["rightlist"]:
            if content["groupAccname"] == "Total":
                data1.append(content["amount"])
        for content in result["gkresult"]["leftlist"]:
            count = 0
            if content["groupAccname"] == "Total":
                count = count + 1
                data2.append(content["amount"])
                if count == 2:
                    data1.append(data2[1])
                else:
                    data1.append(data2[0])
        return {"gkstatus": result["gkstatus"], "gkresult": data1}


    @view_config(
        request_method="GET", renderer="json_extended", request_param="type=account_balances"
    )
    def account_balances(self):
        """This will give response with two lists, one of account name and
        another with account balances. The account and balance that has
        matching indexs will be related.

        This API will require "group" parameter, which will accept "cash_accounts",
        "assets" and "liabilities".
        """
        try:
            token = self.request.headers["gktoken"]
        except:
            return {"gkstatus": enumdict["UnauthorisedAccess"]}
        auth_details = authCheck(token)
        if auth_details["auth"] == False:
            return {"gkstatus": enumdict["UnauthorisedAccess"]}
        with eng.connect() as con:
            account_group = self.request.params["group"]
            groupname_accounts_map = {
                "cash_accounts": ["Cash", "Bank", "Secured", "Unsecured"],
                "assets": ["Current Assets"],
                "liabilities": ["Current Liabilities"],
            }
            group_names = groupname_accounts_map[account_group]

            group_list = con.execute(
                select(
                    [groupsubgroups.c.groupcode, groupsubgroups.c.groupname]
                )
                .where(groupsubgroups.c.groupname.in_(group_names))
            )
            group_codes = [group["groupcode"] for group in group_list.fetchall()]

            group_subgroup_list = con.execute(
                select(
                    [groupsubgroups.c.groupcode, groupsubgroups.c.groupname]
                )
                .where(
                    or_(
                        groupsubgroups.c.subgroupof.in_(group_codes),
                        groupsubgroups.c.groupcode.in_(group_codes),
                    )
                )
            )

            group_subgroup_codes = [
                group["groupcode"] for group in group_subgroup_list.fetchall()
            ]

            cash_accounts = con.execute(
                select(
                    [
                        accounts.c.accountcode,
                        accounts.c.accountname,
                        accounts.c.openingbal,
                        accounts.c.orgcode,
                    ]
                )
                .where(
                    and_(
                        accounts.c.orgcode == auth_details["orgcode"],
                        accounts.c.groupcode.in_(group_subgroup_codes),
                    )
                )
            )
            names, balances = group_accounts_by_name_balance(con, cash_accounts)
            return {
                "gkstatus": enumdict["Success"],
                "gkresult": {
                    "account_names": names,
                    "account_balances": balances,
                }
            }
