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


class TestInvoice:
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
        custdata = {
            "custname": "Jaky Python",
            "custaddr": "goregaon",
            "custphone": "432123",
            "custemail": "jakypython@gmail.com",
            "custfax": "FAX212345",
            "state": "Maharashtra",
            "custpan": "IDPAN1234",
            "custtan": "IDTAN1234",
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
            if record["custname"] == "Jaky Python":
                self.democustid = record["custid"]
                break
        custdata = {
            "custname": "Sachin Khade",
            "custaddr": "goregaon",
            "custphone": "432123",
            "custemail": "sachinkhade@gmail.com",
            "custfax": "FAX212345",
            "state": "Maharashtra",
            "custpan": "IDPAN1234",
            "custtan": "IDTAN1234",
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
            if record["custname"] == "Sachin Khade":
                self.demosuplid = record["custid"]
                break
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
        invoicedata = {
            "invoiceno": "1",
            "taxstate": "Maharashtra",
            "invoicedate": "2016-12-15",
            "tax": {self.demoproductcode: "0.00"},
            "custid": self.democustid,
            "invoicetotal": "10000.00",
            "contents": {self.demoproductcode: {"5000.00": "2"}},
            "issuername": "Bhavesh",
            "designation": "Owner",
        }
        stock = {"inout": "15", "items": {self.demoproductcode: "2"}}
        invoicewholedata = {"invoice": invoicedata, "stock": stock}
        result = requests.post(
            "http://127.0.0.1:6543/invoice",
            data=json.dumps(invoicewholedata),
            headers=self.header,
        )
        self.demoinvoiceid = result.json()["gkresult"]

    @classmethod
    def teardown_class(self):
        result = requests.delete(
            "http://127.0.0.1:6543/invoice",
            data=json.dumps(
                {"invid": self.demoinvoiceid, "cancelflag": 1, "icflag": 9}
            ),
            headers=self.header,
        )
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
        gkdata = {"categorycode": self.democategorycode}
        result = requests.delete(
            "http://127.0.0.1:6543/categories",
            data=json.dumps(gkdata),
            headers=self.header,
        )
        custdata = {"custid": int(self.democustid)}
        result = requests.delete(
            "http://127.0.0.1:6543/customersupplier",
            data=json.dumps(custdata),
            headers=self.header,
        )
        custdata = {"custid": int(self.demosuplid)}
        result = requests.delete(
            "http://127.0.0.1:6543/customersupplier",
            data=json.dumps(custdata),
            headers=self.header,
        )
        result = requests.delete(
            "http://127.0.0.1:6543/organisations", headers=self.header
        )
        result = requests.delete(
            "http://127.0.0.1:6543/unitofmeasurement",
            data=json.dumps({"uomid": self.demouomid}),
            headers=self.header,
        )

    def test_add_delete_invoice(self):
        invoicedata = {
            "invoiceno": "2",
            "taxstate": "Maharashtra",
            "invoicedate": "2016-12-15",
            "tax": {self.demoproductcode: "0.00"},
            "custid": self.democustid,
            "invoicetotal": "10000.00",
            "contents": {self.demoproductcode: {"5000.00": "2"}},
            "issuername": "Akshay",
            "designation": "Owner",
        }
        stock = {"inout": "15", "items": {self.demoproductcode: "2"}}
        invoicewholedata = {"invoice": invoicedata, "stock": stock}
        result = requests.post(
            "http://127.0.0.1:6543/invoice",
            data=json.dumps(invoicewholedata),
            headers=self.header,
        )
        self.invoiceid = result.json()["gkresult"]
        result1 = requests.delete(
            "http://127.0.0.1:6543/invoice",
            data=json.dumps({"invid": self.invoiceid, "cancelflag": 1, "icflag": 9}),
            headers=self.header,
        )
        assert result.json()["gkstatus"] == 0 and result1.json()["gkstatus"] == 0

    def test_getSingle_invoice(self):
        result = requests.get(
            "http://127.0.0.1:6543/invoice?inv=single&invid=%d" % (self.demoinvoiceid),
            headers=self.header,
        )
        invdetails = result.json()["gkresult"]
        assert (
            invdetails["invoiceno"] == "1"
            and invdetails["taxstate"] == "Maharashtra"
            and invdetails["invoicetotal"] == "10000.00"
            and invdetails["issuername"] == "Bhavesh"
            and invdetails["designation"] == "Owner"
        )

    def test_getAll_invoice(self):
        result = requests.get(
            "http://127.0.0.1:6543/invoice?inv=all", headers=self.header
        )
        assert result.json()["gkstatus"] == 0

    def test_getAll_cashMemos(self):
        result = requests.get(
            "http://127.0.0.1:6543/invoice?cash=all", headers=self.header
        )
        assert result.json()["gkstatus"] == 0

    def test_update_invoice(self):
        invoicedata = {
            "invid": self.demoinvoiceid,
            "invoiceno": "3",
            "taxstate": "Punjab",
            "invoicedate": "2016-12-15",
            "tax": {self.demoproductcode: "0.00"},
            "custid": self.democustid,
            "invoicetotal": "10000.00",
            "contents": {self.demoproductcode: {"5000.00": "2"}},
            "issuername": "Ajay",
            "designation": "Clerk",
        }
        stock = {"inout": "15", "items": {self.demoproductcode: "2"}}
        invoicewholedata = {"invoice": invoicedata, "stock": stock}
        result = requests.put(
            "http://127.0.0.1:6543/invoice",
            data=json.dumps(invoicewholedata),
            headers=self.header,
        )
        assert result.json()["gkstatus"] == 0
