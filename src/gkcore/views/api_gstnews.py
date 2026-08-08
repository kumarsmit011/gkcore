from gkcore.utils import authCheck
from pyramid.view import view_config, view_defaults
import requests as r
from gkcore import enumdict


@view_defaults(route_name="gstnews")
class api_state(object):
    def __init__(self, request):
        self.request = request
        self.portal = "https://www.gst.gov.in/fomessage/newsupdates/"
        # use custom user agent, as the gst website does not seem to allow other programs
        # to access their public api
        self.custom_headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/104.0.0.0 Safari/537.36"
        }

    @view_config(request_method="GET", renderer="json")
    def news_summary(self):
        """Returns recent gst news list"""
        # check if user authenticated
        try:
            self.request.headers["gktoken"]
        except:
            return {"gkstatus": 2}

        if authCheck(self.request.headers["gktoken"])["auth"] == False:
            return {"gkstatus": 2}
        # access the api
        response = r.get(url=self.portal, headers=self.custom_headers)
        if response.status_code == 200:
            try:
                return {
                    "gkstatus": enumdict["Success"],
                    "gkresult": response.json()["data"],
                }
            except Exception as e:
                print(e)
        else:
            return {"gkstatus": enumdict["ProxyServerError"]}

    @view_config(request_method="GET", request_param="id", renderer="json")
    def news_item(self):
        """Returns corresponding news item for given code"""
        # auth check
        try:
            self.request.headers["gktoken"]
        except:
            return {"gkstatus": 2}

        if authCheck(self.request.headers["gktoken"])["auth"] == False:
            return {"gkstatus": 2}

        response = r.get(
            url=self.portal + self.request.params["id"], headers=self.custom_headers
        )
        if response.status_code == 200:
            try:
                return {"gkstatus": 0, "gkresult": response.json()["data"][0]}
            except Exception as e:
                print(e)
        else:
            return {"gkstatus": enumdict["ProxyServerError"]}
