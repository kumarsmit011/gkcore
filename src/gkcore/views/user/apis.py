import os
import bcrypt
from gkcore import eng, enumdict
from gkcore.models import gkdb
from gkcore.views.user.schemas import (
    UserSchema,
    UserNameSchema,
    ResetPassword,
    ChangePassword,
)
from gkcore.views.login.schemas import UserLogin
from sqlalchemy.sql import select, delete
from sqlalchemy import and_
from sqlalchemy.sql.expression import text
from pyramid.request import Request
from pyramid.view import view_defaults, view_config
import gkcore
from gkcore.models.meta import (
    tableExists,
)
from gkcore.utils import authCheck, gk_log, userAuthCheck, generateAuthToken, getUserRole
from datetime import datetime
from pydantic import ValidationError


@view_defaults(route_name="gkuser")
class api_gkuser(object):
    def __init__(self, request):
        self.request = Request
        self.request = request
        self.is_user_registration_disabled = os.environ.get(
            "GKCORE_DISABLE_USER_REGISTRATION",
            "false",
        ).lower()

    @view_config(
        request_method="GET",
        renderer="json",
        route_name="gkuser_registration",
    )
    def checkRegistrationStatus(self):
        """
        This function checks if registrations are disabled by server admin
        """
        if self.is_user_registration_disabled == "true":
            try:
                token = self.request.headers["gktoken"]
            except KeyError:
                return {"gkstatus": gkcore.enumdict["ActionDisallowed"]}
            authDetails = authCheck(token)
            if not authDetails["auth"]:
                return {"gkstatus": enumdict["ActionDisallowed"]}
            return {"gkstatus": enumdict["Success"]}

        return {"gkstatus": enumdict["Success"]}

    """
    - Check if the user is logged in using their old username and password
    - If yes,
      - rename their user in the new table
      - generate an new auth token
    - Else
      - send bad privilege
    """

    @view_config(request_method="POST", renderer="json")
    def addUser(self):
        """
        purpose
        adds a user in the users table.
        """

        if self.is_user_registration_disabled == "true":
            try:
                token = self.request.headers["gktoken"]
            except KeyError:
                return {"gkstatus": gkcore.enumdict["ActionDisallowed"]}
            authDetails = authCheck(token)
            if not authDetails["auth"]:
                return {"gkstatus": enumdict["ActionDisallowed"]}

        validated_data = UserSchema.model_validate(self.request.json_body)
        dataset = validated_data.model_dump(exclude_none=True)
        encoded_password = dataset.pop("userpassword").encode('utf-8')
        hashed_password = bcrypt.hashpw(encoded_password, bcrypt.gensalt())
        dataset["userpassword"] = hashed_password.decode('utf-8')

        with eng.begin() as con:

            # insert the user info into gkusers table
            con.execute(gkdb.gkusers.insert(), [dataset])

            # get the userid of the newly created user
            userid = con.execute(
                select([gkdb.gkusers.c.userid]).where(
                    gkdb.gkusers.c.username == dataset["username"]
                )
            ).fetchone()

            # generate the auth token
            token = generateAuthToken(
                con,
                {"userid": userid["userid"], "username": dataset["username"]},
                "user",
            )
            return {"gkstatus": enumdict["Success"], "token": token}


    """
    updateDefaultUserName() method is used to update the username in gkusers table that was created during migration 
    to satisfy the uniqueness constraint, with a user given username.
    """

    # TODO: Must update this method to update either all columns or just a column that is required
    # NOTE: revisit this api again to eval if required validation
    @view_config(
        request_method="PUT", renderer="json", request_param="type=default_user_name"
    )
    def updateDefaultUserName(self):
        try:
            token = self.request.headers["gktoken"]
        except:
            return {"gkstatus": gkcore.enumdict["UnauthorisedAccess"]}
        authDetails = authCheck(token)
        if authDetails["auth"] is False:
            return {"gkstatus": enumdict["UnauthorisedAccess"]}
        else:
            with eng.begin() as con:

                dataset = self.request.json_body

                roleQuery = con.execute(
                    text("select u.orgs#>'{:orgcode,userrole}' as userrole from gkusers u where userid = :userid;"),
                    orgcode = authDetails["orgcode"],
                    userid = dataset["userid"],
                )

                if roleQuery.rowcount == 1:
                    con.execute(
                        gkdb.gkusers.update()
                        .where(gkdb.gkusers.c.userid == dataset["userid"])
                        .values(username=dataset["username"])
                    )

                    """ Deletes old DB data, so commenting it out till dev is completed
                    # delete row from the old table
                    self.con.execute(gkdb.users.delete().where(gkdb.users.c.userid == dataset["olduserid"]))
                    """
                    token = generateAuthToken(
                        con,
                        {"userid": dataset["userid"], "username": dataset["username"]},
                        "user",
                    )

                    return {"gkstatus": enumdict["Success"], "token": token}
                return {
                    "gkstatus": enumdict["ActionDisallowed"],
                    "gkmessage": "Invalid User",
                }


    """This function sends basic data of user like username ,userrole. This API cant be used to fetch the data of other users, only for self use. """

    @view_config(request_method="GET", renderer="json")
    def getUserData(self):
        try:
            token = self.request.headers["gktoken"]
        except:
            return {"gkstatus": gkcore.enumdict["UnauthorisedAccess"]}
        authDetails = authCheck(token)
        if authDetails["auth"] is False:
            return {"gkstatus": gkcore.enumdict["UnauthorisedAccess"]}
        else:
            with eng.connect() as con:
                # there is only one possibility for a catch which is failed connection to db.
                # Retrieve data of that user whose userid is sent
                userid = authDetails["userid"]
                orgcode = authDetails["orgcode"]
                result = con.execute(
                    select(
                        [
                            gkdb.gkusers.c.username,
                            gkdb.gkusers.c.userid,
                        ]
                    ).where(gkdb.gkusers.c.userid == userid)
                )
                row = result.fetchone()
                userData = {
                    "username": row["username"],
                    "userid": row["userid"],
                }

                userRoleResp = getUserRole(userid, orgcode)
                userRole = None
                if "gkresult" in userRoleResp:
                    userRole = userRoleResp["gkresult"]["userrole"]
                userData["userrole"] = userRole
                if userRole == -1:
                    userData["userroleName"] = "Admin"
                elif userRole == 0:
                    userData["userroleName"] = "Manager"
                elif userRole == 1:
                    userData["userroleName"] = "Operator"
                elif userRole == 2:
                    userData["userroleName"] = "Internal Auditor"
                elif userRole == 3:
                    userData["userroleName"] = "Godown In Charge"
                return {"gkstatus": gkcore.enumdict["Success"], "gkresult": userData}


    """
    Following function is to get all users data having same user role .It needs userrole & only admin can view data of other users.
    """

    @view_config(
        route_name="gkuser_users_of_role",
        request_method="GET",
        renderer="json",
    )
    def getSameRoleUsersData(self):
        try:
            token = self.request.headers["gktoken"]
        except:
            return {"gkstatus": enumdict["UnauthorisedAccess"]}
        authDetails = authCheck(token)
        if authDetails["auth"] is False:
            return {"gkstatus": enumdict["UnauthorisedAccess"]}
        else:
            with eng.connect() as con:
                # get user role to validate.
                # only admin can view all users entire data
                userid = authDetails["userid"]
                orgcode = authDetails["orgcode"]
                requestRole = self.request.matchdict["userrole"]
                selfRoleResp = getUserRole(userid, orgcode)
                selfRole = None
                if "gkresult" in selfRoleResp:
                    selfRole = selfRoleResp["gkresult"]["userrole"]
                if selfRole == -1:
                    orgQuery = con.execute(
                        select([gkdb.organisation.c.users]).where(
                            gkdb.organisation.c.orgcode == orgcode
                        )
                    )
                    orgUsers = orgQuery.fetchone()
                    usersList = []
                    for userId in orgUsers:
                        if orgUsers[userId]:
                            userQuery = con.execute(
                                select([gkdb.gkusers]).where(
                                    gkdb.gkusers.c.userid == userId
                                )
                            )
                            userData = userQuery.fetchone()
                            userRole = userData["orgs"][orgcode]["userrole"]
                            if userRole == requestRole:
                                User = {
                                    "userid": userData["userid"],
                                    "username": userData["username"],
                                    "userrole": userRole,
                                    "userquestion": userData["userquestion"],
                                    "useranswer": userData["useranswer"],
                                }
                                # -1 = admin, 0 = Manager ,1 = operator,2 = Internal Auditor , 3 = godown in charge
                                if int(requestRole) == -1:
                                    User["userroleName"] = "Admin"
                                elif int(requestRole == 0):
                                    User["userroleName"] = "Manager"
                                elif int(requestRole == 1):
                                    User["userroleName"] = "Operator"
                                elif int(requestRole == 2):
                                    User["userroleName"] = "Internal Auditor"
                                # if user is godown in-charge we need to retrive associated godown/s

                                elif int(requestRole) == 3:
                                    User["userroleName"] = "Godown In Charge"
                                    usgo = con.execute(
                                        select([gkdb.usergodown.c.goid]).where(
                                            gkdb.gkusers.c.userid == userId
                                        )
                                    )
                                    goids = usgo.fetchall()
                                    userGodowns = {}
                                    for g in goids:
                                        godownid = g["goid"]
                                        # now we have associated godown ids, by which we can get godown name
                                        godownData = con.execute(
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


    @view_config(
        route_name="gkuser_role",
        request_method="GET",
        renderer="json",
    )
    def getRole(self):
        try:
            token = self.request.headers["gktoken"]
        except:
            return {"gkstatus": gkcore.enumdict["UnauthorisedAccess"]}
        authDetails = authCheck(token)
        if authDetails["auth"] is False:
            return {"gkstatus": enumdict["UnauthorisedAccess"]}
        else:
            try:
                return getUserRole(authDetails["userid"], authDetails["orgcode"])
            except:
                return {"gkstatus": enumdict["ConnectionFailed"]}

    # request_param="type=all_user_data",
    """
        Fetches the users that are part of an organisation
    """

    @view_config(
        request_method="GET",
        renderer="json",
        route_name="organisation_gkusers",
    )
    def getAllUserData(self):
        try:
            token = self.request.headers["gktoken"]
        except:
            return {"gkstatus": gkcore.enumdict["UnauthorisedAccess"]}
        authDetails = authCheck(token)
        if authDetails["auth"] is False:
            return {"gkstatus": gkcore.enumdict["UnauthorisedAccess"]}
        else:
            with eng.connect() as con:
                # Fetches the data of the users that are part of a particular organisation
                # TODO: optimize the below query if possible
                allUserData = con.execute(
                    text("select gkusers.userid, orgs->':orgcode' as userconf, username from gkusers inner join (select jsonb_object_keys(users) as userid from organisation where orgcode = :orgcode) orgs on cast(orgs.userid as integer) = gkusers.userid;"),
                    orgcode = authDetails["orgcode"],
                ).fetchall()

                checkFlag = con.execute(
                    select([gkdb.organisation.c.invflag]).where(
                        gkdb.organisation.c.orgcode == authDetails["orgcode"]
                    )
                )
                checkFlag.fetchone()

                users = []
                ROLES = {
                    -1: "Admin",
                    0: "Manager",
                    1: "Operator",
                    2: "Internal Auditor",
                    3: "Godown In Charge",
                }
                for userData in allUserData:
                    # print(userData)
                    users.append(
                        {
                            "userid": userData["userid"],
                            "username": userData["username"],
                            "userrole": userData["userconf"]["userrole"]
                            if userData["userconf"]
                            else "",
                            "userrolename": ROLES[userData["userconf"]["userrole"]]
                            if userData["userconf"]
                            else "",
                            "invitestatus": userData["userconf"]["invitestatus"]
                            if userData["userconf"]
                            else "Rejected",
                        }
                    )

                return {"gkstatus": gkcore.enumdict["Success"], "gkresult": users}


    # request_param="type=get_user_orgs",
    """
        Fetches the organisations that a user is part of
    """

    @view_config(
        request_method="GET",
        renderer="json",
        route_name="gkuser_orgs",
    )
    def getAllUserOrgs(self):
        try:
            token = self.request.headers["gkusertoken"]
        except:
            return {"gkstatus": gkcore.enumdict["UnauthorisedAccess"]}
        authDetails = userAuthCheck(token)
        if authDetails["auth"] is False:
            return {"gkstatus": gkcore.enumdict["UnauthorisedAccess"]}
        else:
            with eng.connect() as con:
                userData = con.execute(
                    select([gkdb.gkusers.c.orgs]).where(
                        gkdb.gkusers.c.userid == authDetails["userid"]
                    )
                ).fetchone()
                payload = {}
                if userData["orgs"] and type(userData["orgs"]) == dict:
                    # TODO: optimize the below code if possible
                    org_list = list(userData["orgs"].keys())
                    org_list.reverse()
                    for orgCode in org_list:
                        orgData = con.execute(
                            select(
                                [
                                    gkdb.organisation.c.orgname,
                                    gkdb.organisation.c.orgtype,
                                    gkdb.organisation.c.yearstart,
                                    gkdb.organisation.c.yearend,
                                ]
                            ).where(gkdb.organisation.c.orgcode == orgCode)
                        ).fetchone()
                        if orgData is not None and "orgname" in orgData:
                            if orgData["orgname"] not in payload:
                                payload[orgData["orgname"]] = []
                            payload[orgData["orgname"]].append(
                            {
                                "orgname": orgData["orgname"],
                                "orgtype": orgData["orgtype"],
                                "yearstart": datetime.strftime(
                                    (orgData["yearstart"]), "%d-%m-%Y"
                                ),
                                "yearend": datetime.strftime(
                                    (orgData["yearend"]), "%d-%m-%Y"
                                ),
                                "orgcode": orgCode,
                                "invitestatus": userData["orgs"][orgCode][
                                    "invitestatus"
                                ],
                                "userrole": userData["orgs"][orgCode]["userrole"],
                            }
                        )
                return {
                    "gkstatus": enumdict["Success"],
                    "gkresult": payload,
                }


    """This function checks if the username sent is unique"""

    # request_param="type=unique_check",
    @view_config(
        request_method="GET",
        renderer="json",
        route_name="gkuser_uname",
    )
    def checkUserNameUnique(self):
        with eng.connect() as con:
            # we now validate the incoming payload
            # and throw an error when it fails
            # Validate against the regex pattern
            validated_data = UserNameSchema.model_validate(self.request.matchdict)
            dataset = validated_data.model_dump(exclude_none=True)

            # there is only one possibility for a catch which is failed connection to db.
            # Retrieve data of that user whose userid is sent
            uname = dataset["username"]
            query = con.execute(
                select(
                    [
                        gkdb.gkusers.c.userid,
                    ]
                ).where(gkdb.gkusers.c.username == uname)
            )
            result = query.rowcount == 0

            if "check_legacy" in self.request.params:
                query2 = {"rowcount": 0}
                if tableExists("users"):
                    query2 = con.execute(
                        select(
                            [
                                gkdb.users.c.userid,
                            ]
                        ).where(gkdb.users.c.username == uname)
                    )

                result = result and query2.rowcount == 0
            return {"gkstatus": gkcore.enumdict["Success"], "gkresult": result}


    # request_param="type=recovery_question",
    @view_config(
        request_method="GET",
        renderer="json",
        route_name="gkuser_pwd_question",
    )
    def getquestion(self):
        with eng.connect() as con:
            username = self.request.params["username"]
            result = con.execute(
                select([gkdb.gkusers]).where(
                    and_(
                        gkdb.gkusers.c.username == username,
                    )
                )
            )
            if result.rowcount > 0:
                row = result.fetchone()
                user = {"userquestion": row["userquestion"], "userid": row["userid"]}
                return {"gkstatus": gkcore.enumdict["Success"], "gkresult": user}
            else:
                # check if orgcode exists
                # if it does, try to recreate the migrated username and check
                # else check if the old users table exists,
                # if it does, ask the user to send both username and orgcode
                if "orgname" in self.request.params:
                    orgQuery = con.execute(
                        select([gkdb.organisation.c.orgcode]).where(
                            and_(
                                gkdb.organisation.c.orgname
                                == self.request.params["orgname"],
                                gkdb.organisation.c.orgtype
                                == self.request.params["orgtype"],
                            )
                        )
                    )
                    if orgQuery.rowcount:
                        orgname = "_".join(self.request.params["orgname"].split(" "))
                        orgtype = (
                            "p"
                            if self.request.params["orgtype"] == "Profit Making"
                            else "np"
                        )
                        uname = (
                            orgname
                            + "_"
                            + orgtype
                            + "_"
                            + self.request.params["username"]
                        )
                        result = con.execute(
                            select([gkdb.gkusers]).where(
                                and_(
                                    gkdb.gkusers.c.username == uname,
                                )
                            )
                        )
                        if result.rowcount > 0:
                            row = result.fetchone()
                            user = {
                                "userquestion": row["userquestion"],
                                "userid": row["userid"],
                            }
                            return {
                                "gkstatus": gkcore.enumdict["Success"],
                                "gkresult": user,
                            }
                elif tableExists("users"):
                    query2 = con.execute(
                        select([gkdb.users.c.userid]).where(
                            gkdb.users.c.username == self.request.params["username"]
                        )
                    )
                    if query2.rowcount > 0:
                        return {"gkstatus": enumdict["ActionDisallowed"]}
                return {"gkstatus": enumdict["BadPrivilege"]}


    # request_param="type=verify_answer",
    @view_config(
        request_method="GET",
        renderer="json",
        route_name="gkuser_pwd_answer",
    )
    def verifyanswer(self):
        with eng.connect() as con:
            userid = self.request.params["userid"]
            useranswer = self.request.params["useranswer"]
            result = con.execute(
                select([gkdb.gkusers]).where(gkdb.gkusers.c.userid == userid)
            )
            row = result.fetchone()
            print(useranswer)
            print(row["useranswer"])
            if useranswer == row["useranswer"]:
                return {"gkstatus": enumdict["Success"]}
            else:
                return {"gkstatus": enumdict["BadPrivilege"]}


    @view_config(
        request_method="PUT",
        renderer="json",
        route_name="gkuser_pwd_reset",
    )
    def resetpassword(self):
        gk_log(__name__).info("reset password")
        with eng.begin() as con:
            # we now validate the incoming payload
            # and throw an error when it fails
            try:
                dataset = self.request.json_body
                dataset = ChangePassword(**dataset).model_dump()
            except ValidationError as e:
                return {
                    "gkstatus": enumdict["ConnectionFailed"],
                    "gkresult": e.errors(),
                }
            # check whether the user is already existing
            # in the database
            user = con.execute(
                select([gkdb.gkusers]).where(
                    and_(
                        gkdb.gkusers.c.userid == dataset["userid"],
                        gkdb.gkusers.c.useranswer == dataset["useranswer"],
                    )
                )
            )
            # if exists, update the relevant column with new password
            if user.rowcount > 0:
                encoded_password = dataset.pop("userpassword").encode('utf-8')
                hashed_password = bcrypt.hashpw(encoded_password, bcrypt.gensalt())
                dataset["userpassword"] = hashed_password.decode('utf-8')

                con.execute(
                    gkdb.gkusers.update()
                    .where(gkdb.gkusers.c.userid == dataset["userid"])
                    .values(userpassword=dataset["userpassword"])
                )
                return {"gkstatus": enumdict["Success"]}
            else:
                return {"gkstatus": enumdict["BadPrivilege"]}


    @view_config(
        request_method="POST", route_name="gkuser_pwd_validate", renderer="json"
    )
    def validateUserPassword(self):
        """
        Following function check status (i.e valid or not) of field
        current password in edituser.
        """
        try:
            token = self.request.headers["gkusertoken"]
        except:
            return {"gkstatus": gkcore.enumdict["UnauthorisedAccess"]}
        authDetails = userAuthCheck(token)
        if authDetails["auth"] is False:
            return {"gkstatus": enumdict["UnauthorisedAcces"]}
        else:
            with eng.connect() as con:
                validated_data = UserLogin.model_validate(self.request.json_body)
                dataset = validated_data.model_dump()
                result = con.execute(
                    select([gkdb.gkusers.c.userpassword]).where(
                        and_(
                            gkdb.gkusers.c.username == dataset["username"],
                        )
                    )
                ).fetchone()
                if not result:
                    return {"gkstatus": enumdict["UnauthorisedAccess"]}

                encoded_password = dataset["userpassword"].encode('utf-8')
                encoded_password_hash = result["userpassword"].encode('utf-8')
                if bcrypt.checkpw(encoded_password, encoded_password_hash):
                    return {"gkstatus": enumdict["Success"]}
                else:
                    return {"gkstatus": enumdict["UnauthorisedAccess"]}


    @view_config(request_method="DELETE", renderer="json")
    def deleteUser(self):
        """
        Delete a user from the database

        First, infer the user info from the gktoken, Check if the user is part of
        an organisation(s). If the user is a part of atleast one org, do not delete
        else, proceed with deletion
        """
        # validate the gktoken
        user = {}
        try:
            token = self.request.headers["gkusertoken"]
        except:
            return {"gkstatus": gkcore.enumdict["UnauthorisedAccess"]}
        authDetails = userAuthCheck(token)
        user = authDetails
        gk_log(__name__).debug(user)
        if authDetails["auth"] is False:
            return {"gkstatus": enumdict["UnauthorisedAccess"]}
        # get the user info from the database
        else:
            with eng.begin() as con:
                result = con.execute(
                    select([gkdb.gkusers]).where(
                        and_(
                            gkdb.gkusers.c.userid == user["userid"],
                        )
                    )
                ).fetchone()
                # loop over the orgs where the user is part of
                admin_of_orgs: list[int] = []
                for i in result.orgs:
                    # check if the user has admin role and
                    # also consider only if invitestatus is True
                    # if so, append the orgcode to admin_of_orgs list
                    if (
                        result.orgs[i]["userrole"] == -1
                        and result.orgs[i]["invitestatus"]
                    ):
                        admin_of_orgs.append(int(i))
                # if the user is admin of even one org, do not proceed for the deletion
                # because those orgs may not contain additional users with admin role
                if len(admin_of_orgs) > 0:
                    gk_log(__name__).debug(
                        f"The user is admin of {len(admin_of_orgs)} orgs with org ids {admin_of_orgs}"
                    )
                    return {"gkstatus": enumdict["ActionDisallowed"]}
                else:
                    # delete the user from the database & return success status code
                    con.execute(
                        delete(gkdb.gkusers).where(
                            gkdb.gkusers.c.userid == user["userid"],
                        )
                    )
                    return {"gkstatus": enumdict["Success"]}


    @view_config(
        request_method="PUT",
        renderer="json",
        route_name="gkuser_change_pwd",
    )
    def changeUserPassword(self):
        """Change user's password"""
        try:
            token = self.request.headers["gkusertoken"]
        except Exception as e:
            return {
                "gkstatus": gkcore.enumdict["UnauthorisedAccess"],
                "gkresult": f"{e}",
            }
        authDetails = userAuthCheck(token)
        if authDetails["auth"] is False:
            return {"gkstatus": enumdict["UnauthorisedAccess"]}
        with eng.begin() as con:
            dataset = self.request.json_body

            # we now validate the incoming payload
            # and throw an error when it fails
            try:
                # we now append the userid key to dataset for validation
                dataset["userid"] = authDetails["userid"]
                dataset = ResetPassword(**dataset).model_dump()
            except ValidationError as e:
                return {
                    "gkstatus": enumdict["ConnectionFailed"],
                    "gkresult": e.errors(),
                }

            # hash password
            encoded_password = dataset.pop("userpassword").encode('utf-8')
            hashed_password = bcrypt.hashpw(encoded_password, bcrypt.gensalt())
            dataset["userpassword"] = hashed_password.decode('utf-8')

            # insert the updated password to the db
            con.execute(
                gkdb.gkusers.update()
                .where(gkdb.gkusers.c.userid == dataset["userid"])
                .values(userpassword=dataset["userpassword"])
            )
            return {"gkstatus": enumdict["Success"]}
