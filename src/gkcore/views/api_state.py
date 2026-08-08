"""
Copyright (C) 2013, 2014, 2015, 2016 Digital Freedom Foundation
Copyright (C) 2017, 2018, 2019, 2020 Digital Freedom Foundation & Accion Labs Pvt. Ltd.
  This file is part of GNUKhata:A modular,robust and Free Accounting System.

  GNUKhata is Free Software; you can redistribute it and/or modify
  it under the terms of the GNU Affero General Public License as
  published by the Free Software Foundation; either version 3 of
  the License, or (at your option) any later version.

  GNUKhata is distributed in the hope that it will be useful, but
  WITHOUT ANY WARRANTY; without even the implied warranty of
  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
  GNU Affero General Public License for more details.

  You should have received a copy of the GNU Affero General Public
  License along with GNUKhata (COPYING); if not, write to the
  Free Software Foundation, Inc., 51 Franklin Street, Fifth Floor,
  Boston, MA  02110-1301  USA59 Temple Place, Suite 330,


Contributors:
"Krishnakant Mane" <kk@gmail.com>
"Prajkta Patkar"<prajakta@dff.org.in>
"Nitesh Chaughule" <nitesh@disroot.org>

"""

from pyramid.config import logging
from gkcore import eng, enumdict
from gkcore.utils import authCheck
from gkcore.models.gkdb import state
from sqlalchemy.sql import select
from sqlalchemy.engine.base import Connection
from pyramid.request import Request
from pyramid.view import view_defaults, view_config

log = logging.getLogger(__name__)


def getStates(con):
    try:
        stateData = con.execute(select([state]).order_by(state.c.statename))
        getStateData = stateData.fetchall()
        states = []
        for st in getStateData:
            states.append({st["statecode"]: st["statename"]})
        return states
    except:
        return []


@view_defaults(route_name="state")
class api_state(object):
    def __init__(self, request):
        self.request = Request
        self.request = request
        self.con = Connection

    @view_config(request_method="GET", renderer="json")
    def getAllStates(self):
        """
        This function returns a list of dictionaries having statecode as key and its corresponding statename as value.
        """
        try:
            self.con = eng.connect()
            states = getStates(self.con)
            if not len(states):
                raise Exception("Issue with fetching states")
            return {"gkstatus": enumdict["Success"], "gkresult": states}
        except:
            return {"gkstatus": enumdict["ConnectionFailed"]}

    @view_config(request_method="GET", renderer="json", request_param="abbreviation")
    def getAbbrevStates(self):
        """
        This function returns a list of dictionaries having statecode as key and its corresponding statename as value.
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
                statecode = int(self.request.params["statecode"])
                abbreviationdata = self.con.execute(
                    select([state.c.abbreviation]).where(state.c.statecode == statecode)
                )
                abbreviation = abbreviationdata.fetchone()
                return {
                    "gkstatus": enumdict["Success"],
                    "abbreviation": abbreviation["abbreviation"],
                }
            except:
                return {"gkstatus": enumdict["ConnectionFailed"]}

    @view_config(request_method="GET", renderer="json", request_param="statename")
    def getstatename(self):
        """
        This function returns 'state name' of 'state abbreviation' taken from front end.
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
                stateabbr = str(self.request.params["stateabbr"])
                statenamesdata = self.con.execute(
                    select([state.c.statename]).where(state.c.abbreviation == stateabbr)
                )
                singlestate = statenamesdata.fetchone()
                return {
                    "gkstatus": enumdict["Success"],
                    "statename": singlestate["statename"],
                }
            except:
                return {"gkstatus": enumdict["ConnectionFailed"]}

    @view_config(request_method="GET", renderer="json", request_param="type=all")
    def allStateInfo(self):
        """
        Return an array of state objects with name, abbr and code
        """
        log.info("getting all states ...")

        self.con = eng.connect()
        try:
            state_data = self.con.execute("select * from state").fetchall()
            states = []
            for state in state_data:
                states.append(
                    {
                        "state_code": state["statecode"],
                        "state_name": state["statename"],
                        "state_abbr": state["abbreviation"],
                    }
                )
            return {"gkstatus": enumdict["Success"], "gkresult": states}
        except Exception as e:
            return {"gkstatus": enumdict["ConnectionFailed"]}
