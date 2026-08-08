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
"Survesh" <123survesh@gmail.com>
"Sai Karthik"<kskarthik@disroot.org>

"""

from gkcore import eng, enumdict
from gkcore.utils import authCheck
from gkcore.models import gkdb
from gkcore.views.config.services import get_conf
import json
from pyramid.view import view_defaults, view_config
from sqlalchemy.sql.expression import text
from jsonschema import RefResolver, Draft202012Validator, validate
from gkcore.data.config_schema import (
    payloadSchema2,
    transactionBaseSchema,
    transactionConfigSchema,
    transactionPageSchema,
    workflowConfigSchema,
    globalConfigSchema,
)

schema_store = {
    transactionBaseSchema["$id"]: transactionBaseSchema,
    transactionConfigSchema["$id"]: transactionConfigSchema,
    transactionPageSchema["party"]["$id"]: transactionPageSchema["party"],
    transactionPageSchema["ship"]["$id"]: transactionPageSchema["ship"],
    transactionPageSchema["bill"]["$id"]: transactionPageSchema["bill"],
    transactionPageSchema["payment"]["$id"]: transactionPageSchema["payment"],
    transactionPageSchema["transport"]["$id"]: transactionPageSchema["transport"],
    transactionPageSchema["total"]["$id"]: transactionPageSchema["total"],
    transactionPageSchema["comments"]["$id"]: transactionPageSchema["comments"],
}

resolver = RefResolver.from_schema(transactionBaseSchema, store=schema_store)
validator = Draft202012Validator(transactionConfigSchema, resolver=resolver)


@view_defaults(route_name="config")
class api_config(object):
    def __init__(self, request):
        self.request = request


    @view_config(request_method="GET", renderer="json")
    def getConfg(self):
        """ Returns the config of a user/organisation, given proper gktoken
        """
        try:
            token = self.request.headers["gktoken"]
        except:
            return {"gkstatus": enumdict["UnauthorisedAccess"]}
        authDetails = authCheck(token)
        if authDetails["auth"] == False:
            return {"gkstatus": enumdict["UnauthorisedAccess"]}
        with eng.connect() as con:
            pageid = None
            confid = None
            if "pageid" in self.request.params:
                pageid = self.request.params["pageid"]
            if "confid" in self.request.params:
                confid = self.request.params["confid"]
            config = get_conf(
                con,
                self.request.params["conftype"],
                authDetails["orgcode"],
                authDetails["userid"],
                pageid,
                confid,
            )
            return {
                "gkstatus": enumdict["Success"],
                "gkresult": config,
            }


    @view_config(request_method="PUT", renderer="json")
    def updateConfig(self):
        """Updates the entire config
        """
        try:
            token = self.request.headers["gktoken"]
        except:
            return {"gkstatus": enumdict["UnauthorisedAccess"]}
        authDetails = authCheck(token)
        if authDetails["auth"] == False:
            return {"gkstatus": enumdict["UnauthorisedAccess"]}
        with eng.begin() as con:
            dataset = self.request.json_body
            config = dataset["config"]
            confType = self.request.params["conftype"]
            if confType == "user":
                targetPath = [authDetails["orgcode"], "userconf"]
                payload = "'" + json.dumps(config) + "'"
                path = "'{" + ",".join(targetPath) + "}'"
                con.execute(
                    text("update gkusers set orgs = jsonb_set(orgs, :path, :payload) where userid = :userid;"),
                    path = str(path),
                    payload = str(payload),
                    userid = authDetails["userid"],
                )
            else:
                con.execute(
                    gkdb.organisation.update()
                    .where(gkdb.organisation.c.orgcode == authDetails["orgcode"])
                    .values(orgconf=config)
                )
            return {"gkstatus": enumdict["Success"]}


    """
        Updates the config based on the given path
    """

    @view_config(request_method="PUT", request_param="update=path", renderer="json")
    def updateConfigByPath(self):
        try:
            token = self.request.headers["gktoken"]
        except:
            return {"gkstatus": enumdict["UnauthorisedAccess"]}
        authDetails = authCheck(token)
        if authDetails["auth"] == False:
            return {"gkstatus": enumdict["UnauthorisedAccess"]}
        with eng.begin() as conn:
            dataset = self.request.json_body

            # Validate the payload structure
            try:
                validate(instance=dataset, schema=payloadSchema2)
                print("Config Structure Validated")
            except Exception as e:
                # print(e)
                return {
                    "gkstatus": enumdict["ActionDisallowed"],
                    "gkmessage": "Invalid Payload. Please check the payload structure",
                }

            # Array of keys in descending order of hierarchy [parent, child, grand child, etc.]
            pathArr = dataset["path"]

            confToValidate = {}
            target = confToValidate
            pathLen = len(pathArr)
            for pathIndex, path in enumerate(pathArr):
                target[path] = {}
                if pathIndex + 1 < pathLen:
                    target = target[path]
                else:
                    target[path] = dataset["config"]

            # Validate the config structure
            try:
                # print(confToValidate)
                if self.request.params["confcategory"] == "transaction":
                    if "inv" in confToValidate:
                        validator.validate(confToValidate)
                elif self.request.params["confcategory"] == "global":
                    validate(instance=confToValidate, schema=globalConfigSchema)
                else:
                    validate(instance=confToValidate, schema=workflowConfigSchema)
                print("Config Validated")
            except Exception:
                return {
                    "gkstatus": enumdict["ActionDisallowed"],
                    "gkmessage": "Invalid Config. Please check the config structure",
                }

            newConfig = dataset["config"]
            oldConfig = get_conf(
                conn,
                self.request.params["conftype"],
                authDetails["orgcode"],
                authDetails["userid"],
                None,
                None,
            )

            target = oldConfig
            targetPath = []
            targetParent = oldConfig
            payload = {}
            for path in pathArr:
                if type(target) != dict:
                    target = {}
                if path in target:
                    targetPath.append(path)
                    target = target[path]
                else:
                    if not payload:
                        payload = target
                        payload[path] = {}
                        targetParent = payload
                        target = payload[path]
                    else:
                        target[path] = {}
                        targetParent = target
                        target = target[path]
            if not payload:
                payload = newConfig
            else:
                targetParent[path] = newConfig
            if not len(targetPath):
                if self.request.params["conftype"] == "user":
                    targetPath = [str(authDetails["orgcode"]), "userconf"]
                    payload = json.dumps(payload)
                    path = "{" + ",".join(targetPath) + "}"

                    conn.execute(
                        text("update gkusers set orgs = jsonb_set(orgs, :path, :payload) where userid = :userid;"),
                        path = path,
                        payload = payload,
                        userid = authDetails["userid"],
                    )

                elif self.request.params["conftype"] == "org":
                    conn.execute(
                        gkdb.organisation.update()
                        .where(
                            gkdb.organisation.c.orgcode == authDetails["orgcode"]
                        )
                        .values(orgconf=payload)
                    )
            else:
                targetPath = [str(authDetails["orgcode"]), "userconf", *targetPath]
                payload = json.dumps(payload)
                path = "{" + ",".join(targetPath) + "}"
                if self.request.params["conftype"] == "user":
                    conn.execute(
                        text("update gkusers set orgs = jsonb_set(orgs, :path, :payload) where userid = :userid;"),
                        path = path,
                        payload = payload,
                        userid = authDetails["userid"],
                    )
                elif self.request.params["conftype"] == "org":
                    conn.execute(
                        text("update organisation set orgconf = jsonb_set(orgs, :path, :payload) where orgcode = :orgcode;"),
                        path = path,
                        payload = payload,
                        orgcode = authDetails["orgcode"],
                    )
            return {"gkstatus": enumdict["Success"]}
