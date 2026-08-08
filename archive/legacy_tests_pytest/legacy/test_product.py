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


class TestProducts:
    @classmethod
    def setup_class(self):
        self.prodcode = 0
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
        categorydata = {"categoryname": "Test Category", "subcategoryof": None}
        result = requests.post(
            "http://127.0.0.1:6543/categories",
            data=json.dumps(categorydata),
            headers=self.header,
        )
        result = requests.get("http://127.0.0.1:6543/categories", headers=self.header)
        for record in result.json()["gkresult"]:
            if record["categoryname"] == "Test Category":
                self.democategorycode = record["categorycode"]
                break
        uomdata = {"unitname": "kilogram"}
        result = requests.post(
            "http://127.0.0.1:6543/unitofmeasurement",
            data=json.dumps(uomdata),
            headers=self.header,
        )
        result = requests.get(
            "http://127.0.0.1:6543/unitofmeasurement?qty=all", headers=self.header
        )
        for record in result.json()["gkresult"]:
            if record["unitname"] == "kilogram":
                self.demouomid = record["uomid"]
                break
        specdata = {
            "attrname": "Type",
            "attrtype": 0,
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
            if record["attrname"] == "Type":
                self.demospeccode = record["spcode"]
                break
        proddetails = {
            "productdesc": "Sugar",
            "specs": {self.demospeccode: "Pure"},
            "uomid": self.demouomid,
            "categorycode": self.democategorycode,
        }
        productdetails = {
            "productdetails": proddetails,
            "godetails": None,
            "godownflag": False,
        }
        result = requests.post(
            "http://127.0.0.1:6543/products",
            data=json.dumps(productdetails),
            headers=self.header,
        )
        self.demoproductcode = result.json()["gkresult"]

    def teardown(self):
        result = requests.delete(
            "http://127.0.0.1:6543/products",
            data=json.dumps({"productcode": int(self.demoproductcode)}),
            headers=self.header,
        )
        result = requests.delete(
            "http://127.0.0.1:6543/categoryspecs",
            data=json.dumps({"spcode": int(self.demospeccode)}),
            headers=self.header,
        )
        result = requests.delete(
            "http://127.0.0.1:6543/unitofmeasurement",
            data=json.dumps({"uomid": self.demouomid}),
            headers=self.header,
        )
        gkdata = {"categorycode": self.democategorycode}
        result = requests.delete(
            "http://127.0.0.1:6543/categories",
            data=json.dumps(gkdata),
            headers=self.header,
        )

    def test_createAndDelete_product(self):
        proddetails = {
            "productdesc": "jaggery",
            "specs": {self.demospeccode: "Pure"},
            "uomid": self.demouomid,
            "categorycode": self.democategorycode,
        }
        productdetails = {
            "productdetails": proddetails,
            "godetails": None,
            "godownflag": False,
        }
        result1 = requests.post(
            "http://127.0.0.1:6543/products",
            data=json.dumps(productdetails),
            headers=self.header,
        )
        self.prodcode = result1.json()["gkresult"]
        result = requests.get("http://127.0.0.1:6543/products", headers=self.header)
        for record in result.json()["gkresult"]:
            if record["productdesc"] == "jaggery":
                productcode = record["productcode"]
                break
        result = requests.delete(
            "http://127.0.0.1:6543/products",
            data=json.dumps({"productcode": int(productcode)}),
            headers=self.header,
        )
        assert result.json()["gkstatus"] == 0 and result1.json()["gkstatus"] == 0

    def test_update_product(self):
        proddetails = {
            "productcode": self.demoproductcode,
            "productdesc": "jaggery",
            "specs": {self.demospeccode: "Pure"},
            "uomid": self.demouomid,
            "categorycode": self.democategorycode,
        }
        productdetails = {
            "productdetails": proddetails,
            "godetails": None,
            "godownflag": False,
        }
        result = requests.put(
            "http://127.0.0.1:6543/products",
            data=json.dumps(productdetails),
            headers=self.header,
        )
        assert result.json()["gkstatus"] == 0

    def test_get_single_product(self):
        result = requests.get(
            "http://127.0.0.1:6543/products?qty=single&productcode=%d"
            % (int(self.demoproductcode)),
            headers=self.header,
        )
        assert (
            result.json()["gkstatus"] == 0
            and result.json()["gkresult"]["unitname"] == "kilogram"
            and result.json()["gkresult"]["productdesc"] == "Sugar"
        )

    def test_get_all_products(self):
        result = requests.get("http://127.0.0.1:6543/products", headers=self.header)
        assert result.json()["gkstatus"] == 0

    def test_get_productsFromGodown(self):
        gkdata = {
            "goname": "Test Godown",
            "state": "Maharashtra",
            "goaddr": "Pune",
            "contactname": "Bhavesh Bavdhane",
            "designation": "Designation",
            "gocontact": "8446611103",
        }
        result = requests.post(
            "http://127.0.0.1:6543/godown", data=json.dumps(gkdata), headers=self.header
        )
        result = requests.get("http://127.0.0.1:6543/godown", headers=self.header)
        for record in result.json()["gkresult"]:
            if record["goname"] == "Test Godown":
                self.demogodownid = record["goid"]
                break
        proddetails = {
            "productdesc": "Jaggery",
            "specs": {self.demospeccode: "Pure"},
            "uomid": self.demouomid,
            "categorycode": self.democategorycode,
        }
        productdetails = {
            "productdetails": proddetails,
            "godetails": {self.demogodownid: 100},
            "godownflag": True,
        }
        result1 = requests.post(
            "http://127.0.0.1:6543/products",
            data=json.dumps(productdetails),
            headers=self.header,
        )
        productcode = result1.json()["gkresult"]
        result = requests.get(
            "http://127.0.0.1:6543/products?from=godown&godownid=%d"
            % int(self.demogodownid),
            headers=self.header,
        )
        assert (
            result.json()["gkstatus"] == 0
            and result.json()["gkresult"][0]["goopeningstock"] == "100.00"
            and result.json()["gkresult"][0]["productcode"] == productcode
        )
