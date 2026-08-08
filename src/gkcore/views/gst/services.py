from ast import literal_eval
from copy import deepcopy
from collections import defaultdict
from sqlalchemy.sql import select
from sqlalchemy.sql.expression import text
from gkcore.views.api_invoice import getInvoiceList, getInvoiceData
from gkcore.models.gkdb import (
    state,
    product,
    unitofmeasurement,
)
from ast import literal_eval
from json import loads
from gkcore.data.enum import GST_REG_TYPE

import traceback  # for printing detailed exception logs




def round_2_dec(value):
    """Round to two decimal places."""
    return round(float(value), 2)

def taxable_value(con, inv, productcode, drcr=False):
    """
    Returns taxable value of product given invoice/drcr note and productcode
    If dr/cr is due to change in quantity(drcrmode=18) then taxable value is
    present in reductionval dict with productcode as key else dr/cr must be a
    change in ppu and new rate has to be retrieved
    """
    try:
        rate, qty = list(inv["contents"][productcode].items())[0]
        query = select([product.c.gsflag]).where(product.c.productcode == productcode)
        gsflag = con.execute(query).fetchone()[0]
        if gsflag == 19:
            qty = 1

        if drcr:
            if inv["drcrmode"] == 18:
                return float(inv["reductionval"][productcode])
            else:
                rate = inv["reductionval"][productcode]

        taxable_value = float(rate) * float(qty)
        if not drcr:
            taxable_value -= float(inv["discount"][productcode])
        return round_2_dec(taxable_value)
    except:
        print(traceback.format_exc())
        return 0


def cess_amount(con, inv, productcode, drcr=False):
    """
    Returns cess amount of product given invoice/drcr note and productcode
    """
    try:
        if inv["cess"].get(productcode) == 0 or inv["cess"] == {}:
            return 0
        else:
            cess_rate = float(inv["cess"][productcode])

            t_value = taxable_value(con, inv, productcode, drcr=drcr)
            cess_amount = t_value * cess_rate / 100

            return round_2_dec(cess_amount)
    except:
        print(traceback.format_exc())
        return 0


def state_name_code(con, statename=None, statecode=None):
    """
    Returns statecode if statename is given
    Returns statename if statecode is given
    """
    if statename:
        query = select([state.c.statecode]).where(state.c.statename == statename)
    else:
        query = select([state.c.statename]).where(state.c.statecode == statecode)
    result = con.execute(query).fetchone()[0]
    return result


def normalise_state_code(statecode, gstin):
    """
    Sometimes statecode < 10 will be prefixed with zero and sometimes not
    This causes issues while using the wrong the statecode in gstin objects
    Returns a normalised statecode that is available in the gstin object
    """
    if int(statecode) < 10:
        if gstin and statecode not in gstin:
            if ("0" + str(statecode)) in gstin:
                statecode = "0" + str(statecode)
    return statecode


def product_level(con, inv, drcr=False):
    """
    Invoices/drcr notes can contain multiple products with different tax rates
    this function adds taxable value and cess amount of all products with same
    rate `data` is a dictionary with tax_rate as key and value is a dictionary
    containing taxable_value and cess_amount

    If drcr flag is True then products will be in reductionval dict
    If drcr is change in quantity then reductionval dict will contain a key
    quantities. Quantities dict contains the new quantity but that will be
    handled by taxable_value function so we can remove it
    """

    data = {}
    if drcr:
        products = list(inv["reductionval"].keys())
        if "quantities" in products:
            products.remove("quantities")
    else:
        products = inv["contents"]

    for prod in products:
        rate = float(inv["tax"][prod])
        if data.get(rate, None):
            data[rate]["taxable_value"] += taxable_value(con, inv, prod, drcr)
            data[rate]["cess"] += cess_amount(con, inv, prod, drcr)
        else:
            data[rate] = {}
            data[rate]["taxable_value"] = taxable_value(con, inv, prod, drcr)
            data[rate]["cess"] = cess_amount(con, inv, prod, drcr)

    return data


def b2b_r1(con, invoices):
    """
    Collects and formats data about invoices made to other registered taxpayers
    """

    try:

        def b2b_filter(inv):
            return check_report_properties(inv)[0]

        invs = list(filter(b2b_filter, invoices))
        b2b = []
        b2b_json = {}
        for inv in invs:
            ts_code = normalise_state_code(
                state_name_code(con, statename=inv["taxstate"]), inv["gstin"]
            )

            row = defaultdict(dict)
            row["gstin"] = list(
                inv["transaction_details"]["contact"]["gstin"].values()
            )[0]
            row["receiver"] = inv["custname"]
            row["invid"] = inv["invid"]
            row["invoice_number"] = inv["invoiceno"]
            row["invoice_date"] = inv["invoicedate"].strftime("%d-%b-%y")
            row["invoice_value"] = round_2_dec(inv["invoicetotal"])
            row["place_of_supply"] = "%s-%s" % (str(ts_code), inv["taxstate"])
            row["applicable_tax_rate"] = ""
            row["invoice_type"] = "Regular"
            row["ecommerce_gstin"] = ""
            if inv["reversecharge"] == "0":
                row["reverse_charge"] = "N"
            else:
                row["reverse_charge"] = "Y"

            b2b_json_inv = {
                "inum": inv["invoiceno"],
                "idt": inv["invoicedate"].strftime("%d-%m-%Y"),
                "val": round_2_dec(inv["invoicetotal"]),
                "pos": "%02d" % int(ts_code),
                "rchrg": row["reverse_charge"],
                "inv_typ": "R",  # Need to handle other gst types
                "itms": [],
            }
            for rate, tax_cess in list(product_level(con, inv).items()):
                prod_row = deepcopy(row)
                prod_row["taxable_value"] = "%.2f" % tax_cess["taxable_value"]
                prod_row["rate"] = "%.2f" % rate
                prod_row["cess"] = "%.2f" % tax_cess["cess"]
                b2b.append(prod_row)

                b2b_json_item = {
                    "num": 1
                    if not prod_row["rate"]
                    else "%d%02d"
                    % (
                        int(float(prod_row["rate"])),
                        1,
                    ),  # need to check how floating vales are handled
                    "itm_det": {
                        "txval": prod_row["taxable_value"],
                        "rt": prod_row["rate"],
                        "csamt": prod_row["cess"],
                    },
                }
                tax_amt = "%.2f" % (
                    (float(prod_row["taxable_value"]) * float(rate)) / 100.0
                )
                if inv["taxstate"] == inv["sourcestate"]:
                    b2b_json_item["itm_det"].update(
                        {
                            "camt": "%.2f" % (float(tax_amt) / 2.0),
                            "samt": "%.2f" % (float(tax_amt) / 2.0),
                        }
                    )
                else:
                    b2b_json_item["itm_det"].update(
                        {
                            "iamt": tax_amt,
                        }
                    )

                b2b_json_inv["itms"].append(b2b_json_item)

            if row["gstin"] not in b2b_json:
                b2b_json[row["gstin"]] = []

            b2b_json[row["gstin"]].append(b2b_json_inv)

        b2b_json_arr = []
        for gstin in b2b_json:
            b2b_json_arr.append({"ctin": gstin, "inv": b2b_json[gstin]})

        return {"status": 0, "data": b2b, "json": b2b_json_arr}
    except:
        print(traceback.format_exc())
        return {"status": 3}


def b2cl_r1(con, invoices):
    """
    Collects and formats data about invoices for taxable outward supplies to
    consumers where:
        a)Place of supply is outside the state where the supplier is registered
        b)The total invoice value is more than Rs 2,50,000
    """

    try:

        def b2cl_filter(inv):
            is_b2b, is_large, is_igst = check_report_properties(inv)
            return (not is_b2b and is_large and is_igst)

        # print("Invoice count = %d" % (len(invoices)))
        invs = list(filter(b2cl_filter, invoices))

        b2cl = []
        b2cl_json = {}
        for inv in invs:
            ts_code = state_name_code(con, statename=inv["taxstate"])

            row = {}
            row["invid"] = inv["invid"]
            row["invoice_number"] = inv["invoiceno"]
            row["invoice_date"] = inv["invoicedate"].strftime("%d-%b-%y")
            row["invoice_value"] = round_2_dec(inv["invoicetotal"])
            row["place_of_supply"] = "%02d-%s" % (ts_code, inv["taxstate"])
            row["applicable_tax_rate"] = ""
            row["ecommerce_gstin"] = ""
            row["sale_from_bonded_wh"] = "N"

            b2cl_json_inv = {
                "inum": inv["invoiceno"],
                "idt": inv["invoicedate"].strftime("%d-%m-%Y"),
                "val": round_2_dec(inv["invoicetotal"]),
                "itms": [],
            }

            for rate, tax_cess in list(product_level(con, inv).items()):
                prod_row = deepcopy(row)
                prod_row["taxable_value"] = "%.2f" % tax_cess["taxable_value"]
                prod_row["rate"] = "%.2f" % rate
                prod_row["cess"] = "%.2f" % tax_cess["cess"]
                b2cl.append(prod_row)
                tax_amt = "%.2f" % (
                    (tax_cess["taxable_value"] * rate) / 100.0
                )

                b2cl_json_item = {
                    "num": 1 if not rate else "%d%02d" % (rate, 1),
                    "itm_det": {
                        "txval": prod_row["taxable_value"],
                        "rt": prod_row["rate"],
                        "csamt": prod_row["cess"],
                        "iamt": tax_amt,
                    },
                }

                b2cl_json_inv["itms"].append(b2cl_json_item)

            if ts_code not in b2cl_json:
                b2cl_json[ts_code] = []

            b2cl_json[ts_code].append(b2cl_json_inv)

        b2cl_json_arr = []
        for b2cl_pos in b2cl_json:
            b2cl_json_arr.append(
                {"pos": "%02d" % (b2cl_pos), "inv": b2cl_json[b2cl_pos]}
            )

        return {"status": 0, "data": b2cl, "json": b2cl_json_arr}
    except:
        print(traceback.format_exc())
        return {"status": 3}


def b2cs_r1(con, invoices, drcr):
    """
    Collects and formats data about supplies made to consumers
    of the following nature:
        a)Intra-State: Any value
        b)Inter-State: Invoice value Rs 2.5 lakhs or less

    Note1: Here entries are not made invoice wise instead entries with same
    place_of_supply and taxrate are consolidated.
    Debit Credit Notes that match the above conditions are also listed under B2CS, with negative value
    """

    try:

        def b2cs_filter(inv):
            is_b2b, is_large, is_igst = check_report_properties(inv)
            return (
                not is_b2b and (
                    (is_large and not is_igst) or not is_large
                )
            )

        invs = list(filter(b2cs_filter, invoices))
        print("inv count = %d" % (len(invoices)))
        b2cs = []
        b2cs_map = {}
        for inv in invs:
            inv = dict(inv)
            ts_code = state_name_code(con, statename=inv["taxstate"])
            if int(ts_code) < 10:
                ts_code = "0" + str(ts_code)
            row = {
                "invid": inv["invid"],
                "invoice_number": inv["invoiceno"],
                "drcrid": inv.get("drcrid"),
                "voucher_number": inv.get("drcrno"),
                "voucher_date": (
                    inv.get("drcrdate").strftime("%d-%b-%y")
                    if inv.get("drcrdate") else ""
                ),
                "icflag": inv.get("icflag", 9),
                "type": "OE",
                "place_of_supply": "%s-%s" % (str(ts_code), inv["taxstate"]),
                "applicable_tax_rate": "",
                "ecommerce_gstin": "",
            }
            b2cs_json_inv = {
                "sply_ty": "INTRA"
                if inv["taxstate"] == inv["sourcestate"]
                else "INTER",
                "pos": "%02d" % (int(ts_code)),
                "typ": "OE",
            }

            for prod in inv["contents"]:
                prod_taxable_value = taxable_value(con, inv, prod, drcr)
                rate = inv["tax"][prod]

                prod_row = {
                    "taxable_value": prod_taxable_value,
                    "rate": round_2_dec(rate),
                    "cess": cess_amount(con, inv, prod, drcr) or 0,
                    **row
                }
                b2cs.append(prod_row)
                tax_amt = float(prod_row["taxable_value"]) * float(rate) / 100

                samt = iamt = 0
                if inv["taxstate"] == inv["sourcestate"]:
                    samt = tax_amt/2
                else:
                    iamt = tax_amt
                tax_rate_string = f"{rate}{ts_code}"
                tax_rate_group = b2cs_map.get(tax_rate_string)

                if tax_rate_group:
                    samt += tax_rate_group.get("samt", 0)
                    iamt += tax_rate_group.get("iamt", 0)
                    prod_taxable_value += tax_rate_group.get("txval", 0)
                else:
                    tax_rate_group = b2cs_map[tax_rate_string] = {
                        **b2cs_json_inv,
                        "rt": prod_row["rate"],
                    }
                tax_rate_group.update(
                    {
                        "samt": samt,
                        "camt": samt,
                        "iamt": iamt,
                        "txval": prod_taxable_value,
                    }
                )

        def format_b2cs_values(b2cs_entry):
            b2cs_entry.update(
                {
                    "samt": round_2_dec(b2cs_entry["samt"]),
                    "camt": round_2_dec(b2cs_entry["samt"]),
                    "iamt": round_2_dec(b2cs_entry["iamt"]),
                    "txval": round_2_dec(b2cs_entry["txval"]),
                }
            )
            return b2cs_entry
        b2cs_json = list(map(format_b2cs_values, b2cs_map.values()))

        for row in b2cs:
            # row["drcr_flag"] = 1 if drcr else 0
            if drcr:
                row["taxable_value"] *= -1
            row["taxable_value"] = "%.2f" % row["taxable_value"]
            if row["cess"] == 0:
                row["cess"] = "0.00"
            else:
                row["cess"] = "%.2f" % row["cess"]
        return {"status": 0, "json": b2cs_json, "data": b2cs}
    except:
        print(traceback.format_exc())
        return {"status": 3, "data": []}


def cdnr_r1(con, drcr_all):
    """
    Collects and formats data about Credit/Debit Notes issued
    to the registered taxpayers
    """

    try:
        def cdnr_filter(drcr):
            return check_report_properties(drcr)[0]

        # print("drcr notes = %d" % (len(drcr_all)))
        drcrs = list(filter(cdnr_filter, drcr_all))

        cdnr = []
        cdnr_json = {}
        for note in drcrs:
            ts_code = normalise_state_code(
                state_name_code(con, statename=note["taxstate"]), note["gstin"]
            )
            # print(note.keys())
            row = {}
            # print("Invoice id: %s"%(str(note["invid"])))
            row["gstin"] = list(
                note["transaction_details"]["contact"]["gstin"].values()
            )[0]
            row["receiver"] = note["custname"]
            row["invid"] = note["invid"]
            row["invoice_number"] = note["invoiceno"]
            row["invoice_date"] = note["invoicedate"].strftime("%d-%b-%y")
            row["drcrid"] = note["drcrid"]
            row["voucher_number"] = note["drcrno"]
            row["voucher_date"] = note["drcrdate"].strftime("%d-%b-%y")
            if note["dctypeflag"] == 4:
                row["document_type"] = "D"
            else:
                row["document_type"] = "C"
            row["place_of_supply"] = "%s-%s" % (str(ts_code), note["taxstate"])
            row["refund_voucher_value"] = round_2_dec(note["totreduct"])
            row["applicable_tax_rate"] = ""
            if note["taxflag"] == 7:
                row["pregst"] = "N"
            else:
                row["pregst"] = "Y"

            cdnr_json_inv = {
                "nt_num": note["drcrno"],
                "nt_dt": note["invoicedate"].strftime("%d-%m-%Y"),
                "val": round_2_dec(note["totreduct"]),
                "ntty": "D" if note["dctypeflag"] == 4 else "C",
                "pos": "%02d" % (ts_code),
                "rchrg": "N",
                "inv_typ": "R",  # Need to handle other gst types
                "itms": [],
            }
            for rate, tax_cess in list(product_level(con, note, drcr=True).items()):
                prod_row = deepcopy(row)
                prod_row["taxable_value"] = "%.2f" % tax_cess["taxable_value"]
                prod_row["rate"] = "%.2f" % rate
                prod_row["cess"] = "%.2f" % tax_cess["cess"]
                cdnr.append(prod_row)

                cdnr_json_item = {
                    "num": 1
                    if not prod_row["rate"]
                    else "%d%02d"
                    % (
                        int(float(prod_row["rate"])),
                        1,
                    ),  # need to check how floating values are handled
                    "itm_det": {
                        "txval": prod_row["taxable_value"],
                        "rt": prod_row["rate"],
                        "csamt": prod_row["cess"],
                    },
                }
                tax_amt = "%.2f" % (
                    (float(prod_row["taxable_value"]) * float(rate)) / 100.0
                )
                if note["taxstate"] == note["sourcestate"]:
                    cdnr_json_item["itm_det"].update(
                        {
                            "camt": "%.2f" % (float(tax_amt) / 2.0),
                            "samt": "%.2f" % (float(tax_amt) / 2.0),
                        }
                    )
                else:
                    cdnr_json_item["itm_det"].update(
                        {
                            "iamt": tax_amt,
                        }
                    )

                cdnr_json_inv["itms"].append(cdnr_json_item)

            if row["gstin"] not in cdnr_json:
                cdnr_json[row["gstin"]] = []

            cdnr_json[row["gstin"]].append(cdnr_json_inv)

        cdnr_json_arr = []
        for cdnr_gstin in cdnr_json:
            cdnr_json_arr.append({"ctin": cdnr_gstin, "nt": cdnr_json[cdnr_gstin]})

        return {"status": 0, "data": cdnr, "json": cdnr_json_arr}
    except:
        print(traceback.format_exc())
        return {"status": 3}


def cdnur_r1(con, drcr_all):
    """
    Collects and formats data about Credit/Debit Notes issued to
    unregistered person for interstate supplies
    """

    try:
        cdnur = []

        def cdnur_filter(drcr):
            return not check_report_properties(drcr)[0]

        drcrs = list(filter(cdnur_filter, drcr_all))
        cdnur_json = []
        # print("drcr notes = %d" % (len(drcrs)))
        for note in drcrs:
            ts_code = state_name_code(con, statename=note["taxstate"])

            row = {}
            # ur_type can be ExportWithPay(EXPWP) / ExportWithoutPay(EXPWOP) / B2CL
            row["ur_type"] = "B2CL"
            row["invoice_number"] = note["invoiceno"]
            row["invid"] = note["invid"]
            row["invoice_date"] = note["invoicedate"].strftime("%d-%b-%y")
            row["drcrid"] = note["drcrid"]
            row["voucher_number"] = note["drcrno"]
            row["voucher_date"] = note["drcrdate"].strftime("%d-%b-%y")
            if note["dctypeflag"] == 4:
                row["document_type"] = "D"
            else:
                row["document_type"] = "C"
            row["place_of_supply"] = "%d-%s" % (ts_code, note["taxstate"])
            row["supply_type"] = "Inter State"
            row["refund_voucher_value"] = round_2_dec(note["totreduct"])
            row["applicable_tax_rate"] = ""
            if note["taxflag"] == 7:
                row["pregst"] = "N"
            else:
                row["pregst"] = "Y"

            cdnur_json_inv = {
                "nt_num": note["drcrno"],
                "nt_dt": note["invoicedate"].strftime("%d-%m-%Y"),
                "val": round_2_dec(note["totreduct"]),
                "ntty": "D" if note["dctypeflag"] == 4 else "C",
                "pos": "%02d" % (ts_code),
                "typ": "B2CL",
                "itms": [],
            }
            for rate, tax_cess in list(product_level(con, note, drcr=True).items()):
                prod_row = deepcopy(row)
                prod_row["taxable_value"] = "%.2f" % tax_cess["taxable_value"]
                prod_row["rate"] = "%.2f" % rate
                prod_row["cess"] = "%.2f" % tax_cess["cess"]
                cdnur.append(prod_row)

                cdnur_json_item = {
                    "num": 1 if not rate else "%d%02d" % (rate, 1),
                    "itm_det": {
                        "txval": prod_row["taxable_value"],
                        "rt": prod_row["rate"],
                        "csamt": prod_row["cess"],
                    },
                }
                tax_amt = "%.2f" % (float(tax_cess["taxable_value"] * rate) / 100.0)
                if note["taxstate"] == note["sourcestate"]:
                    cdnur_json_item["itm_det"].update(
                        {
                            "samt": "%.2f" % (float(tax_amt) / 2.0),
                            "camt": "%.2f" % (float(tax_amt) / 2.0),
                        }
                    )
                else:
                    cdnur_json_item["itm_det"].update(
                        {
                            "iamt": tax_amt,
                        }
                    )

                cdnur_json_inv["itms"].append(cdnur_json_item)

            cdnur_json.append(cdnur_json_inv)
        return {"status": 0, "data": cdnur, "json": cdnur_json}
    except:
        print(traceback.format_exc())
        return {"status": 3}


def get_product_details(invoice):
    taxable_value = 0.00
    cgst_amt = None
    igst_amt = None
    content = literal_eval(invoice["content"])
    discount = float(literal_eval(invoice["disc"]))
    product_rate, qty = list(content.items())[0]
    gst_rate = float(literal_eval(invoice["tax"]))
    cess_rate = float(literal_eval(invoice["cess"]))
    taxable_value = (float(product_rate) * float(qty)) - discount
    # check condition for product and service

    # calculate state level and center level GST
    if invoice["sourcestate"] == invoice["taxstate"]:
        cgst = gst_rate / 2.00
        cgst_amt = taxable_value * (cgst / 100.00)
    else:
        igst_amt = taxable_value * (gst_rate / 100.00)

    cess_amt = taxable_value * (cess_rate / 100.00)
    return float(qty), taxable_value, gst_rate, cgst_amt, igst_amt, cess_amt


def hsn_r1(con, orgcode, start, end):
    """
    Retrieve all products data including product code,product description , hsn code, UOM.
    Loop through product code and retrive all sale invoice related data[ppu,tax,taxtype,sourceState,destinationState] for that particular product code.

    Store this data in following formats:
    {'SGSTamt': '40.50', 'uqc': u'PCS', 'qty': '11.00', 'prodctname': u'Madhura Sugar', 'IGSTamt': '9.90', 'hsnsac': u'45678', 'taxableamt': '505.00', 'totalvalue': '541.10', 'CESSamt': '10.10'},................, {'grand_Value': '6089.20', 'grand_CESSValue': '68.20', 'grand_CGSTValue': '158.00', 'hsnNo': 2, 'grand_ttl_TaxableValue': '6260.00', 'grand_IGSTValue': '69.80'}]
    """
    try:
        orgcode = orgcode
        start = start
        end = end
        products_hsn_data = {
            "b2b": [],
            "b2c": []
        }
        hsn_json = {
            "hsn_b2b": [],
            "hsn_b2c": [],
        }
        b2b_prod_counter = 0
        b2c_prod_counter = 0

        prodData = con.execute(
            select(
                [
                    product.c.productcode,
                    product.c.gscode,
                    product.c.productdesc,
                    product.c.gsflag,
                    product.c.uomid,
                ]
            ).where(product.c.orgcode == orgcode)
        )
        prodData_result = prodData.fetchall()
        for products in prodData_result:
            hsn = 0
            try:
                gscode = loads(products["gscode"])
                if type(gscode) == dict:
                    hsn = gscode["hsn_code"]
            except Exception:
                pass

            if products["gsflag"] == 7:
                um = con.execute(
                    select([unitofmeasurement.c.unitname]).where(
                        unitofmeasurement.c.uomid == int(products["uomid"])
                    )
                )
                unitrow = um.fetchone()
                uqc = unitrow["unitname"]
            else:
                uqc = "OTH"

            prodHSN = {
                "hsnsac": hsn,
                "prodctname": products["productdesc"],
                "uqc": uqc,
            }

            invData = con.execute(
                text("select contents ->> ':productcode' as content ,sourcestate,taxstate,icflag,consignee,discount ->>':productcode' as disc,cess ->> ':productcode' as cess,tax ->> ':productcode' as tax from invoice where contents ? ':productcode' and orgcode = ':orgcode' and inoutflag = ':inoutflag' and taxflag = ':taxflag'  and invoicedate >= :start and invoicedate <= :end"),
                    productcode = products["productcode"],
                    orgcode = orgcode,
                    inoutflag = 15,
                    taxflag = 7,
                    start = start,
                    end = end,
            )
            invoice_Data = invData.fetchall()

            taxable_value_b2b_total = 0.00
            cgst_value_b2b_total = 0.00
            igst_value_b2b_total = 0.00
            cess_value_b2b_total = 0.00
            quantity_b2b_total = 0.00

            taxable_value_b2c_total = 0.00
            cgst_value_b2c_total = 0.00
            igst_value_b2c_total = 0.00
            cess_value_b2c_total = 0.00
            quantity_b2c_total = 0.00


            if invoice_Data != None and len(invoice_Data) > 0:
                for inv in invoice_Data:
                    (
                        qty,
                        taxable_value,
                        gst_rate,
                        cgst_amt,
                        igst_amt,
                        cess_amt
                    ) = get_product_details(inv)
                    if inv["consignee"] and inv["consignee"].get("gstinconsignee"):
                        b2b_prod_counter += 1
                        if products["gsflag"] == 7:
                            quantity_b2b_total += qty
                        taxable_value_b2b_total += taxable_value
                        if cgst_amt:
                            cgst_value_b2b_total += cgst_amt
                        elif igst_amt:
                            igst_value_b2b_total += igst_amt
                        cess_value_b2b_total += cess_amt
                    else:
                        b2c_prod_counter += 1
                        if products["gsflag"] == 7:
                            quantity_b2c_total += qty
                        taxable_value_b2c_total += taxable_value
                        if cgst_amt:
                            cgst_value_b2c_total += cgst_amt
                        elif igst_amt:
                            igst_value_b2c_total += igst_amt
                        cess_value_b2c_total += cess_amt

                if b2b_prod_counter:
                    products_hsn_data["b2b"].append(
                        {
                            "qty": round_2_dec(quantity_b2b_total),
                            "totalvalue": round_2_dec(
                                float(taxable_value_b2b_total)
                                + (2 * cgst_value_b2b_total)
                                + float(igst_value_b2b_total)
                                + float(cess_value_b2b_total)
                            ),
                            "taxableamt": round_2_dec(taxable_value_b2b_total),
                            "SGSTamt": round_2_dec(cgst_value_b2b_total),
                            "IGSTamt": round_2_dec(igst_value_b2b_total),
                            "CESSamt": round_2_dec(cess_value_b2b_total),
                            "product_count": b2b_prod_counter,
                            **prodHSN,
                        }
                    )
                    hsn_json["hsn_b2b"].append(
                        {
                            "num": b2b_prod_counter,
                            "hsn_sc": str(hsn),
                            "desc": products["productdesc"],
                            "uqc": uqc,
                            "qty":  round_2_dec(quantity_b2b_total),
                            "rt": gst_rate,
                            "txval":  round_2_dec(taxable_value_b2b_total),
                            "iamt":  round_2_dec(igst_value_b2b_total),
                            "samt":  round_2_dec(cgst_value_b2b_total),
                            "camt":  round_2_dec(cgst_value_b2b_total),
                            "csamt":  round_2_dec(cess_value_b2b_total),
                        }
                    )
                if b2c_prod_counter:
                    products_hsn_data["b2c"].append(
                        {
                            "qty": round_2_dec(quantity_b2c_total),
                            "totalvalue": round_2_dec(
                                float(taxable_value_b2c_total)
                                + (2 * cgst_value_b2c_total)
                                + float(igst_value_b2c_total)
                                + float(cess_value_b2c_total)
                            ),
                            "taxableamt": round_2_dec(taxable_value_b2c_total),
                            "SGSTamt": round_2_dec(cgst_value_b2c_total),
                            "IGSTamt": round_2_dec(igst_value_b2c_total),
                            "CESSamt": round_2_dec(cess_value_b2c_total),
                            "product_count": b2c_prod_counter,
                            **prodHSN,
                        }
                    )
                    hsn_json["hsn_b2c"].append(
                        {
                            "num": b2c_prod_counter,
                            "hsn_sc": str(hsn),
                            "desc": products["productdesc"],
                            "uqc": uqc,
                            "qty":  round_2_dec(quantity_b2c_total),
                            "rt": gst_rate,
                            "txval":  round_2_dec(taxable_value_b2c_total),
                            "iamt":  round_2_dec(igst_value_b2c_total),
                            "samt":  round_2_dec(cgst_value_b2c_total),
                            "camt":  round_2_dec(cgst_value_b2c_total),
                            "csamt":  round_2_dec(cess_value_b2c_total),
                        }
                    )


        return {"status": 0, "data": products_hsn_data, "json": hsn_json}
    except:
        print(traceback.format_exc())
        return {"status": 3}


def docs_issued(invoices=[], cancelled_invoices=[], drcr_notes=[]):
    """Generates documents issued summary for GSTR1 report save API.

    :param invoices: Invoice database rows
    :param drcr_notes: Debit/Credit note database rows
    """
    def format_doc_summary(
            rows, serial_no_field, from_no=None, to_no=None, cancel_count=0
    ):
        return {
            "num": 1,
            "from": from_no if from_no else getattr(rows[0], serial_no_field),
            "to": to_no if to_no else getattr(rows[-1], serial_no_field),
            "totnum": len(rows),
            "cancel": cancel_count,
            "net_issue": len(rows)+cancel_count,
        }

    party_invoice_docs = []
    pos_invoice_docs = []
    for invoice in invoices:
        if invoice.icflag == 9:
            party_invoice_docs.append(invoice)
        else:
            pos_invoice_docs.append(invoice)

    cancelled_party_invoice_docs = []
    cancelled_pos_invoice_docs = []
    for cancelled_invoice in cancelled_invoices:
        if cancelled_invoice.icflag == 9:
            cancelled_party_invoice_docs.append(cancelled_invoice)
        else:
            cancelled_pos_invoice_docs.append(cancelled_invoice)

    def get_first_last_entries(entries, cancelled_entries):
        first_invoice_entry = entries[0]
        last_invoice_entry = entries[-1]
        first_cancelled_invoice_entry = cancelled_entries[0]
        last_cancelled_invoice_entry = cancelled_entries[-1]
        first_invoice_no = first_invoice_entry.invoiceno
        last_invoice_no = last_invoice_entry.invoiceno

        if first_invoice_entry.invoicedate > first_cancelled_invoice_entry.invoicedate:
            first_invoice_no = first_cancelled_invoice_entry.invoiceno
        if first_invoice_entry.invoicedate == first_cancelled_invoice_entry.invoicedate:
            if first_invoice_entry.invid > first_cancelled_invoice_entry.invid:
                first_invoice_no = first_cancelled_invoice_entry.invoiceno

        if last_invoice_entry.invoicedate < last_cancelled_invoice_entry.invoicedate:
            last_invoice_no = last_cancelled_invoice_entry.invoiceno
        if last_invoice_entry.invoicedate == last_cancelled_invoice_entry.invoicedate:
            if last_invoice_entry.invid < last_cancelled_invoice_entry.invid:
                last_invoice_no = last_cancelled_invoice_entry.invoiceno
        return first_invoice_no, last_invoice_no

    debit_note_docs = []
    credit_note_docs = []
    for drcr_note in drcr_notes:
        if drcr_note.dctypeflag == 3:
            credit_note_docs.append(drcr_note)
        else:
            debit_note_docs.append(drcr_note)

    consolidated_invoices = []
    if party_invoice_docs:
        first_party_invoice_no = party_invoice_docs[0].invoiceno
        last_party_invoice_no = party_invoice_docs[-1].invoiceno
        if cancelled_party_invoice_docs:
            first_party_invoice_no, last_party_invoice_no = get_first_last_entries(
                party_invoice_docs, cancelled_party_invoice_docs
            )
        party_invoices = format_doc_summary(
            party_invoice_docs,
            "invoiceno",
            first_party_invoice_no,
            last_party_invoice_no,
            len(cancelled_party_invoice_docs),
        )
        consolidated_invoices.append(party_invoices)
    if pos_invoice_docs:
        first_pos_invoice_no = pos_invoice_docs[0].invoiceno
        last_pos_invoice_no = pos_invoice_docs[-1].invoiceno
        if cancelled_pos_invoice_docs:
            first_pos_invoice_no, last_pos_invoice_no = get_first_last_entries(
                pos_invoice_docs, cancelled_pos_invoice_docs
            )
        pos_invoices = {
            **format_doc_summary(
                pos_invoice_docs,
                "invoiceno",
                first_pos_invoice_no,
                last_pos_invoice_no,
                len(cancelled_pos_invoice_docs),
            ),
            "num": 2
        }
        consolidated_invoices.append(pos_invoices)

    doc_det = []

    if consolidated_invoices:
        doc_det.append(
            {
                "doc_num": 1,
                "docs": consolidated_invoices,
            }
        )
    if debit_note_docs:
        doc_det.append(
            {
                "doc_num": 4,
                "docs": [format_doc_summary(debit_note_docs, "drcrno")],
            }
        )
    if credit_note_docs:
        doc_det.append(
            {
                "doc_num": 5,
                "docs":[format_doc_summary(credit_note_docs, "drcrno")],
            }
        )

    return {
        "doc_det": doc_det
    }


"""
generate_gstr_3b_data: generates the data required for creating gstr3b json and spreadsheet

"""


def generate_gstr_3b_data(con, orgcode, fromDate, toDate):
    try:
        outward_taxable_supplies = {
            "taxable_value": 0.0,
            "igst": 0.0,
            "cgst": 0.0,
            "sgst": 0.0,
            "cess": 0.0,
        }
        outward_taxable_zero_rated = {
            "taxable_value": 0.0,
            "igst": 0.0,
            "cgst": 0.0,
            "sgst": 0.0,
            "cess": 0.0,
        }
        outward_taxable_exempted = {
            "taxable_value": 0.0,
            "igst": 0.0,
            "cgst": 0.0,
            "sgst": 0.0,
            "cess": 0.0,
        }
        outward_non_gst = {
            "taxable_value": 0.0,
            "igst": 0.0,
            "cgst": 0.0,
            "sgst": 0.0,
            "cess": 0.0,
        }

        inward_reverse_charge = {
            "taxable_value": 0.0,
            "igst": 0.0,
            "cgst": 0.0,
            "sgst": 0.0,
            "cess": 0.0,
        }
        import_goods = {"igst": 0.0, "cgst": 0.0, "sgst": 0.0, "cess": 0.0}
        import_service = {"igst": 0.0, "cgst": 0.0, "sgst": 0.0, "cess": 0.0}
        inward_isd = {"igst": 0.0, "cgst": 0.0, "sgst": 0.0, "cess": 0.0}
        all_itc = {"igst": 0.0, "cgst": 0.0, "sgst": 0.0, "cess": 0.0}
        itc_reversed_1 = {"igst": 0.0, "cgst": 0.0, "sgst": 0.0, "cess": 0.0}
        itc_reversed_2 = {"igst": 0.0, "cgst": 0.0, "sgst": 0.0, "cess": 0.0}
        net_itc = {"igst": 0.0, "cgst": 0.0, "sgst": 0.0, "cess": 0.0}
        ineligible_1 = {"igst": 0.0, "cgst": 0.0, "sgst": 0.0, "cess": 0.0}
        ineligible_2 = {"igst": 0.0, "cgst": 0.0, "sgst": 0.0, "cess": 0.0}

        inward_zero_gst = {"inter": 0.0, "intra": 0.0}
        non_gst = {"inter": 0.0, "intra": 0.0}

        interest = {"igst": 0.0, "cgst": 0.0, "sgst": 0.0, "cess": 0.0}

        g3b_invs = {
            "outward_taxable_supplies": [],
            "outward_taxable_zero_rated": [],
            "outward_taxable_exempted": [],
            "outward_non_gst": [],
            "inward_reverse_charge": [],
            "import_goods": [],
            "import_service": [],
            "inward_isd": [],
            "all_itc": [],
            "net_itc": [],
            "itc_reversed_1": [],
            "itc_reversed_2": [],
            "ineligible_1": [],
            "ineligible_2": [],
            "inward_zero_gst": [],
            "non_gst": [],
            "interest": [],
            "pos_unreg_comp_uin_igst": {"unreg": {}, "compos": {}, "uin": {}},
        }

        g3b_inv_map = {
            "outward_taxable_supplies": {},
            "outward_taxable_zero_rated": {},
            "outward_taxable_exempted": {},
            "outward_non_gst": {},
            "inward_reverse_charge": {},
            "import_goods": {},
            "import_service": {},
            "inward_isd": {},
            "all_itc": {},
            "net_itc": {},
            "itc_reversed_1": {},
            "itc_reversed_2": {},
            "ineligible_1": {},
            "ineligible_2": {},
            "inward_zero_gst": {},
            "non_gst": {},
            "interest": {},
            "pos_unreg_comp_uin_igst": {"unreg": {}, "compos": {}, "uin": {}},
        }

        pos_unreg_comp_uin_igst = (
            {}
        )  # {PoS: Unreg_Taxable_Amt, Unreg_IGST, Composition_Taxable_Amt, Composition_IGST, UIN_Taxamble_Amt, UIN_IGST}

        # For invoice in invoices
        #   For product in invoice.products

        invoices = getInvoiceList(
            con, orgcode, {"fromdate": fromDate, "todate": toDate, "flag": "0"}
        )

        for invoice in invoices:
            inv_data = getInvoiceData(
                con, orgcode, {"inv": "single", "invid": invoice["invid"]}
            )
            if len(inv_data):
                # print(inv_data.keys())
                gst_reg_type = (
                    inv_data["custSupDetails"]["gst_reg_type"]
                    if "gst_reg_type" in inv_data["custSupDetails"]
                    else -1
                )
                gst_party_type = (
                    inv_data["custSupDetails"]["gst_party_type"]
                    if "gst_party_type" in inv_data["custSupDetails"]
                    else -1
                )
                for prod_id in inv_data["invcontents"]:
                    prod = inv_data["invcontents"][prod_id]
                    line_uom = prod["uom"]
                    line_qty = prod["qty"]
                    line_amount = float(prod["taxableamount"])
                    # line_price = invoice_line.price_unit * (1 - (invoice_line.discount or 0.0) / 100.0)
                    # line_taxes = invoice_line.invoice_line_tax_ids.compute_all(line_price, invoice_line.invoice_id.currency_id, invoice_line.quantity, prod_id, invoice_line.invoice_id.partner_id)
                    # _logger.info(line_taxes)
                    igst_amount = cgst_amount = sgst_amount = cess_amount = 0.0

                    # tax_obj = self.env['account.tax'].browse(tax_line['id'])
                    tax_name = prod["taxname"]
                    if tax_name == "IGST":  # tax_obj.gst_type == 'igst':
                        igst_amount += float(prod["taxamount"])
                    elif tax_name == "CGST":  # tax_obj.gst_type == 'cgst':
                        cgst_amount += float(prod["taxamount"])
                    elif (
                        tax_name == "SGST" or tax_name == "UTGST"
                    ):  # tax_obj.gst_type == 'sgst':
                        sgst_amount += float(prod["taxamount"])
                        cgst_amount += float(
                            prod["taxamount"]
                        )  # Currently since CGST and SGST are the same, gkcore only stores SGST.

                    if "cess" in prod:
                        cess_amount += float(prod["cess"])

                    # cgst_amount = invoice_line.invoice_line_tax_ids.filtered(lambda r: r.gst_type == 'cgst').amount
                    # sgst_amount = invoice_line.invoice_line_tax_ids.filtered(lambda r: r.gst_type == 'sgst').amount
                    line_total_amount = float(prod["totalAmount"])
                    # _logger.info(invoice_line.invoice_line_tax_ids)
                    if line_amount < 0:
                        line_total_amount = line_total_amount * -1
                    if inv_data["inoutflag"] == 15:  # Customer Invoice
                        if (
                            line_total_amount > line_amount
                        ):  # Taxable item, not zero rated/nil rated/exempted
                            outward_taxable_supplies["taxable_value"] += line_amount
                            outward_taxable_supplies["igst"] += igst_amount
                            outward_taxable_supplies["cgst"] += cgst_amount
                            outward_taxable_supplies["sgst"] += sgst_amount
                            outward_taxable_supplies["cess"] += cess_amount
                            if (
                                invoice["invid"]
                                not in g3b_inv_map["outward_taxable_supplies"]
                            ):
                                g3b_invs["outward_taxable_supplies"].append(invoice)
                                g3b_inv_map["outward_taxable_supplies"][
                                    invoice["invid"]
                                ] = 1

                            # 3.2 Of the supplies shown in 3.1 (a) above, details of inter-State supplies made to unregisterd persons, composition taxable persons and UIN holders
                            if inv_data["taxstatecode"] != inv_data["sourcestatecode"]:
                                if pos_unreg_comp_uin_igst.get(
                                    inv_data["taxstatecode"]
                                ):
                                    pos_unreg_comp_uin_igst[inv_data["taxstatecode"]][
                                        "unreg_taxable_amt"
                                    ] += line_amount
                                    pos_unreg_comp_uin_igst[inv_data["taxstatecode"]][
                                        "unreg_igst"
                                    ] += igst_amount
                                    if (
                                        invoice["invid"]
                                        not in g3b_inv_map["pos_unreg_comp_uin_igst"][
                                            "unreg"
                                        ][inv_data["taxstatecode"]]
                                    ):
                                        g3b_invs["pos_unreg_comp_uin_igst"]["unreg"][
                                            inv_data["taxstatecode"]
                                        ].append(invoice)
                                        g3b_inv_map["pos_unreg_comp_uin_igst"]["unreg"][
                                            inv_data["taxstatecode"]
                                        ][invoice["invid"]] = 1
                                else:
                                    pos_unreg_comp_uin_igst[
                                        inv_data["taxstatecode"]
                                    ] = {
                                        "unreg_taxable_amt": line_amount,
                                        "unreg_igst": igst_amount,
                                        "comp_taxable_amt": 0,
                                        "comp_igst": 0,
                                        "uin_taxable_amt": 0,
                                        "uin_igst": 0,
                                    }  # TODO: Handle Composition & UIN holders
                                    g3b_invs["pos_unreg_comp_uin_igst"]["unreg"][
                                        inv_data["taxstatecode"]
                                    ] = []
                                    g3b_invs["pos_unreg_comp_uin_igst"]["unreg"][
                                        inv_data["taxstatecode"]
                                    ].append(invoice)

                                    g3b_inv_map["pos_unreg_comp_uin_igst"]["unreg"][
                                        inv_data["taxstatecode"]
                                    ] = {}
                                    g3b_inv_map["pos_unreg_comp_uin_igst"]["unreg"][
                                        inv_data["taxstatecode"]
                                    ][invoice["invid"]] = 1

                        else:  # Tream them all as zero rated for now
                            outward_taxable_zero_rated["taxable_value"] += line_amount
                            outward_taxable_zero_rated["igst"] += igst_amount
                            outward_taxable_zero_rated["cgst"] += cgst_amount
                            outward_taxable_zero_rated["sgst"] += sgst_amount
                            outward_taxable_zero_rated["cess"] += cess_amount
                            if (
                                invoice["invid"]
                                not in g3b_inv_map["outward_taxable_zero_rated"]
                            ):
                                g3b_invs["outward_taxable_zero_rated"].append(invoice)
                                g3b_inv_map["outward_taxable_zero_rated"][
                                    invoice["invid"]
                                ] = 1

                    # TODO: Vendor Bills with reverse charge doesn't have tax lines filled, so it must be calculated
                    elif (
                        inv_data["inoutflag"] == 9
                    ):  # and invoice.reverse_charge: #Vendor Bills with Reverse Charge applicablle
                        if int(inv_data["reversecharge"]) == 1:
                            inward_reverse_charge["taxable_value"] += line_amount
                            inward_reverse_charge["igst"] += igst_amount
                            inward_reverse_charge["cgst"] += cgst_amount
                            inward_reverse_charge["sgst"] += sgst_amount
                            inward_reverse_charge["cess"] += cess_amount
                            if (
                                invoice["invid"]
                                not in g3b_inv_map["inward_reverse_charge"]
                            ):
                                g3b_invs["inward_reverse_charge"].append(invoice)
                                g3b_inv_map["inward_reverse_charge"][
                                    invoice["invid"]
                                ] = 1
                        else:
                            if line_total_amount == line_amount:  # Zero GST taxes
                                # 5. From a supplier under composition scheme, Exempt and Nil rated
                                if gst_reg_type == GST_REG_TYPE["composition"]:
                                    if (
                                        inv_data["taxstatecode"]
                                        != inv_data["sourcestatecode"]
                                    ):
                                        inward_zero_gst["inter"] += line_amount
                                    else:
                                        inward_zero_gst["intra"] += line_amount
                                    if (
                                        invoice["invid"]
                                        not in g3b_inv_map["inward_zero_gst"]
                                    ):
                                        g3b_invs["inward_zero_gst"].append(invoice)
                            else:  # Taxable purchase, eligible for ITC
                                all_itc["igst"] += igst_amount
                                all_itc["cgst"] += cgst_amount
                                all_itc["sgst"] += sgst_amount
                                if invoice["invid"] not in g3b_inv_map["all_itc"]:
                                    g3b_invs["all_itc"].append(invoice)
                                    g3b_inv_map["all_itc"][invoice["invid"]] = 1
        for tax_type in net_itc:
            net_itc[tax_type] = (
                import_goods[tax_type]
                + import_service[tax_type]
                + inward_reverse_charge[tax_type]
                + inward_isd[tax_type]
                + all_itc[tax_type]
            ) - (itc_reversed_1[tax_type] + itc_reversed_2[tax_type])
        return {
            "invoices": g3b_invs,
            "data": {
                "outward_taxable_supplies": outward_taxable_supplies,
                "outward_taxable_zero_rated": outward_taxable_zero_rated,
                "outward_taxable_exempted": outward_taxable_exempted,
                "outward_non_gst": outward_non_gst,
                "inward_reverse_charge": inward_reverse_charge,
                "import_goods": import_goods,
                "import_service": import_service,
                "inward_isd": inward_isd,
                "all_itc": all_itc,
                "net_itc": net_itc,
                "itc_reversed_1": itc_reversed_1,
                "itc_reversed_2": itc_reversed_2,
                "ineligible_1": ineligible_1,
                "ineligible_2": ineligible_2,
                "inward_zero_gst": inward_zero_gst,
                "non_gst": non_gst,
                "interest": interest,
                "pos_unreg_comp_uin_igst": pos_unreg_comp_uin_igst,
            },
        }
    except:
        print(traceback.format_exc())
        return {}

def check_report_properties(inv_cn_row):
    """ Checks if the invoice/note is b2b and of large category.
    Returns `is_b2b` and `is_large` statuses.
    """
    is_igst = False
    is_b2b = False
    is_large = False
    gstin = None
    try:
        gstin = list(inv_cn_row["transaction_details"]["contact"]["gstin"].values())[0]
    except (KeyError, AttributeError):
        pass

    if gstin:
#    if inv_cn_row["consignee"] and inv_cn_row["consignee"].get("gstinconsignee"):
        is_b2b = True
    if inv_cn_row["invoicetotal"] > 100000:
        is_large = True
    if inv_cn_row["taxstate"] != inv_cn_row["sourcestate"]:
        is_igst = True
    return is_b2b, is_large, is_igst
