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
"Bhavesh Bawadhane " <bbhavesh07@gmail.com>
"""
import requests, json


class TestCategorySpecs:
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
        categorydata = {"categoryname": "Test Category"}
        result = requests.post(
            "http://127.0.0.1:6543/categories",
            data=json.dumps(categorydata),
            headers=self.header,
        )
        self.democategorycode = result.json()["gkresult"]
        specdata = {
            "attrname": "Curd",
            "attrtype": 1,
            "categorycode": self.democategorycode,
        }
        specresult = requests.post(
            "http://127.0.0.1:6543/categoryspecs",
            data=json.dumps(specdata),
            headers=self.header,
        )
        result = requests.get(
            "http://127.0.0.1:6543/categoryspecs?categorycode=%d"
            % (int(self.democategorycode)),
            headers=self.header,
        )
        for record in result.json()["gkresult"]:
            if record["attrname"] == "Curd":
                self.demospeccode = record["spcode"]
                break

    def teardown(self):
        deletespecdata = {"spcode": int(self.demospeccode)}
        deletespecresult = requests.delete(
            "http://127.0.0.1:6543/categoryspecs",
            data=json.dumps(deletespecdata),
            headers=self.header,
        )
        gkdata = {"categorycode": self.democategorycode}
        result = requests.delete(
            "http://127.0.0.1:6543/categories",
            data=json.dumps(gkdata),
            headers=self.header,
        )

    def test_createAndDelete_spec(self):
        specdata = {
            "attrname": "Milk",
            "attrtype": 0,
            "categorycode": self.democategorycode,
        }
        addspecresult = requests.post(
            "http://127.0.0.1:6543/categoryspecs",
            data=json.dumps(specdata),
            headers=self.header,
        )
        result = requests.get(
            "http://127.0.0.1:6543/categoryspecs?categorycode=%d"
            % (int(self.democategorycode)),
            headers=self.header,
        )
        for record in result.json()["gkresult"]:
            if record["attrname"] == "Milk":
                self.speccode = record["spcode"]
                break
        gkdata1 = {"spcode": self.speccode}
        deletespecresult = requests.delete(
            "http://127.0.0.1:6543/categoryspecs",
            data=json.dumps(gkdata1),
            headers=self.header,
        )
        assert (
            deletespecresult.json()["gkstatus"] == 0
            and addspecresult.json()["gkstatus"] == 0
        )

    def test_update_spec(self):
        specdata = {
            "attrname": "Mouse",
            "attrtype": 1,
            "spcode": int(self.demospeccode),
            "categorycode": int(self.democategorycode),
        }
        specresult = requests.put(
            "http://127.0.0.1:6543/categoryspecs",
            data=json.dumps(specdata),
            headers=self.header,
        )
        assert specresult.json()["gkstatus"] == 0

    def test_get_all_specs(self):
        result = requests.get(
            "http://127.0.0.1:6543/categoryspecs?categorycode=%d"
            % (int(self.democategorycode)),
            headers=self.header,
        )
        assert result.json()["gkstatus"] == 0
