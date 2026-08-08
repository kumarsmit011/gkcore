from gkcore import eng, enumdict
from gkcore.utils import authCheck
from gkcore.models.gkdb import (
    delchal,
    invoice,
    customerandsupplier,
    stock,
    dcinv,
    godown,
)
from sqlalchemy.sql import select
from sqlalchemy.engine.base import Connection
from sqlalchemy import and_
from pyramid.request import Request
from pyramid.view import view_defaults, view_config
from datetime import datetime


@view_defaults(request_method="GET")
class api_delivery_note(object):
    def __init__(self, request):
        self.request = Request
        self.request = request
        self.con = Connection

    @view_config(route_name="del-unbilled", renderer="json")
    def unbilled_deliveries(self):
        """
        purpose:
        presents a list of deliverys which are unbilled  There are exceptions which should be excluded.
        free replacement or sample are those which are excluded.
                Token is the only required input.
                We also require Orgcode, but it is extracted from the token itself.
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
                orgcode = authDetails["orgcode"]
                if "inputdate" in self.request.params:
                    dataset = {
                        "inputdate": self.request.params["inputdate"],
                        "del_unbilled_type": self.request.params["del_unbilled_type"],
                    }
                else:
                    dataset = self.request.json_body
                inout = self.request.params["inout"]
                inputdate = dataset["inputdate"]
                del_unbilled_type = dataset["del_unbilled_type"]
                new_inputdate = dataset["inputdate"]
                new_inputdate = datetime.strptime(new_inputdate, "%Y-%m-%d")
                dc_unbilled = []
                # Adding the query here only, which will select the dcids either with "delivery-out" type or "delivery-in".
                if inout == "i":  # in
                    # distinct clause must be added to the query.
                    # delchal dcdate need to be added into select clause, since it is mentioned in order_by clause.
                    if del_unbilled_type == "0":
                        alldcids = self.con.execute(
                            select([delchal.c.dcid, delchal.c.dcdate])
                            .distinct()
                            .where(
                                and_(
                                    delchal.c.orgcode == orgcode,
                                    delchal.c.dcdate <= new_inputdate,
                                    stock.c.orgcode == orgcode,
                                    stock.c.dcinvtnflag == 4,
                                    stock.c.inout == 9,
                                    delchal.c.dcid == stock.c.dcinvtnid,
                                )
                            )
                            .order_by(delchal.c.dcdate)
                        )
                    else:
                        alldcids = self.con.execute(
                            select([delchal.c.dcid, delchal.c.dcdate])
                            .distinct()
                            .where(
                                and_(
                                    delchal.c.orgcode == orgcode,
                                    delchal.c.dcflag == int(del_unbilled_type),
                                    delchal.c.dcdate <= new_inputdate,
                                    stock.c.orgcode == orgcode,
                                    stock.c.dcinvtnflag == 4,
                                    stock.c.inout == 9,
                                    delchal.c.dcid == stock.c.dcinvtnid,
                                )
                            )
                            .order_by(delchal.c.dcdate)
                        )
                if inout == "o":  # out
                    # distinct clause must be added to the query.
                    # delchal dcdate need to be added into select clause, since it is mentioned in order_by clause.
                    if del_unbilled_type == "0":
                        alldcids = self.con.execute(
                            select([delchal.c.dcid, delchal.c.dcdate])
                            .distinct()
                            .where(
                                and_(
                                    delchal.c.orgcode == orgcode,
                                    delchal.c.dcdate <= new_inputdate,
                                    stock.c.orgcode == orgcode,
                                    stock.c.dcinvtnflag == 4,
                                    stock.c.inout == 15,
                                    delchal.c.dcid == stock.c.dcinvtnid,
                                )
                            )
                            .order_by(delchal.c.dcdate)
                        )
                    else:
                        alldcids = self.con.execute(
                            select([delchal.c.dcid, delchal.c.dcdate])
                            .distinct()
                            .where(
                                and_(
                                    delchal.c.orgcode == orgcode,
                                    delchal.c.dcflag == int(del_unbilled_type),
                                    delchal.c.dcdate <= new_inputdate,
                                    stock.c.orgcode == orgcode,
                                    stock.c.dcinvtnflag == 4,
                                    stock.c.inout == 15,
                                    delchal.c.dcid == stock.c.dcinvtnid,
                                )
                            )
                            .order_by(delchal.c.dcdate)
                        )
                alldcids = alldcids.fetchall()
                dcResult = []
                # ********* What if multiple delchals are covered by single invoice?*******************
                i = 0
                while i < len(alldcids):
                    dcid = alldcids[i]
                    invidresult = self.con.execute(
                        select([dcinv.c.invid]).where(
                            and_(
                                dcid[0] == dcinv.c.dcid,
                                dcinv.c.orgcode == orgcode,
                                invoice.c.orgcode == orgcode,
                                invoice.c.invid == dcinv.c.invid,
                                invoice.c.invoicedate <= new_inputdate,
                            )
                        )
                    )
                    invidresult = invidresult.fetchall()
                    if len(invidresult) == 0:
                        pass
                    else:
                        # invid's will be distinct only. So no problem to explicitly applying distinct clause.
                        if inout == "i":  # in
                            dcprodresult = self.con.execute(
                                select([stock.c.productcode, stock.c.qty]).where(
                                    and_(
                                        stock.c.orgcode == orgcode,
                                        stock.c.dcinvtnflag == 4,
                                        stock.c.inout == 9,
                                        dcid[0] == stock.c.dcinvtnid,
                                    )
                                )
                            )
                        if inout == "o":  # out
                            dcprodresult = self.con.execute(
                                select([stock.c.productcode, stock.c.qty]).where(
                                    and_(
                                        stock.c.orgcode == orgcode,
                                        stock.c.dcinvtnflag == 4,
                                        stock.c.inout == 15,
                                        dcid[0] == stock.c.dcinvtnid,
                                    )
                                )
                            )
                        dcprodresult = dcprodresult.fetchall()
                        # I am assuming :productcode must be distinct. So, I haven't applied distinct construct.
                        # what if dcprodresult or invprodresult is empty?
                        invprodresult = []
                        for invid in invidresult:
                            temp = self.con.execute(
                                select([invoice.c.contents]).where(
                                    and_(
                                        invoice.c.orgcode == orgcode,
                                        invid == invoice.c.invid,
                                    )
                                )
                            )
                            temp = temp.fetchall()
                            # Below two lines are intentionally repeated. It's not a mistake.
                            temp = temp[0]
                            temp = temp[0]
                            invprodresult.append(temp)
                        # Now we have to compare the two results: dcprodresult and invprodresult
                        # I assume that the delchal must have at most only one entry for a particular product. If not, then it's a bug and needs to be rectified.
                        # But, in case of invprodresult, there can be more than one productcodes mentioned. This is because, with one delchal, there can be many invoices linked.
                        matchedproducts = []
                        remainingproducts = {}
                        for eachitem in dcprodresult:
                            # dcprodresult is a list of tuples. eachitem is one such tuple.
                            for eachinvoice in invprodresult:
                                # invprodresult is a list of dictionaries. eachinvoice is one such dictionary.
                                for eachproductcode in list(eachinvoice.keys()):
                                    # eachitem[0] is unique. It's not repeated.
                                    dcprodcode = eachitem[0]
                                    if int(dcprodcode) == int(
                                        eachproductcode
                                    ):  # why do we need to convert these into string to compare?
                                        # this means that the product in delchal matches with the product in invoice
                                        # now we will check its quantity
                                        invqty = list(
                                            eachinvoice[eachproductcode].values()
                                        )[0]
                                        dcqty = eachitem[1]
                                        if float(dcqty) == float(
                                            invqty
                                        ):  # conversion of datatypes to compatible ones is very important when comparing them.
                                            # this means the quantity of current individual product is matched exactly
                                            matchedproducts.append(int(eachproductcode))
                                        elif float(dcqty) > float(invqty):
                                            # this means current invoice has not billed the whole product quantity.
                                            if dcprodcode in list(
                                                remainingproducts.keys()
                                            ):
                                                if float(dcqty) == (
                                                    float(remainingproducts[dcprodcode])
                                                    + float(invqty)
                                                ):
                                                    matchedproducts.append(
                                                        int(eachproductcode)
                                                    )
                                                    # whether we use eachproductcode or dcprodcode, doesn't matter. Because, both values are the same here.
                                                    del remainingproducts[
                                                        int(eachproductcode)
                                                    ]
                                                else:
                                                    # It must not be the case that below addition is greater than dcqty.
                                                    remainingproducts[
                                                        dcprodcode
                                                    ] = float(
                                                        remainingproducts[dcprodcode]
                                                    ) + float(
                                                        invqty
                                                    )
                                            else:
                                                remainingproducts.update(
                                                    {dcprodcode: float(invqty)}
                                                )
                                        else:
                                            # "dcqty < invqty" should never happen.
                                            # It could happen when multiple delivery chalans have only one invoice.
                                            pass

                        # changing previous logic..
                        if len(matchedproducts) == len(dcprodresult):
                            # Now we have got the delchals, for which invoices are also sent completely.
                            alldcids.remove(dcid)
                            i -= 1
                    i += 1
                    pass

                for eachdcid in alldcids:
                    if inout == "i":  # in
                        # check if current dcid has godown name or it's None. Accordingly, our query should be changed.
                        tmpresult = self.con.execute(
                            select([stock.c.goid])
                            .distinct()
                            .where(
                                and_(
                                    stock.c.orgcode == orgcode,
                                    stock.c.dcinvtnflag == 4,
                                    stock.c.inout == 9,
                                    stock.c.dcinvtnid == eachdcid[0],
                                )
                            )
                        )
                        tmpresult = tmpresult.fetchone()
                        if tmpresult[0] == None:
                            singledcResult = self.con.execute(
                                select(
                                    [
                                        delchal.c.dcid,
                                        delchal.c.dcno,
                                        delchal.c.dcdate,
                                        delchal.c.dcflag,
                                        customerandsupplier.c.custname,
                                    ]
                                )
                                .distinct()
                                .where(
                                    and_(
                                        delchal.c.orgcode == orgcode,
                                        customerandsupplier.c.orgcode == orgcode,
                                        eachdcid[0] == delchal.c.dcid,
                                        delchal.c.custid
                                        == customerandsupplier.c.custid,
                                        stock.c.dcinvtnflag == 4,
                                        stock.c.inout == 9,
                                        eachdcid[0] == stock.c.dcinvtnid,
                                    )
                                )
                            )
                        else:
                            singledcResult = self.con.execute(
                                select(
                                    [
                                        delchal.c.dcid,
                                        delchal.c.dcno,
                                        delchal.c.dcdate,
                                        delchal.c.dcflag,
                                        customerandsupplier.c.custname,
                                        godown.c.goname,
                                    ]
                                )
                                .distinct()
                                .where(
                                    and_(
                                        delchal.c.orgcode == orgcode,
                                        customerandsupplier.c.orgcode == orgcode,
                                        godown.c.orgcode == orgcode,
                                        eachdcid[0] == delchal.c.dcid,
                                        delchal.c.custid
                                        == customerandsupplier.c.custid,
                                        stock.c.dcinvtnflag == 4,
                                        stock.c.inout == 9,
                                        eachdcid[0] == stock.c.dcinvtnid,
                                        stock.c.goid == godown.c.goid,
                                    )
                                )
                            )
                    if inout == "o":  # out
                        # check if current dcid has godown name or it's None. Accordingly, our query should be changed.
                        tmpresult = self.con.execute(
                            select([stock.c.goid])
                            .distinct()
                            .where(
                                and_(
                                    stock.c.orgcode == orgcode,
                                    stock.c.dcinvtnflag == 4,
                                    stock.c.inout == 15,
                                    stock.c.dcinvtnid == eachdcid[0],
                                )
                            )
                        )
                        tmpresult = tmpresult.fetchone()
                        if tmpresult[0] == None:
                            singledcResult = self.con.execute(
                                select(
                                    [
                                        delchal.c.dcid,
                                        delchal.c.dcno,
                                        delchal.c.dcdate,
                                        delchal.c.dcflag,
                                        customerandsupplier.c.custname,
                                    ]
                                )
                                .distinct()
                                .where(
                                    and_(
                                        delchal.c.orgcode == orgcode,
                                        customerandsupplier.c.orgcode == orgcode,
                                        eachdcid[0] == delchal.c.dcid,
                                        delchal.c.custid
                                        == customerandsupplier.c.custid,
                                        stock.c.dcinvtnflag == 4,
                                        stock.c.inout == 15,
                                        eachdcid[0] == stock.c.dcinvtnid,
                                    )
                                )
                            )
                        else:
                            singledcResult = self.con.execute(
                                select(
                                    [
                                        delchal.c.dcid,
                                        delchal.c.dcno,
                                        delchal.c.dcdate,
                                        delchal.c.dcflag,
                                        customerandsupplier.c.custname,
                                        godown.c.goname,
                                    ]
                                )
                                .distinct()
                                .where(
                                    and_(
                                        delchal.c.orgcode == orgcode,
                                        customerandsupplier.c.orgcode == orgcode,
                                        godown.c.orgcode == orgcode,
                                        eachdcid[0] == delchal.c.dcid,
                                        delchal.c.custid
                                        == customerandsupplier.c.custid,
                                        stock.c.dcinvtnflag == 4,
                                        stock.c.inout == 15,
                                        eachdcid[0] == stock.c.dcinvtnid,
                                        stock.c.goid == godown.c.goid,
                                    )
                                )
                            )
                    singledcResult = singledcResult.fetchone()
                    dcResult.append(singledcResult)

                temp_dict = {}
                srno = 1
                for row in dcResult:
                    # if (row["dcdate"].year < inputdate.year) or (row["dcdate"].year == inputdate.year and row["dcdate"].month < inputdate.month) or (row["dcdate"].year == inputdate.year and row["dcdate"].month == inputdate.month and row["dcdate"].day <= inputdate.day):
                    temp_dict = {
                        "dcid": row["dcid"],
                        "srno": srno,
                        "dcno": row["dcno"],
                        "dcdate": datetime.strftime(row["dcdate"], "%d-%m-%Y"),
                        "dcflag": row["dcflag"],
                        "custname": row["custname"],
                    }

                    canceldelchal = 1
                    exist_dcinv = self.con.execute(
                        "select count(dcid) as dccount from dcinv where dcid=%d and orgcode=%d"
                        % (row["dcid"], authDetails["orgcode"])
                    )
                    existDcinv = exist_dcinv.fetchone()
                    if existDcinv["dccount"] > 0:
                        canceldelchal = 0
                    temp_dict["canceldelchal"] = canceldelchal

                    if "goname" in list(row.keys()):
                        temp_dict["goname"] = row["goname"]
                    else:
                        temp_dict["goname"] = None
                    if temp_dict["dcflag"] == 1:
                        temp_dict["dcflag"] = "Approval"
                    elif temp_dict["dcflag"] == 3:
                        temp_dict["dcflag"] = "Consignment"
                    elif temp_dict["dcflag"] == 4:
                        temp_dict["dcflag"] = "Sale"
                    elif temp_dict["dcflag"] == 16:
                        temp_dict["dcflag"] = "Purchase"
                    elif temp_dict["dcflag"] == 19:
                        # We don't have to consider sample.
                        temp_dict["dcflag"] = "Sample"
                    elif temp_dict["dcflag"] == 6:
                        # we ignore this as well
                        temp_dict["dcflag"] = "Free Replacement"
                    else:
                        temp_dict["dcflag"] = "Bad Input"
                    if (
                        temp_dict["dcflag"] != "Sample"
                        and temp_dict["dcflag"] != "Free Replacement"
                    ):
                        dc_unbilled.append(temp_dict)
                        srno += 1
                self.con.close()
                return {"gkstatus": enumdict["Success"], "gkresult": dc_unbilled}
            except:
                self.con.close()
                return {"gkstatus": enumdict["ConnectionFailed"]}
