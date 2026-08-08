from gkcore import eng, enumdict
from gkcore.models import gkdb
from gkcore.utils import authCheck
from sqlalchemy.sql import select
from sqlalchemy.engine.base import Connection
from sqlalchemy.sql.expression import text
from sqlalchemy import and_, or_
from pyramid.request import Request
from pyramid.view import view_defaults, view_config
from sqlalchemy.sql.expression import null


@view_defaults(route_name="project-statement", request_method="GET")
class api_project(object):
    def __init__(self, request):
        self.request = Request
        self.request = request
        self.con = Connection

    @view_config(renderer="json")
    def projectStatement(self):
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
        In addition there will be running Cr and Dr totals for printing purpose.
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
                calculateTo = self.request.params["calculateto"]
                financialStart = self.request.params["financialstart"]
                projectCode = self.request.params["projectcode"]
                totalDr = 0.00
                totalCr = 0.00
                grpaccsdata = self.con.execute(
                    "select accountcode , accountname, groupcode from accounts where orgcode = %d and groupcode in (select groupcode from groupsubgroups where orgcode = %d and groupcode in (select groupcode from groupsubgroups where orgcode = %d and (groupname in ('Direct Expense','Direct Income','Indirect Expense','Indirect Income') or groupname in (select groupname from groupsubgroups where subgroupof in (select groupcode from groupsubgroups where groupname in ('Direct Expense','Direct Income','Indirect Expense','Indirect Income')and orgcode = %d))))) order by accountname"
                    % (
                        authDetails["orgcode"],
                        authDetails["orgcode"],
                        authDetails["orgcode"],
                        authDetails["orgcode"],
                    )
                )
                grpaccs = grpaccsdata.fetchall()

                srno = 1
                projectStatement = []
                for accountRow in grpaccs:
                    statementRow = {}
                    g = gkdb.groupsubgroups.alias("g")
                    sg = gkdb.groupsubgroups.alias("sg")

                    group = self.con.execute(
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
                                    g.c.groupcode == int(accountRow["groupcode"]),
                                    g.c.subgroupof == null(),
                                    sg.c.groupcode == int(accountRow["groupcode"]),
                                    sg.c.subgroupof == null(),
                                ),
                                and_(
                                    g.c.groupcode == sg.c.subgroupof,
                                    sg.c.groupcode == int(accountRow["groupcode"]),
                                ),
                            )
                        )
                    )
                    groupRow = group.fetchone()

                    drresult = self.con.execute(
                        text("select sum(cast(drs->>:accountcode as float)) as total from vouchers where delflag = false and voucherdate >= from_date and voucherdate <= :to_date and projectcode=:projectcode"),
                        accountcode = accountRow["accountcode"],
                        from_date = financialStart,
                        to_date = calculateTo,
                        projectcode = projectCode,
                    )
                    drresultRow = drresult.fetchone()
                    crresult = self.con.execute(
                        text("select sum(cast(crs->>:accountcode as float)) as total from vouchers where delflag = false and voucherdate >= from_date and voucherdate <= :to_date and projectcode=:projectcode"),
                        accountcode = accountRow["accountcode"],
                        from_date = financialStart,
                        to_date = calculateTo,
                        projectcode = projectCode,
                    )
                    crresultRow = crresult.fetchone()
                    if groupRow["groupname"] == groupRow["subgroupname"]:
                        statementRow = {
                            "srno": srno,
                            "accountcode": accountRow["accountcode"],
                            "accountname": accountRow["accountname"],
                            "groupname": groupRow["groupname"],
                            "subgroupname": "",
                            "totalout": "%.2f" % float(totalDr),
                            "totalin": "%.2f" % float(totalCr),
                        }
                    else:
                        statementRow = {
                            "srno": srno,
                            "accountcode": accountRow["accountcode"],
                            "accountname": accountRow["accountname"],
                            "groupname": groupRow["groupname"],
                            "subgroupname": groupRow["subgroupname"],
                            "totalout": "%.2f" % float(totalDr),
                            "totalin": "%.2f" % float(totalCr),
                        }
                    if drresultRow["total"] == None:
                        statementRow["totalout"] = "%.2f" % float(0.00)
                    else:
                        statementRow["totalout"] = "%.2f" % float(drresultRow["total"])
                        totalDr = totalDr + drresultRow["total"]
                    if crresultRow["total"] == None:
                        statementRow["totalin"] = "%.2f" % float(0.00)
                    else:
                        statementRow["totalin"] = "%.2f" % float(crresultRow["total"])
                        totalCr = totalCr + crresultRow["total"]
                    if (
                        float(statementRow["totalout"]) == 0
                        and float(statementRow["totalin"]) == 0
                    ):
                        continue
                    srno = srno + 1
                    statementRow["ttlRunDr"] = "%.2f" % (totalDr)
                    statementRow["ttlRunCr"] = "%.2f" % (totalCr)
                    projectStatement.append(statementRow)
                projectStatement.append(
                    {
                        "srno": "",
                        "accountcode": "",
                        "accountname": "",
                        "groupname": "Total",
                        "subgroupname": "",
                        "totalout": "%.2f" % float(totalDr),
                        "totalin": "%.2f" % float(totalCr),
                    }
                )
                self.con.close()
                return {"gkstatus": enumdict["Success"], "gkresult": projectStatement}
            except:
                self.con.close()
                return {"gkstatus": enumdict["ConnectionFailed"]}
