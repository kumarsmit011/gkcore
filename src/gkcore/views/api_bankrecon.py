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
"Ishan Masdekar " <imasdekar@dff.org.in>
"Navin Karkera" <navin@dff.org.in>
"Mohd. Talha Pawaty" <mtalha456@gmail.com>
"""
# imports contain sqlalchemy modules,
# enumdict containing status messages,
# eng for executing raw sql,
# gkdb from models for all the alchemy expressed tables.
# view_default for setting default route
# view_config for per method configurations predicates etc.
from gkcore import eng, enumdict
from gkcore.utils import authCheck
from gkcore.models.gkdb import (
    bankrecon,
    vouchers,
    accounts,
    organisation,
    groupsubgroups,
)
from sqlalchemy.sql import select
from sqlalchemy.sql.expression import null
from gkcore.views.reports.helpers.balance import calculateBalance
from sqlalchemy.engine.base import Connection
from sqlalchemy import and_
from pyramid.view import view_defaults, view_config
from datetime import datetime

def get_bank_transactions(
        connection, accountCode, calculateFrom, calculateTo, is_cleared=False
):
    """Fetches bank reconciliation table data along with related voucher details.
    This method also returns total Drs and Crs in the list.
    """

    result = connection.execute(
        select(
            [
                bankrecon,
                vouchers.c.voucherdate,
                vouchers.c.narration,
                vouchers.c.vouchernumber,
            ]
        )
        .where(
            and_(
                bankrecon.c.accountcode == accountCode,
                (
                    bankrecon.c.clearancedate != null()
                    if is_cleared
                    else bankrecon.c.clearancedate == null()
                ),
                vouchers.c.voucherdate >= calculateFrom,
                vouchers.c.voucherdate <= calculateTo,
            )
        )
        .order_by(bankrecon.c.reconcode)
        .select_from(
            bankrecon.join(
                vouchers, bankrecon.c.vouchercode == vouchers.c.vouchercode
            )
        )
    )
    recongrid = []
    uctotaldr = 0
    uctotalcr = 0
    for record in result:
        account = connection.execute(
            select([accounts.c.accountname]).where(
                accounts.c.accountcode == record["accountcode"]
            )
        ).fetchone()
        reconRow = {
            "reconcode": record["reconcode"],
            "date": datetime.strftime(record["voucherdate"], "%d-%m-%Y"),
            "particulars": account["accountname"],
            "voucher_code": record["vouchercode"],
            "voucher_no": record["vouchernumber"],
            "narration": record["narration"],
        }
        if record["entry_type"] == "Dr":
            reconRow.update({"dr": record["amount"]})
            uctotaldr += record["amount"]
        else:
            reconRow.update({"cr": record["amount"]})
            uctotalcr += record["amount"]

        reconRow["clearancedate"] = datetime.strftime(
            record["clearancedate"], "%d-%m-%Y"
        ) if record["clearancedate"] else ""
        reconRow["memo"] = record["memo"] or ""
        recongrid.append(reconRow)
    return {"recongrid": recongrid, "uctotaldr": uctotaldr, "uctotalcr": uctotalcr}

"""
default route to be attached to this resource.
refer to the __init__.py of main gkcore package for details on routing url
"""


@view_defaults(route_name="bankrecon")
class bankreconciliation(object):
    # constructor will initialise request.
    def __init__(self, request):
        self.request = request
        self.con = Connection

    @view_config(request_method="GET", renderer="json")
    def banklist(self):
        try:
            token = self.request.headers["gktoken"]
        except:
            return {"gkstatus": enumdict["UnauthorisedAccess"]}
        authDetails = authCheck(token)
        if authDetails["auth"] == False:
            return {"gkstatus": enumdict["UnauthorisedAccess"]}
        else:
            with eng.begin() as con:
                result = con.execute(
                    select([accounts.c.accountname, accounts.c.accountcode])
                    .where(
                        and_(
                            accounts.c.orgcode == authDetails["orgcode"],
                            accounts.c.groupcode
                            == (
                                select([groupsubgroups.c.groupcode]).where(
                                    and_(
                                        groupsubgroups.c.orgcode
                                        == authDetails["orgcode"],
                                        groupsubgroups.c.groupname == str("Bank"),
                                    )
                                )
                            ),
                        )
                    )
                    .order_by(accounts.c.accountname)
                )
                accs = []
                for row in result:
                    accs.append(
                        {
                            "accountcode": row["accountcode"],
                            "accountname": row["accountname"],
                        }
                    )
                return {"gkstatus": enumdict["Success"], "gkresult": accs}

    @view_config(request_method="GET", request_param="recon=uncleared", renderer="json")
    def getUnclearedTransactions(self):
        try:
            token = self.request.headers["gktoken"]
        except:
            return {"gkstatus": enumdict["UnauthorisedAccess"]}
        authDetails = authCheck(token)
        if authDetails["auth"] == False:
            return {"gkstatus": enumdict["UnauthorisedAccess"]}
        else:
            with eng.begin() as con:
                accountCode = self.request.params["accountcode"]
                calculateFrom = datetime.strptime(
                    str(self.request.params["calculatefrom"]), "%Y-%m-%d"
                )
                calculateTo = datetime.strptime(
                    str(self.request.params["calculateto"]), "%Y-%m-%d"
                )
                recongrid = get_bank_transactions(
                    con, accountCode, calculateFrom, calculateTo
                )
                finStartData = con.execute(
                    select([organisation.c.yearstart]).where(
                        organisation.c.orgcode == authDetails["orgcode"]
                    )
                )
                finstartrow = finStartData.fetchone()
                reconstmt = self.reconStatement(
                    con,
                    accountCode,
                    str(self.request.params["calculatefrom"]),
                    str(self.request.params["calculateto"]),
                    recongrid["uctotaldr"],
                    recongrid["uctotalcr"],
                    str(finstartrow["yearstart"]),
                )
                return {
                    "gkstatus": enumdict["Success"],
                    "gkresult": {
                        "recongrid": recongrid["recongrid"],
                        "reconstatement": reconstmt,
                    },
                }


    @view_config(request_method="PUT", renderer="json")
    def updateRecon(self):
        try:
            token = self.request.headers["gktoken"]
        except:
            return {"gkstatus": enumdict["UnauthorisedAccess"]}
        authDetails = authCheck(token)
        if authDetails["auth"] == False:
            return {"gkstatus": enumdict["UnauthorisedAccess"]}
        else:
            with eng.begin() as con:
                dataset = self.request.json_body
                accountCode = dataset.pop("accountcode")
                calculateFrom = datetime.strptime(
                    str(dataset.pop("calculatefrom")), "%Y-%m-%d"
                )
                calculateTo = datetime.strptime(
                    str(dataset.pop("calculateto")), "%Y-%m-%d"
                )
                con.execute(
                    bankrecon.update()
                    .where(bankrecon.c.reconcode == dataset["reconcode"])
                    .values(dataset)
                )
                recongrid = get_bank_transactions(
                    con, accountCode, calculateFrom, calculateTo
                )
                finStartData = con.execute(
                    select([organisation.c.yearstart]).where(
                        organisation.c.orgcode == authDetails["orgcode"]
                    )
                )
                finstartrow = finStartData.fetchone()
                reconstmt = self.reconStatement(
                    con,
                    accountCode,
                    str(self.request.json_body["calculatefrom"]),
                    str(self.request.json_body["calculateto"]),
                    recongrid["uctotaldr"],
                    recongrid["uctotalcr"],
                    str(finstartrow["yearstart"]),
                )
                return {
                    "gkstatus": enumdict["Success"],
                    "gkresult": {"reconstatement": reconstmt},
                }

    @view_config(request_method="GET", request_param="recon=cleared", renderer="json")
    def getClearedTransactions(self):
        try:
            token = self.request.headers["gktoken"]
        except:
            return {"gkstatus": enumdict["UnauthorisedAccess"]}
        authDetails = authCheck(token)
        if authDetails["auth"] == False:
            return {"gkstatus": enumdict["UnauthorisedAccess"]}
        else:
            with eng.begin() as con:
                accountCode = self.request.params["accountcode"]
                calculateFrom = datetime.strptime(
                    str(self.request.params["calculatefrom"]), "%Y-%m-%d"
                )
                calculateTo = datetime.strptime(
                    str(self.request.params["calculateto"]), "%Y-%m-%d"
                )
                recongrid = get_bank_transactions(
                    con, accountCode, calculateFrom, calculateTo, is_cleared=True
                )
                finStartData = con.execute(
                    select([organisation.c.yearstart]).where(
                        organisation.c.orgcode == authDetails["orgcode"]
                    )
                )
                finstartrow = finStartData.fetchone()
                reconstmt = self.reconStatement(
                    con,
                    accountCode,
                    str(self.request.params["calculatefrom"]),
                    str(self.request.params["calculateto"]),
                    recongrid["uctotaldr"],
                    recongrid["uctotalcr"],
                    str(finstartrow["yearstart"]),
                )
                return {
                    "gkstatus": enumdict["Success"],
                    "gkresult": {**recongrid, "reconstatement": reconstmt},
                }

    def reconStatement(
        self,
        connection,
        accountCode,
        calculateFrom,
        calculateTo,
        uctotaldr,
        uctotalcr,
        financialStart,
    ):
        calbaldata = calculateBalance(
            connection, accountCode, financialStart, calculateFrom, calculateTo
        )
        recostmt = [{"particulars": "RECONCILIATION STATEMENT", "amount": "AMOUNT"}]
        midTotal = 0.00
        BankBal = 0.00
        if calbaldata["baltype"] == "Dr" or calbaldata["curbal"] == 0:
            recostmt.append(
                {
                    "particulars": "Balance as per our book (Debit) on "
                    + datetime.strftime(
                        datetime.strptime(str(calculateTo), "%Y-%m-%d").date(),
                        "%d-%m-%Y",
                    ),
                    "amount": "%.2f" % (calbaldata["curbal"]),
                }
            )
            recostmt.append(
                {
                    "particulars": "Add: Cheques issued but not presented",
                    "amount": "%.2f" % (uctotalcr),
                }
            )
            midTotal = calbaldata["curbal"] + uctotalcr
            recostmt.append({"particulars": "", "amount": "%.2f" % (abs(midTotal))})
            recostmt.append(
                {
                    "particulars": "Less: Cheques deposited but not cleared",
                    "amount": "%.2f" % (uctotaldr),
                }
            )
            BankBal = midTotal - uctotaldr
        elif calbaldata["baltype"] == "Cr":
            recostmt.append(
                {
                    "particulars": "Balance as per our book (Credit) on "
                    + datetime.strftime(
                        datetime.strptime(str(calculateTo), "%Y-%m-%d").date(),
                        "%d-%m-%Y",
                    ),
                    "amount": "%.2f" % (calbaldata["curbal"]),
                }
            )
            recostmt.append(
                {
                    "particulars": "Less: Cheques issued but not presented",
                    "amount": "%.2f" % (uctotalcr),
                }
            )
            midTotal = calbaldata["curbal"] - uctotalcr
            if midTotal >= 0:
                recostmt.append({"particulars": "", "amount": "%.2f" % (abs(midTotal))})
                recostmt.append(
                    {
                        "particulars": "Add: Cheques deposited but not cleared",
                        "amount": "%.2f" % (uctotaldr),
                    }
                )
                BankBal = abs(midTotal) + uctotaldr
            else:
                recostmt.append({"particulars": "", "amount": "%.2f" % (abs(midTotal))})
                recostmt.append(
                    {
                        "particulars": "Less: Cheques deposited but not cleared",
                        "amount": "%.2f" % (uctotaldr),
                    }
                )
                BankBal = abs(midTotal) - uctotaldr
        if BankBal < 0:
            recostmt.append(
                {
                    "particulars": "Balance as per Bank (Debit)",
                    "amount": "%.2f" % (abs(BankBal)),
                }
            )

        if BankBal > 0:
            recostmt.append(
                {
                    "particulars": "Balance as per Bank (Credit)",
                    "amount": "%.2f" % (abs(BankBal)),
                }
            )

        if BankBal == 0:
            recostmt.append(
                {
                    "particulars": "Balance as per Bank",
                    "amount": "%.2f" % (abs(BankBal)),
                }
            )
        return recostmt
