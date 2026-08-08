"""
Copyright (C) 2013, 2014, 2015, 2016 Digital Freedom Foundation
Copyright (C) 2017, 2018, 2019, 2020 Digital Freedom Foundation & Accion Labs PVT LTD
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
"Krishnakant Mane" <kk@dff.org.in>
"Arun Kelkar" <arunkelkar@dff.org.in>
"Abhijith Balan" <abhijithb21@openmailbox.org>
"Prajkta Patkar" <prajakta@dff.org.in>
"Sai Karthik" <kskarthik@disroot.org>
"""

import json

from pyramid.response import Response

from gkcore.views.data.json_handler import (
    delete_organisation, export_org_data, import_org_data, update_organisation_rocode, update_user_conf
)
from pyramid.view import view_config
from gkcore import eng
from sqlalchemy.sql import select
from gkcore.models.gkdb import organisation

from gkcore.views.data import spreadsheet_handler


class api_data(object):
    def __init__(self, request):
        self.request = request

    @view_config(
        route_name="export-xlsx",
        request_method="GET",
        renderer="json",
    )
    def export_spreadsheet(self):
        return spreadsheet_handler.export_ledger(self)

    @view_config(
        route_name="import-xlsx",
        request_method="POST",
        renderer="json",
    )
    def import_tally_spreadsheet(self):
        with eng.connect() as con:
            return spreadsheet_handler.import_tally(self, con)

    @view_config(
        route_name="export-json",
        request_method="GET",
        renderer="json_extended",
        permission="admin",
    )
    def export_json(self):
        """Exports organisation data as JSON"""
        orgcode = self.request.identity.get("orgcode")
        with eng.connect() as con:
            export_file = export_org_data(con, orgcode)
            headerList = {
                "Content-Type": "application/json; charset=utf-8",
                "Content-Length": len(export_file),
                "Content-Disposition": "attachment; filename=report.json",
                "X-Content-Type-Options": "nosniff",
                "Set-Cookie": "fileDownload=true; path=/ ;HttpOnly",
            }
            return Response(
                export_file,
                headerlist=list(headerList.items()),
            )

    @view_config(
        route_name="import-organisation",
        request_method="POST",
        renderer="json",
        is_authenticated=True,
    )
    def import_organisation(self):
        """Imports organisation as new organisation"""
        data = self.request.POST["gkfile"].file
        user_id = self.request.authenticated_userid
        with eng.begin() as con:
            new_orgcode = import_org_data(con, json.load(data))
            update_user_conf(con, user_id, new_orgcode)
            update_organisation_rocode(con, new_orgcode)
        return {"gkstatus": 0}


    @view_config(
        route_name="overwrite-organisation",
        request_method="POST",
        renderer="json_extended",
        permission="admin",
    )
    def overwrite_organisation(self):
        """Imports organisation replacing an existing organisation"""
        data = self.request.POST["gkfile"].file
        user_id = self.request.authenticated_userid
        with eng.begin() as con:
            orgcode = self.request.identity.get("orgcode")
            delete_organisation(con, orgcode)
            new_orgcode = import_org_data(con, json.load(data))
            update_user_conf(con, user_id, new_orgcode)
            update_organisation_rocode(con, new_orgcode)
            org_data = con.execute(
                select([organisation.c.yearstart, organisation.c.yearend])
                .where(organisation.c.orgcode == new_orgcode)
            ).fetchone()
            return {
                "gkstatus": 0,
                "gkresult": {
                    "orgcode": new_orgcode,
                    "yearstart": org_data["yearstart"],
                    "yearend": org_data["yearend"],
                }
            }
