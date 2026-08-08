from gkcore.models.gkdb import (
    stock,
    product,
    goprod,
    dcinv,
    godown,
)
from sqlalchemy.sql import select
from sqlalchemy import and_
from sqlalchemy.sql.functions import func


# TODO: methods calculateProfitLossValue and calculateProfitLossPerProduct perform the same activities as calculateStockValue and calculateClosingStockValue.
# only the code to calculate profit and loss difference is extra. If possible merge the two to a generic method
def calculateProfitLossValue(con, orgcode, endDate):
    productList = con.execute(
        select([product.c.productcode, product.c.productdesc]).where(
            product.c.orgcode == orgcode
        )
    ).fetchall()

    godownList = con.execute(
        select([godown.c.goid, godown.c.goname]).where(godown.c.orgcode == orgcode)
    ).fetchall()

    plBuffer = {"total": 0, "products": {}}

    for productItem in productList:
        prodClosingStock = {"total": 0, "godowns": {}}
        if productItem["productcode"]:
            for godownItem in godownList:
                if godownItem["goid"]:
                    godownStockValue = calculateProfitLossPerProduct(
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
        plBuffer["total"] += prodClosingStock["total"]
        plBuffer["products"][productItem["productdesc"]] = (
            0 if not prodClosingStock["total"] else prodClosingStock
        )

    plBuffer["total"] = round(plBuffer["total"], 2)

    return plBuffer


def calculateProfitLossPerProduct(con, orgcode, endDate, productCode, godownCode):
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
    stockOnHand = []
    priceDiff = 0

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
                stock.c.stockdate <= endDate,
            )
        )
        .order_by(stock.c.stockdate, stock.c.stockid)
    ).fetchall()

    for item in stockList:
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
                stockLen = len(stockOnHand)

                if stockLen:
                    priceDiff += (float(item["qty"]) * float(item["rate"])) - (
                        float(item["qty"]) * float(stockOnHand[0]["rate"])
                    )

                    stockOnHand[0]["qty"] = float(stockOnHand[0]["qty"]) - float(
                        item["qty"]
                    )

                    extraQty = stockOnHand[0]["qty"]
                    # if extraQty < 0, items sold > items purchased
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
                                    # In this case price diff need not be calculated
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
    valueOnHand = 0
    for item in stockOnHand:
        valueOnHand += float(item["qty"]) * float(item["rate"])
    return round(priceDiff, 2)
