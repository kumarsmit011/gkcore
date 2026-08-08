from gkcore import eng, enumdict
from gkcore.utils import authCheck
from sqlalchemy.engine.base import Connection
from pyramid.request import Request
from pyramid.view import view_defaults, view_config
from gkcore.views.reports.helpers.balance import calculateBalance


@view_defaults(route_name="closing-balance", request_method="GET")
class api_closing_balance(object):
    def __init__(self, request):
        self.request = Request
        self.request = request
        self.con = Connection

    @view_config(renderer="json")
    def closingBalance(self):
        """
        Purpose: returns the current balance and balance type for the given account as per the current date.
        description:
        This function takes the startedate and enddate (date of transaction) as well as accountcode.
        Returns the balance as on that date with the baltype.
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
                accountCode = self.request.params["accountcode"]
                financialStart = self.request.params["financialstart"]
                calculateTo = self.request.params["calculateto"]
                calbalData = calculateBalance(
                    self.con, accountCode, financialStart, financialStart, calculateTo
                )
                if calbalData["curbal"] == 0:
                    currentBalance = "%.2f" % float(calbalData["curbal"])
                else:
                    currentBalance = "%.2f (%s)" % (
                        float(calbalData["curbal"]),
                        calbalData["baltype"],
                    )
                self.con.close()
                return {"gkstatus": enumdict["Success"], "gkresult": currentBalance}
            except:
                self.con.close()
                return {"gkstatus": enumdict["ConnectionFailed"]}
