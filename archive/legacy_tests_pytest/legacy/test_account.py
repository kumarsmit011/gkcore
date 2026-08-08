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
"Ishan Masdekar " <imasdekar@dff.org.in>
"""
import requests, json


class TestAccount:
    @classmethod
    def setup_class(self):
        orgdata = {
            "orgdetails": {
                "orgname": "Test Organisation",
                "yearend": "2016-03-31",
                "yearstart": "2015-04-01",
                "orgtype": "Profit Making",
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
        result = requests.get(
            "http://127.0.0.1:6543/groupsubgroups", headers=self.header
        )
        for record in result.json()["gkresult"]:
            if record["groupname"] == "Current Assets":
                self.groupcode = record["groupcode"]
                break
        result = requests.get(
            "http://127.0.0.1:6543/groupDetails/%s" % (self.groupcode),
            headers=self.header,
        )
        for record in result.json()["gkresult"]:
            if record["subgroupname"] == "Bank":
                self.grpcode = record["groupcode"]
                break

    @classmethod
    def teardown_class(self):
        result = requests.delete(
            "http://127.0.0.1:6543/organisations", headers=self.header
        )

    def setup(self):
        gkdata = {
            "accountname": "Bank Of India",
            "openingbal": 5,
            "groupcode": self.grpcode,
        }
        result = requests.post(
            "http://127.0.0.1:6543/accounts",
            data=json.dumps(gkdata),
            headers=self.header,
        )
        result = requests.get("http://127.0.0.1:6543/accounts", headers=self.header)
        for record in result.json()["gkresult"]:
            if record["accountname"] == "Bank Of India":
                self.demoaccountcode = record["accountcode"]
                break

    def teardown(self):
        gkdata = {"accountcode": self.demoaccountcode}
        result = requests.delete(
            "http://127.0.0.1:6543/accounts",
            data=json.dumps(gkdata),
            headers=self.header,
        )

    def test_create_account(self):
        gkdata = {
            "accountname": "State Bank Of India",
            "openingbal": 100,
            "groupcode": self.grpcode,
        }
        result = requests.post(
            "http://127.0.0.1:6543/accounts",
            data=json.dumps(gkdata),
            headers=self.header,
        )
        assert result.json()["gkstatus"] == 0

    def test_delete_account(self):
        gkdata = {
            "accountname": "State Bank Of India",
            "openingbal": 100,
            "groupcode": self.grpcode,
        }
        result = requests.get("http://127.0.0.1:6543/accounts", headers=self.header)
        for record in result.json()["gkresult"]:
            if record["accountname"] == "State Bank Of India":
                self.acccode = record["accountcode"]
                break
        gkdata1 = {"accountcode": self.acccode}
        result = requests.delete(
            "http://127.0.0.1:6543/accounts",
            data=json.dumps(gkdata1),
            headers=self.header,
        )
        assert result.json()["gkstatus"] == 0

    def test_update_account(self):
        gkdata = {
            "accountname": "YES Bank",
            "openingbal": 6,
            "accountcode": self.demoaccountcode,
        }
        result = requests.put(
            "http://127.0.0.1:6543/accounts",
            data=json.dumps(gkdata),
            headers=self.header,
        )
        assert result.json()["gkstatus"] == 0

    def test_get_single_account(self):
        result = requests.get(
            "http://127.0.0.1:6543/account/%s" % (self.demoaccountcode),
            headers=self.header,
        )
        assert (
            result.json()["gkresult"]["openingbal"] == "5.00"
            and result.json()["gkresult"]["groupcode"] == self.grpcode
        )

    def test_account_already_exists(self):
        result = requests.get(
            "http://127.0.0.1:6543/accounts?find=exists&accountname=Bank Of India",
            headers=self.header,
        )
        assert result.json()["gkstatus"] == 1

    def test_get_all_accounts(self):
        result = requests.get("http://127.0.0.1:6543/accounts", headers=self.header)
        assert result.json()["gkstatus"] == 0

    def test_get_accounts_list(self):
        result = requests.get(
            "http://127.0.0.1:6543/accounts?acclist", headers=self.header
        )
        assert result.json()["gkstatus"] == 0
