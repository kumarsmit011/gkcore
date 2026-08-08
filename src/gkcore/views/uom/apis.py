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


from sqlalchemy import desc
from requests import request
from gkcore import eng, enumdict
from gkcore.models import gkdb
from gkcore.views.uom.schemas import UnitOfMeasurement, UnitOfMeasurementUpdate
from sqlalchemy.sql import select
from sqlalchemy.engine.base import Connection
from sqlalchemy import and_, exc, desc, func, or_
from pyramid.request import Request
from pyramid.view import view_defaults, view_config
import gkcore
from gkcore.models.meta import gk_api
from gkcore.utils import authCheck, gk_log


@view_defaults(route_name="uom")
class api_unitOfMeasurement(object):
    def __init__(self, request):
        self.request = Request
        self.request = request
        self.con = Connection

    @view_config(request_method="POST", renderer="json")
    def addUnitOfMeasurement(self):
        try:
            token = self.request.headers["gktoken"]
        except:
            return {"gkstatus": gkcore.enumdict["UnauthorisedAccess"]}
        authDetails = authCheck(token)
        if authDetails["auth"] == False:
            return {"gkstatus": enumdict["UnauthorisedAccess"]}
        validated_data = UnitOfMeasurement.model_validate(
            self.request.json_body, context={"orgcode": authDetails["orgcode"]}
        )
        dataset = validated_data.model_dump(exclude_none=True)
        with eng.begin() as con:
            dataset.update(
                {
                    "orgcode": authDetails["orgcode"],
                    "sysunit": 0,
                }
            )
            con.execute(gkdb.unitofmeasurement.insert(), [dataset])
            return {"gkstatus": enumdict["Success"]}


    """
    This function is for the condition that the units of measurement which
    are associated with products can not be deleted.
    """

    @view_config(route_name="uom-single", request_method="GET", renderer="json")
    def getUnitOfMeasurement(self):
        try:
            token = self.request.headers["gktoken"]
        except:
            return {"gkstatus": enumdict["UnauthorisedAccess"]}
        authDetails = authCheck(token)
        if authDetails["auth"] == False:
            return {"gkstatus": enumdict["UnauthorisedAccess"]}
        with eng.connect() as con:
            result = con.execute(
                select([gkdb.unitofmeasurement]).where(
                    gkdb.unitofmeasurement.c.uomid == str(self.request.matchdict["uomid"])
                )
            )
            row = result.fetchone()
            unitofmeasurement = {
                "uomid": row["uomid"],
                "unitname": row["unitname"],
                "conversionrate": "%.2f" % float(row["conversionrate"]),
                "subunitof": row["subunitof"],
                "description": row["description"],
                "sysunit": row["sysunit"],
                "uqc": row["uqc"],
            }
            countresult = con.execute(
                select([func.count(gkdb.product.c.uomid).label("subcount")])
                .where(gkdb.product.c.uomid == row["uomid"])
            )
            countrow = countresult.fetchone()
            subcount = countrow["subcount"]
            if subcount > 0:
                unitofmeasurement["flag"] = "True"
            else:
                unitofmeasurement["flag"] = "False"
            return {
                "gkstatus": gkcore.enumdict["Success"],
                "gkresult": unitofmeasurement,
            }


    @view_config(request_method="PUT", renderer="json")
    def editunitofmeasurement(self):
        try:
            token = self.request.headers["gktoken"]
        except:
            return {"gkstatus": gkcore.enumdict["UnauthorisedAccess"]}
        authDetails = authCheck(token)
        if authDetails["auth"] == False:
            return {"gkstatus": enumdict["UnauthorisedAccess"]}
        validated_data = UnitOfMeasurementUpdate.model_validate(
            self.request.json_body, context={"orgcode": authDetails["orgcode"]}
        )
        dataset = validated_data.model_dump(exclude_none=True)
        dataset.update(
            {
                "orgcode": authDetails["orgcode"],
                "sysunit": 0,
            }
        )
        with eng.begin() as con:
            uom = con.execute(
                gkdb.unitofmeasurement.update()
                .where(
                    and_(
                        gkdb.unitofmeasurement.c.uomid == dataset["uomid"],
                        gkdb.unitofmeasurement.c.orgcode == authDetails["orgcode"],
                    )
                )
                .values(dataset)
                .returning(gkdb.unitofmeasurement.c.uomid)
            )
            if not uom.scalar():
                return {"gkstatus": enumdict["ActionDisallowed"]}
            return {"gkstatus": enumdict["Success"]}


    @view_config(request_method="GET", renderer="json_extended")
    def getAllunitofmeasurements(self):
        try:
            token = self.request.headers["gktoken"]
        except:
            return {"gkstatus": gkcore.enumdict["UnauthorisedAccess"]}
        authDetails = authCheck(token)
        if authDetails["auth"] == False:
            return {"gkstatus": gkcore.enumdict["UnauthorisedAccess"]}
        with eng.connect() as con:
            # there is only one possibility for a catch which is failed connection to db.
            result = con.execute(
                select(
                    [
                        gkdb.unitofmeasurement.c.unitname,
                        gkdb.unitofmeasurement.c.uomid,
                        gkdb.unitofmeasurement.c.description,
                        gkdb.unitofmeasurement.c.subunitof,
                        gkdb.unitofmeasurement.c.sysunit,
                        gkdb.unitofmeasurement.c.uqc,
                        gkdb.unitofmeasurement.c.conversionrate,
                    ]
                )
                .where(
                    or_(
                        gkdb.unitofmeasurement.c.orgcode == authDetails["orgcode"],
                        gkdb.unitofmeasurement.c.orgcode == None,
                    )
                )
                .order_by(desc(gkdb.unitofmeasurement.c.uomid))
            )
            unitofmeasurements = []
            for row in result:
                unitofmeasurements.append(
                    {
                        "uomid": row["uomid"],
                        "unitname": row["unitname"],
                        "description": row["description"],
                        "subunitof": row["subunitof"],
                        "sysunit": row["sysunit"],
                        "uqc": row["uqc"],
                        "conversionrate": row["conversionrate"],
                    }
                )
            return {
                "gkstatus": gkcore.enumdict["Success"],
                "gkresult": unitofmeasurements,
            }


    @view_config(request_method="DELETE", renderer="json")
    def deleteunitofmeasurement(self):
        """Delete a Unit of measurement. Do not delete UOM which is associated with a product"""
        try:
            token = self.request.headers["gktoken"]
        except:
            return {"gkstatus": enumdict["UnauthorisedAccess"]}
        authDetails = authCheck(token)
        if authDetails["auth"] == False:
            return {"gkstatus": enumdict["UnauthorisedAccess"]}
        with eng.begin() as con:
            dataset = self.request.json_body
            # check if uom is associated with any product/service
            check_uom = gk_api(
                url=f"/unitofmeasurement/{dataset['uomid']}",
                request=self.request,
                header=self.request.headers,
            )
            gk_log(__name__).warn(check_uom)
            # if it is used in a product/service, do not delete it
            if check_uom["gkresult"]["flag"] == "True":
                return {"gkstatus": enumdict["ActionDisallowed"]}
            # proceed to deletion if not used
            uom = con.execute(
                gkdb.unitofmeasurement
                .delete()
                .where(
                    and_(
                        gkdb.unitofmeasurement.c.uomid == dataset["uomid"],
                        gkdb.unitofmeasurement.c.orgcode == authDetails["orgcode"],
                    )
                )
                .returning(gkdb.unitofmeasurement.c.uomid)
            )
            if not uom.scalar():
                return {"gkstatus": enumdict["ActionDisallowed"]}
            return {"gkstatus": enumdict["Success"]}
