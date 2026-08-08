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


class TestGroupsSubgroups:
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
        result = requests.get(
            "http://127.0.0.1:6543/groupsubgroups", headers=self.header
        )
        groupname = "Current Assets"
        for record in result.json()["gkresult"]:
            if record["groupname"] == "Current Assets":
                self.demo_groupcode = record["groupcode"]
                break
        gkdata = {"groupname": "demo_subgroup", "subgroupof": self.demo_groupcode}
        result = requests.post(
            "http://127.0.0.1:6543/groupsubgroups",
            data=json.dumps(gkdata),
            headers=self.header,
        )
        result = requests.get(
            "http://127.0.0.1:6543/groupsubgroups?groupflatlist", headers=self.header
        )
        self.demo_subgroupcode = result.json()["gkresult"]["demo_subgroup"]

    def teardown(self):
        gkdata = {"groupcode": self.demo_subgroupcode}
        result = requests.delete(
            "http://127.0.0.1:6543/groupsubgroups",
            data=json.dumps(gkdata),
            headers=self.header,
        )

    def test_create_subgroup(self):
        result = requests.get(
            "http://127.0.0.1:6543/groupsubgroups", headers=self.header
        )
        groupname = "Capital"
        for record in result.json()["gkresult"]:
            if record["groupname"] == "Capital":
                groupcode = record["groupcode"]
                break
        gkdata = {"groupname": "test_subgroup", "subgroupof": groupcode}
        result = requests.post(
            "http://127.0.0.1:6543/groupsubgroups",
            data=json.dumps(gkdata),
            headers=self.header,
        )
        assert result.json()["gkstatus"] == 0

    def test_delete_subgroup(self):
        result = requests.get(
            "http://127.0.0.1:6543/groupsubgroups?groupflatlist", headers=self.header
        )
        subgroupcode = result.json()["gkresult"]["test_subgroup"]
        gkdata = {"groupcode": subgroupcode}
        result = requests.delete(
            "http://127.0.0.1:6543/groupsubgroups",
            data=json.dumps(gkdata),
            headers=self.header,
        )
        assert result.json()["gkstatus"] == 0

    def test_update_subgroup(self):
        result = requests.get(
            "http://127.0.0.1:6543/groupsubgroups", headers=self.header
        )
        groupname = "Fixed Assets"
        for record in result.json()["gkresult"]:
            if record["groupname"] == "Fixed Assets":
                groupcode = record["groupcode"]
                break
        gkdata = {"groupname": "demo_subgroup", "subgroupof": groupcode}
        result = requests.put(
            "http://127.0.0.1:6543/groupsubgroups",
            data=json.dumps(gkdata),
            headers=self.header,
        )
        assert result.json()["gkstatus"] == 0

    def test_get_groupflatlist(self):
        """groupflatlist means that it will contain all the groups' information.
        Whether the group is main group or a subgroup, doesn't matter."""
        result = requests.get(
            "http://127.0.0.1:6543/groupsubgroups?groupflatlist", headers=self.header
        )
        assert result.json()["gkstatus"] == 0

    def test_get_subgroupsbygroup(self):
        """Get all the subgroups of a given group."""
        result = requests.get(
            "http://127.0.0.1:6543/groupDetails/%s" % (self.demo_groupcode),
            headers=self.header,
        )
        assert result.json()["gkstatus"] == 0

    def test_get_all_groups(self):
        """getAllGroups essentially means that it will contain only main groups.
        It will exclude all the subgroups, allowing only main groups."""
        result = requests.get(
            "http://127.0.0.1:6543/groupsubgroups", headers=self.header
        )
        assert result.json()["gkstatus"] == 0

    def test_get_groupsubgroup(self):
        """There are four attributes returned:- groupcode, groupname, subgroupcode, subgroupname.
        In a particular row:-
        Either groupcode and subgroupcode will be same i.e. the row will contain information of only main group
        OR
        groupcode will be the parent group of the group having its code = subgroupcode i.e. groupcode, groupname & subgroupcode, subgroupname will be present.
        """
        result = requests.get(
            "http://127.0.0.1:6543/groupsubgroup/%s" % (self.demo_groupcode),
            headers=self.header,
        )
        assert result.json()["gkstatus"] == 0

    def test_get_groupallsubgroup(self):
        result = requests.get(
            "http://127.0.0.1:6543/groupallsubgroup/%s" % (self.demo_groupcode),
            headers=self.header,
        )
        assert result.json()["gkstatus"] == 0
