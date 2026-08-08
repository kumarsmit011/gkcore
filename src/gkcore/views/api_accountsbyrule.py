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
"Ishan Masdekar " <imasdekar@dff.org.in>
"Navin Karkera" <navin@dff.org.in>
"""


from gkcore import eng, enumdict
from gkcore.utils import authCheck
from gkcore.models.gkdb import accounts, groupsubgroups
from sqlalchemy.sql import select
import json
from sqlalchemy.engine.base import Connection
from sqlalchemy import and_
from pyramid.request import Request
from pyramid.response import Response
from pyramid.view import view_defaults, view_config
from sqlalchemy.ext.baked import Result


@view_defaults(route_name="accountsbyrule", request_method="GET")
class api_accountsbyrule(object):
    def __init__(self, request):
        self.request = Request
        self.request = request
        self.con = Connection

    @view_config(request_param="type=contra", renderer="json")
    def contra(self):
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
                contraAccs = self.con.execute(
                    "select accountname , accountcode from accounts where groupcode in (select groupcode from groupsubgroups where groupname in ('Bank','Cash')and orgcode = %d) and orgcode = %d order by accountname"
                    % (authDetails["orgcode"], authDetails["orgcode"])
                )
                contraList = []
                for contraRow in contraAccs:
                    contraList.append(
                        {
                            "accountname": contraRow["accountname"],
                            "accountcode": contraRow["accountcode"],
                        }
                    )
                return {"gkstatus": enumdict["Success"], "gkresult": contraList}
            except:
                return {"gkstatus": enumdict["ConnectionFailed"]}
            finally:
                self.con.close()

    @view_config(request_param="type=journal", renderer="json")
    def journal(self):
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
                journalAccs = self.con.execute(
                    "select accountname , accountcode from accounts where groupcode not in (select groupcode from groupsubgroups where groupname in ('Bank','Cash')and orgcode = %d) and orgcode = %d order by accountname"
                    % (authDetails["orgcode"], authDetails["orgcode"])
                )
                journalList = []
                for contraRow in journalAccs:
                    journalList.append(
                        {
                            "accountname": contraRow["accountname"],
                            "accountcode": contraRow["accountcode"],
                        }
                    )
                return {"gkstatus": enumdict["Success"], "gkresult": journalList}
            except:
                return {"gkstatus": enumdict["ConnectionFailed"]}
            finally:
                self.con.close()

    @view_config(request_param="type=payment", renderer="json")
    def payment(self):
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
                if self.request.params["side"] == "Dr":
                    try:
                        accs = self.con.execute(
                            "select accountname , accountcode from accounts where orgcode = %d and accountname not in ('Opening Stock','Closing Stock','Stock at the Beginning','Profit & Loss','Income & Expenditure') and groupcode not in (select groupcode from groupsubgroups where groupname in ('Bank','Cash') and orgcode = %d ) order by accountname"
                            % (authDetails["orgcode"], authDetails["orgcode"])
                        )
                        list = []
                        for row in accs:
                            list.append(
                                {
                                    "accountname": row["accountname"],
                                    "accountcode": row["accountcode"],
                                }
                            )
                        return {"gkstatus": enumdict["Success"], "gkresult": list}
                    except:
                        return {"gkstatus": enumdict["ConnectionFailed"]}
                if self.request.params["side"] == "Cr":
                    try:
                        accs = self.con.execute(
                            "select accountname , accountcode from accounts where accountname not in ('Opening Stock','Closing Stock','Stock at the Beginning','Profit & Loss','Income & Expenditure') and    groupcode in (select groupcode from groupsubgroups where groupname in ('Bank','Cash','Direct Income','Indirect Income','Direct Expense','Indirect Expense') or subgroupof in (select groupcode from groupsubgroups where groupname in ('Direct Income','Indirect Income','Direct Expense','Indirect Expense') and orgcode = %d) and orgcode = %d) and orgcode = %d order by accountname"
                            % (
                                authDetails["orgcode"],
                                authDetails["orgcode"],
                                authDetails["orgcode"],
                            )
                        )
                        list = []
                        for row in accs:
                            list.append(
                                {
                                    "accountname": row["accountname"],
                                    "accountcode": row["accountcode"],
                                }
                            )
                        return {"gkstatus": enumdict["Success"], "gkresult": list}
                    except:
                        return {"gkstatus": enumdict["ConnectionFailed"]}
            except:
                return {"gkstatus": enumdict["ConnectionFailed"]}
            finally:
                self.con.close()

    @view_config(request_param="type=receipt", renderer="json")
    def receipt(self):
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
                if self.request.params["side"] == "Cr":
                    try:
                        accs = self.con.execute(
                            "select accountname , accountcode from accounts where orgcode = %d and accountname not in ('Opening Stock','Closing Stock','Stock at the Beginning','Profit & Loss','Income & Expenditure') and groupcode not in (select groupcode from groupsubgroups where groupname in ('Bank','Cash') and orgcode = %d ) order by accountname"
                            % (authDetails["orgcode"], authDetails["orgcode"])
                        )
                        list = []
                        for row in accs:
                            list.append(
                                {
                                    "accountname": row["accountname"],
                                    "accountcode": row["accountcode"],
                                }
                            )
                        return {"gkstatus": enumdict["Success"], "gkresult": list}
                    except:
                        return {"gkstatus": enumdict["ConnectionFailed"]}
                if self.request.params["side"] == "Dr":
                    try:
                        accs = self.con.execute(
                            "select accountname , accountcode from accounts where accountname not in ('Opening Stock','Closing Stock','Stock at the Beginning','Profit & Loss','Income & Expenditure') and    groupcode in (select groupcode from groupsubgroups where groupname in ('Bank','Cash','Direct Income','Indirect Income','Direct Expense','Indirect Expense') or subgroupof in (select groupcode from groupsubgroups where groupname in ('Direct Income','Indirect Income','Direct Expense','Indirect Expense') and orgcode = %d) and orgcode = %d) and orgcode = %d order by accountname"
                            % (
                                authDetails["orgcode"],
                                authDetails["orgcode"],
                                authDetails["orgcode"],
                            )
                        )
                        list = []
                        for row in accs:
                            list.append(
                                {
                                    "accountname": row["accountname"],
                                    "accountcode": row["accountcode"],
                                }
                            )
                        return {"gkstatus": enumdict["Success"], "gkresult": list}
                    except:
                        return {"gkstatus": enumdict["ConnectionFailed"]}
            except:
                return {"gkstatus": enumdict["ConnectionFailed"]}
            finally:
                self.con.close()

    @view_config(request_param="type=sales", renderer="json")
    def sales(self):
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
                if self.request.params["side"] == "Cr":
                    try:
                        accs = self.con.execute(
                            "select accountname , accountcode from accounts where orgcode = %d and accountname not in ('Profit & Loss','Income & Expenditure') and groupcode in (select groupcode from groupsubgroups where groupname in ('Direct Income', 'Indirect Income','Current Liabilities' ) or subgroupof in (select groupcode from groupsubgroups where groupname in ('Direct Income', 'Indirect Income','Current Liabilities','Current Assets' )) and orgcode = %d ) order by accountname"
                            % (authDetails["orgcode"], authDetails["orgcode"])
                        )
                        list = []
                        for row in accs:
                            list.append(
                                {
                                    "accountname": row["accountname"],
                                    "accountcode": row["accountcode"],
                                }
                            )
                        return {"gkstatus": enumdict["Success"], "gkresult": list}
                    except:
                        return {"gkstatus": enumdict["ConnectionFailed"]}
                if self.request.params["side"] == "Dr":
                    try:
                        accs = self.con.execute(
                            "select accountname , accountcode from accounts where orgcode = %d and accountname not in ('Closing Stock', 'Stock at the Beginning') and groupcode in (select groupcode from groupsubgroups where subgroupof in  (select groupcode from groupsubgroups where groupname in('Current Assets','Current Liabilities' )and orgcode = %d)and orgcode = %d ) order by accountname"
                            % (
                                authDetails["orgcode"],
                                authDetails["orgcode"],
                                authDetails["orgcode"],
                            )
                        )
                        list = []
                        for row in accs:
                            list.append(
                                {
                                    "accountname": row["accountname"],
                                    "accountcode": row["accountcode"],
                                }
                            )
                        return {"gkstatus": enumdict["Success"], "gkresult": list}
                    except:
                        return {"gkstatus": enumdict["ConnectionFailed"]}
            except:
                return {"gkstatus": enumdict["ConnectionFailed"]}
            finally:
                self.con.close()

    @view_config(request_param="type=purchase", renderer="json")
    def purchase(self):
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
                if self.request.params["side"] == "Cr":
                    try:
                        accs = self.con.execute(
                            "select accountname , accountcode from accounts where orgcode = %d and accountname not in ('Closing Stock', 'Stock at the Beginning') and groupcode in (select groupcode from groupsubgroups where groupname in ('Bank','Cash') or subgroupof in (select groupcode from groupsubgroups where groupname in ( 'Current Liabilities','Current Assets') and orgcode = %d)   and orgcode = %d ) order by accountname"
                            % (
                                authDetails["orgcode"],
                                authDetails["orgcode"],
                                authDetails["orgcode"],
                            )
                        )
                        list = []
                        for row in accs:
                            list.append(
                                {
                                    "accountname": row["accountname"],
                                    "accountcode": row["accountcode"],
                                }
                            )
                        return {"gkstatus": enumdict["Success"], "gkresult": list}
                    except:
                        return {"gkstatus": enumdict["ConnectionFailed"]}
                if self.request.params["side"] == "Dr":
                    try:
                        accs = self.con.execute(
                            "select accountname , accountcode from accounts where orgcode = %d and accountname != 'Opening Stock' and groupcode in (select groupcode from groupsubgroups where groupname in ('Direct Expense','Indirect Expense') or subgroupof in (select groupcode from groupsubgroups where groupname in ('Direct Expense','Indirect Expense','Current Liabilities','Current Assets'))and orgcode = %d ) order by accountname"
                            % (authDetails["orgcode"], authDetails["orgcode"])
                        )
                        list = []
                        for row in accs:
                            list.append(
                                {
                                    "accountname": row["accountname"],
                                    "accountcode": row["accountcode"],
                                }
                            )
                        return {"gkstatus": enumdict["Success"], "gkresult": list}
                    except:
                        return {"gkstatus": enumdict["ConnectionFailed"]}
            except:
                return {"gkstatus": enumdict["ConnectionFailed"]}
            finally:
                self.con.close()

    @view_config(request_param="type=salesreturn", renderer="json")
    def salesreturn(self):
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
                if self.request.params["side"] == "Cr":
                    try:
                        accs = self.con.execute(
                            "select accountname , accountcode from accounts where orgcode = %d and groupcode in (select groupcode from groupsubgroups where groupname in ('Bank','Cash','Sundry Creditors for Purchase','Sundry Creditors for Expense') and orgcode = %d ) order by accountname"
                            % (authDetails["orgcode"], authDetails["orgcode"])
                        )
                        list = []
                        for row in accs:
                            list.append(
                                {
                                    "accountname": row["accountname"],
                                    "accountcode": row["accountcode"],
                                }
                            )
                        return {"gkstatus": enumdict["Success"], "gkresult": list}
                    except:
                        return {"gkstatus": enumdict["ConnectionFailed"]}
                if self.request.params["side"] == "Dr":
                    try:
                        accs = self.con.execute(
                            "select accountname , accountcode from accounts where orgcode = %d and accountname not in ('Opening Stock') and groupcode in (select groupcode from groupsubgroups where groupname in ('Direct Expense','Indirect Expense' or subgroupof in (select groupcode from groupsubgroups where groupname in 'Direct Expense','Indirect Expense','Current Liabilities')) and orgcode = %d) order by accountname"
                            % (authDetails["orgcode"], authDetails["orgcode"])
                        )
                        list = []
                        for row in accs:
                            list.append(
                                {
                                    "accountname": row["accountname"],
                                    "accountcode": row["accountcode"],
                                }
                            )
                        return {"gkstatus": enumdict["Success"], "gkresult": list}
                    except:
                        return {"gkstatus": enumdict["ConnectionFailed"]}
            except:
                return {"gkstatus": enumdict["ConnectionFailed"]}
            finally:
                self.con.close()

    @view_config(request_param="type=purchasereturn", renderer="json")
    def purchasereturn(self):
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
                if self.request.params["side"] == "Cr":
                    try:
                        accs = self.con.execute(
                            "select accountname , accountcode from accounts where orgcode = %d and accountname not in ('Profit & Loss','Income & Expenditure') and groupcode in (select groupcode from groupsubgroups where groupname in ('Direct Income','Indirect Income' or subgroupof in(select groupcode from groupsubgroups where groupname in ('Direct Income','Indirect Income','Current Liabilities')) ) and orgcode = %d) order by accountname"
                            % (authDetails["orgcode"], authDetails["orgcode"])
                        )
                        list = []
                        for row in accs:
                            list.append(
                                {
                                    "accountname": row["accountname"],
                                    "accountcode": row["accountcode"],
                                }
                            )
                        return {"gkstatus": enumdict["Success"], "gkresult": list}
                    except:
                        return {"gkstatus": enumdict["ConnectionFailed"]}
                if self.request.params["side"] == "Dr":
                    try:
                        accs = self.con.execute(
                            "select accountname , accountcode from accounts where orgcode = %d and groupcode in (select groupcode from groupsubgroups where groupname in ('Bank','Cash','Sundry Debtors')and orgcode = %d) order by accountname"
                            % (authDetails["orgcode"], authDetails["orgcode"])
                        )
                        list = []
                        for row in accs:
                            list.append(
                                {
                                    "accountname": row["accountname"],
                                    "accountcode": row["accountcode"],
                                }
                            )
                        return {"gkstatus": enumdict["Success"], "gkresult": list}
                    except:
                        return {"gkstatus": enumdict["ConnectionFailed"]}
            except:
                return {"gkstatus": enumdict["ConnectionFailed"]}
            finally:
                self.con.close()

    @view_config(request_param="type=debitnote", renderer="json")
    def debitnote(self):
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
                if self.request.params["side"] == "Cr":
                    try:
                        accs = self.con.execute(
                            "select accountname , accountcode from accounts where orgcode = %d and accountname not in ('Profit & Loss','Income & Expenditure') and groupcode in (select groupcode from groupsubgroups where groupname in ('Direct Income','Indirect Income') and orgcode = %d)  order by accountname"
                            % (authDetails["orgcode"], authDetails["orgcode"])
                        )
                        list = []
                        for row in accs:
                            list.append(
                                {
                                    "accountname": row["accountname"],
                                    "accountcode": row["accountcode"],
                                }
                            )
                        return {"gkstatus": enumdict["Success"], "gkresult": list}
                    except:
                        return {"gkstatus": enumdict["ConnectionFailed"]}
                if self.request.params["side"] == "Dr":
                    try:
                        accs = self.con.execute(
                            "select accountname , accountcode from accounts where orgcode = %d and groupcode in (select groupcode from groupsubgroups where groupname in ('Bank','Cash','Sundry Debtors')and orgcode = %d)  order by accountname"
                            % (authDetails["orgcode"], authDetails["orgcode"])
                        )
                        list = []
                        for row in accs:
                            list.append(
                                {
                                    "accountname": row["accountname"],
                                    "accountcode": row["accountcode"],
                                }
                            )
                        return {"gkstatus": enumdict["Success"], "gkresult": list}
                    except:
                        return {"gkstatus": enumdict["ConnectionFailed"]}
            except:
                return {"gkstatus": enumdict["ConnectionFailed"]}
            finally:
                self.con.close()

    @view_config(request_param="type=creditnote", renderer="json")
    def creditnote(self):
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
                if self.request.params["side"] == "Cr":
                    try:
                        accs = self.con.execute(
                            "select accountname , accountcode from accounts where orgcode = %d and groupcode in (select groupcode from groupsubgroups where groupname in ('Bank','Cash','Sundry Creditors for Purchase','Sundry Creditors for Expense') and orgcode = %d)  order by accountname"
                            % (authDetails["orgcode"], authDetails["orgcode"])
                        )
                        list = []
                        for row in accs:
                            list.append(
                                {
                                    "accountname": row["accountname"],
                                    "accountcode": row["accountcode"],
                                }
                            )
                        return {"gkstatus": enumdict["Success"], "gkresult": list}
                    except:
                        return {"gkstatus": enumdict["ConnectionFailed"]}
                if self.request.params["side"] == "Dr":
                    try:
                        accs = self.con.execute(
                            "select accountname , accountcode from accounts where orgcode = %d and accountname not in ('Opening Stock') and groupcode in (select groupcode from groupsubgroups where groupname in ('Direct Expense','Indirect Expense')and orgcode = %d)  order by accountname"
                            % (authDetails["orgcode"], authDetails["orgcode"])
                        )
                        list = []
                        for row in accs:
                            list.append(
                                {
                                    "accountname": row["accountname"],
                                    "accountcode": row["accountcode"],
                                }
                            )
                        return {"gkstatus": enumdict["Success"], "gkresult": list}
                    except:
                        return {"gkstatus": enumdict["ConnectionFailed"]}
            except:
                return {"gkstatus": enumdict["ConnectionFailed"]}
            finally:
                self.con.close()

    @view_config(request_param="type=all", renderer="json")
    def allAcc(self):
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
                allAccs = self.con.execute(
                    "select accountname , accountcode from accounts where orgcode = %d order by accountname"
                    % (authDetails["orgcode"])
                )
                allList = []
                for contraRow in allAccs:
                    allList.append(
                        {
                            "accountname": contraRow["accountname"],
                            "accountcode": contraRow["accountcode"],
                        }
                    )
                return {"gkstatus": enumdict["Success"], "gkresult": allList}
            except:
                return {"gkstatus": enumdict["ConnectionFailed"]}
            finally:
                self.con.close()
