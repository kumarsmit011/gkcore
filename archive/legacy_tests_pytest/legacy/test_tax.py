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


class TestTax:
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
        taxdata = {
            "taxname": "VAT",
            "taxrate": float(4.5),
            "categorycode": self.democategorycode,
        }
        taxresult = requests.post(
            "http://127.0.0.1:6543/tax", data=json.dumps(taxdata), headers=self.header
        )
        result = requests.get("http://127.0.0.1:6543/tax", headers=self.header)
        for record in result.json()["gkdata"]:
            if record["taxname"] == "VAT":
                self.demotaxid = record["taxid"]
                break

    def teardown(self):
        deletetaxdata = {"taxid": int(self.demotaxid)}
        deletetaxresult = requests.delete(
            "http://127.0.0.1:6543/tax",
            data=json.dumps(deletetaxdata),
            headers=self.header,
        )
        gkdata = {"categorycode": self.democategorycode}
        result = requests.delete(
            "http://127.0.0.1:6543/categories",
            data=json.dumps(gkdata),
            headers=self.header,
        )

    def test_createAndDelete_tax(self):
        taxdata = {
            "taxname": "CVAT",
            "taxrate": float(4.5),
            "categorycode": self.democategorycode,
        }
        addtaxresult = requests.post(
            "http://127.0.0.1:6543/tax", data=json.dumps(taxdata), headers=self.header
        )
        result = requests.get("http://127.0.0.1:6543/tax", headers=self.header)
        for record in result.json()["gkdata"]:
            if record["taxname"] == "CVAT":
                self.taxid = record["taxid"]
                break
        gkdata1 = {"taxid": self.taxid}
        deletetaxresult = requests.delete(
            "http://127.0.0.1:6543/tax", data=json.dumps(gkdata1), headers=self.header
        )
        assert (
            deletetaxresult.json()["gkstatus"] == 0
            and addtaxresult.json()["gkstatus"] == 0
        )

    def test_update_tax(self):
        taxdata = {
            "taxid": self.demotaxid,
            "taxname": "CVAT",
            "taxrate": float(4.5),
            "categorycode": self.democategorycode,
        }
        taxresult = requests.put(
            "http://127.0.0.1:6543/tax", data=json.dumps(taxdata), headers=self.header
        )
        assert taxresult.json()["gkstatus"] == 0

    def test_get_all_taxes(self):
        result = requests.get("http://127.0.0.1:6543/tax", headers=self.header)
        assert result.json()["gkstatus"] == 0
