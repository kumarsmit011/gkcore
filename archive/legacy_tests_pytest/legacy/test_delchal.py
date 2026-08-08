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


class TestDelChal:
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

        """ User creation """
        """ Check and delete the user creation if it's not being used! """
        userdata = {
            "username": "user",
            "userpassword": "passwd",
            "userrole": 0,
            "userquestion": "what is my pet name?",
            "useranswer": "cat",
        }
        result = requests.post(
            "http://127.0.0.1:6543/users",
            data=json.dumps(userdata),
            headers=self.header,
        )
        result = requests.get("http://127.0.0.1:6543/users", headers=self.header)
        for record in result.json()["gkresult"]:
            if record["username"] == "user":
                self.userid = record["userid"]
                break

        """ Customer and Supplier creation """
        """ Doubt: This should be a customer or supplier? I have created both!"""
        custdata = {
            "custname": "customer",
            "custaddr": "goregaon",
            "custphone": "22432123",
            "custemail": "customer@gmail.com",
            "custfax": "FAXCUST212345",
            "state": "Maharashtra",
            "custpan": "CUSTPAN1234",
            "custtan": "CUSTTAN1234",
            "csflag": 3,
        }
        result = requests.post(
            "http://127.0.0.1:6543/customersupplier",
            data=json.dumps(custdata),
            headers=self.header,
        )
        result = requests.get(
            "http://127.0.0.1:6543/customersupplier?qty=custall", headers=self.header
        )
        for record in result.json()["gkresult"]:
            if record["custname"] == "customer":
                self.custid = record["custid"]
                break

        """ supid is used to store custid attribute """
        custdata = {
            "custname": "supplier",
            "custaddr": "borivali",
            "custphone": "44432123",
            "custemail": "supplier@gmail.com",
            "custfax": "FAXSUP212345",
            "state": "Maharashtra",
            "custpan": "SUPPAN1234",
            "custtan": "SUPTAN1234",
            "csflag": 19,
        }
        result = requests.post(
            "http://127.0.0.1:6543/customersupplier",
            data=json.dumps(custdata),
            headers=self.header,
        )
        result = requests.get(
            "http://127.0.0.1:6543/customersupplier?qty=supall", headers=self.header
        )
        for record in result.json()["gkresult"]:
            if record["custname"] == "supplier":
                self.supid = record["custid"]
                break

        """ setup() is also combined with setup_class()"""
        """ Product Creation """
        categorydata = {"categoryname": "Test Category", "subcategoryof": None}
        result = requests.post(
            "http://127.0.0.1:6543/categories",
            data=json.dumps(categorydata),
            headers=self.header,
        )
        print("categories creation: ", result.json()["gkstatus"])
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
        print("unitofmeasurement creation: ", result.json()["gkstatus"])
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
        print("category-specs creation: ", result.json()["gkstatus"])
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
        print("product creation: ", result.json()["gkstatus"])
        self.demoproductcode = result.json()["gkresult"]

        """ Creating Delchallan """
        """ In this testcase, godown is not linked with Delivery Challan """
        self.qty = 1
        products = {self.demoproductcode: self.qty}
        delchaldata = {
            "custid": self.custid,
            "dcno": "15",
            "dcdate": "2016-03-30",
            "dcflag": 16,
            "noofpackages": 2,
            "modeoftransport": "By Road",
        }
        """ inout = 9 means stock is IN and inout = 15 means stock is OUT """
        stockdata = {"inout": 9, "items": products}
        self.demo_delchalwholedata = {
            "delchaldata": delchaldata,
            "stockdata": stockdata,
        }
        result = requests.post(
            "http://127.0.0.1:6543/delchal",
            data=json.dumps(self.demo_delchalwholedata),
            headers=self.header,
        )
        print("delchal creation: ", result.json()["gkstatus"])
        result = requests.get(
            "http://127.0.0.1:6543/delchal?delchal=all", headers=self.header
        )
        for record in result.json()["gkresult"]:
            if record["dcno"] == "15":
                self.demo_delchalid = record["dcid"]
                break

    @classmethod
    def teardown_class(self):
        """Actually no need to do all this before deleting an organisation. Since, organisation can be deleted directly which deltes all the data underneath it. Still we have done."""
        deldata = {"dcid": self.demo_delchalid, "cancelflag": 1}
        result = requests.delete(
            "http://127.0.0.1:6543/delchal",
            data=json.dumps(deldata),
            headers=self.header,
        )
        print("delchal delete: ", result.json()["gkstatus"])
        result = requests.delete(
            "http://127.0.0.1:6543/products",
            data=json.dumps({"productcode": int(self.demoproductcode)}),
            headers=self.header,
        )
        print("products delete: ", result.json()["gkstatus"])
        result = requests.delete(
            "http://127.0.0.1:6543/categoryspecs",
            data=json.dumps({"spcode": int(self.demospeccode)}),
            headers=self.header,
        )
        print("categoryspecs delete: ", result.json()["gkstatus"])
        gkdata = {"categorycode": self.democategorycode}
        result = requests.delete(
            "http://127.0.0.1:6543/categories",
            data=json.dumps(gkdata),
            headers=self.header,
        )
        print("categories delete: ", result.json()["gkstatus"])
        result = requests.delete(
            "http://127.0.0.1:6543/organisations", headers=self.header
        )
        print("organisations delete: ", result.json()["gkstatus"])
        result = requests.delete(
            "http://127.0.0.1:6543/unitofmeasurement",
            data=json.dumps({"uomid": self.demouomid}),
            headers=self.header,
        )
        print("unitofmeasurement delete: ", result.json()["gkstatus"])

    def test_create_and_delete_delchal(self):
        """Create and Delete Delivery Challan"""
        """
			IMP Doubt: In this testcase, godown is not linked with Delivery Challan
			So, how it gets the quantity? and how and where it gets stored in the database table stock?
		"""
        """ Create Delivery Challan """
        qty = 2
        products = {self.demoproductcode: qty}
        delchaldata = {
            "custid": self.custid,
            "dcno": "30",
            "dcdate": "2016-03-10",
            "dcflag": 3,
            "noofpackages": 2,
            "modeoftransport": "By Road",
        }
        """ 'inout = 9' means stock is IN and 'inout = 15' means stock is OUT """
        stockdata = {"inout": 9, "items": products}
        delchalwholedata = {"delchaldata": delchaldata, "stockdata": stockdata}
        result = requests.post(
            "http://127.0.0.1:6543/delchal",
            data=json.dumps(delchalwholedata),
            headers=self.header,
        )

        """ Delete Delivery Challan """
        delchals = requests.get(
            "http://127.0.0.1:6543/delchal?delchal=all", headers=self.header
        )
        for record in delchals.json()["gkresult"]:
            if record["dcno"] == "30":
                self.delchalid = record["dcid"]
                break
        deldata = {"dcid": self.delchalid, "cancelflag": 1}
        result = requests.delete(
            "http://127.0.0.1:6543/delchal",
            data=json.dumps(deldata),
            headers=self.header,
        )
        print("delchal: status ", result.json()["gkstatus"])
        assert result.json()["gkstatus"] == 0

    def test_update_delchal(self):
        delchalwholedata = self.demo_delchalwholedata
        delchaldata = delchalwholedata["delchaldata"]
        delchaldata["dcid"] = self.demo_delchalid
        stockdata = delchalwholedata["stockdata"]
        delchaldata["dcno"] = 16
        delchaldata["dcdate"] = "2016-03-29"
        result = requests.put(
            "http://127.0.0.1:6543/delchal",
            data=json.dumps(delchalwholedata),
            headers=self.header,
        )
        assert result.json()["gkstatus"] == 0

    def test_get_all_delchal(self):
        delchals = requests.get(
            "http://127.0.0.1:6543/delchal?delchal=all", headers=self.header
        )
        assert delchals.json()["gkstatus"] == 0

    def test_get_single_delchal(self):
        delchaldata = requests.get(
            "http://127.0.0.1:6543/delchal?delchal=single&dcid=%d"
            % (int(self.demo_delchalid)),
            headers=self.header,
        )
        result = delchaldata.json()["gkresult"]
        dc = result["delchaldata"]
        stock = result["stockdata"]
        assert (
            dc["dcno"] == "15"
            and dc["dcflag"] == 16
            and dc["dcdate"] == "30-03-2016"
            and dc["custid"] == self.custid
        )

    def test_getLastDelChalDetails(self):
        qty = 2
        products = {self.demoproductcode: qty}
        delchaldata = {
            "custid": self.custid,
            "dcno": "31",
            "dcdate": "2016-03-10",
            "dcflag": 4,
            "noofpackages": 2,
            "modeoftransport": "By Road",
        }
        """ 'inout = 9' means stock is IN and 'inout = 15' means stock is OUT """
        stockdata = {"inout": 9, "items": products}
        delchalwholedata = {"delchaldata": delchaldata, "stockdata": stockdata}
        result = requests.post(
            "http://127.0.0.1:6543/delchal",
            data=json.dumps(delchalwholedata),
            headers=self.header,
        )
        delchaldata = {
            "custid": self.custid,
            "dcno": "32",
            "dcdate": "2016-03-10",
            "dcflag": 4,
            "noofpackages": 2,
            "modeoftransport": "By Road",
        }
        stockdata = {"inout": 9, "items": products}
        delchalwholedata = {"delchaldata": delchaldata, "stockdata": stockdata}
        result = requests.post(
            "http://127.0.0.1:6543/delchal",
            data=json.dumps(delchalwholedata),
            headers=self.header,
        )
        """ two delivery challan entries made and now trying to fetch last made entry """
        delchaldata = requests.get(
            "http://127.0.0.1:6543/delchal?delchal=last&dcflag=4", headers=self.header
        )
        assert (
            delchaldata.json()["gkresult"]["dcno"] == "32"
            and delchaldata.json()["gkresult"]["dcdate"] == "10-03-2016"
        )
