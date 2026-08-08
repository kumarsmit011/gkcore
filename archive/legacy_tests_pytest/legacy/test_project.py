"""
Copyright (C) 2013, 2014, 2015, 2016 Digital Freedom Foundation
Copyright (C) 2017, 2018 Digital Freedom Foundation & Accion Labs 
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
"Vaibhav Kurhe" <vaibhav.kurhe@gmail.com>
"""

import requests, json


class TestProject:
    @classmethod
    def setup_class(self):
        orgdata = {
            "orgdetails": {
                "orgname": "Test Organisation",
                "yearend": "2016-03-31",
                "yearstart": "2015-04-01",
                "orgtype": "Profit Making",
                "invflag": 1,
            },
            "userdetails": {
                "username": "admin",
                "userpassword": "admin",
                "userquestion": "who am i?",
                "useranswer": "hacker",
            },
        }
        result = requests.post(
            "http://127.0.0.1:6543/organisations", data=json.dumps(orgdata)
        )
        self.key = result.json()["token"]
        self.header = {"gktoken": self.key}

    @classmethod
    def teardown_class(self):
        result = requests.delete(
            "http://127.0.0.1:6543/organisations", headers=self.header
        )

    def setup(self):
        gkdata = {"projectname": "dff", "sanctionedamount": float(5000)}
        result = requests.post(
            "http://127.0.0.1:6543/projects",
            data=json.dumps(gkdata),
            headers=self.header,
        )
        result = requests.get("http://127.0.0.1:6543/projects", headers=self.header)
        for record in result.json()["gkresult"]:
            if record["projectname"] == "dff":
                self.demo_projectcode = record["projectcode"]
                break

    def teardown(self):
        gkdata = {"projectcode": self.demo_projectcode}
        result = requests.delete(
            "http://127.0.0.1:6543/projects",
            data=json.dumps(gkdata),
            headers=self.header,
        )

    def test_create_project(self):
        gkdata = {"projectname": "freedomfoundation", "sanctionedamount": float(10000)}
        result = requests.post(
            "http://127.0.0.1:6543/projects",
            data=json.dumps(gkdata),
            headers=self.header,
        )
        assert result.json()["gkstatus"] == 0

    def test_delete_project(self):
        result = requests.get("http://127.0.0.1:6543/projects", headers=self.header)
        for record in result.json()["gkresult"]:
            if record["projectname"] == "freedomfoundation":
                projectcode = record["projectcode"]
                break
        gkdata = {"projectcode": projectcode}
        result = requests.delete(
            "http://127.0.0.1:6543/projects",
            data=json.dumps(gkdata),
            headers=self.header,
        )
        assert result.json()["gkstatus"] == 0

    def test_update_project(self):
        gkdata = {
            "projectcode": self.demo_projectcode,
            "projectname": "dff_updated",
            "sanctionedamount": float(5555),
        }
        result = requests.put(
            "http://127.0.0.1:6543/projects",
            data=json.dumps(gkdata),
            headers=self.header,
        )
        assert result.json()["gkstatus"] == 0

    def test_get_all_projects(self):
        result = requests.get("http://127.0.0.1:6543/projects", headers=self.header)
        assert result.json()["gkstatus"] == 0

    def test_get_single_project(self):
        code = self.demo_projectcode
        result = requests.get(
            "http://127.0.0.1:6543/project/%s" % (code), headers=self.header
        )
        data = result.json()["gkresult"]
        assert data["projectname"] == "dff"
        """and int(data["sanctionedamount"]) == 5000"""
