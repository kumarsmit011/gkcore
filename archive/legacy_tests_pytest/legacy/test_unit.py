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
"Sachin Patil " <sachpatil@openmailbox.org>
"""
import requests, json


class Testunit:
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

    @classmethod
    def teardown_class(self):
        result = requests.delete(
            "http://127.0.0.1:6543/organisations", headers=self.header
        )

    def setup(self):
        gkdata = {"unitname": "test_Mega"}
        result = requests.post(
            "http://127.0.0.1:6543/unitofmeasurement",
            data=json.dumps(gkdata),
            headers=self.header,
        )
        result = requests.get(
            "http://127.0.0.1:6543/unitofmeasurement?qty=all", headers=self.header
        )
        for record in result.json()["gkresult"]:
            if record["unitname"] == "test_Mega":
                self.demoid = record["uomid"]
                break

    def teardown(self):
        gkdata = {"uomid": self.demoid}
        result = requests.delete(
            "http://127.0.0.1:6543/unitofmeasurement",
            data=json.dumps(gkdata),
            headers=self.header,
        )

    def test_create_unit(self):
        gkdata = {"unitname": "test_b"}
        result = requests.post(
            "http://127.0.0.1:6543/unitofmeasurement",
            data=json.dumps(gkdata),
            headers=self.header,
        )
        assert result.json()["gkstatus"] == 0

    def test_create_subunit(self):
        print(self.demoid)
        gkdata = {
            "unitname": "test_c",
            "conversionrate": float(5),
            "subunitof": int(self.demoid),
        }
        result = requests.post(
            "http://127.0.0.1:6543/unitofmeasurement",
            data=json.dumps(gkdata),
            headers=self.header,
        )
        assert result.json()["gkstatus"] == 0

    def test_delete_unit_testc(self):
        gkdata = {"unitname": "test_c"}
        result = requests.get(
            "http://127.0.0.1:6543/unitofmeasurement?qty=all", headers=self.header
        )
        for record in result.json()["gkresult"]:
            if record["unitname"] == "test_c":
                uid = record["uomid"]
                break
        gkdata1 = {"uomid": uid}
        result = requests.delete(
            "http://127.0.0.1:6543/unitofmeasurement",
            data=json.dumps(gkdata1),
            headers=self.header,
        )
        assert result.json()["gkstatus"] == 0

    def test_duplicate_unit(self):
        gkdata = {"unitname": "test_Mega"}
        result = requests.post(
            "http://127.0.0.1:6543/unitofmeasurement",
            data=json.dumps(gkdata),
            headers=self.header,
        )
        assert result.json()["gkstatus"] == 1

    def test_delete_unit_testb(self):
        gkdata = {"unitname": "test_b"}
        result = requests.get(
            "http://127.0.0.1:6543/unitofmeasurement?qty=all", headers=self.header
        )
        for record in result.json()["gkresult"]:
            if record["unitname"] == "test_b":
                uid = record["uomid"]
                break
        gkdata1 = {"uomid": uid}
        result = requests.delete(
            "http://127.0.0.1:6543/unitofmeasurement",
            data=json.dumps(gkdata1),
            headers=self.header,
        )
        assert result.json()["gkstatus"] == 0

    def test_update_unit(self):
        gkdata = {"unitname": "test_giga", "uomid": self.demoid}
        result = requests.put(
            "http://127.0.0.1:6543/unitofmeasurement",
            data=json.dumps(gkdata),
            headers=self.header,
        )
        assert result.json()["gkstatus"] == 0

    def test_get_single_unit(self):
        result = requests.get(
            "http://127.0.0.1:6543/unitofmeasurement?qty=single&uomid=%d"
            % (self.demoid),
            headers=self.header,
        )
        assert result.json()["gkresult"]["unitname"] == "test_Mega"

    def test_get_all_unit(self):
        result = requests.get(
            "http://127.0.0.1:6543/unitofmeasurement?qty=all", headers=self.header
        )
        assert result.json()["gkstatus"] == 0
