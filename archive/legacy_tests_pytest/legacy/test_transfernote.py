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


class TestTransferNote:
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
        gkdata = {
            "goname": "From Godown",
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
            if record["goname"] == "From Godown":
                self.fromgodownid = record["goid"]
                break
        proddetails = {
            "productdesc": "Sugar",
            "specs": {self.demospeccode: "Pure"},
            "uomid": self.demouomid,
            "categorycode": self.democategorycode,
        }
        productdetails = {
            "productdetails": proddetails,
            "godetails": {self.fromgodownid: 100},
            "godownflag": True,
        }
        result = requests.post(
            "http://127.0.0.1:6543/products",
            data=json.dumps(productdetails),
            headers=self.header,
        )
        self.demoproductcode = result.json()["gkresult"]
        gkdata = {
            "goname": "To Godown",
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
            if record["goname"] == "To Godown":
                self.togodownid = record["goid"]
                break
        transferdata = {
            "transfernoteno": "1",
            "transfernotedate": "2016-12-15",
            "nopkt": 1,
            "togodown": self.togodownid,
            "transportationmode": "Direct",
            "issuername": "Bhavesh",
            "designation": "Owner",
        }
        products = {self.demoproductcode: 5}
        stockdata = {"goid": self.fromgodownid, "items": products}
        tnwholedata = {"transferdata": transferdata, "stockdata": stockdata}
        result = requests.post(
            "http://127.0.0.1:6543/transfernote",
            data=json.dumps(tnwholedata),
            headers=self.header,
        )
        result = requests.get(
            "http://127.0.0.1:6543/transfernote?tn=all", headers=self.header
        )
        for record in result.json()["gkresult"]:
            if record["transfernoteno"] == "1":
                self.demotransfernoteid = record["transfernoteid"]
                break

    @classmethod
    def teardown_class(self):
        dataset = {"transfernoteid": int(self.demotransfernoteid), "cancelflag": 1}
        result = requests.delete(
            "http://127.0.0.1:6543/transfernote",
            data=json.dumps(dataset),
            headers=self.header,
        )
        # result = requests.delete("http://127.0.0.1:6543/products", data=json.dumps({"productcode":int(self.demoproductcode)}),headers=self.header)
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
        gkdata = {"goid": self.fromgodownid}
        result = requests.delete(
            "http://127.0.0.1:6543/godown", data=json.dumps(gkdata), headers=self.header
        )
        gkdata = {"goid": self.togodownid}
        result = requests.delete(
            "http://127.0.0.1:6543/godown", data=json.dumps(gkdata), headers=self.header
        )
        result = requests.delete(
            "http://127.0.0.1:6543/organisations", headers=self.header
        )
        result = requests.delete(
            "http://127.0.0.1:6543/unitofmeasurement",
            data=json.dumps({"uomid": self.demouomid}),
            headers=self.header,
        )

    def test_createAndDelete_transfernote(self):
        transferdata = {
            "transfernoteno": "2",
            "transfernotedate": "2016-12-15",
            "nopkt": 1,
            "togodown": self.togodownid,
            "transportationmode": "Direct",
            "issuername": "Bhavesh",
            "designation": "Owner",
        }
        products = {self.demoproductcode: 3}
        stockdata = {"goid": self.fromgodownid, "items": products}
        tnwholedata = {"transferdata": transferdata, "stockdata": stockdata}
        resultCreate = requests.post(
            "http://127.0.0.1:6543/transfernote",
            data=json.dumps(tnwholedata),
            headers=self.header,
        )
        result = requests.get(
            "http://127.0.0.1:6543/transfernote?tn=all", headers=self.header
        )
        for record in result.json()["gkresult"]:
            if record["transfernoteno"] == "2":
                self.transfernoteid = record["transfernoteid"]
                break
        dataset = {"transfernoteid": int(self.transfernoteid), "cancelflag": 1}
        resultDelete = requests.delete(
            "http://127.0.0.1:6543/transfernote",
            data=json.dumps(dataset),
            headers=self.header,
        )
        assert (
            resultCreate.json()["gkstatus"] == 0
            and resultDelete.json()["gkstatus"] == 0
        )

    def test_get_single_transfernote(self):
        result = requests.get(
            "http://127.0.0.1:6543/transfernote?tn=single&transfernoteid=%d"
            % (int(self.demotransfernoteid)),
            headers=self.header,
        )
        assert (
            result.json()["gkresult"]["transfernoteno"] == "1"
            and result.json()["gkresult"]["nopkt"] == 1
            and result.json()["gkresult"]["issuername"] == "Bhavesh"
            and result.json()["gkresult"]["designation"] == "Owner"
        )

    def test_get_all_transfernote(self):
        result = requests.get(
            "http://127.0.0.1:6543/transfernote?tn=all", headers=self.header
        )
        assert result.json()["gkstatus"] == 0

    def test_received_transfernote(self):
        dataset = {"transfernoteid": int(self.demotransfernoteid)}
        result = requests.put(
            "http://127.0.0.1:6543/transfernote?received=true",
            data=json.dumps(dataset),
            headers=self.header,
        )
        assert result.json()["gkstatus"] == 0

    def test_update_transfernote(self):
        transferdata = {
            "transfernoteno": 4,
            "transfernotedate": "2016-12-15",
            "nopkt": 5,
            "transfernoteid": self.demotransfernoteid,
            "togodown": self.togodownid,
            "transportationmode": "Direct",
            "issuername": "Mohan",
            "designation": "Clerk",
        }
        products = {self.demoproductcode: 3}
        stockdata = {"goid": self.fromgodownid, "items": products}
        tnwholedata = {"transferdata": transferdata, "stockdata": stockdata}
        result = requests.put(
            "http://127.0.0.1:6543/transfernote",
            data=json.dumps(tnwholedata),
            headers=self.header,
        )
        assert result.json()["gkstatus"] == 0
