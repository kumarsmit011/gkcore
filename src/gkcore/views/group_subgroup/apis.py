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
"Rupali Badgujar" <rupalibadgujar1234@gmail.com>
"""


from gkcore import eng, enumdict
from gkcore.models import gkdb
from gkcore.models.gkdb import groupsubgroups
from gkcore.views.group_subgroup.schemas import GroupSubgroup, GroupSubgroupUpdate
from sqlalchemy.sql import select, update, insert, delete
from sqlalchemy.engine.base import Connection
from sqlalchemy import and_, or_
from pyramid.request import Request
from pyramid.view import view_defaults, view_config
import gkcore
from gkcore.utils import authCheck, getUserRole
from sqlalchemy.sql.expression import null
from gkcore.models.gkdb import groupsubgroups


@view_defaults(route_name="groups_subgroups", renderer="json_extended")
class api_groups_subgroups(object):
    def __init__(self, request):
        self.request = request

    @view_config(request_method="POST")
    def add_group_subgroup(self):
        """ API to add Groups and Subgroups.
        Requried Fields: Group/sub group name
        Optional Fields: Parent group
        """
        try:
            token = self.request.headers["gktoken"]
        except:
            return {"gkstatus": enumdict["UnauthorisedAccess"]}
        authDetails = authCheck(token)
        if authDetails["auth"] == False:
            return {"gkstatus": enumdict["UnauthorisedAccess"]}
        validated_data = GroupSubgroup.model_validate(
            self.request.json_body, context={"orgcode": authDetails["orgcode"]}
        )
        dataset = validated_data.model_dump()
        with eng.begin() as conn:
            dataset["orgcode"] = authDetails["orgcode"]
            result = conn.execute(
                insert(groupsubgroups)
                .values(dataset)
                .returning(groupsubgroups.c.groupcode)
            )
            return {
                "gkstatus": enumdict["Success"],
                "gkresult": result.scalar(),
            }


    @view_config(request_method="PUT")
    def update_group_subgroup(self):
        """ API to udpate Groups and Subgroups.
        Requried Fields: Group/sub group name, groupcode
        Optional Fields: Parent group
        """
        try:
            token = self.request.headers["gktoken"]
        except:
            return {"gkstatus": enumdict["UnauthorisedAccess"]}
        authDetails = authCheck(token)
        if authDetails["auth"] == False:
            return {"gkstatus": enumdict["UnauthorisedAccess"]}
        validated_data = GroupSubgroupUpdate.model_validate(
            self.request.json_body, context={"orgcode": authDetails["orgcode"]}
        )
        dataset = validated_data.model_dump()
        with eng.begin() as conn:
            groupcode = dataset.pop("groupcode")
            dataset["orgcode"] = authDetails["orgcode"]
            result = conn.execute(
                update(groupsubgroups)
                .where(groupsubgroups.c.groupcode == groupcode)
                .values(dataset)
                .returning(groupsubgroups.c.groupcode)
            )
            return {
                "gkstatus": enumdict["Success"],
                "gkresult": result.scalar(),
            }


    @view_config(request_method="DELETE")
    def delete_group_subgroup(self):
        """ API to delete Groups and Subgroups.
        Requried Fields: groupcode
        """
        try:
            token = self.request.headers["gktoken"]
        except:
            return {"gkstatus": gkcore.enumdict["UnauthorisedAccess"]}
        authDetails = authCheck(token)
        if authDetails["auth"] == False:
            return {"gkstatus": enumdict["UnauthorisedAccess"]}
        with eng.begin() as conn:
            dataset = self.request.json_body
            conn.execute(
                delete(groupsubgroups).where(
                    gkdb.groupsubgroups.c.groupcode == dataset["groupcode"]
                )
            )
            return {"gkstatus": enumdict["Success"]}


    @view_config(request_method="GET")
    def get_groups_subgroups(self):
        """ API to list Groups and Subgroups.
        Optional Parameters:
        - group_type: ["group", "subgroup"] `group_type` can be used to filter by groups
        and subgroups. If `group_type` is not provided, both will be listed.
        """
        try:
            token = self.request.headers["gktoken"]
        except:
            return {"gkstatus": enumdict["UnauthorisedAccess"]}
        authDetails = authCheck(token)
        if authDetails["auth"] == False:
            return {"gkstatus": enumdict["UnauthorisedAccess"]}

        group_type = self.request.params.get("group_type")

        with eng.connect() as conn:
            groupsubgroups_alias = groupsubgroups.alias()
            statement = (
                select(
                    [
                        groupsubgroups,
                        groupsubgroups_alias.c.groupname.label("parent_group_name")
                    ]
                )
                .select_from(
                    groupsubgroups.join(
                        groupsubgroups_alias,
                        groupsubgroups.c.subgroupof == groupsubgroups_alias.c.groupcode,
                        isouter=True
                    )
                )
                .where(
                    groupsubgroups.c.orgcode == authDetails["orgcode"]
                )
            )
            if group_type == "group":
                statement = statement.where(groupsubgroups.c.subgroupof == None)
            elif group_type == "subgroup":
                statement = statement.where(groupsubgroups.c.subgroupof != None)

            groups_subgroups = conn.execute(statement).fetchall()
            groups_subgroups = [
                dict(group_subgroup)
                for group_subgroup in groups_subgroups
            ]

            return {
                "gkstatus": gkcore.enumdict["Success"],
                "gkresult": groups_subgroups,
            }


@view_defaults(route_name="groupsubgroups")
class api_user(object):
    def __init__(self, request):
        self.request = Request
        self.request = request
        self.con = Connection

    @view_config(request_method="POST", renderer="json")
    def addSubgroup(self):
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
                dataset = self.request.json_body
                dataset["orgcode"] = authDetails["orgcode"]
                result = self.con.execute(gkdb.groupsubgroups.insert(), [dataset])
                if result.rowcount == 1:
                    result = self.con.execute(
                        select([gkdb.groupsubgroups.c.groupcode]).where(
                            and_(
                                gkdb.groupsubgroups.c.orgcode == authDetails["orgcode"],
                                gkdb.groupsubgroups.c.groupname == dataset["groupname"],
                            )
                        )
                    )
                    row = result.fetchone()
                    return {
                        "gkstatus": enumdict["Success"],
                        "gkresult": row["groupcode"],
                    }
                else:
                    return {"gkstatus": enumdict["ConnectionFailed"]}
            except:
                return {"gkstatus": enumdict["ConnectionFailed"]}
            finally:
                self.con.close()

    @view_config(route_name="groupallsubgroup", request_method="GET", renderer="json")
    def getGroupAllSubgroup(self):
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
                g = gkdb.groupsubgroups.alias("g")
                sg = gkdb.groupsubgroups.alias("sg")
                resultset = self.con.execute(
                    select(
                        [
                            (g.c.groupcode).label("groupcode"),
                            (g.c.groupname).label("groupname"),
                            (sg.c.groupcode).label("subgroupcode"),
                            (sg.c.groupname).label("subgroupname"),
                        ]
                    ).where(
                        and_(
                            g.c.groupcode == sg.c.subgroupof,
                            g.c.groupcode == self.request.matchdict["groupcode"],
                        )
                    )
                )
                grpsubs = []
                for row in resultset:
                    grpsubs.append(
                        {
                            "groupcode": row["groupcode"],
                            "groupname": row["groupname"],
                            "subgroupcode": row["subgroupcode"],
                            "subgroupname": row["subgroupname"],
                        }
                    )
                return {"gkstatus": gkcore.enumdict["Success"], "gkresult": grpsubs}
            except:
                return {"gkstatus": gkcore.enumdict["ConnectionFailed"]}
            finally:
                self.con.close()

    @view_config(route_name="groupsubgroup", request_method="GET", renderer="json")
    def getGroupSubgroup(self):
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

                g = gkdb.groupsubgroups.alias("g")
                sg = gkdb.groupsubgroups.alias("sg")

                resultset = self.con.execute(
                    select(
                        [
                            (g.c.groupcode).label("groupcode"),
                            (g.c.groupname).label("groupname"),
                            (sg.c.groupcode).label("subgroupcode"),
                            (sg.c.groupname).label("subgroupname"),
                        ]
                    ).where(
                        or_(
                            and_(
                                g.c.groupcode == self.request.matchdict["groupcode"],
                                g.c.subgroupof == null(),
                                sg.c.groupcode == self.request.matchdict["groupcode"],
                                sg.c.subgroupof == null(),
                            ),
                            and_(
                                g.c.groupcode == sg.c.subgroupof,
                                sg.c.groupcode == self.request.matchdict["groupcode"],
                            ),
                        )
                    )
                )
                row = resultset.fetchone()
                grpsub = {
                    "groupcode": row["groupcode"],
                    "groupname": row["groupname"],
                    "subgroupcode": row["subgroupcode"],
                    "subgroupname": row["subgroupname"],
                }
                return {"gkstatus": gkcore.enumdict["Success"], "gkresult": grpsub}
            except:
                return {"gkstatus": gkcore.enumdict["ConnectionFailed"]}
            finally:
                self.con.close()

    # This fuction return group code of groupsubgroups for organisation
    @view_config(
        route_name="groupsubgroups",
        request_param="orgbank",
        request_method="GET",
        renderer="json",
    )
    def getGroupSubgroupfororg(self):
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
                subgroupData = self.con.execute(
                    select([gkdb.groupsubgroups.c.groupcode]).where(
                        and_(
                            gkdb.groupsubgroups.c.groupname == "Bank",
                            gkdb.groupsubgroups.c.subgroupof
                            == (
                                select([gkdb.groupsubgroups.c.groupcode]).where(
                                    and_(
                                        gkdb.groupsubgroups.c.groupname
                                        == "Current Assets",
                                        gkdb.groupsubgroups.c.orgcode
                                        == (authDetails["orgcode"]),
                                    )
                                )
                            ),
                            gkdb.groupsubgroups.c.orgcode == (authDetails["orgcode"]),
                        )
                    )
                )
                subgroupcode = subgroupData.fetchone()

                return {
                    "gkstatus": gkcore.enumdict["Success"],
                    "gkresult": subgroupcode["groupcode"],
                }
            except:
                return {"gkstatus": gkcore.enumdict["ConnectionFailed"]}
            finally:
                self.con.close()

    @view_config(request_method="PUT", renderer="json")
    def editSubgroup(self):
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
                dataset = self.request.json_body
                dataset["orgcode"] = authDetails["orgcode"]
                result = self.con.execute(
                    gkdb.groupsubgroups.update()
                    .where(
                        and_(
                            gkdb.groupsubgroups.c.groupname == dataset["groupname"],
                            gkdb.groupsubgroups.c.orgcode == dataset["orgcode"],
                        )
                    )
                    .values(dataset)
                )
                return {"gkstatus": gkcore.enumdict["Success"]}
            except:
                return {"gkstatus": gkcore.enumdict["ConnectionFailed"]}
            finally:
                self.con.close()

    @view_config(request_method="GET", renderer="json")
    def getAllGroups(self):
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
                            gkdb.groupsubgroups.c.groupname,
                            gkdb.groupsubgroups.c.groupcode,
                        ]
                    )
                    .where(
                        and_(
                            gkdb.groupsubgroups.c.orgcode == authDetails["orgcode"],
                            gkdb.groupsubgroups.c.subgroupof == null(),
                        )
                    )
                    .order_by(gkdb.groupsubgroups.c.groupname)
                )
                grps = []
                for row in result:
                    grps.append(
                        {"groupname": row["groupname"], "groupcode": row["groupcode"]}
                    )
                grpbal = self.getGroupBalance(authDetails["orgcode"])
                return {
                    "gkstatus": gkcore.enumdict["Success"],
                    "gkresult": grps,
                    "baltbl": grpbal,
                }
            except:
                return {"gkstatus": gkcore.enumdict["ConnectionFailed"]}
            finally:
                self.con.close()

    @view_config(route_name="groupDetails", request_method="GET", renderer="json")
    def getSubgroupsByGroup(self):
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
                            gkdb.groupsubgroups.c.groupname,
                            gkdb.groupsubgroups.c.groupcode,
                        ]
                    )
                    .where(
                        and_(
                            gkdb.groupsubgroups.c.subgroupof
                            == self.request.matchdict["groupcode"]
                        )
                    )
                    .order_by(gkdb.groupsubgroups.c.groupname)
                )
                subs = []
                for row in result:
                    subs.append(
                        {
                            "subgroupname": row["groupname"],
                            "groupcode": row["groupcode"],
                        }
                    )
                return {"gkstatus": gkcore.enumdict["Success"], "gkresult": subs}
            except:
                return {"gkstatus": gkcore.enumdict["ConnectionFailed"]}
            finally:
                self.con.close()

    @view_config(request_method="GET", request_param="groupflatlist", renderer="json")
    def getGroupFlatList(self):
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
                gsData = self.con.execute(
                    select(
                        [groupsubgroups.c.groupname, groupsubgroups.c.groupcode]
                    ).where(groupsubgroups.c.orgcode == authDetails["orgcode"])
                )
                gsRows = gsData.fetchall()
                gsList = {}
                for row in gsRows:
                    gsList[row["groupname"]] = row["groupcode"]

                    # gsList.append({"groupname":row["groupname"],"groupcode":row["groupcode"]})
                return {"gkstatus": enumdict["Success"], "gkresult": gsList}
            except:
                return {"gkstatus": enumdict["ConnectionFailed"]}
            finally:
                self.con.close()

    @view_config(request_method="DELETE", renderer="json")
    def deleteSubgroup(self):
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
                userRole = userRoleData["gkresult"]["userrole"]
                dataset = self.request.json_body
                if userRole == -1:
                    result = self.con.execute(
                        gkdb.groupsubgroups.delete().where(
                            gkdb.groupsubgroups.c.groupcode == dataset["groupcode"]
                        )
                    )
                    return {"gkstatus": enumdict["Success"]}
                else:
                    {"gkstatus": enumdict["BadPrivilege"]}
            except:
                return {"gkstatus": gkcore.enumdict["ConnectionFailed"]}
            finally:
                self.con.close()

    def getGroupBalance(self, orgcode):
        typeData = self.con.execute(
            select([gkdb.organisation.c.orgtype]).where(
                gkdb.organisation.c.orgcode == orgcode
            )
        )
        typeRow = typeData.fetchone()
        liabilityTotal = 0.00
        assetsTotal = 0.00
        difference = 0.00
        groupBalanceTable = []
        profitgroups = [
            "Capital",
            "Reserves",
            "Loans(Liability)",
            "Current Liabilities",
            "Fixed Assets",
            "Investments",
            "Loans(Asset)",
            "Current Assets",
            "Miscellaneous Expenses(Asset)",
        ]
        nonprofitgroups = [
            "Corpus",
            "Reserves",
            "Loans(Liability)",
            "Current Liabilities",
            "Fixed Assets",
            "Investments",
            "Loans(Asset)",
            "Current Assets",
        ]
        if str(typeRow["orgtype"]) == "Not For Profit":
            groupBalanceTable.append("CORPUS & LIABILITIES")
            for groupRow in nonprofitgroups:
                if (
                    groupRow == "Current Liabilities"
                    or groupRow == "Reserves"
                    or groupRow == "Corpus"
                    or groupRow == "Loans(Liability)"
                ):
                    groupBalance = self.con.execute(
                        "select count(accountname) as NumberOfAccounts, sum(openingbal) as groupBalance from accounts where orgcode = %d and groupcode in (select groupcode from groupsubgroups where orgcode = %d and groupname = '%s' or subgroupof = (select groupcode from groupsubgroups where orgcode = %d and groupname = '%s'));"
                        % (orgcode, orgcode, groupRow, orgcode, groupRow)
                    )
                    balCountRow = groupBalance.fetchone()
                    balCountRow = [balCountRow[0], balCountRow[1]]
                    if balCountRow[1] == None:
                        balCountRow[1] = 0.00
                    liabilityDict = {
                        "groupname": groupRow,
                        "numberofaccounts": int(balCountRow[0]),
                        "groupbalance": "%.2f" % float(balCountRow[1]),
                    }
                    groupBalanceTable.append(liabilityDict)
                    liabilityTotal = liabilityTotal + float(balCountRow[1])
            groupBalanceTable.append({"Total": "%.2f" % (liabilityTotal)})
            groupBalanceTable.append("PROPERTY & ASSETS")
            for groupRow in nonprofitgroups:
                if (
                    groupRow == "Fixed Assets"
                    or groupRow == "Current Assets"
                    or groupRow == "Investments"
                    or groupRow == "Loans(Asset)"
                ):
                    groupBalance = self.con.execute(
                        "select count(accountname) as NumberOfAccounts, sum(openingbal) as groupBalance from accounts where orgcode = %d and groupcode in (select groupcode from groupsubgroups where orgcode = %d and groupname = '%s' or subgroupof = (select groupcode from groupsubgroups where orgcode = %d and groupname = '%s'));"
                        % (orgcode, orgcode, groupRow, orgcode, groupRow)
                    )
                    balCountRow = groupBalance.fetchone()
                    balCountRow = [balCountRow[0], balCountRow[1]]
                    if balCountRow[1] == None:
                        balCountRow[1] = 0.00
                    AssetDict = {
                        "groupname": groupRow,
                        "numberofaccounts": int(balCountRow[0]),
                        "groupbalance": "%.2f" % float(balCountRow[1]),
                    }
                    groupBalanceTable.append(AssetDict)
                    assetsTotal = assetsTotal + float(balCountRow[1])
            groupBalanceTable.append({"Total": "%.2f" % (assetsTotal)})
            difference = abs(assetsTotal - liabilityTotal)
            groupBalanceTable.append({"Difference in balance": "%.2f" % (difference)})
        if str(typeRow["orgtype"]) == "Profit Making":
            groupBalanceTable.append("CAPITAL & LIABILITIES")
            for groupRow in profitgroups:
                if (
                    groupRow == "Capital"
                    or groupRow == "Reserves"
                    or groupRow == "Current Liabilities"
                    or groupRow == "Loans(Liability)"
                ):
                    groupBalance = self.con.execute(
                        "select count(accountname) as NumberOfAccounts, sum(openingbal) as groupBalance from accounts where orgcode = %d and groupcode in (select groupcode from groupsubgroups where orgcode = %d and groupname = '%s' or subgroupof = (select groupcode from groupsubgroups where orgcode = %d and groupname = '%s'));"
                        % (orgcode, orgcode, groupRow, orgcode, groupRow)
                    )
                    balCountRow = groupBalance.fetchone()
                    balCountRow = [balCountRow[0], balCountRow[1]]
                    if balCountRow[1] == None:
                        balCountRow[1] = 0.00
                    liabilityDict = {
                        "groupname": groupRow,
                        "numberofaccounts": int(balCountRow[0]),
                        "groupbalance": "%.2f" % float(balCountRow[1]),
                    }
                    groupBalanceTable.append(liabilityDict)
                    liabilityTotal = liabilityTotal + float(balCountRow[1])
            groupBalanceTable.append({"Total": "%.2f" % (liabilityTotal)})
            groupBalanceTable.append("PROPERTY & ASSETS")
            for groupRow in profitgroups:
                if (
                    groupRow == "Fixed Assets"
                    or groupRow == "Current Assets"
                    or groupRow == "Investments"
                    or groupRow == "Loans(Asset)"
                    or groupRow == "Miscellaneous Expenses(Asset)"
                ):
                    groupBalance = self.con.execute(
                        "select count(accountname) as NumberOfAccounts, sum(openingbal) as groupBalance from accounts where orgcode = %d and groupcode in (select groupcode from groupsubgroups where orgcode = %d and groupname = '%s' or subgroupof = (select groupcode from groupsubgroups where orgcode = %d and groupname = '%s'));"
                        % (orgcode, orgcode, groupRow, orgcode, groupRow)
                    )
                    balCountRow = groupBalance.fetchone()
                    balCountRow = [balCountRow[0], balCountRow[1]]
                    if balCountRow[1] == None:
                        balCountRow[1] = 0.00
                    AssetDict = {
                        "groupname": groupRow,
                        "numberofaccounts": int(balCountRow[0]),
                        "groupbalance": "%.2f" % float(balCountRow[1]),
                    }
                    groupBalanceTable.append(AssetDict)
                    assetsTotal = assetsTotal + float(balCountRow[1])
            groupBalanceTable.append({"Total": "%.2f" % (assetsTotal)})
            difference = abs(assetsTotal - liabilityTotal)
            groupBalanceTable.append(
                {"Difference in balance": "%.2f" % float(difference)}
            )
        return groupBalanceTable
