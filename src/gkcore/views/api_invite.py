from gkcore import eng, enumdict
from gkcore.models import gkdb
from sqlalchemy.sql import select
import json
from sqlalchemy.engine.base import Connection
from sqlalchemy.sql.expression import text
from pyramid.request import Request
from pyramid.view import view_defaults, view_config
import gkcore
from gkcore.models.meta import gk_api
from gkcore.utils import authCheck, gk_log, userAuthCheck
import traceback


"""
api_invite is used to handle user org relation related functionalities like invitations, role updates, etc.
"""


@view_defaults(route_name="invite")
class api_invite(object):
    def __init__(self, request):
        self.request = Request
        self.request = request
        self.con = Connection

    # request_param="type=create_invite",
    @view_config(request_method="POST", renderer="json")
    def createInvite(self):
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
                header = {"gktoken": self.request.headers["gktoken"]}
                # check if the user adding the invite is part of the requested org
                userOrgQuery = self.con.execute(
                    text("select orgs->':orgcode' from gkusers where userid = :userid;"),
                    orgcode = authDetails["orgcode"],
                    userid = authDetails["userid"],
                )
                if userOrgQuery.rowcount < 1:
                    return {"gkstatus": enumdict["ActionDisallowed"]}
                userOrgData = userOrgQuery.fetchone()
                userRole = userOrgData[0]["userrole"]

                dataset = self.request.json_body
                result = gk_api("/godown", header, self.request)["gkresult"]
                goid_list = [entry['goid'] for entry in result]
                if 'golist' in dataset:
                    all_godown_present = all(item not in goid_list for item in dataset['golist'])
                    if all_godown_present:
                        return {"gkstatus": enumdict["ActionDisallowed"]}
                # check if the user adding the invite has admin or manager role in the requested org
                # (Note: manager can only add operator)
                if userRole == -1 or (userRole == 0 and dataset["userrole"] == 1):
                    userid = self.con.execute(
                        select([gkdb.gkusers.c.userid]).where(
                            gkdb.gkusers.c.username == dataset["username"]
                        )
                    ).fetchone()
                    # Check and proceed if user is not part of the org yet
                    userInOrgQuery = self.con.execute(
                        text("select orgs->':orgcode' from gkusers where userid = :userid;"),
                        orgcode = authDetails["orgcode"],
                        userid = userid["userid"],
                    )

                    # print(userInOrgQuery.rowcount)
                    if userInOrgQuery.rowcount:
                        userInOrg = userInOrgQuery.fetchone()
                        if type(userInOrg[0]) == dict and len(userInOrg[0].keys()):
                            return {"gkstatus": enumdict["DuplicateEntry"]}

                    # Add entry in gkusers and organisation table, with invite status false
                    userOrgPayload = {
                        "invitestatus": False,
                        "userconf": {},
                        "userrole": dataset["userrole"],
                    }

                    # TODO: unit test the below code for godown incharge invites
                    # When the user accepts the invite, this golist will be added to the usergodowns table
                    if "golist" in dataset:
                        userOrgPayload["golist"] = dataset["golist"]
                    # data in the gkusers table will be used by the user to determine invite status
                    self.con.execute(
                        text("update gkusers set orgs = jsonb_set(orgs, '{:orgcode}', :user_org_payload) where userid = :userid;"),
                            orgcode = authDetails["orgcode"],
                            user_org_payload = json.dumps(userOrgPayload),
                            userid = userid["userid"],
                    )
                    # data in the organisation table will be used by the organisation to determine invited users
                    self.con.execute(
                        text("update organisation set users = jsonb_set(users, '{:userid}', 'false') where orgcode = :orgcode;"),
                        userid = userid["userid"],
                        orgcode = authDetails["orgcode"],
                    )
                    return {"gkstatus": enumdict["Success"]}
                return {"gkstatus": enumdict["ActionDisallowed"]}
            except:
                print(traceback.format_exc())
                return {"gkstatus": gkcore.enumdict["ConnectionFailed"]}
            finally:
                self.con.close()

    @view_config(request_method="POST", route_name="invite_accept", renderer="json")
    def acceptInvite(self):
        try:
            token = self.request.headers["gkusertoken"]
        except:
            return {"gkstatus": gkcore.enumdict["UnauthorisedAccess"]}
        authDetails = userAuthCheck(token)
        if authDetails["auth"] == False:
            return {"gkstatus": enumdict["UnauthorisedAccess"]}
        else:
            try:
                self.con = eng.connect()
                dataset = self.request.json_body

                # check if the user has a valid invite in the requested org
                userData = self.con.execute(
                    text("select orgs->':orgcode' from gkusers where userid = :userid;"),
                    orgcode = dataset["orgcode"],
                    userid = authDetails["userid"],
                ).fetchone()

                orgData = self.con.execute(
                    text("select users->':userid' from organisation where orgcode = :orgcode;"),
                    userid = authDetails["userid"],
                    orgcode = dataset["orgcode"],
                ).fetchone()

                if (
                    type(userData[0]) == dict
                    and userData[0]["invitestatus"] == False
                    and type(orgData[0]) == bool
                ):
                    # Update the gkusers and organisation tables

                    # update invite status to true
                    self.con.execute(
                        text("update gkusers set orgs = jsonb_set(orgs, '{:orgcode,invitestatus}', 'true') where userid = :userid;"),
                        orgcode = dataset["orgcode"],
                        userid = authDetails["userid"],
                    )
                    self.con.execute(
                        text("update organisation set users = jsonb_set(users, '{:userid}', 'true') where orgcode = :orgcode;"),
                        userid = authDetails["userid"],
                        orgcode = dataset["orgcode"],
                    )
                    # TODO: unit test the below code
                    # add the godown permissions if any present
                    if "golist" in userData[0]:
                        try:
                            for goid in userData[0]["golist"]:
                                godata = {
                                    "userid": authDetails["userid"],
                                    "goid": goid,
                                    "orgcode": dataset["orgcode"],
                                }
                                result = self.con.execute(
                                    gkdb.usergodown.insert(), [godata]
                                )
                            # remove the golist from gkusers
                            self.con.execute(
                                text("update gkusers set orgs = orgs #- '{:orgcode,golist}' WHERE userid = :userid;"),
                                orgcode = dataset["orgcode"],
                                userid = authDetails["userid"],
                            )
                        except:
                            return {
                                "gkstatus": gkcore.enumdict["ConnectionFailed"],
                                "gkmessage": "Error while assigning godown permissions, please contact admin and get those permissions reassigned",
                            }
                    return {"gkstatus": enumdict["Success"]}
                return {
                    "gkstatus": enumdict["UnauthorisedAccess"],
                    "gkmessage": "Invalid invite, please contact admin",
                }
            except:
                print(traceback.format_exc())
                return {"gkstatus": gkcore.enumdict["ConnectionFailed"]}
            finally:
                self.con.close()

    @view_config(request_method="POST", route_name="invite_reject", renderer="json")
    def rejectInvite(self):
        try:
            token = self.request.headers["gkusertoken"]
        except:
            return {"gkstatus": gkcore.enumdict["UnauthorisedAccess"]}
        authDetails = userAuthCheck(token)
        if authDetails["auth"] == False:
            return {"gkstatus": enumdict["UnauthorisedAccess"]}
        else:
            try:
                self.con = eng.connect()
                dataset = self.request.json_body

                # check if the user has a valid invite in the requested org
                userData = self.con.execute(
                    text("select orgs->':orgcode' from gkusers where userid = :userid;"),
                    orgcode = dataset["orgcode"],
                    userid = authDetails["userid"],
                ).fetchone()

                orgData = self.con.execute(
                    text("select users->':userid' from organisation where orgcode = :orgcode;"),
                    userid = authDetails["userid"],
                    orgcode = dataset["orgcode"],
                ).fetchone()

                if userData[0]["invitestatus"] == False and orgData[0] == False:
                    # if userQuery.rowcount == 1 and orgQuery.rowcount == 1:
                    # remove the entry from users table but leave it in organisation table
                    # userData = userQuery.fetchone()
                    # if not userData["invitestatus"]:
                    self.con.execute(
                        text("update gkusers set orgs = orgs - ':orgcode' WHERE userid = :userid;"),
                        orgcode = dataset["orgcode"],
                        userid = authDetails["userid"],
                    )
                    return {"gkstatus": enumdict["Success"]}
                return {
                    "gkstatus": enumdict[
                        "ActionDisallowed"
                    ],  # disallowed because invitation has been accepted
                }
            except:
                print(traceback.format_exc())
                return {"gkstatus": gkcore.enumdict["ConnectionFailed"]}

    @view_config(request_method="DELETE", renderer="json")
    def deleteInvite(self):
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
                userOrgs = self.con.execute(
                    text("select orgs->':orgcode' from gkusers where userid = :userid;"),
                    orgcode = authDetails["orgcode"],
                    userid = authDetails["userid"],
                ).fetchone()
                if not (len(userOrgs) and type(userOrgs[0]) == dict):
                    return {"gkstatus": enumdict["ActionDisallowed"]}
                userRole = userOrgs[0]["userrole"]

                # Allow delete only if requesting user is an admin
                if userRole == -1:
                    dataset = self.request.json_body
                    # check if the user has a valid invite in the requested org
                    userData = self.con.execute(
                        text("select orgs->':orgcode' from gkusers where userid = :userid;"),
                        orgcode = authDetails["orgcode"],
                        userid = dataset["userid"],
                    ).fetchone()

                    orgData = self.con.execute(
                        text("select users->':userid' from organisation where orgcode = :orgcode;"),
                        userid = dataset["userid"],
                        orgcode = authDetails["orgcode"],
                    ).fetchone()

                    if type(userData[0]) == dict and type(orgData[0]) == bool:
                        if not userData[0]["invitestatus"]:
                            # delete the invites
                            # remove the entry from gkusers and organisation table
                            self.con.execute(
                                text("update gkusers set orgs = orgs - ':orgcode' WHERE userid = :userid;"),
                                orgcode = authDetails["orgcode"],
                                userid = dataset["userid"],
                            )
                            self.con.execute(
                                text("update organisation set users = users - ':userid' WHERE orgcode = :orgcode;"),
                                userid = dataset["userid"],
                                orgcode = authDetails["orgcode"],
                            )
                            return {"gkstatus": enumdict["Success"]}
                        return {
                            "gkstatus": enumdict[
                                "ActionDisallowed"
                            ],  # disallowed because invitation has been accepted
                        }
                    elif type(orgData[0]) == bool:
                        self.con.execute(
                            text("update organisation set users = users - ':userid' WHERE orgcode = :orgcode;"),
                            userid = dataset["userid"],
                            orgcode = authDetails["orgcode"],
                        )
                        return {"gkstatus": enumdict["Success"]}

                # disallowed because invitation has been accepted
                return {
                    "gkstatus": enumdict["ActionDisallowed"],
                }
            except:
                print(traceback.format_exc())
                return {"gkstatus": gkcore.enumdict["ConnectionFailed"]}

    # TODO: Add user role update method
    # use the updateuser method in api_user as base
