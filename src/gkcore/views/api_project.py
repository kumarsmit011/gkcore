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
# imports contain sqlalchemy modules,
# enumdict containing status messages,
# eng for executing raw sql,
# gkdb from models for all the alchemy expressed tables.
# view_default for setting default route
# view_config for per method configurations predicates etc.
from gkcore import eng, enumdict
from gkcore.utils import authCheck, getUserRole
from gkcore.models import gkdb
from sqlalchemy.sql import select
import json
from sqlalchemy.engine.base import Connection
from sqlalchemy import and_, exc, func
from pyramid.request import Request
from pyramid.response import Response
from pyramid.view import view_defaults, view_config
from sqlalchemy.ext.baked import Result

"""
purpose:
This class is the resource to create, update, read and delete projects.

connection rules:
con is used for executing sql expression language based queries,
while eng is used for raw sql execution.
routing mechanism:
@view_defaults is used for setting the default route for crud on the given resource class.
if specific route is to be attached to a certain method, or for giving get, post, put, delete methods to default route, the view_config decorator is used.
For other predicates view_config is generally used.
"""

"""
default route to be attached to this resource.
refer to the __init__.py of main gkcore package for details on routing url
"""


@view_defaults(route_name="projects")
class api_project(object):
    # constructor will initialise request.
    def __init__(self, request):
        self.request = Request
        self.request = request
        self.con = Connection

    @view_config(request_method="POST", renderer="json")
    def addproject(self):
        """
        purpose:
        Adds a project.
        Request_method is post which means adding a resource.
        returns a json object containing success result as true if account is created.
        Alchemy expression language will be used for inserting into accounts table.
        The data is fetched from request.json_body.
        Expects projectname and sanctionedamount.
        Function will only proceed if auth check is successful, because orgcode needed as a common parameter can be procured only through the said method.
        """
        try:
            token = self.request.headers["gktoken"]
        except:
            return {"gkstatus": enumdict["UnauthorisedAccess"]}
        authDetails = authCheck(token)
        if authDetails["auth"] == False:
            return {"gkstatus": enumdict["UnauthorisedAccess"]}
        else:
            self.con = eng.connect()
            try:
                dataset = self.request.json_body
                dataset["orgcode"] = authDetails["orgcode"]
                # Check for duplicate entry before insertion
                result_duplicate_check = self.con.execute(
                    select([gkdb.projects.c.projectname])
                    .where(
                        and_(
                            gkdb.projects.c.orgcode == authDetails["orgcode"],
                            func.lower(gkdb.projects.c.projectname) == func.lower(dataset["projectname"]),
                        )
                    )
                )

                if result_duplicate_check.rowcount > 0:
                    return {"gkstatus": enumdict["DuplicateEntry"]}

                self.con.execute(gkdb.projects.insert(), [dataset])
                return {"gkstatus": enumdict["Success"]}
            except exc.IntegrityError:
                return {"gkstatus": enumdict["DuplicateEntry"]}
            except:
                return {"gkstatus": enumdict["ConnectionFailed"]}
            finally:
                self.con.close()

    @view_config(route_name="project", request_method="GET", renderer="json")
    def getproject(self):
        """
        Purpose:
        Returns a project given it's project code.
        Returns a json object containing:
        *projectcode
        *projectname
        *sanctionedamount as float

        The request_method is  get meaning retriving data.
        The route_name has been override here to make a special call which does not come under view_default.
        parameter will be taken from request.matchdict in a get request.
        Function will only proceed if auth check is successful, because orgcode needed as a common parameter can be procured only through the said method.
        """
        try:
            token = self.request.headers["gktoken"]
        except:
            return {"gkstatus": enumdict["UnauthorisedAccess"]}
        authDetails = authCheck(token)
        if authDetails["auth"] == False:
            return {"gkstatus": enumdict["UnauthorisedAccess"]}
        else:
            self.con = eng.connect()
            try:
                result = self.con.execute(
                    select([gkdb.projects]).where(
                        gkdb.projects.c.projectcode
                        == self.request.matchdict["projectcode"]
                    )
                )
                row = result.fetchone()
                acc = {
                    "projectcode": row["projectcode"],
                    "projectname": row["projectname"],
                    "sanctionedamount": "%.2f" % float(row["sanctionedamount"]),
                }
                return {"gkstatus": enumdict["Success"], "gkresult": acc}
            except:
                return {"gkstatus": enumdict["ConnectionFailed"]}
            finally:
                self.con.close()

    @view_config(request_method="GET", renderer="json")
    def getAllprojects(self):
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
                result = self.con.execute(
                    select(
                        [
                            gkdb.projects.c.projectname,
                            gkdb.projects.c.projectcode,
                            gkdb.projects.c.sanctionedamount,
                        ]
                    )
                    .where(gkdb.projects.c.orgcode == authDetails["orgcode"])
                    .order_by(gkdb.projects.c.projectname)
                )
                prjs = []
                for row in result:
                    prjs.append(
                        {
                            "projectcode": row["projectcode"],
                            "projectname": row["projectname"],
                            "sanctionedamount": "%.2f" % float(row["sanctionedamount"]),
                        }
                    )
                return {"gkstatus": enumdict["Success"], "gkresult": prjs}
            except:
                return {"gkstatus": enumdict["ConnectionFailed"]}
            finally:
                self.con.close()

    @view_config(request_method="GET", request_param="projlist", renderer="json")
    def getProjslist(self):
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
                projData = self.con.execute(
                    select(
                        [gkdb.projects.c.projectcode, gkdb.projects.c.projectname]
                    ).where(gkdb.projects.c.orgcode == authDetails["orgcode"])
                )
                projRows = projData.fetchall()
                projList = {}
                for row in projRows:
                    projList[row["projectname"]] = row["projectcode"]

                return {"gkstatus": enumdict["Success"], "gkresult": projList}
            except:
                self.con.close()
                return {"gkstatus": enumdict["ConnectionFailed"]}
            finally:
                self.con.close()

    @view_config(request_method="PUT", renderer="json")
    def editproject(self):
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
                dataset = self.request.json_body
                result = self.con.execute(
                    gkdb.projects.update()
                    .where(gkdb.projects.c.projectcode == dataset["projectcode"])
                    .values(dataset)
                )
                return {"gkstatus": enumdict["Success"]}
            except:
                return {"gkstatus": enumdict["ConnectionFailed"]}
            finally:
                self.con.close()

    @view_config(request_method="DELETE", renderer="json")
    def deleteproject(self):
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
                userRoleData = getUserRole(
                    authDetails["userid"], authDetails["orgcode"]
                )
                userRole = userRoleData["gkresult"]["userrole"]
                dataset = self.request.json_body
                if userRole == -1:
                    result = self.con.execute(
                        gkdb.projects.delete().where(
                            gkdb.projects.c.projectcode == dataset["projectcode"]
                        )
                    )
                    return {"gkstatus": enumdict["Success"]}
                else:
                    {"gkstatus": enumdict["BadPrivilege"]}
            except exc.IntegrityError:
                return {"gkstatus": enumdict["ActionDisallowed"]}
            except:
                return {"gkstatus": enumdict["ConnectionFailed"]}
            finally:
                self.con.close()
