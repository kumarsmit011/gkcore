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
"Mohd. Talha Pawaty" <mtalha456@gmail.com>
"Prajkta Patkar" <prajakta@dff.org.in>
"Nitesh Chaughule" <nitesh@disroot.org>

"""


from gkcore import eng, enumdict
from gkcore.models import gkdb
from sqlalchemy.sql import select
import json
from sqlalchemy.engine.base import Connection
from sqlalchemy import and_, exc
from pyramid.request import Request
from pyramid.response import Response
from pyramid.view import view_defaults, view_config
import jwt
import gkcore
from gkcore.utils import authCheck


def getUserRole(userid):
    try:
        con = Connection
        con = eng.connect()
        uid = userid
        user = con.execute(
            select([gkdb.users.c.userrole]).where(gkdb.users.c.userid == uid)
        )
        row = user.fetchone()
        User = {"userrole": row["userrole"]}
        con.close()
        return {"gkstatus": gkcore.enumdict["Success"], "gkresult": User}
    except:
        return {"gkstatus": gkcore.enumdict["ConnectionFailed"]}


@view_defaults(route_name="users")
class api_user(object):
    def __init__(self, request):
        self.request = Request
        self.request = request
        self.con = Connection

    @view_config(request_method="POST", renderer="json")
    def addUser(self):
        """
        purpose
        adds a user in the users table.
        description:
        this function  takes username and role as basic parameters.
        It may also have a list of goids for the godowns associated with this user.
        This is only true if goflag is True.
        The frontend must send the role as godownkeeper for this."""
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
                user = self.con.execute(
                    select([gkdb.users.c.userrole]).where(
                        gkdb.users.c.userid == authDetails["userid"]
                    )
                )
                userRole = user.fetchone()
                dataset = self.request.json_body
                if userRole[0] == -1 or (userRole[0] == 0 and dataset["userrole"] == 1):
                    dataset["orgcode"] = authDetails["orgcode"]
                    # golist is present when godown / branch are assign
                    if "golist" in dataset:
                        golist = tuple(dataset.pop("golist"))
                        result = self.con.execute(gkdb.users.insert(), [dataset])
                        userdata = self.con.execute(
                            select([gkdb.users.c.userid]).where(
                                and_(
                                    gkdb.users.c.username == dataset["username"],
                                    gkdb.users.c.orgcode == dataset["orgcode"],
                                )
                            )
                        )
                        userRow = userdata.fetchone()
                        lastid = userRow["userid"]
                        for goid in golist:
                            godata = {
                                "userid": lastid,
                                "goid": goid,
                                "orgcode": dataset["orgcode"],
                            }
                            result = self.con.execute(
                                gkdb.usergodown.insert(), [godata]
                            )
                    else:
                        result = self.con.execute(gkdb.users.insert(), [dataset])
                    return {"gkstatus": enumdict["Success"]}
                else:
                    return {"gkstatus": enumdict["BadPrivilege"]}
            except exc.IntegrityError:
                return {"gkstatus": enumdict["DuplicateEntry"]}
            except:
                return {"gkstatus": gkcore.enumdict["ConnectionFailed"]}
            finally:
                self.con.close()

    """
    Following function is to retrive user data.It needs userid & only admin can view data of other users.
    """

    @view_config(
        route_name="user",
        request_method="GET",
        request_param="userAllData",
        renderer="json",
    )
    def getUserAllData(self):
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
                # get necessary user data by comparing userid
                user = self.con.execute(
                    select([gkdb.users.c.userrole]).where(
                        gkdb.users.c.userid == authDetails["userid"]
                    )
                )
                userRole = user.fetchone()
                if userRole[0] == -1:
                    result = self.con.execute(
                        select([gkdb.users]).where(
                            gkdb.users.c.userid == self.request.params["userid"]
                        )
                    )
                    row = result.fetchone()
                    User = {
                        "userid": row["userid"],
                        "username": row["username"],
                        "userrole": row["userrole"],
                        "userquestion": row["userquestion"],
                        "useranswer": row["useranswer"],
                    }
                    if row["userrole"] == -1:
                        User["userroleName"] = "Admin"
                    elif row["userrole"] == 0:
                        User["userroleName"] = "Manager"
                    elif row["userrole"] == 1:
                        User["userroleName"] = "Operator"
                    elif row["userrole"] == 2:
                        User["userroleName"] = "Internal Auditor"

                    # -1 = admin,1 = operator,2 = manager , 3 = godown in charge
                    # if user is godown in-charge we need to retrive associated godown/s
                    if User["userrole"] == 3:
                        User["userroleName"] = "Godown In Charge"
                    usgo = self.con.execute(
                        select([gkdb.usergodown.c.goid]).where(
                            gkdb.usergodown.c.userid == self.request.params["userid"]
                        )
                    )
                    goids = usgo.fetchall()
                    userGodowns = {}
                    for g in goids:
                        godownid = g["goid"]
                        # now we have associated godown ids, by which we can get godown name
                        godownData = self.con.execute(
                            select([gkdb.godown.c.goname]).where(
                                gkdb.godown.c.goid == godownid
                            )
                        )
                        gNameRow = godownData.fetchone()
                        userGodowns[godownid] = gNameRow["goname"]
                    User["godowns"] = userGodowns

                    return {"gkstatus": gkcore.enumdict["Success"], "gkresult": User}
                else:
                    return {"gkstatus": gkcore.enumdict["ActionDisallowed"]}

            except:
                return {"gkstatus": gkcore.enumdict["ConnectionFailed"]}
            finally:
                self.con.close()

    """
    Following function is to get all users data having same user role .It needs userrole & only admin can view data of other users.
    """

    @view_config(
        route_name="user",
        request_method="GET",
        request_param="sameRoleUsers",
        renderer="json",
    )
    def getAllUsersData(self):
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
                # get user role to validate.
                # only admin can view all users entire data
                user = self.con.execute(
                    select([gkdb.users.c.userrole]).where(
                        gkdb.users.c.userid == authDetails["userid"]
                    )
                )
                userRole = user.fetchone()
                if userRole[0] == -1:
                    # get all users having same user role.
                    result = self.con.execute(
                        select(
                            [
                                gkdb.users.c.username,
                                gkdb.users.c.userid,
                                gkdb.users.c.userquestion,
                                gkdb.users.c.useranswer,
                            ]
                        ).where(
                            and_(
                                gkdb.users.c.userrole
                                == self.request.params["userrole"],
                                gkdb.users.c.orgcode == authDetails["orgcode"],
                            )
                        )
                    )
                    userData = result.fetchall()
                    usersList = []
                    for row in userData:
                        User = {
                            "userid": row["userid"],
                            "username": row["username"],
                            "userrole": self.request.params["userrole"],
                            "userquestion": row["userquestion"],
                            "useranswer": row["useranswer"],
                        }
                        # -1 = admin, 0 = Manager ,1 = operator,2 = Internal Auditor , 3 = godown in charge
                        if int(self.request.params["userrole"]) == -1:
                            User["userroleName"] = "Admin"
                        elif int(self.request.params["userrole"] == 0):
                            User["userroleName"] = "Manager"
                        elif int(self.request.params["userrole"] == 1):
                            User["userroleName"] = "Operator"
                        elif int(self.request.params["userrole"] == 2):
                            User["userroleName"] = "Internal Auditor"
                        # if user is godown in-charge we need to retrive associated godown/s

                        elif int(self.request.params["userrole"]) == 3:
                            User["userroleName"] = "Godown In Charge"
                            usgo = self.con.execute(
                                select([gkdb.usergodown.c.goid]).where(
                                    gkdb.users.c.userid == row["userid"]
                                )
                            )
                            goids = usgo.fetchall()
                            userGodowns = {}
                            for g in goids:
                                godownid = g["goid"]
                                # now we have associated godown ids, by which we can get godown name
                                godownData = self.con.execute(
                                    select([gkdb.godown.c.goname]).where(
                                        gkdb.godown.c.goid == godownid
                                    )
                                )
                                gNameRow = godownData.fetchone()
                                userGodowns[godownid] = gNameRow["goname"]
                            User["godowns"] = userGodowns
                        usersList.append(User)

                    return {
                        "gkstatus": gkcore.enumdict["Success"],
                        "gkresult": usersList,
                    }
                else:
                    return {"gkstatus": gkcore.enumdict["ActionDisallowed"]}

            except:
                return {"gkstatus": gkcore.enumdict["ConnectionFailed"]}
            finally:
                self.con.close()

    @view_config(request_method="PUT", renderer="json")
    def editUser(self):
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
                user = self.con.execute(
                    select([gkdb.users.c.userrole]).where(
                        gkdb.users.c.userid == authDetails["userid"]
                    )
                )
                userRole = user.fetchone()
                dataset = self.request.json_body
                if userRole[0] == -1 or int(authDetails["userid"]) == int(
                    dataset["userid"]
                ):
                    result = self.con.execute(
                        gkdb.users.update()
                        .where(gkdb.users.c.userid == dataset["userid"])
                        .values(dataset)
                    )
                    return {"gkstatus": enumdict["Success"]}
                else:
                    return {"gkstatus": enumdict["BadPrivilege"]}
            except:
                return {"gkstatus": gkcore.enumdict["ConnectionFailed"]}
            finally:
                self.con.close()

    """
    Following function check status (i.e valid or not) of field current password in edituser.  
"""

    @view_config(
        request_method="POST", request_param="userloginstatus", renderer="json"
    )
    def userLoginstatus(self):
        try:
            print("ggg")
            self.con = eng.connect()
            token = self.request.headers["gktoken"]
        except:
            return {"gkstatus": gkcore.enumdict["UnauthorisedAccess"]}
        authDetails = authCheck(token)
        if authDetails["auth"] == False:
            return {"gkstatus": enumdict["UnauthorisedAcces"]}
        else:
            try:
                dataset = self.request.json_body
                result = self.con.execute(
                    select([gkdb.users.c.userid]).where(
                        and_(
                            gkdb.users.c.username == dataset["username"],
                            gkdb.users.c.userpassword == dataset["userpassword"],
                            gkdb.users.c.orgcode == authDetails["orgcode"],
                        )
                    )
                )
                if result.rowcount == 1:
                    return {"gkstatus": enumdict["Success"]}
                else:
                    return {"gkstatus": enumdict["BadPrivilege"]}
            except:
                return {"gkstatus": enumdict["ConnectionFailed"]}
            finally:
                self.con.close()

    """
        Following function update user, in the users table.
        It may also have a list of goids for the godowns associated with this user.
        The frontend must send the role as Godown In Charge for this.
"""

    @view_config(request_method="PUT", request_param="editdata", renderer="json")
    def updateuser(self):
        try:
            token = self.request.headers["gktoken"]
        except:
            return {"gkstatus": gkcore.enumdict["UnauthorisedAccess"]}
        authDetails = authCheck(token)
        if authDetails["auth"] == False:
            return {"gkstatus": enumdict["UnauthorisedAcces"]}
        else:
            try:
                self.con = eng.connect()
                userRole = getUserRole(authDetails["userid"])
                dataset = self.request.json_body
                if userRole["gkresult"]["userrole"] == -1:
                    dataset["orgcode"] = authDetails["orgcode"]
                    # "originalrole" gives userrole of old user
                    originalrole = getUserRole(dataset["userid"])
                    # if golist is present then it has access related to godown / branch
                    if "golist" in dataset:
                        result = self.con.execute(
                            gkdb.usergodown.delete().where(
                                gkdb.usergodown.c.userid == dataset["userid"]
                            )
                        )
                    # dataset["userrole"] gives userrole of new user
                    if "userrole" in dataset:
                        # if golist is present then it has access related to godown / branch
                        if "golist" in dataset:
                            golists = tuple(dataset.pop("golist"))
                            result = self.con.execute(
                                gkdb.users.update()
                                .where(gkdb.users.c.userid == dataset["userid"])
                                .values(dataset)
                            )
                            currentid = dataset["userid"]
                            for goid in golists:
                                godata = {
                                    "userid": currentid,
                                    "goid": goid,
                                    "orgcode": dataset["orgcode"],
                                }
                                result = self.con.execute(
                                    gkdb.usergodown.insert(), [godata]
                                )
                            return {"gkstatus": enumdict["Success"]}
                        else:
                            result = self.con.execute(
                                gkdb.users.update()
                                .where(gkdb.users.c.userid == dataset["userid"])
                                .values(dataset)
                            )
                            return {"gkstatus": enumdict["Success"]}
                    else:
                        result = self.con.execute(
                            gkdb.users.update()
                            .where(gkdb.users.c.userid == dataset["userid"])
                            .values(dataset)
                        )
                        return {"gkstatus": enumdict["Success"]}
                else:
                    return {"gkstatus": gkcore.enumdict["ActionDisallowed"]}
            except exc.IntegrityError:
                return {"gkstatus": enumdict["DuplicateEntry"]}
            except:
                return {"gkstatus": gkcore.enumdict["ConnectionFailed"]}
            finally:
                self.con.close()

    @view_config(request_method="GET", renderer="json")
    def getAllUsers(self):
        try:
            token = self.request.headers["gktoken"]
        except:
            return {"gkstatus": gkcore.enumdict["UnauthorisedAccess"]}
        authDetails = authCheck(token)
        if authDetails["auth"] == False:
            return {"gkstatus": gkcore.enumdict["UnauthorisedAccess"]}
        else:
            try:
                self.con = eng.connect()
                # there is only one possibility for a catch which is failed connection to db.
                result = self.con.execute(
                    select(
                        [
                            gkdb.users.c.username,
                            gkdb.users.c.userid,
                            gkdb.users.c.userrole,
                        ]
                    )
                    .where(gkdb.users.c.orgcode == authDetails["orgcode"])
                    .order_by(gkdb.users.c.username)
                )
                checkFlag = self.con.execute(
                    select([gkdb.organisation.c.invflag]).where(
                        gkdb.organisation.c.orgcode == authDetails["orgcode"]
                    )
                )
                invf = checkFlag.fetchone()

                users = []
                for row in result:
                    if not (invf["invflag"] == 0 and row["userrole"] == 3):
                        # Specify user role
                        if row["userrole"] == -1:
                            userroleName = "Admin"
                        elif row["userrole"] == 0:
                            userroleName = "Manager"
                        elif row["userrole"] == 1:
                            userroleName = "Operator"
                        elif row["userrole"] == 2:
                            userroleName = "Internal Auditor"
                        elif row["userrole"] == 3:
                            userroleName = "Godown In Charge"
                        users.append(
                            {
                                "userid": row["userid"],
                                "username": row["username"],
                                "userrole": row["userrole"],
                                "userrolename": userroleName,
                            }
                        )

                return {"gkstatus": gkcore.enumdict["Success"], "gkresult": users}
            except:
                return {"gkstatus": gkcore.enumdict["ConnectionFailed"]}
            finally:
                self.con.close()

    # This method makes a list of users. If the user is godown incharge then its respective godowns is also added in list. This method will be used to make list of users report.
    @view_config(request_method="GET", request_param="type=list", renderer="json")
    def getListofUsers(self):
        try:
            token = self.request.headers["gktoken"]
        except:
            return {"gkstatus": gkcore.enumdict["UnauthorisedAccess"]}
        authDetails = authCheck(token)
        if authDetails["auth"] == False:
            return {"gkstatus": gkcore.enumdict["UnauthorisedAccess"]}
        else:
            try:
                self.con = eng.connect()
                result = self.con.execute(
                    select(
                        [
                            gkdb.users.c.username,
                            gkdb.users.c.userid,
                            gkdb.users.c.userrole,
                        ]
                    )
                    .where(gkdb.users.c.orgcode == authDetails["orgcode"])
                    .order_by(gkdb.users.c.username)
                )
                users = []
                srno = 1
                for row in result:
                    godowns = []
                    urole = ""
                    if row["userrole"] == -1:
                        urole = "Admin"
                    elif row["userrole"] == 0:
                        urole = "Manager"
                    elif row["userrole"] == 1:
                        urole = "Operator"
                    elif row["userrole"] == 2:
                        urole = "Internal Auditor"
                    else:
                        urole = "Godown In Charge"
                        godownresult = self.con.execute(
                            select([gkdb.usergodown.c.goid]).where(
                                and_(
                                    gkdb.usergodown.c.orgcode == authDetails["orgcode"],
                                    gkdb.usergodown.c.userid == row["userid"],
                                )
                            )
                        )
                        for goid in godownresult:
                            godownnameres = self.con.execute(
                                select(
                                    [gkdb.godown.c.goname, gkdb.godown.c.goaddr]
                                ).where(gkdb.godown.c.goid == goid[0])
                            )
                            goname = godownnameres.fetchone()
                            godowns.append(
                                str(goname["goname"] + "(" + goname["goaddr"] + ")")
                            )
                    users.append(
                        {
                            "srno": srno,
                            "userid": row["userid"],
                            "username": row["username"],
                            "userrole": urole,
                            "godowns": godowns,
                            "noofgodowns": len(godowns),
                        }
                    )
                    srno += 1
                return {"gkstatus": gkcore.enumdict["Success"], "gkresult": users}
            except:
                return {"gkstatus": gkcore.enumdict["ConnectionFailed"]}
            finally:
                self.con.close()

    @view_config(request_method="DELETE", renderer="json")
    def deleteuser(self):
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
                user = self.con.execute(
                    select([gkdb.users.c.userrole]).where(
                        gkdb.users.c.userid == authDetails["userid"]
                    )
                )
                userRole = user.fetchone()
                dataset = self.request.json_body
                if userRole[0] == -1:
                    result = self.con.execute(
                        gkdb.users.delete().where(
                            gkdb.users.c.userid == dataset["userid"]
                        )
                    )
                    return {"gkstatus": enumdict["Success"]}
                else:
                    return {"gkstatus": enumdict["BadPrivilege"]}
            except exc.IntegrityError:
                return {"gkstatus": enumdict["ActionDisallowed"]}
            except:
                return {"gkstatus": enumdict["ConnectionFailed"]}
            finally:
                self.con.close()

    @view_config(route_name="forgotpassword", request_method="GET", renderer="json")
    def getquestion(self):
        try:
            self.con = eng.connect()
            orgcode = self.request.params["orgcode"]
            username = self.request.params["username"]
            result = self.con.execute(
                select([gkdb.users]).where(
                    and_(
                        gkdb.users.c.username == username,
                        gkdb.users.c.orgcode == orgcode,
                    )
                )
            )
            if result.rowcount > 0:
                row = result.fetchone()
                User = {"userquestion": row["userquestion"], "userid": row["userid"]}
                return {"gkstatus": gkcore.enumdict["Success"], "gkresult": User}
            else:
                return {"gkstatus": enumdict["BadPrivilege"]}
        except:
            return {"gkstatus": enumdict["ConnectionFailed"]}
        finally:
            self.con.close()

    @view_config(
        route_name="forgotpassword",
        request_method="GET",
        request_param="type=securityanswer",
        renderer="json",
    )
    def verifyanswer(self):
        try:
            self.con = eng.connect()
            userid = self.request.params["userid"]
            useranswer = self.request.params["useranswer"]
            result = self.con.execute(
                select([gkdb.users]).where(gkdb.users.c.userid == userid)
            )
            row = result.fetchone()
            if useranswer == row["useranswer"]:
                return {"gkstatus": enumdict["Success"]}
            else:
                return {"gkstatus": enumdict["BadPrivilege"]}
        except:
            return {"gkstatus": enumdict["ConnectionFailed"]}
        finally:
            self.con.close()

    @view_config(route_name="forgotpassword", request_method="PUT", renderer="json")
    def verifypassword(self):
        try:
            self.con = eng.connect()
            dataset = self.request.json_body
            user = self.con.execute(
                select([gkdb.users]).where(
                    and_(
                        gkdb.users.c.userid == dataset["userid"],
                        gkdb.users.c.useranswer == dataset["useranswer"],
                    )
                )
            )
            if user.rowcount > 0:
                result = self.con.execute(
                    gkdb.users.update()
                    .where(gkdb.users.c.userid == dataset["userid"])
                    .values(dataset)
                )
                return {"gkstatus": enumdict["Success"]}
            else:
                return {"gkstatus": enumdict["BadPrivilege"]}
        except:
            return {"gkstatus": enumdict["ConnectionFailed"]}
        finally:
            self.con.close()

    @view_config(
        route_name="user",
        request_method="PUT",
        request_param="type=theme",
        renderer="json",
    )
    def addtheme(self):
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
                result = self.con.execute(
                    gkdb.users.update()
                    .where(gkdb.users.c.userid == authDetails["userid"])
                    .values(dataset)
                )
                return {"gkstatus": enumdict["Success"]}
            except:
                try:
                    self.con.execute(
                        "alter table users add column themename text default 'Default'"
                    )
                    dataset = self.request.json_body
                    result = self.con.execute(
                        gkdb.users.update()
                        .where(gkdb.users.c.userid == authDetails["userid"])
                        .values(dataset)
                    )
                    return {"gkstatus": enumdict["Success"]}
                except:
                    return {"gkstatus": enumdict["ConnectionFailed"]}
            finally:
                self.con.close()

    @view_config(
        route_name="user",
        request_method="GET",
        request_param="type=theme",
        renderer="json",
    )
    def gettheme(self):
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
                    select([gkdb.users.c.themename]).where(
                        gkdb.users.c.userid == authDetails["userid"]
                    )
                )
                row = result.fetchone()
                return {
                    "gkstatus": gkcore.enumdict["Success"],
                    "gkresult": row["themename"],
                }
            except:
                try:
                    self.con = eng.connect()
                    self.con.execute(
                        "alter table users add column themename text default 'Default'"
                    )
                    result = self.con.execute(
                        select([gkdb.users.c.themename]).where(
                            gkdb.users.c.userid == authDetails["userid"]
                        )
                    )
                    row = result.fetchone()
                    return {
                        "gkstatus": gkcore.enumdict["Success"],
                        "gkresult": row["themename"],
                    }
                except:
                    return {"gkstatus": enumdict["ConnectionFailed"]}
            finally:
                self.con.close()

    @view_config(
        route_name="user",
        request_method="GET",
        request_param="type=role",
        renderer="json",
    )
    def getRole(self):
        try:
            token = self.request.headers["gktoken"]
        except:
            return {"gkstatus": gkcore.enumdict["UnauthorisedAccess"]}
        authDetails = authCheck(token)
        if authDetails["auth"] == False:
            return {"gkstatus": enumdict["UnauthorisedAccess"]}
        else:
            try:
                userrole = getUserRole(authDetails["userid"])
                if userrole["gkstatus"] == 0:
                    return {
                        "gkresult": userrole["gkresult"]["userrole"],
                        "gkstatus": userrole["gkstatus"],
                    }
                else:
                    return {"gkstatus": userrole["gkstatus"]}

            except:
                return {"gkstatus": enumdict["ConnectionFailed"]}

    """This function sends basic data of user like username ,userrole """

    @view_config(request_method="GET", request_param="user=single", renderer="json")
    def getDataofUser(self):
        try:
            token = self.request.headers["gktoken"]
        except:
            return {"gkstatus": gkcore.enumdict["UnauthorisedAccess"]}
        authDetails = authCheck(token)
        if authDetails["auth"] == False:
            return {"gkstatus": gkcore.enumdict["UnauthorisedAccess"]}
        else:
            try:
                self.con = eng.connect()
                # there is only one possibility for a catch which is failed connection to db.
                # Retrieve data of that user whose userid is sent
                result = self.con.execute(
                    select(
                        [
                            gkdb.users.c.username,
                            gkdb.users.c.userrole,
                            gkdb.users.c.userid,
                        ]
                    ).where(gkdb.users.c.userid == authDetails["userid"])
                )
                row = result.fetchone()
                userData = {
                    "username": row["username"],
                    "userrole": row["userrole"],
                    "userid": row["userid"],
                }
                if row["userrole"] == -1:
                    userData["userroleName"] = "Admin"
                elif row["userrole"] == 0:
                    userData["userroleName"] = "Manager"
                elif row["userrole"] == 1:
                    userData["userroleName"] = "Operator"
                elif row["userrole"] == 2:
                    userData["userroleName"] = "Internal Auditor"
                elif row["userrole"] == 3:
                    userData["userroleName"] = "Godown In Charge"
                return {"gkstatus": gkcore.enumdict["Success"], "gkresult": userData}
            except:
                return {"gkstatus": gkcore.enumdict["ConnectionFailed"]}
            finally:
                self.con.close()
