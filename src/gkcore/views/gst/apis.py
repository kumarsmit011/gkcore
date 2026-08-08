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
  Free Software Foundation, Inc.,51 Franklin Street,
  Fifth Floor, Boston, MA 02110, United States


Contributors:
"AKhil KP" <akhilkpdasan@protonmail.com>
'Prajkta Patkar' <prajakta@dff.org.in>
"""

from datetime import datetime
from .schemas import Gstr1SchemaV42
from gkcore.views.gst.services import (
    b2b_r1,
    b2cl_r1,
    b2cs_r1,
    cdnr_r1,
    cdnur_r1,
    docs_issued,
    generate_gstr_3b_data,
    hsn_r1,
)
from sqlalchemy.sql import select, and_
from pyramid.request import Request
from pyramid.view import view_defaults, view_config
from gkcore.utils import authCheck
from gkcore import eng, enumdict
from gkcore.models.gkdb import (
    invoice,
    invoicebin,
    customerandsupplier,
    state,
    drcr,
    transaction,
    organisation,
)
import requests
from base64 import b64decode, b64encode
from json import dumps, loads
import traceback  # for printing detailed exception logs


# @view_defaults(route_name="gstreturns")
class GstReturn(object):
    def __init__(self, request):
        self.request = Request
        self.request = request

    @view_config(request_method="GET", route_name="gstr1", renderer="json")
    def r1(self):
        """
        Returns JSON with b2b, b2cl, b2cs, cdnr, cdnur data required
        to file GSTR1
        Note: In sheets b2b, b2cl, cdnr, cdnur entries are according to
        GST tax rate
        Example:
            If Invoice contains 3 products with taxrates 6%, 12%, 6%
            respectively taxable value of Product 1 and Product 3 will be
            combined into single entry (taxable value and cess amount of these
            products will be added)
            Product 2 will have a separate entry
        """

        token = self.request.headers.get("gktoken", None)
        if token == None:
            return {"gkstatus": enumdict["UnauthorisedAccess"]}

        authDetails = authCheck(token)
        if authDetails["auth"] == False:
            return {"gkstatus": enumdict["UnauthorisedAccess"]}

        with eng.connect() as con:
            dataset = self.request.params
            start_period = datetime.strptime(dataset["start"], "%Y-%m-%d")
            end_period = datetime.strptime(dataset["end"], "%Y-%m-%d")
            orgcode = authDetails["orgcode"]

            # All Sale Invoices
            invoices = con.execute(
               select(
                    [
                        invoice.c.invid,
                        invoice.c.invoiceno,
                        invoice.c.reversecharge,
                        invoice.c.discount,
                        invoice.c.invoicedate,
                        invoice.c.invoicetotal,
                        invoice.c.taxstate,
                        invoice.c.sourcestate,
                        invoice.c.tax,
                        invoice.c.icflag,
                        invoice.c.cess,
                        invoice.c.taxflag,
                        invoice.c.contents,
                        invoice.c.consignee,
                        customerandsupplier.c.gstin,
                        customerandsupplier.c.custname,
                        customerandsupplier.c.gst_reg_type,
                        customerandsupplier.c.gst_party_type,
                        transaction.c.transaction_details,
                    ]
                )
                .select_from(invoice.join(customerandsupplier).join(transaction))
                .where(
                    and_(
                        invoice.c.invoicedate.between(
                            start_period.strftime("%Y-%m-%d"),
                            end_period.strftime("%Y-%m-%d"),
                        ),
                        invoice.c.inoutflag == 15,
                        invoice.c.taxflag == 7,
                        invoice.c.orgcode == orgcode,
                    )
                )
                .order_by(invoice.c.invoicedate)
                .order_by(invoice.c.invid)
            ).fetchall()

            cancelled_invoices = con.execute(
                select([
                    invoicebin.c.invid,
                    invoicebin.c.invoiceno,
                    invoicebin.c.invoicedate,
                    invoicebin.c.icflag,
                ]).where(
                    and_(
                        invoicebin.c.invoicedate.between(
                            start_period.strftime("%Y-%m-%d"),
                            end_period.strftime("%Y-%m-%d"),
                        ),
                        invoicebin.c.inoutflag == 15,
                        invoicebin.c.taxflag == 7,
                        invoicebin.c.orgcode == orgcode,
                    )
                )
                .order_by(invoicebin.c.invoicedate)
                .order_by(invoicebin.c.invid)
            ).fetchall()
            # Debit/credit notes
            drcrs_all = con.execute(
                select(
                    [
                        drcr,
                        invoice.c.invoiceno,
                        invoice.c.invoicedate,
                        invoice.c.invoicetotal,
                        invoice.c.taxstate,
                        invoice.c.sourcestate,
                        invoice.c.tax,
                        invoice.c.cess,
                        invoice.c.taxflag,
                        invoice.c.contents,
                        invoice.c.consignee,
                        customerandsupplier.c.gstin,
                        customerandsupplier.c.custname,
                        customerandsupplier.c.gst_reg_type,
                        customerandsupplier.c.gst_party_type,
                        transaction.c.transaction_details,
                    ]
                )
                .select_from(drcr.join(invoice).join(customerandsupplier).join(transaction))
                .where(
                    and_(
                        drcr.c.drcrdate.between(
                            start_period.strftime("%Y-%m-%d"),
                            end_period.strftime("%Y-%m-%d"),
                        ),
                        invoice.c.inoutflag == 15,
                        drcr.c.orgcode == orgcode,
                    )
                )
                .order_by(drcr.c.drcrid)
            ).fetchall()

            gkdata = {}
            b2b = b2b_r1(con, invoices)
            b2cl = b2cl_r1(con, invoices)
            b2cs = b2cs_r1(con, invoices, False)
            cdnr = cdnr_r1(con, drcrs_all)
            cdnur = cdnur_r1(con, drcrs_all)
            hsn = hsn_r1(con, orgcode, dataset["start"], dataset["end"])
            gkdata["b2b"] = b2b.get("data", [])
            gkdata["b2cl"] = b2cl.get("data", [])
            gkdata["b2cs"] = b2cs.get("data", [])
            gkdata["cdnr"] = cdnr.get("data", [])
            gkdata["cdnur"] = cdnur.get("data", [])
            gkdata["hsn1"] = hsn.get("data", [])

            # JSON prep
            gstin_data = con.execute(
                select([organisation.c.gstin, organisation.c.orgstate]).where(
                    organisation.c.orgcode == orgcode
                )
            ).fetchone()
            gstin = ""
            print(gstin_data)
            if gstin_data["orgstate"]:
                state_code = con.execute(
                    select([state.c.statecode]).where(
                        state.c.statename == gstin_data["orgstate"]
                    )
                ).fetchone()
                state_code = state_code["statecode"]
                print(state_code)
                gstin = ""
                if gstin_data["gstin"]:
                    if str(state_code) in gstin_data["gstin"]:
                        gstin = gstin_data["gstin"][str(state_code)]
                    elif "0" + str(state_code) in gstin_data["gstin"]:
                        gstin = gstin_data["gstin"]["0" + str(state_code)]

            fp = "%s%s" % (end_period.strftime("%m"), end_period.strftime("%Y"))

            gstr1_json = {
                "version": "GST4.2",
                "hash": "hash",
                "gstin": gstin,
                "fp": fp,
                "b2b": b2b["json"],
                "b2cs": b2cs["json"],
                "b2cl": b2cl["json"],
                "cdnr": cdnr["json"],
                "cdnur": cdnur["json"],
                "hsn": hsn["json"],
                "doc_issue": docs_issued(invoices, cancelled_invoices, drcrs_all),
                "nil": {
                    "inv": [
                        {
                            "sply_ty": "INTRB2B",
                            "expt_amt": 0.0,
                            "nil_amt": 0.0,
                            "ngsup_amt": 0,
                        },
                        {
                            "sply_ty": "INTRAB2B",
                            "expt_amt": 0.0,
                            "nil_amt": 0.0,
                            "ngsup_amt": 0,
                        },
                        {
                            "sply_ty": "INTRB2C",
                            "expt_amt": 0.0,
                            "nil_amt": 0.0,
                            "ngsup_amt": 0,
                        },
                        {
                            "sply_ty": "INTRAB2C",
                            "expt_amt": 0.0,
                            "nil_amt": 0.0,
                            "ngsup_amt": 0,
                        },
                    ]
                },
            }

            Gstr1SchemaV42.model_validate(gstr1_json)

            return {
                "gkstatus": enumdict["Success"],
                "gkdata": gkdata,
                "json": gstr1_json,
            }


    @view_config(request_method="GET", route_name="gstr3b", renderer="json")
    def r3b(self):
        token = self.request.headers.get("gktoken", None)
        print("GST return")
        if token == None:
            return {"gkstatus": enumdict["UnauthorisedAccess"]}

        authDetails = authCheck(token)
        if authDetails["auth"] == False:
            return {"gkstatus": enumdict["UnauthorisedAccess"]}

        with eng.connect() as con:

            gst_result = generate_gstr_3b_data(
                con,
                authDetails["orgcode"],
                self.request.params["calculatefrom"],
                self.request.params["calculateto"],
            )

            gst_data = gst_result["data"]
            gst_invoices = gst_result["invoices"]

            date_split = self.request.params["calculateto"].split("-")
            ret_period = date_split[1] + date_split[0]

            gst_json = {
                "gstin": self.request.params["gstin"],
                "ret_period": ret_period,
            }

            # 3.1 Details of Outward Supplies and inward supplies liable to reverse charge
            gst_json["sup_details"] = {
                "osup_zero": {
                    "txval": round(
                        gst_data["outward_taxable_zero_rated"]["taxable_value"], 2
                    ),
                    "iamt": round(gst_data["outward_taxable_zero_rated"]["igst"], 2),
                    "camt": round(gst_data["outward_taxable_zero_rated"]["cgst"], 2),
                    "samt": round(gst_data["outward_taxable_zero_rated"]["sgst"], 2),
                    "csamt": round(gst_data["outward_taxable_zero_rated"]["cess"], 2),
                },
                "osup_nil_exmp": {
                    "txval": round(
                        gst_data["outward_taxable_exempted"]["taxable_value"], 2
                    ),
                    "iamt": round(gst_data["outward_taxable_exempted"]["igst"], 2),
                    "camt": round(gst_data["outward_taxable_exempted"]["cgst"], 2),
                    "samt": round(gst_data["outward_taxable_exempted"]["sgst"], 2),
                    "csamt": round(gst_data["outward_taxable_exempted"]["cess"], 2),
                },
                "osup_det": {
                    "txval": round(
                        gst_data["outward_taxable_supplies"]["taxable_value"], 2
                    ),
                    "iamt": round(gst_data["outward_taxable_supplies"]["igst"], 2),
                    "camt": round(gst_data["outward_taxable_supplies"]["cgst"], 2),
                    "samt": round(gst_data["outward_taxable_supplies"]["sgst"], 2),
                    "csamt": round(gst_data["outward_taxable_supplies"]["cess"], 2),
                },
                "isup_rev": {
                    "txval": round(
                        gst_data["inward_reverse_charge"]["taxable_value"], 2
                    ),
                    "iamt": round(gst_data["inward_reverse_charge"]["igst"], 2),
                    "camt": round(gst_data["inward_reverse_charge"]["cgst"], 2),
                    "samt": round(gst_data["inward_reverse_charge"]["sgst"], 2),
                    "csamt": round(gst_data["inward_reverse_charge"]["cess"], 2),
                },
                "osup_nongst": {
                    "txval": round(gst_data["outward_non_gst"]["taxable_value"], 2),
                    "iamt": round(gst_data["outward_non_gst"]["igst"], 2),
                    "camt": round(gst_data["outward_non_gst"]["cgst"], 2),
                    "samt": round(gst_data["outward_non_gst"]["sgst"], 2),
                    "csamt": round(gst_data["outward_non_gst"]["cess"], 2),
                },
            }

            # 3.2  Of the supplies shown in 3.1 (a), details of inter-state supplies made to unregistered persons, composition taxable person and UIN
            gst_json["inter_sup"] = {
                "unreg_details": [],
                "comp_details": [],
                "uin_details": [],
            }

            for state_code in gst_data["pos_unreg_comp_uin_igst"]:
                item = gst_data["pos_unreg_comp_uin_igst"][state_code]
                gst_json["inter_sup"]["unreg_details"].append(
                    {
                        "pos": state_code,
                        "txval": round(item["unreg_taxable_amt"], 2),
                        "iamt": round(item["unreg_igst"], 2),
                    }
                )
                gst_json["inter_sup"]["comp_details"].append(
                    {
                        "pos": state_code,
                        "txval": round(item["comp_taxable_amt"], 2),
                        "iamt": round(item["comp_igst"], 2),
                    }
                )
                gst_json["inter_sup"]["uin_details"].append(
                    {
                        "pos": state_code,
                        "txval": round(item["uin_taxable_amt"], 2),
                        "iamt": round(item["uin_igst"], 2),
                    }
                )

            # 4. Eligible ITC
            gst_json["itc_elg"] = {
                "itc_avl": [
                    {
                        "ty": "IMPG",
                        "samt": round(gst_data["import_goods"]["sgst"], 2),
                        "csamt": round(gst_data["import_goods"]["cess"], 2),
                        "camt": round(gst_data["import_goods"]["cgst"], 2),
                        "iamt": round(gst_data["import_goods"]["igst"], 2),
                    },
                    {
                        "ty": "IMPS",
                        "samt": round(gst_data["import_service"]["sgst"], 2),
                        "csamt": round(gst_data["import_service"]["cess"], 2),
                        "camt": round(gst_data["import_service"]["cgst"], 2),
                        "iamt": round(gst_data["import_service"]["igst"], 2),
                    },
                    {
                        "ty": "ISRC",
                        "samt": round(gst_data["inward_reverse_charge"]["sgst"], 2),
                        "csamt": round(gst_data["inward_reverse_charge"]["cess"], 2),
                        "camt": round(gst_data["inward_reverse_charge"]["cgst"], 2),
                        "iamt": round(gst_data["inward_reverse_charge"]["igst"], 2),
                    },
                    {
                        "ty": "ISD",
                        "samt": round(gst_data["inward_isd"]["sgst"], 2),
                        "csamt": round(gst_data["inward_isd"]["cess"], 2),
                        "camt": round(gst_data["inward_isd"]["cgst"], 2),
                        "iamt": round(gst_data["inward_isd"]["igst"], 2),
                    },
                    {
                        "ty": "OTH",
                        "samt": round(gst_data["all_itc"]["sgst"], 2),
                        "csamt": round(gst_data["all_itc"]["cess"], 2),
                        "camt": round(gst_data["all_itc"]["cgst"], 2),
                        "iamt": round(gst_data["all_itc"]["igst"], 2),
                    },
                ],
                "itc_net": {
                    "samt": round(gst_data["net_itc"]["sgst"], 2),
                    "csamt": round(gst_data["net_itc"]["cess"], 2),
                    "camt": round(gst_data["net_itc"]["cgst"], 2),
                    "iamt": round(gst_data["net_itc"]["igst"], 2),
                },
                "itc_rev": [
                    {
                        "ty": "RUL",
                        "samt": round(gst_data["itc_reversed_1"]["sgst"], 2),
                        "csamt": round(gst_data["itc_reversed_1"]["cess"], 2),
                        "camt": round(gst_data["itc_reversed_1"]["cgst"], 2),
                        "iamt": round(gst_data["itc_reversed_1"]["igst"], 2),
                    },
                    {
                        "ty": "OTH",
                        "samt": round(gst_data["itc_reversed_2"]["sgst"], 2),
                        "csamt": round(gst_data["itc_reversed_2"]["cess"], 2),
                        "camt": round(gst_data["itc_reversed_2"]["cgst"], 2),
                        "iamt": round(gst_data["itc_reversed_2"]["igst"], 2),
                    },
                ],
                "itc_inelg": [
                    {
                        "ty": "RUL",
                        "samt": round(gst_data["ineligible_1"]["sgst"], 2),
                        "csamt": round(gst_data["ineligible_1"]["cess"], 2),
                        "camt": round(gst_data["ineligible_1"]["cgst"], 2),
                        "iamt": round(gst_data["ineligible_1"]["igst"], 2),
                    },
                    {
                        "ty": "OTH",
                        "samt": round(gst_data["ineligible_2"]["sgst"], 2),
                        "csamt": round(gst_data["ineligible_2"]["cess"], 2),
                        "camt": round(gst_data["ineligible_2"]["cgst"], 2),
                        "iamt": round(gst_data["ineligible_2"]["igst"], 2),
                    },
                ],
            }

            # 5. Values of exempt, Nil-rated and non-GST inward supplies
            gst_json["inward_sup"] = {
                "isup_details": [
                    {
                        "ty": "GST",
                        "inter": round(gst_data["inward_zero_gst"]["inter"], 2),
                        "intra": round(gst_data["inward_zero_gst"]["intra"], 2),
                    },
                    {
                        "ty": "NONGST",
                        "inter": round(gst_data["non_gst"]["inter"], 2),
                        "intra": round(gst_data["non_gst"]["intra"], 2),
                    },
                ]
            }

            # 5.1 Interest & late fee payable
            gst_json["intr_ltfee"] = {
                "intr_details": {
                    "samt": round(gst_data["interest"]["sgst"], 2),
                    "csamt": round(gst_data["interest"]["cess"], 2),
                    "camt": round(gst_data["interest"]["cgst"], 2),
                    "iamt": round(gst_data["interest"]["igst"], 2),
                },
                "ltfee_details": {},
            }

            return {
                "gkstatus": enumdict["Success"],
                "gkresult": {"json": gst_json, "invoice": gst_invoices},
            }


    @view_config(request_method="GET", route_name="gst-captcha", renderer="json")
    def getGstinCaptcha(self):
        req1 = requests.get("https://www.gst.gov.in/")
        if req1.status_code == 200:
            cookie1 = {}
            for cookie in req1.cookies:
                cookie1[cookie.name] = cookie.value
            URL = "https://services.gst.gov.in/services/captcha"
            # print(req1.cookies)
            headers = {
                "User-Agent": "GNUKhata_devel_0",  # The GST API maintainers have blocked the default python user agent. In the future they may add more restrictions, so must move to a better API
            }
            req = requests.get(url=URL, cookies=cookie1, headers=headers)
            if req.status_code == 200:
                # print(req.content)
                cookieString = "Lang=en;"
                for cookie in req.cookies:
                    cookieString += cookie.name + "=" + cookie.value + ";"
                img = b64encode(req.content).decode("utf-8")
                payload = {
                    "gkstatus": enumdict["Success"],
                    "gkresult": {
                        "captcha": img,
                        "cookie": cookieString,
                    },
                }
            else:
                print(req.status_code)
                payload = {"gkstatus": enumdict["ConnectionFailed"]}
        else:
            print(req.status_code)
            payload = {"gkstatus": enumdict["ConnectionFailed"]}
        return payload

    @view_config(request_method="POST", route_name="gst-captcha", renderer="json")
    def validateGstinCaptcha(self):
        dataset = self.request.json_body
        URL = "https://services.gst.gov.in/services/api/search/taxpayerDetails"
        headers = {
            "Referer": "https://services.gst.gov.in/services/searchtp",
            "Cookie": dataset["cookie"],
            "Content-Type": "application/json",
            "User-Agent": "GNUKhata_devel_0",  # The GST API maintainers have blocked the default python user agent. In the future they may add more restrictions, so must move to a better API
        }
        req = requests.post(url=URL, data=dumps(dataset["payload"]), headers=headers)
        if req.status_code == 200:
            resp = loads(req.text)
            if "errorCode" in resp:
                payload = {"gkstatus": enumdict["ConnectionFailed"], "gkerror": resp}
            else:
                payload = {"gkstatus": enumdict["Success"], "gkresult": resp}
        else:
            payload = {"gkstatus": enumdict["ConnectionFailed"]}
        return payload
