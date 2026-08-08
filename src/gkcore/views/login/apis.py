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


import bcrypt
from gkcore import eng, enumdict
from gkcore.models import gkdb
from gkcore.views.login.schemas import OrgLogin, UserLogin
from sqlalchemy.sql import select
from sqlalchemy import and_, func
from pyramid.view import view_config
import gkcore
from datetime import datetime
from gkcore.utils import generateAuthToken, userAuthCheck


@view_config(
    route_name="login_user",
    request_method="POST",
    renderer="json",
)
def userLogin(request):
    """
    Checks if username and password match a row in gkusers table.

    If they match a row, org data related to that user are fetched from the orgs column
    in gkusers table. If not the username and password are checked in the old users
    table. If the username is mapped only to one org, then that org's details are
    returned. If the username is mapped to more than one org, then ActionDisallowed
    status is sent with a message asking to contact the admin for login details.
    """
    validated_data = UserLogin.model_validate(request.json_body)
    dataset = validated_data.model_dump()

    with eng.begin() as con:
        result = con.execute(
            select([gkdb.gkusers.c.userid, gkdb.gkusers.c.userpassword]).where(
                and_(
                    gkdb.gkusers.c.username == dataset["username"],
                )
            )
        )
        # if username and password exist in gkusers table
        if result.rowcount != 1:
            return {"gkstatus": enumdict["UnauthorisedAccess"]}

        record = result.fetchone()

        encoded_password = dataset["userpassword"].encode('utf-8')
        encoded_password_hash = record["userpassword"].encode('utf-8')
        if not bcrypt.checkpw(encoded_password, encoded_password_hash):
            return {"gkstatus": enumdict["UnauthorisedAccess"]}

        # check if any orgs are mapped to the userid
        userData = con.execute(
            select([gkdb.gkusers.c.orgs]).where(
                gkdb.gkusers.c.userid == record["userid"]
            )
        ).fetchone()

        payload = {}
        if userData["orgs"]:
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
                if not orgData:
                    print("Log: %d org data is missing " % (int(orgCode)))
                    continue
                if orgData["orgname"] not in payload:
                    payload[orgData["orgname"]] = []
                payload[orgData["orgname"]].append(
                    {
                        "orgname": orgData["orgname"],
                        "yearstart": datetime.strftime(
                            (orgData["yearstart"]), "%d-%m-%Y"
                        ),
                        "orgtype": orgData["orgtype"],
                        "yearend": datetime.strftime(
                            (orgData["yearend"]), "%d-%m-%Y"
                        ),
                        "orgcode": orgCode,
                        "invitestatus": userData["orgs"][orgCode]["invitestatus"],
                        "userrole": userData["orgs"][orgCode]["userrole"],
                    }
                )
        token = generateAuthToken(
            con,
            {"userid": record["userid"], "username": dataset["username"]},
            "user",
        )
        return {
            "gkstatus": enumdict["Success"],
            "userid": record["userid"],
            "token": token,
            "gkresult": payload,
        }


@view_config(route_name="login_org", request_method="POST", renderer="json")
def orgLogin(request):
    """
    purpose:
    """
    try:
        token = request.headers["gkusertoken"]
    except:
        return {"gkstatus": gkcore.enumdict["UnauthorisedAccess"]}
    authDetails = userAuthCheck(token)
    if authDetails["auth"] == False:
        return {"gkstatus": enumdict["UnauthorisedAccess"]}
    validated_data = OrgLogin.model_validate(request.json_body)
    dataset = validated_data.model_dump()
    userId = authDetails["userid"]
    with eng.begin() as con:
        user_org = con.execute(
            select([gkdb.gkusers.c.orgs[str(dataset["orgcode"])]])
            .where(
                and_(
                    func.jsonb_extract_path_text(
                        gkdb.gkusers.c.orgs, str(dataset["orgcode"])
                    ) != None,
                    gkdb.gkusers.c.userid == userId,
                )
            )
        )

        if user_org.rowcount == 1:
            token = generateAuthToken(
                con, {"userid": userId, "orgcode": dataset["orgcode"]}
            )
            if token == -1:
                raise Exception("Issue with generating Auth Token")
            payload = {
                "gkstatus": enumdict["Success"],
                "token": token,
                "userid": userId,
            }
            return payload
        return {"gkstatus": enumdict["UnauthorisedAccess"]}
