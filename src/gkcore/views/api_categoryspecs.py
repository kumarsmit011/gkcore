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


from gkcore import eng, enumdict
from gkcore.models.gkdb import categoryspecs, categorysubcategories
from sqlalchemy.sql import select
import json
from sqlalchemy.engine.base import Connection
from sqlalchemy import and_, exc
from pyramid.request import Request
from pyramid.view import view_defaults, view_config
import gkcore
from gkcore.utils import authCheck


@view_defaults(route_name="categoryspecs")
class api_categoryspecs(object):
    def __init__(self, request):
        self.request = Request
        self.request = request
        self.con = Connection

    @view_config(request_method="POST", renderer="json")
    def addcategoryspec(self):
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
                dataset["orgcode"] = authDetails["orgcode"]
                result = self.con.execute(categoryspecs.insert(), [dataset])
                result1 = self.con.execute(
                    select([categorysubcategories.c.categorycode]).where(
                        categorysubcategories.c.subcategoryof == dataset["categorycode"]
                    )
                )
                subcatdata = result1.fetchall()
                for categorycode in subcatdata:
                    dataset["categorycode"] = categorycode[0]
                    result1 = self.con.execute(categoryspecs.insert(), [dataset])
                return {"gkstatus": enumdict["Success"]}
            except exc.IntegrityError:
                return {"gkstatus": enumdict["DuplicateEntry"]}
            except:
                return {"gkstatus": gkcore.enumdict["ConnectionFailed"]}
            finally:
                self.con.close()

    @view_config(request_method="GET", renderer="json")
    def getAllcategoryspecs(self):
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
                categorycode = self.request.params["categorycode"]
                result = self.con.execute(
                    select(
                        [
                            categoryspecs.c.attrname,
                            categoryspecs.c.spcode,
                            categoryspecs.c.attrtype,
                        ]
                    )
                    .where(categoryspecs.c.categorycode == categorycode)
                    .order_by(categoryspecs.c.attrname)
                )
                catspecs = []
                for row in result:
                    catspecs.append(
                        {
                            "attrname": row["attrname"],
                            "attrtype": row["attrtype"],
                            "spcode": row["spcode"],
                        }
                    )
                return {"gkstatus": gkcore.enumdict["Success"], "gkresult": catspecs}
            except:
                return {"gkstatus": gkcore.enumdict["ConnectionFailed"]}
            finally:
                self.con.close()

    @view_config(request_method="PUT", renderer="json")
    def editCategorySpecs(self):
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
                result1 = self.con.execute(
                    select([categoryspecs.c.attrname, categoryspecs.c.attrtype]).where(
                        categoryspecs.c.spcode == dataset["spcode"]
                    )
                )
                parentcatdata = result1.fetchone()
                result = self.con.execute(
                    categoryspecs.update()
                    .where(categoryspecs.c.spcode == dataset["spcode"])
                    .values(dataset)
                )
                result1 = self.con.execute(
                    select([categorysubcategories.c.categorycode]).where(
                        categorysubcategories.c.subcategoryof == dataset["categorycode"]
                    )
                )
                subcatdata = result1.fetchall()
                for categorycode in subcatdata:
                    result1 = self.con.execute(
                        select([categoryspecs.c.spcode]).where(
                            and_(
                                categoryspecs.c.categorycode == categorycode[0],
                                categoryspecs.c.attrname
                                == str(parentcatdata["attrname"]),
                                categoryspecs.c.attrtype == parentcatdata["attrtype"],
                            )
                        )
                    )
                    subcatspcode = result1.fetchone()
                    if subcatspcode:
                        dataset["spcode"] = subcatspcode[0]
                        dataset["categorycode"] = categorycode[0]
                        result = self.con.execute(
                            categoryspecs.update()
                            .where(categoryspecs.c.spcode == subcatspcode[0])
                            .values(dataset)
                        )
                return {"gkstatus": enumdict["Success"]}
            except:
                return {"gkstatus": gkcore.enumdict["ConnectionFailed"]}
            finally:
                self.con.close()

    @view_config(request_method="DELETE", renderer="json")
    def deleteCategoryspecs(self):
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
                productcountdata = self.con.execute(
                    select(
                        [
                            categoryspecs.c.productcount,
                            categoryspecs.c.attrname,
                            categoryspecs.c.attrtype,
                            categoryspecs.c.categorycode,
                        ]
                    ).where(categoryspecs.c.spcode == dataset["spcode"])
                )
                productcountrow = productcountdata.fetchone()
                if productcountrow["productcount"] != 0:
                    return {"gkstatus": enumdict["ActionDisallowed"]}
                else:
                    result1 = self.con.execute(
                        select([categorysubcategories.c.categorycode]).where(
                            categorysubcategories.c.subcategoryof
                            == productcountrow["categorycode"]
                        )
                    )
                    subcatdata = result1.fetchall()
                    for categorycode in subcatdata:
                        result1 = self.con.execute(
                            select([categoryspecs.c.spcode]).where(
                                and_(
                                    categoryspecs.c.categorycode == categorycode[0],
                                    categoryspecs.c.attrname
                                    == str(productcountrow["attrname"]),
                                    categoryspecs.c.attrtype
                                    == productcountrow["attrtype"],
                                )
                            )
                        )
                        subcatspcode = result1.fetchone()
                        if subcatspcode:
                            result = self.con.execute(
                                categoryspecs.delete().where(
                                    categoryspecs.c.spcode == subcatspcode[0]
                                )
                            )
                    result = self.con.execute(
                        categoryspecs.delete().where(
                            categoryspecs.c.spcode == dataset["spcode"]
                        )
                    )
                    return {"gkstatus": enumdict["Success"]}
            except:
                return {"gkstatus": enumdict["ConnectionFailed"]}
            finally:
                self.con.close()
