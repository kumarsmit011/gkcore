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
"Prajkta Patkar"<prajakta@dff.org.in>
"Bhagyashree Pandhare"<bhagya.pandhare@openmailbox.org>
"""

from gkcore import eng, enumdict
from gkcore.utils import authCheck
from gkcore.models.gkdb import (
    tax,
    users,
    product,
    state,
    organisation,
    customerandsupplier,
    groupsubgroups,
    accounts,
)
from sqlalchemy.sql import select
import json
from sqlalchemy.engine.base import Connection
from sqlalchemy import and_, exc
from pyramid.request import Request
from pyramid.response import Response
from pyramid.view import view_defaults, view_config
from sqlalchemy.ext.baked import Result
import gkcore
from sqlalchemy.sql.expression import null


def gstAccName(con, taxname, taxrate, orgcode):
    """
    {u'productcode': 55, u'taxrate': 5.0, u'taxname': u'IGST', 'orgcode': 159}
    tax initialized
    {u'productcode': 55, u'taxrate': 2.0, u'taxname': u'CESS', 'orgcode': 159}
    tax initialized
    {u'productcode': 55, u'taxrate': 1.0, u'taxname': u'VAT', 'orgcode': 159, u'state': u'Maharashtra'}
    category initialized


    This function returns a dictionary which will have all data that is require to create multipleaccounts under subgroup Duties
    & Taxes.

    This function takes taxname, taxrate as parameters.
    create 2 lists for gst and cess tax.
    gst = ["CGSTIN_","CGSTOUT_","SGSTIN_","SGSTOUT_","IGSTIN_","IGSTOUT_"]
    cess = ["CESSIN_","CESSOUT_"]
    Collect all states. for this first get all gstins in organisation where key is statecode,
    then searches for statename and create a list of it.
    Now we have to get all distinct states from customerandsupplier table, and add these states in list if it is not present in list.
    now loop through states list for each state we have create tax accounts.
    First check taxname whether it is IGST i.e. GST
    loop through gst list and concatenate taxname and create tax


    """
    try:
        state_Abbv = []
        accDict = []
        taxNameSGSTIN = ""
        taxNameSGSTOUT = ""
        taxNameCGSTIN = ""
        taxNameCGSTOUT = ""
        taxNameSGSTIN = ""
        taxNameSGSTOUT = ""
        taxNameCGSTIN = ""
        taxNameCGSTOUT = ""
        taxNameIGSTIN = ""
        taxNameIGSTOUT = ""
        taxNameCESSIN = ""
        taxNameCESSOUT = ""

        taxRate = {5: 2.5, 12: 6, 18: 9, 28: 14}

        gstIN = con.execute(
            select([organisation.c.gstin]).where(organisation.c.orgcode == orgcode)
        )
        stCode = gstIN.fetchall()

        if gstIN.rowcount > 0:
            for st in stCode[0][0]:
                if st != "undefined":
                    stABV = con.execute(
                        select([state.c.abbreviation]).where(
                            state.c.statecode == int(st)
                        )
                    )
                    state_Abb = stABV.fetchone()
                    state_Abbv.append(str(state_Abb["abbreviation"]))
                else:
                    continue
        # get distinct states from customerandsupplier
        custState = con.execute(
            select([customerandsupplier.c.gstin]).where(
                customerandsupplier.c.orgcode == orgcode
            )
        )
        cust_sup_state = custState.fetchall()
        if custState.rowcount > 0:
            for b in cust_sup_state:
                c = list(b[0].keys())
                for css in c:
                    stAB = con.execute(
                        select([state.c.abbreviation]).where(
                            state.c.statecode == int(css)
                        )
                    )
                    state_Abbre = stAB.fetchone()
                    if str(state_Abbre["abbreviation"]) not in state_Abbv:
                        state_Abbv.append(str(state_Abbre["abbreviation"]))
                    else:
                        continue

        if len(state_Abbv) != 0:
            grp = con.execute(
                select([groupsubgroups.c.groupcode]).where(
                    and_(
                        groupsubgroups.c.groupname == "Duties & Taxes",
                        groupsubgroups.c.orgcode == orgcode,
                    )
                )
            )
            grpCode = grp.fetchone()
            for states in state_Abbv:
                if taxname == "IGST":
                    if int(taxrate) in taxRate:
                        tx = int(taxrate)
                        taxNameSGSTIN = (
                            "SGSTIN_" + states + "@" + str(taxRate[tx]) + "%"
                        )
                        taxNameSGSTOUT = (
                            "SGSTOUT_" + states + "@" + str(taxRate[tx]) + "%"
                        )
                        taxNameCGSTIN = (
                            "CGSTIN_" + states + "@" + str(taxRate[tx]) + "%"
                        )
                        taxNameCGSTOUT = (
                            "CGSTOUT_" + states + "@" + str(taxRate[tx]) + "%"
                        )

                    taxNameIGSTIN = "IGSTIN_" + states + "@" + "%d" % (taxrate) + "%"
                    taxNameIGSTOUT = "IGSTOUT_" + states + "@" + "%d" % (taxrate) + "%"

                    accDict = [
                        {
                            "accountname": taxNameSGSTIN,
                            "groupcode": grpCode["groupcode"],
                            "orgcode": orgcode,
                            "sysaccount": 1,
                        },
                        {
                            "accountname": taxNameSGSTOUT,
                            "groupcode": grpCode["groupcode"],
                            "orgcode": orgcode,
                            "sysaccount": 1,
                        },
                        {
                            "accountname": taxNameCGSTIN,
                            "groupcode": grpCode["groupcode"],
                            "orgcode": orgcode,
                            "sysaccount": 1,
                        },
                        {
                            "accountname": taxNameCGSTOUT,
                            "groupcode": grpCode["groupcode"],
                            "orgcode": orgcode,
                            "sysaccount": 1,
                        },
                        {
                            "accountname": taxNameIGSTIN,
                            "groupcode": grpCode["groupcode"],
                            "orgcode": orgcode,
                            "sysaccount": 1,
                        },
                        {
                            "accountname": taxNameIGSTOUT,
                            "groupcode": grpCode["groupcode"],
                            "orgcode": orgcode,
                            "sysaccount": 1,
                        },
                    ]
                    try:
                        for acc in accDict:
                            result = con.execute(accounts.insert(), [acc])
                    except:
                        pass

                if taxname == "CESS":
                    taxNameCESSIN = "CESSIN_" + states + "@" + str(int(taxrate)) + "%"
                    taxNameCESSOUT = "CESSOUT_" + states + "@" + str(int(taxrate)) + "%"

                    accDict = [
                        {
                            "accountname": taxNameCESSIN,
                            "groupcode": grpCode["groupcode"],
                            "orgcode": orgcode,
                            "sysaccount": 1,
                        },
                        {
                            "accountname": taxNameCESSOUT,
                            "groupcode": grpCode["groupcode"],
                            "orgcode": orgcode,
                            "sysaccount": 1,
                        },
                    ]
                    try:
                        result = con.execute(accounts.insert(), accDict)
                    except:
                        pass

        return {"gkstatus": "success"}
    except:
        return {"gkstatus": gkcore.enumdict["ConnectionFailed"]}


def calTax(taxflag, source, destination, productcode, con):
    """
    Purpose:
    Takes the product code and returns tax rate based on inter or intra state basis either GST or VAT depending on what is asked for.
    Description:
    This function takes product code, custermer and supplier states and taxflag as parameters and
    returns the tax rate (either GST or VAT).
    Also returns Cess rate if GST is selected.
    The function searches the tax table for the tax rate given the productcode.
    If GST is sent as taxflag then IGST is returned for inter state sales.
    For this the 2 states provided as parameters must be different.
    If it is intra state then IGST is divided by 2 and the values are sent as CGST and SGST.
    In both cases (CGST and IGST) CESS is returned if available in the tax table for the given product code.
    Returns the taxnames as keys (CESS and GST in cases of GST) and their respective rates as values in  dictionary in gkresult.
    """
    try:
        if taxflag == 22:
            # this is VAT.
            if source == destination:
                taxResult = con.execute(
                    select([tax.c.taxrate]).where(
                        and_(
                            tax.c.taxname == "VAT",
                            tax.c.productcode == productcode,
                            tax.c.state == source,
                        )
                    )
                )
                taxData = taxResult.fetchone()
                return {
                    "gkstatus": enumdict["Success"],
                    "gkresult": {"VAT": "%.2f" % float(taxData["taxrate"])},
                }
            else:
                taxResult = con.execute(
                    select([tax.c.taxrate]).where(
                        and_(tax.c.taxname == "CVAT", tax.c.productcode == productcode)
                    )
                )
                taxData = taxResult.fetchone()
                return {
                    "gkstatus": enumdict["Success"],
                    "gkresult": {"CVAT": "%.2f" % float(taxData["taxrate"])},
                }
        else:
            # since it is not 22 means it is 7 = "GST".
            # Also we will need CESS in Both Inter and Intra State GST.
            taxDict = {}
            CESSResult = con.execute(
                select([tax.c.taxrate]).where(
                    and_(tax.c.taxname == "CESS", tax.c.productcode == productcode)
                )
            )
            if CESSResult.rowcount > 0:
                cessRow = CESSResult.fetchone()
                cessData = "%.2f" % float(cessRow["taxrate"])
                taxDict["CESS"] = cessData

            if source == destination:
                # this is SGST and CGST.
                # IGST / 2 = SGST and CGST.
                taxResult = con.execute(
                    select([tax.c.taxrate]).where(
                        and_(tax.c.taxname == "IGST", tax.c.productcode == productcode)
                    )
                )
                taxData = taxResult.fetchone()
                gst = float(taxData["taxrate"]) / 2
                # note although we are returning only SGST, same rate applies to CGST.
                # so when u see taxname is sgst then cgst with same rate is asumed.
                taxDict["SGST"] = gst
                return {"gkstatus": enumdict["Success"], "gkresult": taxDict}
            else:
                # this is IGST.
                taxResult = con.execute(
                    select([tax.c.taxrate]).where(
                        and_(tax.c.taxname == "IGST", tax.c.productcode == productcode)
                    )
                )
                taxData = taxResult.fetchone()
                taxDict["IGST"] = "%.2f" % float(taxData["taxrate"])
                return {"gkstatus": enumdict["Success"], "gkresult": taxDict}
    except:
        return {"gkstatus": gkcore.enumdict["ConnectionFailed"]}


@view_defaults(route_name="tax")
class api_tax(object):
    def __init__(self, request):
        self.request = Request
        self.request = request
        self.con = Connection
        print("tax initialized")

    @view_config(request_method="POST", renderer="json")
    def addtax(self):
        """This method creates tax
        First it checks the user role if the user is admin then only user can add new tax
        """
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
                    select([users.c.userrole]).where(
                        users.c.userid == authDetails["userid"]
                    )
                )
                userRole = user.fetchone()
                dataset = self.request.json_body
                if (
                    userRole["userrole"] == -1
                    or userRole["userrole"] == 1
                    or userRole["userrole"] == 0
                    or userRole["userrole"] == 3
                ):
                    dataset["orgcode"] = authDetails["orgcode"]
                    result = self.con.execute(tax.insert(), [dataset])
                    # In case of gst and cess create tax accounts
                    if dataset["taxname"] != "VAT":
                        r = gstAccName(
                            self.con,
                            dataset["taxname"],
                            dataset["taxrate"],
                            dataset["orgcode"],
                        )
                    return {"gkstatus": enumdict["Success"]}
                else:
                    return {"gkstatus": enumdict["BadPrivilege"]}
            except exc.IntegrityError:
                return {"gkstatus": enumdict["DuplicateEntry"]}
            except:
                return {"gkstatus": gkcore.enumdict["ConnectionFailed"]}
            finally:
                self.con.close()

    @view_config(
        request_method="GET",
        route_name="tax_product",
        request_param="pscflag",
        renderer="json",
    )
    def getprodtax(self):
        """
        This method will return the list of taxes for a product or a category.
        The tax will be either returned for a given product or a category, or with the combination of product and state (Specially for VAT).
        Takes in a parameter for productcode or categorycode, optionally statecode.
        If the flag is p then all the taxes for that product will be returned.
        If it is s then for that product for that state will be returned.
        If it is c then for that category will be returned.
        returns a list of JSON objects.
        """
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
                if self.request.params["pscflag"] == "p":
                    result = self.con.execute(
                        select(
                            [tax.c.taxid, tax.c.taxname, tax.c.taxrate, tax.c.state]
                        ).where(tax.c.productcode == self.request.params["productcode"])
                    )
                    tx = []
                    for row in result:
                        tx.append(
                            {
                                "taxid": row["taxid"],
                                "taxname": row["taxname"],
                                "taxrate": "%.2f" % float(row["taxrate"]),
                                "state": row["state"],
                            }
                        )
                    return {"gkstatus": enumdict["Success"], "gkresult": tx}

                if self.request.params["pscflag"] == "s":
                    result = self.con.execute(
                        select([tax.c.taxid, tax.c.taxname, tax.c.taxrate]).where(
                            and_(
                                tax.c.productcode == self.request.params["productcode"],
                                tax.c.state == self.request.params["state"],
                            )
                        )
                    )
                    tx = []
                    for row in result:
                        tx.append(
                            {
                                "taxid": row["taxid"],
                                "taxname": row["taxname"],
                                "taxrate": "%.2f" % float(row["taxrate"]),
                            }
                        )
                    return {"gkstatus": enumdict["Success"], "gkresult": tx}
                    self.con.close()

                if self.request.params["pscflag"] == "c":
                    result = self.con.execute(
                        select(
                            [tax.c.taxid, tax.c.taxname, tax.c.taxrate, tax.c.state]
                        ).where(
                            tax.c.categorycode == self.request.params["categorycode"]
                        )
                    )
                    tx = []
                    for row in result:
                        tx.append(
                            {
                                "taxid": row["taxid"],
                                "taxname": row["taxname"],
                                "taxrate": "%.2f" % float(row["taxrate"]),
                                "state": row["state"],
                            }
                        )
                    return {"gkstatus": enumdict["Success"], "gkresult": tx}
                if self.request.params["pscflag"] == "i":
                    result = self.con.execute(
                        select([product.c.categorycode]).where(
                            product.c.productcode == self.request.params["productcode"]
                        )
                    )
                    catcoderow = result.fetchone()
                    tx = 0.00
                    if catcoderow["categorycode"] != None:
                        if "state" in self.request.params:
                            result = self.con.execute(
                                select([tax.c.taxrate]).where(
                                    and_(
                                        tax.c.categorycode
                                        == catcoderow["categorycode"],
                                        tax.c.state == self.request.params["state"],
                                    )
                                )
                            )
                            if result.rowcount > 0:
                                taxrow = result.fetchone()
                                tx = taxrow["taxrate"]
                        else:
                            result = self.con.execute(
                                select([tax.c.taxrate]).where(
                                    and_(
                                        tax.c.categorycode
                                        == catcoderow["categorycode"],
                                        tax.c.state == null(),
                                    )
                                )
                            )
                            if result.rowcount > 0:
                                taxrow = result.fetchone()
                                tx = taxrow["taxrate"]
                    else:
                        if "state" in self.request.params:
                            result = self.con.execute(
                                select([tax.c.taxrate]).where(
                                    and_(
                                        tax.c.productcode
                                        == self.request.params["productcode"],
                                        tax.c.state == self.request.params["state"],
                                    )
                                )
                            )
                            if result.rowcount > 0:
                                taxrow = result.fetchone()
                                tx = taxrow["taxrate"]
                        else:
                            result = self.con.execute(
                                select([tax.c.taxrate]).where(
                                    and_(
                                        tax.c.productcode
                                        == self.request.params["productcode"],
                                        tax.c.state == null(),
                                    )
                                )
                            )
                            if result.rowcount > 0:
                                taxrow = result.fetchone()
                                tx = taxrow["taxrate"]
                    return {
                        "gkstatus": enumdict["Success"],
                        "gkresult": "%.2f" % float(tx),
                    }
            except:
                self.con.close()
                return {"gkstatus": enumdict["ConnectionFailed"]}
            finally:
                self.con.close()

    @view_config(request_method="GET", renderer="json")
    def getAllTax(self):
        """This method returns  all existing data about taxes for current organisation"""
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
                    select([tax]).where(tax.c.orgcode == authDetails["orgcode"])
                )
                tx = []
                for row in result:
                    tx.append(
                        {
                            "taxid": row["taxid"],
                            "taxname": row["taxname"],
                            "taxrate": "%.2f" % float(row["taxrate"]),
                            "state": row["state"],
                            "categorycode": row["categorycode"],
                            "productcode": row["productcode"],
                            "orgcode": row["orgcode"],
                        }
                    )

                self.con.close()
                return {"gkstatus": enumdict["Success"], "gkdata": tx}
            except:
                self.con.close()
                return {"gkstatus": enumdict["ConnectionFailed"]}
            finally:
                self.con.close()

    @view_config(request_method="PUT", route_name="tax_taxid", renderer="json")
    def edittaxdata(self):
        """This method updates the taxdata"""
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
                    select([users.c.userrole]).where(
                        users.c.userid == authDetails["userid"]
                    )
                )
                userRole = user.fetchone()
                taxid = self.request.matchdict["taxid"]
                dataset = self.request.json_body
                if (
                    userRole["userrole"] == -1
                    or userRole["userrole"] == 1
                    or userRole["userrole"] == 0
                ):
                    result = self.con.execute(
                        tax.update().where(tax.c.taxid == taxid).values(dataset)
                    )
                    return {"gkstatus": enumdict["Success"]}
                else:
                    return {"gkstatus": enumdict["BadPrivilege"]}
            except:
                return {"gkstatus": gkcore.enumdict["ConnectionFailed"]}
            finally:
                self.con.close()

    @view_config(request_method="DELETE", route_name="tax_taxid", renderer="json")
    def deletetaxdata(self):
        """This method delets the tax data by matching taxid"""
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
                    select([users.c.userrole]).where(
                        users.c.userid == authDetails["userid"]
                    )
                )
                userRole = user.fetchone()
                taxid = self.request.matchdict["taxid"]
                if (
                    userRole["userrole"] == -1
                    or userRole["userrole"] == 1
                    or userRole["userrole"] == 0
                    or userRole["userrole"] == 3
                ):
                    result = self.con.execute(tax.delete().where(tax.c.taxid == taxid))
                    return {"gkstatus": enumdict["Success"]}
                else:
                    {"gkstatus": enumdict["BadPrivilege"]}
            except exc.IntegrityError:
                return {"gkstatus": enumdict["ActionDisallowed"]}
            except:
                return {"gkstatus": enumdict["ConnectionFailed"]}
            finally:
                self.con.close()
