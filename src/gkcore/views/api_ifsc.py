from pyramid.request import Request
from gkcore import enumdict
from pyramid.view import view_defaults, view_config
from gkcore.utils import authCheck, gk_log
from gkcore.views.helpers.fin_utils import ifsc_codes


@view_defaults(route_name="ifsc")
class api_ifsc(object):
    def __init__(self, request):
        self.request = Request
        self.request = request

    @view_config(request_method="GET", request_param="check", renderer="json")
    def validate_ifsc(self):
        """
        Validate provided IFSC code

        This method first checks the user auth status, Then validates given
        ifsc code with the razorpay/ifsc docker server & get's the response
        """
        # Check whether the user is registered & valid
        try:
            token = self.request.headers["gktoken"]
        except Exception as e:
            gk_log(__name__).warn(e)
            return {"gkstatus": enumdict["UnauthorisedAccess"]}

        auth_details = authCheck(token)

        if auth_details["auth"] is False:
            return {"gkstatus": enumdict["UnauthorisedAccess"]}

        # grab the ifsc code provided in api params
        user_ifsc_code = self.request.params["check"]

        # define a default result & mutate according to logic below
        result = {"gkstatus": enumdict["ConnectionFailed"]}

        # validate the ifsc code return appropriate response
        try:
            for bank in ifsc_codes():
                if bank["IFSC"] == user_ifsc_code:
                    result["gkstatus"] = enumdict["Success"]
                    result["gkresult"] = bank
                    return result
            else:
                return result
        except Exception as e:
            print(e)
            result["gkstatus"] = enumdict["ConnectionFailed"]
            result["gkresult"] = f"{e}"
            return result
