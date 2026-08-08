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
"Sai Karthik"<kskarthik@disrot.org>

"""


from gkcore.utils import authCheck
from pyramid.request import Request
from pyramid.view import view_defaults, view_config
import re
from gkcore import enumdict
from gkcore.views.helpers.fin_utils import hsn_codes


@view_defaults(route_name="hsn")
class api_hsn(object):
    def __init__(self, request):
        self.request = Request
        self.request = request

    @view_config(
        request_method="GET",
        request_param="validate",
        renderer="json",
    )
    def hsn_validate(self):
        """Validate given HSN code\n
        Return gkstatus 0 when success. Else, return Status 3.

        `params:`\n
        *validate* = hsn code

        """
        # Check whether the user is registered & valid
        try:
            token = self.request.headers["gktoken"]
        except:
            return {"gkstatus": enumdict["UnauthorisedAccess"]}

        auth_details = authCheck(token)

        if auth_details["auth"] == False:
            return {"gkstatus": enumdict["UnauthorisedAccess"]}

        # eval the given hsn code
        try:
            for code in hsn_codes():
                if self.request.params["validate"] == str(code["hsn_code"]):
                    return {"gkstatus": 0, "gkresult": code}
            else:
                return {"gkstatus": 3}
        except Exception as e:
            print(e)
            return {"gkstatus": 3}

    @view_config(
        request_method="GET",
        request_param="search",
        renderer="json",
    )
    def hsn_search(self):
        """Search for given HSN text

        Return gkstatus 0 when success & gkresult array. Else, return Status 3

        # params:
        `search` = search term

        """

        # Check whether the user is registered & valid
        try:
            token = self.request.headers["gktoken"]
        except:
            return {"gkstatus": enumdict["UnauthorisedAccess"]}

        auth_details = authCheck(token)

        if auth_details["auth"] is False:
            return {"gkstatus": enumdict["UnauthorisedAccess"]}

        # search result handling
        try:
            search_term: str = self.request.params["search"].lower()
            search_results = []

            for obj in hsn_codes():
                desc_occurances = re.findall(search_term, obj["hsn_desc"].lower())
                code_occurances = re.findall(search_term, str(obj["hsn_code"]))

                if len(desc_occurances) > 0:
                    search_results.append(obj)

                if len(code_occurances) > 0:
                    search_results.append(obj)

            return {"gkstatus": 0, "gkresult": search_results}
        except Exception as e:
            print(e)
            return {"gkstatus": 3}
