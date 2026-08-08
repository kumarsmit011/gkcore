from pyramid.config import os
from pyramid.view import view_config, view_defaults
import pkg_resources
import subprocess


@view_defaults(route_name="index")
class api_state(object):
    def __init__(self, request):
        self.request = request

    @view_config(request_method="GET", renderer="json")
    def main(self):

        gkcore_version = os.getenv("GKCORE_VERSION")

        if not gkcore_version:
            try:
                gkcore_version = subprocess.check_output(
                    ["git", "rev-parse", "HEAD"]
                ).strip().decode()[:8]
            except FileNotFoundError:
                gkcore_version = pkg_resources.require("gkcore")[0].version

        return {
            "gkstatus": 0,
            "version": gkcore_version,
        }
