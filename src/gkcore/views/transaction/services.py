from gkcore import eng, enumdict
from gkcore.models.gkdb import (
    vouchers,
    accounts,
    voucherbin,
    projects,
)
from sqlalchemy.sql import select
from sqlalchemy import and_
from datetime import datetime


# This function deletes a voucher and inserts an entry into voucherbin table.
def voucherBinInsert(con, vcode, orgcode):
    voucherdata = con.execute(
        select([vouchers]).where(vouchers.c.vouchercode == int(vcode))
    )
    voucherRow = voucherdata.fetchone()

    # Actual delete of voucher.
    con.execute(
        "delete from vouchers  where vouchercode = %d and lockflag= 'f'" % (int(vcode))
    )

    # Updating vouchercount field of accounts.
    DrData = voucherRow["drs"]
    CrData = voucherRow["crs"]
    for drKey in list(DrData.keys()):
        con.execute(
            "update accounts set vouchercount = (vouchercount -1) where accountcode = %d"
            % (int(drKey))
        )
    for crKey in list(CrData.keys()):
        con.execute(
            "update accounts set vouchercount = (vouchercount -1) where accountcode = %d"
            % (int(crKey))
        )
    finalCrs = {}
    finalDrs = {}

    # Collecting details for insert query for voucherbin.
    projectNameData = con.execute(
        select([projects.c.projectname]).where(
            projects.c.projectcode == voucherRow["projectcode"]
        )
    )
    prjNameRow = projectNameData.fetchone()
    if prjNameRow == None:
        projectName = ""
    else:
        projectName = prjNameRow["projectname"]
    for d in list(DrData.keys()):
        accname = con.execute(
            select([accounts.c.accountname]).where(accounts.c.accountcode == int(d))
        )
        account = accname.fetchone()
        finalDrs[account["accountname"]] = DrData[d]
    for c in list(CrData.keys()):
        accname = con.execute(
            select([accounts.c.accountname]).where(accounts.c.accountcode == int(c))
        )
        account = accname.fetchone()
        finalCrs[account["accountname"]] = CrData[c]
    voucherBinData = {
        "vouchercode": voucherRow["vouchercode"],
        "vouchertype": voucherRow["vouchertype"],
        "voucherdate": voucherRow["voucherdate"],
        "vouchernumber": voucherRow["vouchernumber"],
        "narration": voucherRow["narration"],
        "drs": finalDrs,
        "crs": finalCrs,
        "projectname": projectName,
        "orgcode": orgcode,
    }
    con.execute(voucherbin.insert(), [voucherBinData])


# this fuction is called to delete vouchers.
def deleteVoucherFun(vcode, orgcode):
    with eng.begin() as con:
        # Removing invoice related entries.
        invoices = con.execute(
            "select invid from billwise  where vouchercode = %d " % (int(vcode))
        )
        invid = invoices.fetchall()
        for row in invid:
            amt = con.execute(
                "select adjamount from billwise  where vouchercode = %d and invid = %d "
                % (int(vcode), row["invid"])
            )
            adjamount = amt.fetchone()
            # Updating amountpaid field of invoice.
            con.execute(
                "update invoice set amountpaid = amountpaid - %.2f where invid =%d and orgcode = %d"
                % (float(adjamount["adjamount"]), row["invid"], (int(orgcode)))
            )
            # Deleting round off vouchers.
            voucherToBeDeleted = con.execute(
                select([vouchers.c.vouchercode]).where(
                    and_(
                        vouchers.c.invid == int(row["invid"]),
                        vouchers.c.orgcode == int(orgcode),
                        vouchers.c.narration.like("Round off amount%"),
                    )
                )
            )
            voucherCodeToDelete = voucherToBeDeleted.fetchone()
            if voucherCodeToDelete and voucherCodeToDelete["vouchercode"] != None:
                con.execute(
                    "delete from billwise where vouchercode=%d"
                    % (int(voucherCodeToDelete["vouchercode"]))
                )
                voucherBinInsert(con, voucherCodeToDelete["vouchercode"], orgcode)
        con.execute("delete from billwise where vouchercode=%d" % (int(vcode)))
        # Removing drcr related vouchers.
        drcrs = con.execute(
            "select drcrid from vouchers  where vouchercode = %d " % (int(vcode))
        )
        drcridToBeDeleted = drcrs.fetchone()
        if drcridToBeDeleted and drcridToBeDeleted["drcrid"] != None:
            # Deleting round off vouchers.
            voucherToBeDeleted = con.execute(
                select([vouchers.c.vouchercode]).where(
                    and_(
                        vouchers.c.drcrid == int(drcridToBeDeleted["drcrid"]),
                        vouchers.c.orgcode == int(orgcode),
                        vouchers.c.narration.like("Round off amount%"),
                    )
                )
            )
            voucherCodeToDelete = voucherToBeDeleted.fetchone()
            if voucherCodeToDelete and voucherCodeToDelete["vouchercode"] != None:
                voucherBinInsert(con, voucherCodeToDelete["vouchercode"], orgcode)
        voucherBinInsert(con, vcode, orgcode)
        return {"gkstatus": enumdict["Success"]}


def getInvVouchers(con, orgcode, invid, include_drcrid=False, include_invid=False):
    columns = [
        vouchers.c.vouchercode,
        vouchers.c.attachmentcount,
        vouchers.c.vouchernumber,
        vouchers.c.voucherdate,
        vouchers.c.narration,
        vouchers.c.drs,
        vouchers.c.crs,
        vouchers.c.prjcrs,
        vouchers.c.prjdrs,
        vouchers.c.vouchertype,
        vouchers.c.lockflag,
        vouchers.c.delflag,
        vouchers.c.projectcode,
        vouchers.c.orgcode,
    ]

    # Construct the query based on the conditions
    if include_drcrid:
        vouchersData = con.execute(select(columns).where(
            and_(
                vouchers.c.orgcode == orgcode,
                vouchers.c.drcrid == invid,
                vouchers.c.delflag == False,
            )
        ).order_by(vouchers.c.voucherdate, vouchers.c.vouchercode))
    elif include_invid:
        vouchersData = con.execute(select(columns).where(
            and_(
                vouchers.c.orgcode == orgcode,
                vouchers.c.invid == invid,
                vouchers.c.delflag == False,
            )
        ).order_by(vouchers.c.voucherdate, vouchers.c.vouchercode)
    )
    voucherRecords = []

    for voucher in vouchersData:
        rawDr = dict(voucher["drs"])
        rawCr = dict(voucher["crs"])
        finalDR = {}
        finalCR = {}

        for d in list(rawDr.keys()):
            accname = con.execute(
                select([accounts.c.accountname]).where(
                    accounts.c.accountcode == int(d)
                )
            )
            account = accname.fetchone()
            finalDR[account["accountname"]] = rawDr[d]

        for c in list(rawCr.keys()):
            accname = con.execute(
                select([accounts.c.accountname]).where(
                    accounts.c.accountcode == int(c)
                )
            )
            account = accname.fetchone()
            finalCR[account["accountname"]] = rawCr[c]

        if voucher["narration"] == "null":
            voucher["narration"] = ""
        voucherRecords.append(
            {
                "invid": invid,
                "vouchercode": voucher["vouchercode"],
                "attachmentcount": voucher["attachmentcount"],
                "vouchernumber": voucher["vouchernumber"],
                "voucherdate": datetime.strftime(
                    voucher["voucherdate"], "%d-%m-%Y"
                ),
                "narration": voucher["narration"],
                "drs": finalDR,
                "crs": finalCR,
                "prjdrs": voucher["prjdrs"],
                "prjcrs": voucher["prjcrs"],
                "vouchertype": voucher["vouchertype"],
                "delflag": voucher["delflag"],
                "orgcode": voucher["orgcode"],
                "status": voucher["lockflag"],
            }
        )
    return voucherRecords


def check_voucher_exists(vouchernumber, vouchercode, orgcode):
    with eng.connect() as con:
        result = con.execute(
            select([vouchers]).where(
                and_(
                    vouchers.c.orgcode == orgcode,
                    vouchers.c.vouchernumber == vouchernumber,
                    vouchers.c.vouchercode == vouchercode,
                )
            )
        )
        if result.rowcount == 0:
            raise ValueError("Invalid voucher details.")
