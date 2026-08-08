from gkcore import eng, enumdict
from gkcore.utils import authCheck, getUserRole
from gkcore.models.gkdb import voucherbin
from sqlalchemy.sql import select
from sqlalchemy import desc
from pyramid.view import view_config, view_defaults
from datetime import datetime
from sqlalchemy.engine.base import Connection


@view_defaults(route_name="deleted-voucher", request_method="GET")
class api_voucher(object):
    def __init__(self, request):
        self.request = request
        self.con = Connection

    @view_config(renderer="json")
    def getdeletedVoucher(self):
        """
        this function is called when type=deletedvoucher is passed to the url /report
        it returns a grid containing details of all the deleted vouchers
        it first checks the userrole then fetches the data from voucherbin puts into a list.
        """
        try:
            token = self.request.headers["gktoken"]
        except:
            return {"gkstatus": enumdict["UnauthorisedAccess"]}
        authDetails = authCheck(token)
        if authDetails["auth"] == False:
            return {"gkstatus": enumdict["UnauthorisedAccess"]}
        else:
            # try:
            self.con = eng.connect()
            orgcode = authDetails["orgcode"]
            orgcode = int(orgcode)
            userRoleData = getUserRole(authDetails["userid"], authDetails["orgcode"])
            userrole = userRoleData["gkresult"]["userrole"]
            vouchers = []
            if userrole == -1 or userrole == 0:
                if "orderflag" in self.request.params:
                    voucherRow = self.con.execute(
                        select([voucherbin])
                        .where(voucherbin.c.orgcode == orgcode)
                        .order_by(
                            desc(voucherbin.c.voucherdate), voucherbin.c.vouchercode
                        )
                    )
                else:
                    voucherRow = self.con.execute(
                        select([voucherbin])
                        .where(voucherbin.c.orgcode == orgcode)
                        .order_by(voucherbin.c.voucherdate, voucherbin.c.vouchercode)
                    )
                voucherData = voucherRow.fetchall()
                for voucher in voucherData:
                    vouchers.append(
                        {
                            "vouchercode": voucher["vouchercode"],
                            "vouchernumber": voucher["vouchernumber"],
                            "voucherdate": datetime.strftime(
                                voucher["voucherdate"], "%d-%m-%Y"
                            ),
                            "narration": voucher["narration"],
                            "drs": voucher["drs"],
                            "crs": voucher["crs"],
                            "vouchertype": voucher["vouchertype"],
                            "projectname": voucher["projectname"],
                        }
                    )
                self.con.close()
                return {"gkstatus": enumdict["Success"], "gkresult": vouchers}
            else:
                self.con.close()
                return {"gkstatus": enumdict["BadPrivilege"]}
