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
"Navin Karkera" <navin@dff.org.in>
'Prajkta Patkar'<prajkta@riseup.net>
"""

from gkcore import eng, enumdict
from gkcore.utils import authCheck, gk_log
from gkcore.views.reports.helpers.stock import (
    stockonhandfun,
    godownwise_stock_on_hand,
    calculateStockValue,
)
from gkcore.views.reports.helpers.balance import calculateBalance
from gkcore.models.gkdb import (
    vouchers,
    accounts,
    groupsubgroups,
    organisation,
    # users,
    customerandsupplier,
    product,
    categorysubcategories,
    categoryspecs,
    tax,
    godown,
    goprod,
    usergodown,
)
from sqlalchemy.sql import select
from sqlalchemy import func
from sqlalchemy.engine.base import Connection
from sqlalchemy import and_
from pyramid.request import Request
from pyramid.view import view_defaults, view_config
import json

from datetime import datetime, date, timedelta
import traceback


@view_defaults(route_name="rollclose", request_method="GET")
class api_rollclose(object):
    """
    This class has the functions for closing books and roll over, meaning creating new organisation's books for the subsequent financial year.
    It will have only one route namely rollclose and the 2 methods will be called on the basis of request_param,
    The request_method will be get and will be the default in view_defaults.
    """

    def __init__(self, request):
        """
        Initialising the request object which gets the data from client.
        """
        self.request = Request
        self.request = request
        self.con = Connection

    @view_config(route_name="close-books", renderer="json")
    def closeBooks(self):
        """
        Purpose:
        Transfers all the income and expence accounts to P&L.
        Also updates organisation table and sets closebook flag to true for the given orgcode.
        Returns success status if true.
        description:
        This method is called when the /rollclose route is invoked with task=closebooks as parameter.
        First, the list of all accounts in direct indirect income and expence are collected with their account codes and name in the list.
        Then for each account under the said 4 groups a loop will be run to get closing balance and baltype using calculateBalance.
        The private metho is found in api_reports module.
        balances of all direct and indirect income accounts will be credited to P&L and debeted from the respective accounts through jv.
        Similarly all balances from direct and indirect expences will be debited to P&L.
        In addition, if the function finds that roflag is already set to True then,
        balances of all accounts will be collected and the private function to get nextYear orgcode will be called.
        A dictionary with account names as keys and balances as values will be generated.
        Then the function will traverse the dictionary and fire update query to reset all opening balances for respective accounts in the new year.

        """
        try:
            token = self.request.headers["gktoken"]
        except:
            return {"gkstatus": enumdict["UnauthorisedAccess"]}
        authDetails = authCheck(token)
        if authDetails["auth"] == False:
            return {"gkstatus": enumdict["UnauthorisedAccess"]}
        else:
            with eng.begin() as con:
                orgCode = int(authDetails["orgcode"])
                financialStartEnd = con.execute(
                    "select yearstart, yearend, orgtype from organisation where orgcode = %d"
                    % int(orgCode)
                )
                startEndRow = financialStartEnd.fetchone()
                startDate = str(startEndRow["yearstart"])
                endDate = str(startEndRow["yearend"])
                closBal = 0.00
                blacktransactionsdata = con.execute(
                    select(
                        [func.count(vouchers.c.vouchercode).label("blackcount")]
                    ).where(
                        and_(
                            vouchers.c.voucherdate > endDate,
                            vouchers.c.orgcode == orgCode,
                        )
                    )
                )
                blacktransactions = blacktransactionsdata.fetchone()
                if blacktransactions["blackcount"] > 0:
                    return {"gkstatus": enumdict["ActionDisallowed"]}
                closingAccount = ""
                closingAccountCode = 0
                if startEndRow["orgtype"] == "Profit Making":
                    closingAccount = "Profit & Loss"
                    closeCodeData = con.execute(
                        "select accountcode from accounts where orgcode = %d and accountname = '%s'"
                        % (orgCode, closingAccount)
                    )
                    codeRow = closeCodeData.fetchone()
                    closingAccountCode = int(codeRow["accountcode"])
                else:
                    closingAccount = "Income & Expenditure"
                    closeCodeData = con.execute(
                        "select accountcode from accounts where orgcode = %d and accountname = '%s'"
                        % (orgCode, closingAccount)
                    )
                    codeRow = closeCodeData.fetchone()
                    closingAccountCode = int(codeRow["accountcode"])
                directIncomeData = con.execute(
                    "select accountcode, accountname from accounts where orgcode = %d and groupcode in(select groupcode from groupsubgroups where orgcode =%d and groupname in ('Direct Income', 'Indirect Income') or subgroupof in (select groupcode from groupsubgroups where orgcode = %d and groupname in ('Direct Income','Indirect Income')));"
                    % (orgCode, orgCode, orgCode)
                )
                diRecords = directIncomeData.fetchall()
                for di in diRecords:
                    if (
                        di["accountname"] == "Profit & Loss"
                        or di["accountname"] == "Income & Expenditure"
                    ):
                        continue
                    cbRecord = calculateBalance(
                        con, int(di["accountcode"]), startDate, startDate, endDate
                    )
                    if float(cbRecord["curbal"]) == 0:
                        continue
                    curtime = datetime.now()
                    str_time = str(curtime.microsecond)
                    new_microsecond = str_time[0:2]
                    voucherNumber = (
                        str(curtime.year)
                        + str(curtime.month)
                        + str(curtime.day)
                        + str(curtime.hour)
                        + str(curtime.minute)
                        + str(curtime.second)
                        + new_microsecond
                    )
                    entryDate = str(date.today())
                    voucherDate = endDate
                    drs = {di["accountcode"]: "%.2f" % (cbRecord["curbal"])}
                    crs = {closingAccountCode: "%.2f" % (cbRecord["curbal"])}
                    cljv = {
                        "vouchernumber": voucherNumber,
                        "voucherdate": voucherDate,
                        "entrydate": entryDate,
                        "narration": "jv for closing books",
                        "drs": drs,
                        "crs": crs,
                        "vouchertype": "journal",
                        "orgcode": orgCode,
                    }
                    result = con.execute(vouchers.insert(), [cljv])
                directExpenseData = con.execute(
                    "select accountcode, accountname from accounts where orgcode = %d and groupcode in(select groupcode from groupsubgroups where orgcode =%d and groupname in ('Direct Expense', 'Indirect Expense') or subgroupof in (select groupcode from groupsubgroups where orgcode = %d and groupname in ('Direct Expense','Indirect Expense')));"
                    % (orgCode, orgCode, orgCode)
                )
                deRecords = directExpenseData.fetchall()
                for de in deRecords:
                    cbRecord = calculateBalance(
                        con, int(de["accountcode"]), startDate, startDate, endDate
                    )
                    if float(cbRecord["curbal"]) == 0:
                        continue
                    curtime = datetime.now()
                    str_time = str(curtime.microsecond)
                    new_microsecond = str_time[0:2]
                    voucherNumber = (
                        str(curtime.year)
                        + str(curtime.month)
                        + str(curtime.day)
                        + str(curtime.hour)
                        + str(curtime.minute)
                        + str(curtime.second)
                        + new_microsecond
                    )
                    entryDate = str(date.today())
                    voucherDate = endDate
                    crs = {de["accountcode"]: "%.2f" % (cbRecord["curbal"])}
                    drs = {closingAccountCode: "%.2f" % (cbRecord["curbal"])}
                    cljv = {
                        "vouchernumber": voucherNumber,
                        "voucherdate": voucherDate,
                        "entrydate": entryDate,
                        "narration": "jv for closing books",
                        "drs": drs,
                        "crs": crs,
                        "vouchertype": "journal",
                        "orgcode": orgCode,
                    }
                    result = con.execute(vouchers.insert(), [cljv])
                plResult = calculateBalance(
                    con, closingAccountCode, startDate, startDate, endDate
                )
                startEndRow["orgtype"]
                groupCodeData = con.execute(
                    "select groupcode from groupsubgroups where groupname = 'Reserves' and orgcode = %d"
                    % (orgCode)
                )
                gcRecord = groupCodeData.fetchone()
                groupCode = gcRecord["groupcode"]
                if (
                    plResult["baltype"] == "Cr"
                    and startEndRow["orgtype"] == "Profit Making"
                ):
                    pAccount = {
                        "accountname": "Profit For The Year",
                        "groupcode": int(groupCode),
                        "orgcode": orgCode,
                    }
                    ins = con.execute(accounts.insert(), [pAccount])
                    finalreservecode = 0
                    curreservedata = con.execute(
                        select([accounts.c.accountcode]).where(
                            and_(
                                accounts.c.orgcode == orgCode,
                                accounts.c.accountname == "Profit For The Year",
                            )
                        )
                    )
                    curreserverow = curreservedata.fetchone()
                    curreserve = curreserverow["accountcode"]
                    curtime = datetime.now()
                    str_time = str(curtime.microsecond)
                    new_microsecond = str_time[0:2]
                    voucherNumber = (
                        str(curtime.year)
                        + str(curtime.month)
                        + str(curtime.day)
                        + str(curtime.hour)
                        + str(curtime.minute)
                        + str(curtime.second)
                        + new_microsecond
                    )
                    entryDate = str(date.today())
                    voucherDate = endDate
                    drs = {closingAccountCode: "%.2f" % (plResult["curbal"])}
                    crs = {curreserve: "%.2f" % (plResult["curbal"])}
                    cljv = {
                        "vouchernumber": voucherNumber,
                        "voucherdate": voucherDate,
                        "entrydate": entryDate,
                        "narration": "Entry for recording Profit & Loss",
                        "drs": drs,
                        "crs": crs,
                        "vouchertype": "journal",
                        "orgcode": orgCode,
                    }
                    result = con.execute(vouchers.insert(), [cljv])
                    paccnumdata = con.execute(
                        select(
                            [func.count(accounts.c.accountcode).label("account")]
                        ).where(
                            and_(
                                accounts.c.orgcode == orgCode,
                                accounts.c.accountname == "Profit B/F",
                            )
                        )
                    )
                    laccnumdata = con.execute(
                        select(
                            [func.count(accounts.c.accountcode).label("account")]
                        ).where(
                            and_(
                                accounts.c.orgcode == orgCode,
                                accounts.c.accountname == "Loss B/F",
                            )
                        )
                    )
                    paccnumrow = paccnumdata.fetchone()
                    laccnumrow = laccnumdata.fetchone()
                    if paccnumrow["account"] == 0 and laccnumrow["account"] == 0:
                        pAccount = {
                            "accountname": "Profit C/F",
                            "groupcode": int(groupCode),
                            "orgcode": orgCode,
                        }
                        ins = con.execute(accounts.insert(), [pAccount])
                        finalreservedata = con.execute(
                            select([accounts.c.accountcode]).where(
                                and_(
                                    accounts.c.orgcode == orgCode,
                                    accounts.c.accountname == "Profit C/F",
                                )
                            )
                        )
                        finalreserverow = finalreservedata.fetchone()
                        finalreservecode = finalreserverow["accountcode"]
                    else:
                        if paccnumrow["account"] > 0:
                            res = con.execute(
                                "update accounts set accountname = 'Profit C/F' where orgcode = %d and accountname = 'Profit B/F'"
                                % (orgCode)
                            )
                            finalreservedata = con.execute(
                                select([accounts.c.accountcode]).where(
                                    and_(
                                        accounts.c.orgcode == orgCode,
                                        accounts.c.accountname == "Profit C/F",
                                    )
                                )
                            )
                            finalreserverow = finalreservedata.fetchone()
                            finalreservecode = finalreserverow["accountcode"]
                        if laccnumrow["account"] > 0:
                            lcfData = con.execute(
                                select([accounts.c.openingbal]).where(
                                    and_(
                                        accounts.c.orgcode == orgCode,
                                        accounts.c.accountname == "Loss B/F",
                                    )
                                )
                            )
                            lcfRow = lcfData.fetchone()
                            lcf = float(lcfRow["openingbal"])
                            if lcf > plResult["curbal"]:
                                res = con.execute(
                                    "update accounts set accountname = 'Loss C/F' where orgcode = %d and accountname = 'Loss B/F'"
                                    % (orgCode)
                                )
                                finalreservedata = con.execute(
                                    select([accounts.c.accountcode]).where(
                                        and_(
                                            accounts.c.orgcode == orgCode,
                                            accounts.c.accountname == "Loss C/F",
                                        )
                                    )
                                )
                                finalreserverow = finalreservedata.fetchone()
                                finalreservecode = finalreserverow["accountcode"]
                            elif lcf < plResult["curbal"]:
                                res = con.execute(
                                    "update accounts set accountname = 'Profit C/F' where orgcode = %d and accountname = 'Loss B/F'"
                                    % (orgCode)
                                )
                                finalreservedata = con.execute(
                                    select([accounts.c.accountcode]).where(
                                        and_(
                                            accounts.c.orgcode == orgCode,
                                            accounts.c.accountname == "Profit C/F",
                                        )
                                    )
                                )
                                finalreserverow = finalreservedata.fetchone()
                                finalreservecode = finalreserverow["accountcode"]
                            else:
                                res = con.execute(
                                    "delete from accounts where orgcode = %d and accountname = 'Loss B/F'"
                                    % (orgCode)
                                )
                                finalreservecode = 0
                    if finalreservecode != 0:
                        curtime = datetime.now()
                        str_time = str(curtime.microsecond)
                        new_microsecond = str_time[0:2]
                        voucherNumber = (
                            str(curtime.year)
                            + str(curtime.month)
                            + str(curtime.day)
                            + str(curtime.hour)
                            + str(curtime.minute)
                            + str(curtime.second)
                            + new_microsecond
                        )
                        entryDate = str(date.today())
                        voucherDate = endDate
                        drs = {curreserve: "%.2f" % (plResult["curbal"])}
                        crs = {finalreservecode: "%.2f" % (plResult["curbal"])}
                        cljv = {
                            "vouchernumber": voucherNumber,
                            "voucherdate": voucherDate,
                            "entrydate": entryDate,
                            "narration": "Entry for recording Profit For The Year",
                            "drs": drs,
                            "crs": crs,
                            "vouchertype": "journal",
                            "orgcode": orgCode,
                        }
                        result = con.execute(vouchers.insert(), [cljv])

                if (
                    plResult["baltype"] == "Cr"
                    and startEndRow["orgtype"] == "Not For Profit"
                ):
                    sAccount = {
                        "accountname": "Surplus For The Year",
                        "groupcode": int(groupCode),
                        "orgcode": orgCode,
                    }
                    ins = con.execute(accounts.insert(), [sAccount])
                    finalreservecode = 0
                    curreservedata = con.execute(
                        select([accounts.c.accountcode]).where(
                            and_(
                                accounts.c.orgcode == orgCode,
                                accounts.c.accountname == "Surplus For The Year",
                            )
                        )
                    )
                    curreserverow = curreservedata.fetchone()
                    curreserve = curreserverow["accountcode"]
                    curtime = datetime.now()
                    str_time = str(curtime.microsecond)
                    new_microsecond = str_time[0:2]
                    voucherNumber = (
                        str(curtime.year)
                        + str(curtime.month)
                        + str(curtime.day)
                        + str(curtime.hour)
                        + str(curtime.minute)
                        + str(curtime.second)
                        + new_microsecond
                    )
                    entryDate = str(date.today())
                    voucherDate = endDate
                    drs = {closingAccountCode: "%.2f" % (plResult["curbal"])}
                    crs = {curreserve: "%.2f" % (plResult["curbal"])}
                    cljv = {
                        "vouchernumber": voucherNumber,
                        "voucherdate": voucherDate,
                        "entrydate": entryDate,
                        "narration": "Entry for recording Income & Expenditure",
                        "drs": drs,
                        "crs": crs,
                        "vouchertype": "journal",
                        "orgcode": orgCode,
                    }
                    result = con.execute(vouchers.insert(), [cljv])
                    paccnumdata = con.execute(
                        select(
                            [func.count(accounts.c.accountcode).label("account")]
                        ).where(
                            and_(
                                accounts.c.orgcode == orgCode,
                                accounts.c.accountname == "Surplus B/F",
                            )
                        )
                    )
                    laccnumdata = con.execute(
                        select(
                            [func.count(accounts.c.accountcode).label("account")]
                        ).where(
                            and_(
                                accounts.c.orgcode == orgCode,
                                accounts.c.accountname == "Deficit B/F",
                            )
                        )
                    )
                    paccnumrow = paccnumdata.fetchone()
                    laccnumrow = laccnumdata.fetchone()
                    if paccnumrow["account"] == 0 and laccnumrow["account"] == 0:
                        pAccount = {
                            "accountname": "Surplus C/F",
                            "groupcode": int(groupCode),
                            "orgcode": orgCode,
                        }
                        ins = con.execute(accounts.insert(), [pAccount])
                        finalreservedata = con.execute(
                            select([accounts.c.accountcode]).where(
                                and_(
                                    accounts.c.orgcode == orgCode,
                                    accounts.c.accountname == "Surplus C/F",
                                )
                            )
                        )
                        finalreserverow = finalreservedata.fetchone()
                        finalreservecode = finalreserverow["accountcode"]
                    else:
                        if paccnumrow["account"] > 0:
                            res = con.execute(
                                "update accounts set accountname = 'Surplus C/F' where orgcode = %d and accountname = 'Surplus B/F'"
                                % (orgCode)
                            )
                            finalreservedata = con.execute(
                                select([accounts.c.accountcode]).where(
                                    and_(
                                        accounts.c.orgcode == orgCode,
                                        accounts.c.accountname == "Surplus C/F",
                                    )
                                )
                            )
                            finalreserverow = finalreservedata.fetchone()
                            finalreservecode = finalreserverow["accountcode"]
                        if laccnumrow["account"] > 0:
                            lcfData = con.execute(
                                select([accounts.c.openingbal]).where(
                                    and_(
                                        accounts.c.orgcode == orgCode,
                                        accounts.c.accountname == "Deficit B/F",
                                    )
                                )
                            )
                            lcfRow = lcfData.fetchone()
                            lcf = float(lcfRow["openingbal"])
                            if lcf > plResult["curbal"]:
                                res = con.execute(
                                    "update accounts set accountname = 'Deficit C/F' where orgcode = %d and accountname = 'Deficit B/F'"
                                    % (orgCode)
                                )
                                finalreservedata = con.execute(
                                    select([accounts.c.accountcode]).where(
                                        and_(
                                            accounts.c.orgcode == orgCode,
                                            accounts.c.accountname == "Deficit C/F",
                                        )
                                    )
                                )
                                finalreserverow = finalreservedata.fetchone()
                                finalreservecode = finalreserverow["accountcode"]
                            elif lcf < plResult["curbal"]:
                                res = con.execute(
                                    "update accounts set accountname = 'Surplus C/F' where orgcode = %d and accountname = 'Deficit B/F'"
                                    % (orgCode)
                                )
                                finalreservedata = con.execute(
                                    select([accounts.c.accountcode]).where(
                                        and_(
                                            accounts.c.orgcode == orgCode,
                                            accounts.c.accountname == "Surplus C/F",
                                        )
                                    )
                                )
                                finalreserverow = finalreservedata.fetchone()
                                finalreservecode = finalreserverow["accountcode"]
                            else:
                                res = con.execute(
                                    "delete from accounts where orgcode = %d and accountname = 'Deficit B/F'"
                                    % (orgCode)
                                )
                                finalreservecode = 0
                    if finalreservecode != 0:
                        curtime = datetime.now()
                        str_time = str(curtime.microsecond)
                        new_microsecond = str_time[0:2]
                        voucherNumber = (
                            str(curtime.year)
                            + str(curtime.month)
                            + str(curtime.day)
                            + str(curtime.hour)
                            + str(curtime.minute)
                            + str(curtime.second)
                            + new_microsecond
                        )
                        entryDate = str(date.today())
                        voucherDate = endDate
                        drs = {curreserve: "%.2f" % (plResult["curbal"])}
                        crs = {finalreservecode: "%.2f" % (plResult["curbal"])}
                        cljv = {
                            "vouchernumber": voucherNumber,
                            "voucherdate": voucherDate,
                            "entrydate": entryDate,
                            "narration": "Entry for recording Surplus For The Year",
                            "drs": drs,
                            "crs": crs,
                            "vouchertype": "journal",
                            "orgcode": orgCode,
                        }
                        result = con.execute(vouchers.insert(), [cljv])
                if (
                    plResult["baltype"] == "Dr"
                    and startEndRow["orgtype"] == "Profit Making"
                ):
                    lAccount = {
                        "accountname": "Loss For The Year",
                        "groupcode": int(groupCode),
                        "orgcode": orgCode,
                    }
                    ins = con.execute(accounts.insert(), [lAccount])
                    finalreservecode = 0
                    curreservedata = con.execute(
                        select([accounts.c.accountcode]).where(
                            and_(
                                accounts.c.orgcode == orgCode,
                                accounts.c.accountname == "Loss For The Year",
                            )
                        )
                    )
                    curreserverow = curreservedata.fetchone()
                    curreserve = curreserverow["accountcode"]
                    curtime = datetime.now()
                    str_time = str(curtime.microsecond)
                    new_microsecond = str_time[0:2]
                    voucherNumber = (
                        str(curtime.year)
                        + str(curtime.month)
                        + str(curtime.day)
                        + str(curtime.hour)
                        + str(curtime.minute)
                        + str(curtime.second)
                        + new_microsecond
                    )
                    entryDate = str(date.today())
                    voucherDate = endDate
                    crs = {closingAccountCode: "%.2f" % (plResult["curbal"])}
                    drs = {curreserve: "%.2f" % (plResult["curbal"])}
                    cljv = {
                        "vouchernumber": voucherNumber,
                        "voucherdate": voucherDate,
                        "entrydate": entryDate,
                        "narration": "Entry for recording Profit & Loss",
                        "drs": drs,
                        "crs": crs,
                        "vouchertype": "journal",
                        "orgcode": orgCode,
                    }
                    result = con.execute(vouchers.insert(), [cljv])
                    paccnumdata = con.execute(
                        select(
                            [func.count(accounts.c.accountcode).label("account")]
                        ).where(
                            and_(
                                accounts.c.orgcode == orgCode,
                                accounts.c.accountname == "Profit B/F",
                            )
                        )
                    )
                    laccnumdata = con.execute(
                        select(
                            [func.count(accounts.c.accountcode).label("account")]
                        ).where(
                            and_(
                                accounts.c.orgcode == orgCode,
                                accounts.c.accountname == "Loss B/F",
                            )
                        )
                    )
                    paccnumrow = paccnumdata.fetchone()
                    laccnumrow = laccnumdata.fetchone()
                    if paccnumrow["account"] == 0 and laccnumrow["account"] == 0:
                        pAccount = {
                            "accountname": "Loss C/F",
                            "groupcode": int(groupCode),
                            "orgcode": orgCode,
                        }
                        ins = con.execute(accounts.insert(), [pAccount])
                        finalreservedata = con.execute(
                            select([accounts.c.accountcode]).where(
                                and_(
                                    accounts.c.orgcode == orgCode,
                                    accounts.c.accountname == "Loss C/F",
                                )
                            )
                        )
                        finalreserverow = finalreservedata.fetchone()
                        finalreservecode = finalreserverow["accountcode"]
                    else:
                        if laccnumrow["account"] > 0:
                            res = con.execute(
                                "update accounts set accountname = 'Loss C/F' where orgcode = %d and accountname = 'Loss B/F'"
                                % (orgCode)
                            )
                            finalreservedata = con.execute(
                                select([accounts.c.accountcode]).where(
                                    and_(
                                        accounts.c.orgcode == orgCode,
                                        accounts.c.accountname == "Loss C/F",
                                    )
                                )
                            )
                            finalreserverow = finalreservedata.fetchone()
                            finalreservecode = finalreserverow["accountcode"]
                        if paccnumrow["account"] > 0:
                            pcfData = con.execute(
                                select([accounts.c.openingbal]).where(
                                    and_(
                                        accounts.c.orgcode == orgCode,
                                        accounts.c.accountname == "Profit B/F",
                                    )
                                )
                            )
                            pcfRow = pcfData.fetchone()
                            pcf = float(pcfRow["openingbal"])
                            if pcf > plResult["curbal"]:
                                res = con.execute(
                                    "update accounts set accountname = 'Profit C/F' where orgcode = %d and accountname = 'Profit B/F'"
                                    % (orgCode)
                                )
                                finalreservedata = con.execute(
                                    select([accounts.c.accountcode]).where(
                                        and_(
                                            accounts.c.orgcode == orgCode,
                                            accounts.c.accountname == "Profit C/F",
                                        )
                                    )
                                )
                                finalreserverow = finalreservedata.fetchone()
                                finalreservecode = finalreserverow["accountcode"]
                            elif pcf < plResult["curbal"]:
                                res = con.execute(
                                    "update accounts set accountname = 'Loss C/F' where orgcode = %d and accountname = 'Profit B/F'"
                                    % (orgCode)
                                )
                                finalreservedata = con.execute(
                                    select([accounts.c.accountcode]).where(
                                        and_(
                                            accounts.c.orgcode == orgCode,
                                            accounts.c.accountname == "Loss C/F",
                                        )
                                    )
                                )
                                finalreserverow = finalreservedata.fetchone()
                                finalreservecode = finalreserverow["accountcode"]
                            else:
                                res = con.execute(
                                    "delete from accounts where orgcode = %d and accountname = 'Profit B/F'"
                                    % (orgCode)
                                )
                                finalreservecode = 0
                    if finalreservecode != 0:
                        curtime = datetime.now()
                        str_time = str(curtime.microsecond)
                        new_microsecond = str_time[0:2]
                        voucherNumber = (
                            str(curtime.year)
                            + str(curtime.month)
                            + str(curtime.day)
                            + str(curtime.hour)
                            + str(curtime.minute)
                            + str(curtime.second)
                            + new_microsecond
                        )
                        entryDate = str(date.today())
                        voucherDate = endDate
                        crs = {curreserve: "%.2f" % (plResult["curbal"])}
                        drs = {finalreservecode: "%.2f" % (plResult["curbal"])}
                        cljv = {
                            "vouchernumber": voucherNumber,
                            "voucherdate": voucherDate,
                            "entrydate": entryDate,
                            "narration": "Entry for recording Loss For The Year",
                            "drs": drs,
                            "crs": crs,
                            "vouchertype": "journal",
                            "orgcode": orgCode,
                        }
                        result = con.execute(vouchers.insert(), [cljv])
                if (
                    plResult["baltype"] == "Dr"
                    and startEndRow["orgtype"] == "Not For Profit"
                ):
                    dAccount = {
                        "accountname": "Deficit For The Year",
                        "groupcode": int(groupCode),
                        "orgcode": orgCode,
                    }
                    ins = con.execute(accounts.insert(), [dAccount])
                    finalreservecode = 0
                    curreservedata = con.execute(
                        select([accounts.c.accountcode]).where(
                            and_(
                                accounts.c.orgcode == orgCode,
                                accounts.c.accountname == "Deficit For The Year",
                            )
                        )
                    )
                    curreserverow = curreservedata.fetchone()
                    curreserve = curreserverow["accountcode"]
                    curtime = datetime.now()
                    str_time = str(curtime.microsecond)
                    new_microsecond = str_time[0:2]
                    voucherNumber = (
                        str(curtime.year)
                        + str(curtime.month)
                        + str(curtime.day)
                        + str(curtime.hour)
                        + str(curtime.minute)
                        + str(curtime.second)
                        + new_microsecond
                    )
                    entryDate = str(date.today())
                    voucherDate = endDate
                    crs = {closingAccountCode: "%.2f" % (plResult["curbal"])}
                    drs = {curreserve: "%.2f" % (plResult["curbal"])}
                    cljv = {
                        "vouchernumber": voucherNumber,
                        "voucherdate": voucherDate,
                        "entrydate": entryDate,
                        "narration": "Entry for recording Income & Expenditure",
                        "drs": drs,
                        "crs": crs,
                        "vouchertype": "journal",
                        "orgcode": orgCode,
                    }
                    result = con.execute(vouchers.insert(), [cljv])
                    paccnumdata = con.execute(
                        select(
                            [func.count(accounts.c.accountcode).label("account")]
                        ).where(
                            and_(
                                accounts.c.orgcode == orgCode,
                                accounts.c.accountname == "Surplus B/F",
                            )
                        )
                    )
                    laccnumdata = con.execute(
                        select(
                            [func.count(accounts.c.accountcode).label("account")]
                        ).where(
                            and_(
                                accounts.c.orgcode == orgCode,
                                accounts.c.accountname == "Deficit B/F",
                            )
                        )
                    )
                    paccnumrow = paccnumdata.fetchone()
                    laccnumrow = laccnumdata.fetchone()
                    if paccnumrow["account"] == 0 and laccnumrow["account"] == 0:
                        pAccount = {
                            "accountname": "Deficit C/F",
                            "groupcode": int(groupCode),
                            "orgcode": orgCode,
                        }
                        ins = con.execute(accounts.insert(), [pAccount])
                        finalreservedata = con.execute(
                            select([accounts.c.accountcode]).where(
                                and_(
                                    accounts.c.orgcode == orgCode,
                                    accounts.c.accountname == "Deficit C/F",
                                )
                            )
                        )
                        finalreserverow = finalreservedata.fetchone()
                        finalreservecode = finalreserverow["accountcode"]
                    else:
                        if laccnumrow["account"] > 0:
                            res = con.execute(
                                "update accounts set accountname = 'Deficit C/F' where orgcode = %d and accountname = 'Deficit B/F'"
                                % (orgCode)
                            )
                            finalreservedata = con.execute(
                                select([accounts.c.accountcode]).where(
                                    and_(
                                        accounts.c.orgcode == orgCode,
                                        accounts.c.accountname == "Deficit C/F",
                                    )
                                )
                            )
                            finalreserverow = finalreservedata.fetchone()
                            finalreservecode = finalreserverow["accountcode"]
                        if paccnumrow["account"] > 0:
                            pcfData = con.execute(
                                select([accounts.c.openingbal]).where(
                                    and_(
                                        accounts.c.orgcode == orgCode,
                                        accounts.c.accountname == "Surplus B/F",
                                    )
                                )
                            )
                            pcfRow = pcfData.fetchone()
                            pcf = float(pcfRow["openingbal"])
                            if pcf > plResult["curbal"]:
                                res = con.execute(
                                    "update accounts set accountname = 'Surplus C/F' where orgcode = %d and accountname = 'Surplus B/F'"
                                    % (orgCode)
                                )
                                finalreservedata = con.execute(
                                    select([accounts.c.accountcode]).where(
                                        and_(
                                            accounts.c.orgcode == orgCode,
                                            accounts.c.accountname == "Surplus C/F",
                                        )
                                    )
                                )
                                finalreserverow = finalreservedata.fetchone()
                                finalreservecode = finalreserverow["accountcode"]
                            elif pcf < plResult["curbal"]:
                                res = con.execute(
                                    "update accounts set accountname = 'Deficit C/F' where orgcode = %d and accountname = 'Surplus B/F'"
                                    % (orgCode)
                                )
                                finalreservedata = con.execute(
                                    select([accounts.c.accountcode]).where(
                                        and_(
                                            accounts.c.orgcode == orgCode,
                                            accounts.c.accountname == "Deficit C/F",
                                        )
                                    )
                                )
                                finalreserverow = finalreservedata.fetchone()
                                finalreservecode = finalreserverow["accountcode"]
                            else:
                                res = con.execute(
                                    "delete from accounts where orgcode = %d and accountname = 'Profit B/F'"
                                    % (orgCode)
                                )
                                finalreservecode = 0
                    if finalreservecode != 0:
                        curtime = datetime.now()
                        str_time = str(curtime.microsecond)
                        new_microsecond = str_time[0:2]
                        voucherNumber = (
                            str(curtime.year)
                            + str(curtime.month)
                            + str(curtime.day)
                            + str(curtime.hour)
                            + str(curtime.minute)
                            + str(curtime.second)
                            + new_microsecond
                        )
                        entryDate = str(date.today())
                        voucherDate = endDate
                        crs = {curreserve: "%.2f" % (plResult["curbal"])}
                        drs = {finalreservecode: "%.2f" % (plResult["curbal"])}
                        cljv = {
                            "vouchernumber": voucherNumber,
                            "voucherdate": voucherDate,
                            "entrydate": entryDate,
                            "narration": "Entry for recording Deficit For The Year",
                            "drs": drs,
                            "crs": crs,
                            "vouchertype": "journal",
                            "orgcode": orgCode,
                        }
                        con.execute(vouchers.insert(), [cljv])
                # set existing org's booksclosedflag to 1
                con.execute(
                    organisation.update()
                    .where(organisation.c.orgcode == orgCode)
                    .values({"booksclosedflag": 1})
                )
                # check if rollclose is true.
                ROData = con.execute(
                    select([organisation.c.roflag]).where(
                        organisation.c.orgcode == orgCode
                    )
                )
                ROFlagRow = ROData.fetchone()
                roStatus = ROFlagRow["roflag"]
                if roStatus == 1:
                    accList = con.execute(
                        select([accounts.c.accountname, accounts.c.accountcode]).where(
                            accounts.c.orgcode == orgCode
                        )
                    )
                    accData = accList.fetchall()
                    RoOrgCode = self.getNextOrgCode(orgCode, con)
                    for acc in accData:
                        # we must compare if the rolled over organisation contains all these accounts.
                        newAccData = con.execute(
                            select([accounts.c.accountcode]).where(
                                and_(
                                    accounts.c.accountname == acc["accountname"],
                                    accounts.c.orgcode == RoOrgCode,
                                )
                            )
                        )
                        # called closebook and get the balance.
                        calBalData = calculateBalance(
                            con, acc["accountcode"], startDate, startDate, endDate
                        )
                        closBal = calBalData["curbal"]
                        if newAccData.rowcount == 0:
                            # this means  we first need to created this account for the rolled over org.
                            grpResult = con.execute(
                                "select groupname from groupsubgroups where orgcode = %d and groupcode = (select groupcode from accounts where accountcode = %d and orgcode = %d)"
                                % (orgCode, acc["accountcode"], orgCode)
                            )
                            grpName = grpResult.fetchone()
                            newGrpResult = con.execute(
                                select([groupsubgroups.c.groupcode]).where(
                                    and_(
                                        groupsubgroups.c.orgcode == RoOrgCode,
                                        groupsubgroups.c.groupname
                                        == grpName["groupname"],
                                    )
                                )
                            )
                            grpCD = newGrpResult.fetchone()
                            # This is structure of account data {u'accountname': u'ICICI', u'openingbal': u'550.00', 'orgcode': 31, u'groupcode': u'1180'}

                            dataset = {
                                "accountname": acc["accountname"],
                                "openingbal": closBal,
                                "groupcode": grpCD["groupcode"],
                                "orgcode": RoOrgCode,
                            }
                            insACC = con.execute(accounts.insert(), [dataset])
                        else:
                            newAcc = newAccData.fetchone()
                            updateData = con.execute(
                                accounts.update()
                                .where(accounts.c.accountcode == newAcc["accountcode"])
                                .values(openingbal=closBal)
                            )

                return {"gkstatus": enumdict["Success"]}


    @view_config(route_name="roll-over", renderer="json")
    def rollOver(self):
        """
        Purpose:
        Creates a new organisation by adding new row in Organisation table,
        And transfering all accounts from the old organisation to the newly created one.
        Also updates organisation table and sets roflag to true for the old orgcode.
        Note that if Roll over is done before closing books,
        The balances will still be carried forward and the current roflag will be set to 1 without setting the closebook flag to 1.
        Returns success status if true.
        """
        try:
            token = self.request.headers["gktoken"]
        except:
            return {"gkstatus": enumdict["UnauthorisedAccess"]}
        authDetails = authCheck(token)
        if authDetails["auth"] == False:
            return {"gkstatus": enumdict["UnauthorisedAccess"]}
        else:
            with eng.begin() as con:
                orgCode = int(authDetails["orgcode"])
                financialStartEnd = con.execute(
                    "select * from organisation where orgcode = %d" % int(orgCode)
                )
                startEndRow = financialStartEnd.fetchone()
                oldstartDate = startEndRow["yearstart"]
                endDate = startEndRow["yearend"]
                newYearStart = (endDate + timedelta(1)).strftime("%Y-%m-%d")
                newYearEnd = self.request.params["financialend"]
                #               print newYearStart
                #               print newYearEnd
                newOrg = {
                    "orgname": startEndRow["orgname"],
                    "orgtype": startEndRow["orgtype"],
                    "yearstart": newYearStart,
                    "yearend": newYearEnd,
                    "orgcity": startEndRow["orgcity"],
                    "orgaddr": startEndRow["orgaddr"],
                    "orgpincode": startEndRow["orgpincode"],
                    "orgstate": startEndRow["orgstate"],
                    "orgcountry": startEndRow["orgcountry"],
                    "orgtelno": startEndRow["orgtelno"],
                    "orgfax": startEndRow["orgfax"],
                    "orgwebsite": startEndRow["orgwebsite"],
                    "orgemail": startEndRow["orgemail"],
                    "orgpan": startEndRow["orgpan"],
                    "orgmvat": startEndRow["orgmvat"],
                    "orgstax": startEndRow["orgstax"],
                    "orgregno": startEndRow["orgregno"],
                    "orgregdate": startEndRow["orgregdate"],
                    "orgfcrano": startEndRow["orgfcrano"],
                    "orgfcradate": startEndRow["orgfcradate"],
                    "roflag": startEndRow["roflag"],
                    "booksclosedflag": 0,
                    "invflag": startEndRow["invflag"],
                    "billflag": startEndRow["billflag"],
                    "invsflag": startEndRow["invsflag"],
                    "avflag": startEndRow["avflag"],
                    "maflag": startEndRow["maflag"],
                    "modeflag": startEndRow["modeflag"],
                    "avnoflag": startEndRow["avnoflag"],
                    "ainvnoflag": startEndRow["ainvnoflag"],
                    "logo": startEndRow["logo"],
                    "gstin": startEndRow["gstin"],
                    "tin": startEndRow["tin"],
                    "bankdetails": startEndRow["bankdetails"],
                    "users": startEndRow["users"],
                }
                con.execute(organisation.insert(), newOrg)
                # must move all the users data from old org to the new org
                newOrgCodeData = con.execute(
                    select([organisation.c.orgcode]).where(
                        and_(
                            organisation.c.orgname == newOrg["orgname"],
                            organisation.c.orgtype == newOrg["orgtype"],
                            organisation.c.yearstart == newOrg["yearstart"],
                            organisation.c.yearend == newOrg["yearend"],
                        )
                    )
                )
                newOrgRow = newOrgCodeData.fetchone()
                newOrgCode = newOrgRow["orgcode"]
                # need not create a new user here. But update the new orgcode in the gkusers table
                oldUsers = con.execute(
                    select([organisation.c.users]).where(
                        organisation.c.orgcode == orgCode
                    )
                ).fetchone()

                if type(oldUsers["users"]) == str:
                    oldUsers = json.loads(oldUsers["users"])
                elif type(oldUsers["users"]) == dict:
                    oldUsers = oldUsers["users"]
                else:
                    oldUsers = {}

                for oldUser in oldUsers:
                    # print(oldUser)
                    orgDataQuery = con.execute(
                        "select u.orgs#>'{%s}' as data from gkusers u where userid = %d;"
                        % (str(orgCode), int(oldUser))
                    )
                    orgData = (
                        orgDataQuery.fetchone()
                        if orgDataQuery.rowcount > 0
                        else {"data": {}}
                    )
                    con.execute(
                        "update gkusers set orgs = jsonb_set(orgs, '{%s}', '%s') where userid = %d;"
                        % (
                            str(newOrgCode),
                            json.dumps(orgData["data"]),
                            int(oldUser),
                        )
                    )
                oldGroups = con.execute(
                    "select groupname from groupsubgroups where subgroupof is null and orgcode = %d"
                    % (orgCode)
                )
                oldGroupRecords = oldGroups.fetchall()
                for oldgrp in oldGroupRecords:
                    con.execute(
                        groupsubgroups.insert(),
                        {"groupname": oldgrp["groupname"], "orgcode": newOrgCode},
                    )
                    oldSubGroupsForGroupData = con.execute(
                        "select groupname from groupsubgroups where orgcode = %d and subgroupof = (select groupcode from groupsubgroups where groupname = '%s' and orgcode = %d)"
                        % (orgCode, oldgrp["groupname"], orgCode)
                    )
                    newgroupCodeData = con.execute(
                        select([groupsubgroups.c.groupcode]).where(
                            and_(
                                groupsubgroups.c.groupname == oldgrp["groupname"],
                                groupsubgroups.c.orgcode == newOrgCode,
                            )
                        )
                    )
                    newGroupCodeRow = newgroupCodeData.fetchone()
                    newGroupCode = newGroupCodeRow["groupcode"]
                    for osg in oldSubGroupsForGroupData:
                        res = con.execute(
                            groupsubgroups.insert(),
                            {
                                "groupname": osg["groupname"],
                                "subgroupof": newGroupCode,
                                "orgcode": newOrgCode,
                            },
                        )
                oldGroupAccounts = con.execute(
                    "select accountname,accountcode,sysaccount,groupname,defaultflag from accounts,groupsubgroups where accounts.orgcode = %d and accounts.groupcode = groupsubgroups.groupcode and accountname not in ('Profit For The Year','Loss For The Year','Surplus For The Year','Deficit For The Year')"
                    % (orgCode)
                )
                for angn in oldGroupAccounts:
                    newCodeForGroup = con.execute(
                        select([groupsubgroups.c.groupcode]).where(
                            and_(
                                groupsubgroups.c.groupname == angn["groupname"],
                                groupsubgroups.c.orgcode == newOrgCode,
                            )
                        )
                    )
                    newGroupCodeRow = newCodeForGroup.fetchone()
                    cbRecord = calculateBalance(
                        con,
                        angn["accountcode"],
                        str(oldstartDate),
                        str(oldstartDate),
                        str(endDate),
                    )
                    opnbal = 0.00
                    accname = angn["accountname"]
                    if (
                        cbRecord["grpname"] == "Current Assets"
                        or cbRecord["grpname"] == "Fixed Assets"
                        or cbRecord["grpname"] == "Investments"
                        or cbRecord["grpname"] == "Loans(Asset)"
                        or cbRecord["grpname"] == "Miscellaneous Expenses(Asset)"
                    ):
                        if cbRecord["baltype"] == "Cr":
                            opnbal = -cbRecord["curbal"]
                        else:
                            opnbal = cbRecord["curbal"]
                    if (
                        cbRecord["grpname"] == "Corpus"
                        or cbRecord["grpname"] == "Capital"
                        or cbRecord["grpname"] == "Current Liabilities"
                        or cbRecord["grpname"] == "Loans(Liability)"
                        or cbRecord["grpname"] == "Reserves"
                    ):
                        if cbRecord["baltype"] == "Dr":
                            opnbal = -cbRecord["curbal"]
                        else:
                            opnbal = cbRecord["curbal"]
                    if angn["accountname"] in (
                        "Profit C/F",
                        "Loss C/F",
                        "Surplus C/F",
                        "Deficit C/F",
                    ):
                        accname = accname.replace("C/F", "B/F")
                    con.execute(
                        accounts.insert(),
                        {
                            "accountname": accname,
                            "openingbal": float(opnbal),
                            "groupcode": newGroupCodeRow["groupcode"],
                            "orgcode": newOrgCode,
                            "sysaccount": angn["sysaccount"],
                            "defaultflag": angn["defaultflag"],
                        },
                    )
                csobData = con.execute(
                    select([accounts.c.openingbal]).where(
                        and_(
                            accounts.c.orgcode == newOrgCode,
                            accounts.c.accountname == "Closing Stock",
                        )
                    )
                )
                csobRow = csobData.fetchone()
                csob = csobRow["openingbal"]
                if csob > 0:
                    con.execute(
                        "update accounts set openingbal = %f where accountname = 'Stock at the Beginning' and orgcode = %d"
                        % (csob, newOrgCode)
                    )
                    con.execute(
                        "update accounts set openingbal = 0.00 where accountname = 'Closing Stock' and orgcode = %d"
                        % (newOrgCode)
                    )
                    osCodeData = con.execute(
                        "select accountcode from accounts where accountname = 'Opening Stock' and orgcode = %d"
                        % (newOrgCode)
                    )
                    osCodeRow = osCodeData.fetchone()
                    osCode = osCodeRow["accountcode"]
                    sabData = con.execute(
                        "select accountcode from accounts where accountname = 'Stock at the Beginning' and orgcode = %d"
                        % (newOrgCode)
                    )
                    sabRow = sabData.fetchone()
                    sabCode = sabRow["accountcode"]
                    crs = {sabCode: "%.2f" % (csob)}
                    drs = {osCode: "%.2f" % (csob)}
                    con.execute(
                        vouchers.insert(),
                        {
                            "vouchernumber": "1",
                            "voucherdate": str(newYearStart),
                            "entrydate": str(newYearStart),
                            "narration": "jv for stock",
                            "drs": drs,
                            "crs": crs,
                            "orgcode": newOrgCode,
                            "vouchertype": "journal",
                        },
                    )
                # Customer / supplier Migration
                oldContacts = con.execute(
                    "select * from customerandsupplier where orgcode = %d" % (orgCode)
                )
                for row in oldContacts:
                    contact_data = {
                        "custname": row["custname"],
                        "custaddr": row["custaddr"],
                        "custphone": row["custphone"],
                        "custemail": row["custemail"],
                        "custfax": row["custfax"],
                        "custpan": row["custpan"],
                        "custtan": row["custtan"],
                        "state": row["state"],
                        "custdoc": row["custdoc"],
                        "csflag": row["csflag"],
                        "pincode": row["pincode"],
                        "bankdetails": row["bankdetails"],
                        "orgcode": newOrgCode,
                        "gst_reg_type": row["gst_reg_type"],
                        "gst_party_type": row["gst_party_type"],
                        "tin": row["tin"],
                        "country": row["country"],
                    }
                    gstin = row["gstin"]
                    if gstin:
                        contact_data = contact_data.update({"gstin": gstin})
                    con.execute(
                        customerandsupplier.insert(),
                        contact_data,
                    )
                ## Category Migration

                # old category code to new category code referrence dict
                oldToNewCatCodes = {}
                oldCategoryData = con.execute(
                    "select * from categorysubcategories where orgcode = %d and subcategoryof is null"
                    % (orgCode)
                )
                oldCategoryRows = oldCategoryData.fetchall()
                for category in oldCategoryRows:
                    children = [category]
                    while len(children):
                        cat = children.pop()
                        parentCode = None
                        if cat["subcategoryof"] in oldToNewCatCodes:
                            parentCode = oldToNewCatCodes[cat["subcategoryof"]]
                        con.execute(
                            categorysubcategories.insert(),
                            {
                                "categoryname": cat["categoryname"],
                                "subcategoryof": parentCode,
                                "orgcode": newOrgCode,
                            },
                        )
                        newCatCodeData = con.execute(
                            "select categorycode from categorysubcategories where orgcode = %d and categoryname = '%s'"
                            % (newOrgCode, cat["categoryname"])
                        )
                        newCatCodeRow = newCatCodeData.fetchone()
                        newCatCode = newCatCodeRow["categorycode"]
                        oldToNewCatCodes[cat["categorycode"]] = newCatCode
                        grandchildrenData = con.execute(
                            "select * from categorysubcategories where orgcode = %d and subcategoryof = %d"
                            % (orgCode, cat["categorycode"])
                        )
                        if grandchildrenData.rowcount > 0:
                            children.extend(grandchildrenData.fetchall())
                oldCategorySpecData = con.execute(
                    "select * from categoryspecs where orgcode = %d" % (orgCode)
                )
                oldCategorySpecRows = oldCategorySpecData.fetchall()
                for categorySpec in oldCategorySpecRows:
                    con.execute(
                        categoryspecs.insert(),
                        {
                            "attrname": categorySpec["attrname"],
                            "attrtype": categorySpec["attrtype"],
                            "productcount": categorySpec["productcount"],
                            "categorycode": oldToNewCatCodes[
                                categorySpec["categorycode"]
                            ],
                            "orgcode": newOrgCode,
                        },
                    )

                ## Product/ Service Migration
                oldProductData = con.execute(
                    "select * from product where orgcode = %d" % (orgCode)
                )
                oldProductRows = oldProductData.fetchall()

                # old product code to new product code reference dict
                oldToNewProdCodes = {}
                for prodRow in oldProductRows:
                    categoryCode = None
                    if (
                        prodRow["categorycode"] is not None
                        and prodRow["categorycode"] in oldToNewCatCodes
                    ):
                        categoryCode = oldToNewCatCodes[prodRow["categorycode"]]

                    openingStock = float(0)
                    if prodRow["gscode"] == "19":
                        stockData = stockonhandfun(con, orgCode, prodRow["productcode"], endDate)
                        openingStock = float(stockData["gkresult"][0]["balance"])

                    con.execute(
                        product.insert(),
                        {
                            "gscode": prodRow["gscode"],
                            "gsflag": prodRow["gsflag"],
                            "percentdiscount": prodRow["percentdiscount"],
                            "amountdiscount": prodRow["amountdiscount"],
                            "productdesc": prodRow["productdesc"],
                            "openingstock": openingStock,
                            "specs": prodRow["specs"],
                            "categorycode": categoryCode,
                            "uomid": prodRow["uomid"],
                            "prodsp": prodRow["prodsp"],
                            "prodmrp": prodRow["prodmrp"],
                            "orgcode": newOrgCode,
                        },
                    )
                    newProdData = con.execute(
                        "select productcode from product where orgcode = %d and productdesc = '%s'"
                        % (newOrgCode, prodRow["productdesc"])
                    )
                    newProdRow = newProdData.fetchone()
                    oldToNewProdCodes[prodRow["productcode"]] = newProdRow[
                        "productcode"
                    ]

                # Tax Migration
                oldTaxData = con.execute(
                    "select * from tax where orgcode = %d" % (orgCode)
                )
                oldTaxRows = oldTaxData.fetchall()
                for taxRow in oldTaxRows:
                    newProdCode = None
                    newCatCode = None
                    oldProdCode = taxRow["productcode"]
                    oldCatCode = taxRow["categorycode"]
                    if oldCatCode is not None and oldCatCode in oldToNewCatCodes:
                        newCatCode = oldToNewCatCodes[oldCatCode]
                    if oldProdCode is not None and oldProdCode in oldToNewProdCodes:
                        newProdCode = oldToNewProdCodes[oldProdCode]
                    con.execute(
                        tax.insert(),
                        {
                            "taxname": taxRow["taxname"],
                            "taxrate": taxRow["taxrate"],
                            "taxfromdate": taxRow["taxfromdate"],
                            "state": taxRow["state"],
                            "productcode": newProdCode,
                            "categorycode": newCatCode,
                            "orgcode": newOrgCode,
                        },
                    )

                # Godowns Migration
                oldGodowns = con.execute(
                    "select * from godown where orgcode = %d" % (orgCode)
                )
                for row in oldGodowns:
                    con.execute(
                        godown.insert(),
                        {
                            "goname": row["goname"],
                            "goaddr": row["goaddr"],
                            "gocontact": row["gocontact"],
                            "state": row["state"],
                            "contactname": row["contactname"],
                            "designation": row["designation"],
                            "orgcode": newOrgCode,
                        },
                    )
                # Old/New Godown Id's mapping
                oldgo = con.execute(
                    f"select * from godown where orgcode={orgCode}"
                ).fetchall()
                godownMap = {}
                for i in oldgo:
                    newgo = con.execute(
                        f"select * from godown where orgcode={newOrgCode} and goname='%s'"
                        % (i["goname"])
                    ).fetchone()
                    godownMap[i["goid"]] = newgo["goid"]

                # Godown Producs
                oldGp = con.execute(
                    "select * from goprod where orgcode = %d" % (orgCode)
                )
                product_opening_balances = {}
                for row in oldGp:
                    oldProdCode = row["productcode"]
                    newProdCode = None
                    if oldProdCode is not None and oldProdCode in oldToNewProdCodes:
                        newProdCode = oldToNewProdCodes[oldProdCode]
                    if newProdCode not in product_opening_balances:
                        product_opening_balances[newProdCode] = 0.0
                    stockData = godownwise_stock_on_hand(
                        con,
                        orgCode,
                        oldstartDate,
                        endDate,
                        oldProdCode,
                        row["goid"],
                    )
                    product_opening_balances[newProdCode] += stockData["balance"]
                    con.execute(
                        goprod.insert(),
                        {
                            "goid": godownMap[row["goid"]],
                            "productcode": newProdCode,
                            "goopeningstock": stockData["balance"],
                            "openingstockvalue": stockData["value"],
                            "orgcode": newOrgCode,
                        },
                    )

                for product_code, balance in product_opening_balances.items():
                    con.execute(
                        product
                        .update()
                        .where(product.c.productcode == product_code)
                        .values(openingstock = balance)
                    )
                # User Godowns migration
                oldUserGodowns = con.execute(
                    f"select * from usergodown where orgcode={orgCode}"
                ).fetchall()
                oldgi = con.execute(
                    f"select * from users where userrole=3 and orgcode={orgCode}"
                ).fetchall()
                gimap = {}
                for i in oldgi:
                    newgi = con.execute(
                        f"select userid from users where userrole=3 and orgcode={newOrgCode} and username='%s'"
                        % (i["username"])
                    ).fetchone()
                    gimap[i["userid"]] = newgi["userid"]
                for row in oldUserGodowns:
                    con.execute(
                        usergodown.insert(),
                        {
                            "goid": godownMap[row["goid"]],
                            "userid": gimap[row["userid"]],
                            "orgcode": newOrgCode,
                        },
                    )
                # set existing org's roflag to 1
                gk_log(__name__).info("setting roflag to 1")
                con.execute(
                    organisation.update()
                    .where(organisation.c.orgcode == orgCode)
                    .values({"roflag": 1})
                )
                payload = {
                    "neworgcode": newOrgCode,
                    "yearstart": newYearStart,
                    "yearend": newYearEnd,
                }
                return {"gkstatus": enumdict["Success"], "gkresult": payload}


    def getNextOrgCode(self, prevOrgCode, con):
        """
        Purpose:
        gets the orgcode for the given organization for subsequent financial year.
        description:
        When user does a rollover for an organisation without closing books,
        then we need to reset the opening balances for all accounts after closing books.
        This function will provide the needed orgcode of the organisation for the subsequent financialstart.
        The function will take orgcode of the organisation who's books were just closed.
        Then will return the subsequent orgcode.
        """
        curEndYearRecord = con.execute(
            select([organisation.c.yearend, organisation.c.orgname]).where(
                organisation.c.orgcode == prevOrgCode
            )
        )
        curEndRow = curEndYearRecord.fetchone()
        endYear = curEndRow["yearend"]
        nextYearStart = endYear + timedelta(days=1)
        nextYearEnd = nextYearStart + timedelta(days=364)
        nxtOrgCodeRecord = con.execute(
            select([organisation.c.orgcode]).where(
                and_(
                    organisation.c.yearstart == nextYearStart,
                    organisation.c.yearend == nextYearEnd,
                    organisation.c.orgname == curEndRow["orgname"],
                )
            )
        )
        nxtOrgCodeRow = nxtOrgCodeRecord.fetchone()
        nxtOrgcode = nxtOrgCodeRow["orgcode"]
        return nxtOrgcode
