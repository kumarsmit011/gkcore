import logging
from gkcore import eng, enumdict
from gkcore.models.gkdb import (
    organisation,
    delchal,
    invoice,
    customerandsupplier,
    stock,
    product,
    transfernote,
    goprod,
    dcinv,
    godown,
    drcr,
)
from sqlalchemy.sql import select
from sqlalchemy import and_, or_
from datetime import datetime
from sqlalchemy.sql.functions import func
import traceback  # for printing detailed exception logs

def stockonhandfun(con, orgcode, productCode, endDate):
    stockReport = []
    totalinward = 0.00
    totaloutward = 0.00
    if productCode != "all":
        openingStockResult = con.execute(
            select(
                [
                    product.c.openingstock,
                    product.c.productdesc,
                    product.c.productcode,
                    product.c.gsflag,
                ]
            ).where(
                and_(
                    product.c.productcode == productCode,
                    product.c.gsflag == 7,
                    product.c.orgcode == orgcode,
                )
            )
        )
        osRow = openingStockResult.fetchone()
        if not osRow:
            raise ValueError(f"Productcode: {productCode} is not a product.")
        openingStock = osRow["openingstock"]
        prodName = osRow["productdesc"]
        prodCode = osRow["productcode"]
        gsflag = osRow["gsflag"]
        stockRecords = con.execute(
            select([stock])
            .where(
                and_(
                    stock.c.productcode == productCode,
                    stock.c.orgcode == orgcode,
                )
            )
            .order_by(stock.c.stockdate)
        )
        stockData = stockRecords.fetchall()
        totalinward = totalinward + float(openingStock)

        for finalRow in stockData:
            if finalRow["dcinvtnflag"] == 3 or finalRow["dcinvtnflag"] == 9:
                countresult = con.execute(
                    select(
                        [
                            invoice.c.invoicedate,
                            invoice.c.invoiceno,
                            invoice.c.custid,
                        ]
                    ).where(
                        and_(
                            invoice.c.invoicedate <= endDate,
                            invoice.c.invid == finalRow["dcinvtnid"],
                        )
                    )
                )
                if countresult.rowcount == 1:
                    countrow = countresult.fetchone()
                    custdata = con.execute(
                        select([customerandsupplier.c.custname]).where(
                            customerandsupplier.c.custid == countrow["custid"]
                        )
                    )
                    custrow = custdata.fetchone()
                    if custrow != None:
                        custnamedata = custrow["custname"]
                    else:
                        custnamedata = "Cash Memo"
                    if finalRow["inout"] == 9:
                        openingStock = float(openingStock) + float(finalRow["qty"])
                        totalinward = float(totalinward) + float(finalRow["qty"])
                    if finalRow["inout"] == 15:
                        openingStock = float(openingStock) - float(finalRow["qty"])
                        totaloutward = float(totaloutward) + float(finalRow["qty"])
            if finalRow["dcinvtnflag"] == 4:
                countresult = con.execute(
                    select(
                        [delchal.c.dcdate, delchal.c.dcno, delchal.c.custid]
                    ).where(
                        and_(
                            delchal.c.dcdate <= endDate,
                            delchal.c.dcid == finalRow["dcinvtnid"],
                        )
                    )
                )
                if countresult.rowcount == 1:
                    countrow = countresult.fetchone()
                    custdata = con.execute(
                        select([customerandsupplier.c.custname]).where(
                            customerandsupplier.c.custid == countrow["custid"]
                        )
                    )
                    custrow = custdata.fetchone()
                    dcinvresult = con.execute(
                        select([dcinv.c.invid]).where(
                            dcinv.c.dcid == finalRow["dcinvtnid"]
                        )
                    )
                    if dcinvresult.rowcount == 1:
                        dcinvrow = dcinvresult.fetchone()
                        invresult = con.execute(
                            select([invoice.c.invoiceno]).where(
                                invoice.c.invid == dcinvrow["invid"]
                            )
                        )
                        """ No need to check if invresult has rowcount 1 since it must be 1 """
                        invrow = invresult.fetchone()
                        trntype = "delchal&invoice"
                    else:
                        dcinvrow = {"invid": ""}
                        invrow = {"invoiceno": ""}
                        trntype = "delchal"
                    if finalRow["inout"] == 9:
                        openingStock = float(openingStock) + float(finalRow["qty"])
                        totalinward = float(totalinward) + float(finalRow["qty"])
                    if finalRow["inout"] == 15:
                        openingStock = float(openingStock) - float(finalRow["qty"])
                        totaloutward = float(totaloutward) + float(finalRow["qty"])
            if finalRow["dcinvtnflag"] == 18:
                if finalRow["inout"] == 9:
                    openingStock = float(openingStock) + float(finalRow["qty"])
                    totalinward = float(totalinward) + float(finalRow["qty"])
                if finalRow["inout"] == 15:
                    openingStock = float(openingStock) - float(finalRow["qty"])
                    totaloutward = float(totaloutward) + float(finalRow["qty"])
            if finalRow["dcinvtnflag"] == 7:
                countresult = con.execute(
                    select([func.count(drcr.c.drcrid).label("dc")]).where(
                        and_(
                            drcr.c.drcrdate <= endDate,
                            drcr.c.drcrid == finalRow["dcinvtnid"],
                        )
                    )
                )
                countrow = countresult.fetchone()
                if countrow["dc"] == 1:
                    if finalRow["inout"] == 9:
                        openingStock = float(openingStock) + float(finalRow["qty"])
                        totalinward = float(totalinward) + float(finalRow["qty"])
                    if finalRow["inout"] == 15:
                        openingStock = float(openingStock) - float(finalRow["qty"])
                        totaloutward = float(totaloutward) + float(finalRow["qty"])
        stockReport.append(
            {
                "srno": 1,
                "productname": prodName,
                "productcode": prodCode,
                "totalinwardqty": "%.2f" % float(totalinward),
                "totaloutwardqty": "%.2f" % float(totaloutward),
                "balance": "%.2f" % float(openingStock),
                "gsflag": gsflag,

            }
        )
        return {"gkstatus": enumdict["Success"], "gkresult": stockReport}
    if productCode == "all":
        products = con.execute(
            select(
                [
                    product.c.openingstock,
                    product.c.productcode,
                    product.c.productdesc,
                ]
            ).where(and_(product.c.orgcode == orgcode, product.c.gsflag == 7))
        )
        prodDesc = products.fetchall()
        srno = 1
        for row in prodDesc:
            totalinward = 0.00
            totaloutward = 0.00
            openingStock = row["openingstock"]
            productCd = row["productcode"]
            prodName = row["productdesc"]
            stockRecords = con.execute(
                select([stock]).where(
                    and_(
                        stock.c.productcode == productCd,
                        stock.c.orgcode == orgcode,
                    )
                )
            )
            stockData = stockRecords.fetchall()
            totalinward = totalinward + float(openingStock)
            for finalRow in stockData:
                if finalRow["dcinvtnflag"] == 3 or finalRow["dcinvtnflag"] == 9:
                    countresult = con.execute(
                        select(
                            [
                                invoice.c.invoicedate,
                                invoice.c.invoiceno,
                                invoice.c.custid,
                            ]
                        ).where(
                            and_(
                                invoice.c.invoicedate <= endDate,
                                invoice.c.invid == finalRow["dcinvtnid"],
                            )
                        )
                    )
                    if countresult.rowcount == 1:
                        countrow = countresult.fetchone()
                        custdata = con.execute(
                            select([customerandsupplier.c.custname]).where(
                                customerandsupplier.c.custid == countrow["custid"]
                            )
                        )
                        custrow = custdata.fetchone()
                        if custrow != None:
                            custnamedata = custrow["custname"]
                        else:
                            custnamedata = "Cash Memo"
                        if finalRow["inout"] == 9:
                            openingStock = float(openingStock) + float(
                                finalRow["qty"]
                            )
                            totalinward = float(totalinward) + float(
                                finalRow["qty"]
                            )
                        if finalRow["inout"] == 15:
                            openingStock = float(openingStock) - float(
                                finalRow["qty"]
                            )
                            totaloutward = float(totaloutward) + float(
                                finalRow["qty"]
                            )
                if finalRow["dcinvtnflag"] == 4:
                    countresult = con.execute(
                        select(
                            [delchal.c.dcdate, delchal.c.dcno, delchal.c.custid]
                        ).where(
                            and_(
                                delchal.c.dcdate <= endDate,
                                delchal.c.dcid == finalRow["dcinvtnid"],
                            )
                        )
                    )
                    if countresult.rowcount == 1:
                        countrow = countresult.fetchone()
                        custdata = con.execute(
                            select([customerandsupplier.c.custname]).where(
                                customerandsupplier.c.custid == countrow["custid"]
                            )
                        )
                        custrow = custdata.fetchone()
                        dcinvresult = con.execute(
                            select([dcinv.c.invid]).where(
                                dcinv.c.dcid == finalRow["dcinvtnid"]
                            )
                        )
                        if dcinvresult.rowcount == 1:
                            dcinvrow = dcinvresult.fetchone()
                            invresult = con.execute(
                                select([invoice.c.invoiceno]).where(
                                    invoice.c.invid == dcinvrow["invid"]
                                )
                            )
                            """ No need to check if invresult has rowcount 1 since it must be 1 """
                            invrow = invresult.fetchone()
                            trntype = "delchal&invoice"
                        else:
                            dcinvrow = {"invid": ""}
                            invrow = {"invoiceno": ""}
                            trntype = "delchal"
                        if finalRow["inout"] == 9:
                            openingStock = float(openingStock) + float(
                                finalRow["qty"]
                            )
                            totalinward = float(totalinward) + float(
                                finalRow["qty"]
                            )
                        if finalRow["inout"] == 15:
                            openingStock = float(openingStock) - float(
                                finalRow["qty"]
                            )
                            totaloutward = float(totaloutward) + float(
                                finalRow["qty"]
                            )
                if finalRow["dcinvtnflag"] == 18:
                    if finalRow["inout"] == 9:
                        openingStock = float(openingStock) + float(finalRow["qty"])
                        totalinward = float(totalinward) + float(finalRow["qty"])
                    if finalRow["inout"] == 15:
                        openingStock = float(openingStock) - float(finalRow["qty"])
                        totaloutward = float(totaloutward) + float(finalRow["qty"])
                if finalRow["dcinvtnflag"] == 7:
                    countresult = con.execute(
                        select([func.count(drcr.c.drcrid).label("dc")]).where(
                            and_(
                                drcr.c.drcrdate <= endDate,
                                drcr.c.drcrid == finalRow["dcinvtnid"],
                            )
                        )
                    )
                    countrow = countresult.fetchone()
                    if countrow["dc"] == 1:
                        if finalRow["inout"] == 9:
                            openingStock = float(openingStock) + float(
                                finalRow["qty"]
                            )
                            totalinward = float(totalinward) + float(
                                finalRow["qty"]
                            )
                        if finalRow["inout"] == 15:
                            openingStock = float(openingStock) - float(
                                finalRow["qty"]
                            )
                            totaloutward = float(totaloutward) + float(
                                finalRow["qty"]
                            )
            stockReport.append(
                {
                    "srno": srno,
                    "productname": prodName,
                    "productcode": productCd,
                    "totalinwardqty": "%.2f" % float(totalinward),
                    "totaloutwardqty": "%.2f" % float(totaloutward),
                    "balance": "%.2f" % float(openingStock),
                }
            )
            srno = srno + 1
    return {"gkresult": stockReport}


def calculateOpeningStockValue(con, orgcode):
    try:
        # product table contains both product & service entries, filter only products
        productList = con.execute(
            select([product.c.productcode, product.c.productdesc]).where(
                and_(product.c.orgcode == orgcode, product.c.gsflag == 7)
            )
        ).fetchall()

        godownList = con.execute(
            select([godown.c.goid, godown.c.goname]).where(godown.c.orgcode == orgcode)
        ).fetchall()

        opStock = {"total": 0, "products": {}}
        for productItem in productList:
            prodOpStock = {"total": 0, "godowns": {}}
            if productItem["productcode"]:
                for godownItem in godownList:
                    if godownItem["goid"]:
                        openingStockQuery = con.execute(
                            select(
                                [goprod.c.goopeningstock, goprod.c.openingstockvalue]
                            ).where(
                                and_(
                                    goprod.c.productcode == productItem["productcode"],
                                    goprod.c.goid == godownItem["goid"],
                                    goprod.c.orgcode == orgcode,
                                )
                            )
                        )
                        if openingStockQuery.rowcount:
                            openingStock = openingStockQuery.fetchone()
                            if openingStock["goopeningstock"] != 0:
                                rate = (
                                    openingStock["openingstockvalue"]
                                    / openingStock["goopeningstock"]
                                )
                                # stockOnHand.append(
                                #     {
                                #         "qty": float(openingStock["goopeningstock"]),
                                #         "rate": float(rate),
                                #     }
                                # )
                                # print(stockOnHand)
                                prodOpStock["total"] += float(
                                    openingStock["openingstockvalue"]
                                )
                                if float(openingStock["openingstockvalue"]):
                                    prodOpStock["godowns"][
                                        godownItem["goname"]
                                    ] = float(openingStock["openingstockvalue"])
            opStock["total"] += prodOpStock["total"]
            opStock["products"][productItem["productdesc"]] = (
                0 if not prodOpStock["total"] else prodOpStock
            )
        opStock["total"] = round(opStock["total"], 2)
        return opStock
    except:
        print(traceback.format_exc())
        return {"total": 0, "products": {}}


def calculateClosingStockValue(con, orgcode, endDate):
    try:
        # product table contains both products & services, we fetch only products
        productList = con.execute(
            select([product.c.productcode, product.c.productdesc]).where(
                and_(
                product.c.orgcode == orgcode, product.c.gsflag == 7)
            )
        ).fetchall()

        godownList = con.execute(
            select([godown.c.goid, godown.c.goname]).where(godown.c.orgcode == orgcode)
        ).fetchall()

        closingStock = {"total": 0, "products": {}}
        # loop over all products
        for productItem in productList:
            prodClosingStock = {"total": 0, "godowns": {}}
            if productItem["productcode"]:
                for godownItem in godownList:
                    if godownItem["goid"]:
                        godownStockValue = calculateStockValue(
                            con,
                            orgcode,
                            endDate,
                            productItem["productcode"],
                            godownItem["goid"],
                        )
                        prodClosingStock["total"] += godownStockValue
                        if godownStockValue:
                            prodClosingStock["godowns"][
                                godownItem["goname"]
                            ] = godownStockValue
            closingStock["total"] += prodClosingStock["total"]
            closingStock["products"][productItem["productdesc"]] = (
                0 if not prodClosingStock["total"] else prodClosingStock
            )

        closingStock["total"] = round(closingStock["total"], 2)

        return closingStock
    except:
        print(traceback.format_exc())
        return {"total": 0, "products": {}}


def calculateStockValue(con, orgcode, endDate, productCode, godownCode):
    """
    Note: Preform the below steps for a product in a godown

    Algorithm
    step1: stockInHand = []
    step2: Get the opening stock qty and value from goprod table and push the same into stockInHand array.
    step3: Get all the stock table entries for the product in a godown
    step4: Loop through all the stock data:
            if trn == invoice/ cash memo/ delivery note:
            if purchase:
                stockInHand.append({qty: trn.qty, rate: trn.rate})
            else if sale:
                stockInHand[0][qty] -= trn.qty
    step5: Loop through the stockInHand arr:
            valueOnHand += float(item["qty"]) * float(item["rate"])
    """
    try:
        stockOnHand = []

        # opening stock
        openingStockQuery = con.execute(
            select([goprod.c.goopeningstock, goprod.c.openingstockvalue]).where(
                and_(
                    goprod.c.productcode == productCode,
                    goprod.c.goid == godownCode,
                    goprod.c.orgcode == orgcode,
                )
            )
        )

        if openingStockQuery.rowcount:
            openingStock = openingStockQuery.fetchone()
            if openingStock["goopeningstock"] != 0:
                rate = (
                    openingStock["openingstockvalue"] / openingStock["goopeningstock"]
                )
                stockOnHand.append(
                    {"qty": float(openingStock["goopeningstock"]), "rate": float(rate)}
                )
                print(stockOnHand)

        print(endDate)
        # stock sale and purchase data
        stockList = con.execute(
            select(
                [
                    stock.c.inout,
                    stock.c.rate,
                    stock.c.qty,
                    stock.c.dcinvtnid,
                    stock.c.dcinvtnflag,
                ]
            )
            .where(
                and_(
                    stock.c.orgcode == orgcode,
                    stock.c.productcode == productCode,
                    stock.c.goid == godownCode,
                )
            )
            .order_by(stock.c.stockdate, stock.c.stockid)
        ).fetchall()
        # print(len(stockList))

        for item in stockList:
            # print(item["qty"])
            trnId = item["dcinvtnid"]
            trnFlag = item["dcinvtnflag"]

            proceed = True
            stockIn = item["inout"] == 9

            if trnFlag == 4:  # avoid unlinked delchal
                linkCount = con.execute(
                    select([func.count(dcinv.c.invid)]).where(
                        and_(dcinv.c.dcid == trnId, dcinv.c.orgcode == orgcode)
                    )
                ).scalar()
                # print("linkcount = %d"%(linkCount))
                # some delivery challans wont be linked to invoices, so avoid them here
                if linkCount <= 0:
                    proceed = False
            if proceed:
                # update stockOnHand based on FIFO
                if stockIn:  # purchase or stock in
                    stockLen = len(stockOnHand)
                    if stockLen:
                        lastStock = stockOnHand[stockLen - 1]
                        if float(lastStock["qty"]) < 0 and float(
                            lastStock["rate"]
                        ) == float(
                            item["rate"]
                        ):  # case where sale or stock out has happened before any purchase or stock in
                            lastStock["qty"] = float(lastStock["qty"]) + float(
                                item["qty"]
                            )
                            continue
                    stockOnHand.append({"rate": item["rate"], "qty": item["qty"]})
                else:  # sale or stock out
                    # print("==============soh=============")
                    # print(stockOnHand)
                    stockLen = len(stockOnHand)

                    if stockLen:
                        stockOnHand[0]["qty"] = float(stockOnHand[0]["qty"]) - float(
                            item["qty"]
                        )

                        extraQty = stockOnHand[0]["qty"]

                        if extraQty <= 0:
                            extraQty *= -1
                            while extraQty:
                                stockOnHand.pop(0)
                                if extraQty == 0:
                                    break
                                if len(stockOnHand) > 0:
                                    if float(stockOnHand[0]["qty"]) > 0:
                                        stockOnHand[0]["qty"] = (
                                            float(stockOnHand[0]["qty"]) - extraQty
                                        )
                                        extraQty = stockOnHand[0]["qty"]
                                        if extraQty >= 0:
                                            break
                                        else:
                                            extraQty *= -1
                                    else:
                                        # if the qty is negative (stock out happened before stock in), then the remaining negative will also be added to it
                                        stockOnHand[0]["qty"] = (
                                            float(stockOnHand[0]["qty"]) - extraQty
                                        )
                                        break
                                else:
                                    stockOnHand.append(
                                        {"rate": item["rate"], "qty": -1 * extraQty}
                                    )
                                    break
                    else:
                        stockOnHand.append(
                            {"rate": item["rate"], "qty": -1 * item["qty"]}
                        )
                # print(stockOnHand)
        valueOnHand = 0
        # print("Stock value calculation")
        for item in stockOnHand:
            valueOnHand += float(item["qty"]) * float(item["rate"])
            # print(valueOnHand)
        return round(valueOnHand, 2)
    except:
        print(traceback.format_exc())
        return -1


def godownwise_stock_on_hand(
    con, orgcode, startDate, endDate, productCode, godownCode
):
    with eng.connect() as con:
        totalinward = 0.00
        totaloutward = 0.00
        productCode = productCode
        godownCode = godownCode
        goopeningStockResult = con.execute(
            select([goprod.c.goopeningstock]).where(
                and_(
                    goprod.c.productcode == productCode,
                    goprod.c.goid == godownCode,
                    goprod.c.orgcode == orgcode,
                )
            )
        )
        gosRow = goopeningStockResult.fetchone()
        if gosRow != None:
            gopeningStock = gosRow["goopeningstock"]
        else:
            gopeningStock = 0.00
        stockRecords = con.execute(
            select([stock])
            .where(
                and_(
                    stock.c.productcode == productCode,
                    stock.c.goid == godownCode,
                    stock.c.orgcode == orgcode,
                )
            )
            .order_by(stock.c.stockdate)
        )
        stockData = stockRecords.fetchall()
        ysData = con.execute(
            select([organisation.c.yearstart]).where(
                organisation.c.orgcode == orgcode
            )
        )
        ysRow = ysData.fetchone()
        yearStart = datetime.strptime(str(ysRow["yearstart"]), "%Y-%m-%d")
        if not startDate:
            startDate = yearStart
        totalinward = totalinward + float(gopeningStock)
        for finalRow in stockData:
            if finalRow["dcinvtnflag"] == 4:
                # Delivery note
                countresult = con.execute(
                    select(
                        [delchal.c.dcdate, delchal.c.dcno, delchal.c.custid]
                    ).where(
                        and_(
                            delchal.c.dcdate <= endDate,
                            delchal.c.dcid == finalRow["dcinvtnid"],
                        )
                    )
                )
                if countresult.rowcount == 1:
                    countrow = countresult.fetchone()
                    custdata = con.execute(
                        select([customerandsupplier.c.custname]).where(
                            customerandsupplier.c.custid == countrow["custid"]
                        )
                    )
                    custrow = custdata.fetchone()
                    dcinvresult = con.execute(
                        select([dcinv.c.invid]).where(
                            dcinv.c.dcid == finalRow["dcinvtnid"]
                        )
                    )
                    if dcinvresult.rowcount == 1:
                        dcinvrow = dcinvresult.fetchone()
                        invresult = con.execute(
                            select([invoice.c.invoiceno]).where(
                                invoice.c.invid == dcinvrow["invid"]
                            )
                        )
                        """ No need to check if invresult has rowcount 1 since it must be 1 """
                        invrow = invresult.fetchone()
                        trntype = "delchal&invoice"
                    else:
                        dcinvrow = {"invid": ""}
                        invrow = {"invoiceno": ""}
                        trntype = "delcha"
                    if finalRow["inout"] == 9:
                        gopeningStock = float(gopeningStock) + float(
                            finalRow["qty"]
                        )
                        totalinward = float(totalinward) + float(finalRow["qty"])
                    if finalRow["inout"] == 15:
                        gopeningStock = float(gopeningStock) - float(
                            finalRow["qty"]
                        )
                        totaloutward = float(totaloutward) + float(finalRow["qty"])
            if finalRow["dcinvtnflag"] == 20:
                # Transfer Note
                countresult = con.execute(
                    select(
                        [
                            transfernote.c.transfernotedate,
                            transfernote.c.transfernoteno,
                        ]
                    ).where(
                        and_(
                            transfernote.c.transfernotedate <= endDate,
                            transfernote.c.transfernoteid == finalRow["dcinvtnid"],
                        )
                    )
                )
                if countresult.rowcount == 1:
                    countrow = countresult.fetchone()
                    if finalRow["inout"] == 9:
                        gopeningStock = float(gopeningStock) + float(
                            finalRow["qty"]
                        )
                        totalinward = float(totalinward) + float(finalRow["qty"])
                    if finalRow["inout"] == 15:
                        gopeningStock = float(gopeningStock) - float(
                            finalRow["qty"]
                        )
                        totaloutward = float(totaloutward) + float(finalRow["qty"])
            if finalRow["dcinvtnflag"] == 18:
                # Rejection Note
                if finalRow["inout"] == 9:
                    gopeningStock = float(gopeningStock) + float(finalRow["qty"])
                    totalinward = float(totalinward) + float(finalRow["qty"])
                if finalRow["inout"] == 15:
                    gopeningStock = float(gopeningStock) - float(finalRow["qty"])
                    totaloutward = float(totaloutward) + float(finalRow["qty"])
            if finalRow["dcinvtnflag"] == 7:
                # Debite Credit Note
                countresult = con.execute(
                    select([func.count(drcr.c.drcrid).label("dc")]).where(
                        and_(
                            drcr.c.drcrdate >= yearStart,
                            drcr.c.drcrdate <= endDate,
                            drcr.c.drcrid == finalRow["dcinvtnid"],
                        )
                    )
                )
                countrow = countresult.fetchone()
                if countrow["dc"] == 1:
                    if finalRow["inout"] == 9:
                        gopeningStock = float(gopeningStock) + float(
                            finalRow["qty"]
                        )
                        totalinward = float(totalinward) + float(finalRow["qty"])
                    if finalRow["inout"] == 15:
                        gopeningStock = float(gopeningStock) - float(
                            finalRow["qty"]
                        )
                        totaloutward = float(totaloutward) + float(finalRow["qty"])
        product_value = calculateStockValue(
                    con, orgcode, endDate, productCode, godownCode
                )

        return {
            "totalinwardqty": float(totalinward),
            "totaloutwardqty": float(totaloutward),
            "balance": float(gopeningStock),
            "value": float(product_value),
        }
