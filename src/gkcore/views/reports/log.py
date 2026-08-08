from gkcore import eng, enumdict
from gkcore.utils import authCheck
from gkcore.models.gkdb import log
from sqlalchemy.sql import select
from sqlalchemy.engine.base import Connection
from sqlalchemy import and_, desc
from pyramid.request import Request
from pyramid.view import view_defaults, view_config
from datetime import datetime


@view_defaults(route_name="log-statement", request_method="GET")
class api_log_statement(object):
    def __init__(self, request):
        self.request = Request
        self.request = request
        self.con = Connection
    @view_config(request_param="type=org", renderer="json")
    def logByOrg(self):
        """
        purpose: returns complete log statement for an organisation.
        Date range is taken from calculatefrom and calculateto.
        description:
        This function returns entire log statement for a given organisation.
        Date range is taken from client and orgcode from authdetails.
        Date sorted according to orderflag.
        If request params has orderflag then date sorted in descending order otherwise in ascending order.
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
                if "orderflag" in self.request.params:
                    result = self.con.execute(
                        select([log])
                        .where(
                            and_(
                                log.c.orgcode == authDetails["orgcode"],
                                log.c.time >= self.request.params["calculatefrom"],
                                log.c.time <= self.request.params["calculateto"],
                            )
                        )
                        .order_by(desc(log.c.time))
                    )
                else:
                    result = self.con.execute(
                        select([log])
                        .where(
                            and_(
                                log.c.orgcode == authDetails["orgcode"],
                                log.c.time >= self.request.params["calculatefrom"],
                                log.c.time <= self.request.params["calculateto"],
                            )
                        )
                        .order_by(log.c.time)
                    )
                logdata = []
                ROLES = {
                    -1: "Admin",
                    0: "Manager",
                    1: "Operator",
                    2: "Internal Auditor",
                    3: "Godown In Charge",
                }
                for row in result:
                    rowuser = self.con.execute(
                        "select username, orgs->'%s'->'userrole' as userrole from gkusers where userid = %d"
                        % (str(authDetails["orgcode"]), int(row["userid"]))
                    ).fetchone()
                    userrole = ROLES[rowuser["userrole"]]
                    logdata.append(
                        {
                            "logid": row["logid"],
                            "time": datetime.strftime(row["time"], "%d-%m-%Y"),
                            "activity": row["activity"],
                            "userid": row["userid"],
                            "username": rowuser["username"] + "(" + userrole + ")",
                        }
                    )

                return {"gkstatus": enumdict["Success"], "gkresult": logdata}
            except:
                return {"gkstatus": enumdict["ConnectionFailed"]}
            finally:
                self.con.close()

    @view_config(request_param="type=user", renderer="json")
    def logByUser(self):
        """
        This function is the replica of the previous one except the log here is for a particular user.
        All parameter are same with the addition of userid."""
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
                if "orderflag" in self.request.params:
                    result = self.con.execute(
                        select([log])
                        .where(
                            and_(
                                log.c.userid == self.request.params["userid"],
                                log.c.orgcode == authDetails["orgcode"],
                                log.c.time >= self.request.params["calculatefrom"],
                                log.c.time <= self.request.params["calculateto"],
                            )
                        )
                        .order_by(desc(log.c.time))
                    )
                else:
                    result = self.con.execute(
                        select([log])
                        .where(
                            and_(
                                log.c.userid == self.request.params["userid"],
                                log.c.orgcode == authDetails["orgcode"],
                                log.c.time >= self.request.params["calculatefrom"],
                                log.c.time <= self.request.params["calculateto"],
                            )
                        )
                        .order_by(log.c.time)
                    )
                logdata = []
                for row in result:
                    logdata.append(
                        {
                            "logid": row["logid"],
                            "time": datetime.strftime(row["time"], "%d-%m-%Y"),
                            "activity": row["activity"],
                        }
                    )
                return {"gkstatus": enumdict["Success"], "gkresult": logdata}
            except:
                return {"gkstatus": enumdict["ConnectionFailed"]}
            finally:
                self.con.close()
