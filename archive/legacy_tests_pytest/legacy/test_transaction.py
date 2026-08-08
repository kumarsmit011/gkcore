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


class TestTransaction:
    @classmethod
    def setup_class(self):
        """Organization Initialization Data"""
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

        """ Project Initialization Data """
        gkdata = {"projectname": "dff", "sanctionedamount": float(5000)}
        result = requests.post(
            "http://127.0.0.1:6543/projects",
            data=json.dumps(gkdata),
            headers=self.header,
        )
        result = requests.get("http://127.0.0.1:6543/projects", headers=self.header)
        for record in result.json()["gkresult"]:
            if record["projectname"] == "dff":
                self.projectcode = record["projectcode"]
                break

        """ Invoice Initialization Data """
        """ Customer Initialization Data """
        """
		custdata = {"custname":"rahul kande","custaddr":"goregaon","custphone":"432123","custemail":"rahulkande@gmail.com","custfax":"FAX212345","state":"Maharashtra","custpan":"IDPAN1234","custtan":"IDTAN1234","csflag":3}
		result = requests.post("http://127.0.0.1:6543/customersupplier",data=json.dumps(custdata),headers=self.header)
		result = requests.get("http://127.0.0.1:6543/customersupplier?qty=custall", headers=self.header)
		for record in result.json()["gkresult"]:
			if record["custname"] == "rahul kande":
				self.custid = record["custid"]
				break
		"""

    @classmethod
    def teardown_class(self):
        result = requests.delete(
            "http://127.0.0.1:6543/organisations", headers=self.header
        )

    def setup(self):
        """Initialization of a group-subgroup"""
        result = requests.get(
            "http://127.0.0.1:6543/groupsubgroups", headers=self.header
        )
        for record in result.json()["gkresult"]:
            if record["groupname"] == "Current Assets":
                self.demo_groupcode = record["groupcode"]
                break

        result = requests.get(
            "http://127.0.0.1:6543/groupDetails/%s" % (self.demo_groupcode),
            headers=self.header,
        )
        for record in result.json()["gkresult"]:
            if record["subgroupname"] == "Bank":
                self.demo_grpcode = record["groupcode"]
                break

        """ Initialization of two Accounts for creating a voucher """
        gkdata = {
            "accountname": "Bank Of India",
            "openingbal": 500,
            "groupcode": self.demo_grpcode,
        }
        result = requests.post(
            "http://127.0.0.1:6543/accounts",
            data=json.dumps(gkdata),
            headers=self.header,
        )
        # print result.json()["gkstatus"], "India status"
        result = requests.get("http://127.0.0.1:6543/accounts", headers=self.header)
        for record in result.json()["gkresult"]:
            if record["accountname"] == "Bank Of India":
                # print result.json()["gkstatus"], "Bank of India"
                self.demo_accountcode1 = record["accountcode"]
                break

        gkdata = {
            "accountname": "Bank Of Badoda",
            "openingbal": 1000,
            "groupcode": self.demo_grpcode,
        }
        result = requests.post(
            "http://127.0.0.1:6543/accounts",
            data=json.dumps(gkdata),
            headers=self.header,
        )
        # print result.json()["gkstatus"], "Badoda status"
        result = requests.get("http://127.0.0.1:6543/accounts", headers=self.header)
        for record in result.json()["gkresult"]:
            if record["accountname"] == "Bank Of Badoda":
                # print result.json()["gkstatus"], "Bank of Badoda"
                self.demo_accountcode2 = record["accountcode"]
                break

        """ Preparing gkdata to pass to Create Voucher """
        drs = {self.demo_accountcode1: 100}
        crs = {self.demo_accountcode2: 100}
        gkdata = {
            "invid": None,
            "vouchernumber": 100,
            "voucherdate": "2016-03-30",
            "narration": "Demo Narration",
            "drs": drs,
            "crs": crs,
            "vouchertype": "purchase",
            "projectcode": int(self.projectcode),
        }
        result = requests.post(
            "http://127.0.0.1:6543/transaction",
            data=json.dumps(gkdata),
            headers=self.header,
        )
        # print "gkstatus: post ", result.json()["gkstatus"]

        vnum = "100"  # string or integer?
        searchby = "vnum"
        result = requests.get(
            "http://127.0.0.1:6543/transaction?searchby=%s&voucherno=%s"
            % (searchby, vnum),
            headers=self.header,
        )
        # print "gkstatus: get ", result.json()["gkstatus"]
        # print "list: ", result.json()["gkresult"]
        self.demo_vouchercode = result.json()["gkresult"][0]["vouchercode"]

    def teardown(self):
        """Check if this order of deleting is correct?"""
        gkdata = {"vouchercode": self.demo_vouchercode}
        result = requests.delete(
            "http://127.0.0.1:6543/transaction",
            data=json.dumps(gkdata),
            headers=self.header,
        )
        print("gkstatus voucher delete: ", result.json()["gkstatus"])

        gkdata = {"accountcode": self.demo_accountcode1}
        result = requests.delete(
            "http://127.0.0.1:6543/accounts",
            data=json.dumps(gkdata),
            headers=self.header,
        )
        print("gkstatus acc 1 delete: ", result.json()["gkstatus"])

        gkdata = {"accountcode": self.demo_accountcode2}
        result = requests.delete(
            "http://127.0.0.1:6543/accounts",
            data=json.dumps(gkdata),
            headers=self.header,
        )
        print("gkstatus acc 2 delete: ", result.json()["gkstatus"])

    def test_create_and_delete_voucher(self):
        """Create and Delete Voucher Code"""

        """ Create voucher """
        """ Initialization of two Accounts for creating a voucher """
        gkdata = {
            "accountname": "India Bank",
            "openingbal": 500,
            "groupcode": self.demo_grpcode,
        }
        result = requests.post(
            "http://127.0.0.1:6543/accounts",
            data=json.dumps(gkdata),
            headers=self.header,
        )
        print("acc 1 create: ", result.json()["gkstatus"])

        result = requests.get("http://127.0.0.1:6543/accounts", headers=self.header)
        for record in result.json()["gkresult"]:
            if record["accountname"] == "India Bank":
                self.accountcode1 = record["accountcode"]
                break

        gkdata = {
            "accountname": "Badoda Bank",
            "openingbal": 1000,
            "groupcode": self.demo_grpcode,
        }
        result = requests.post(
            "http://127.0.0.1:6543/accounts",
            data=json.dumps(gkdata),
            headers=self.header,
        )
        print("acc 2 create: ", result.json()["gkstatus"])
        result = requests.get("http://127.0.0.1:6543/accounts", headers=self.header)
        for record in result.json()["gkresult"]:
            if record["accountname"] == "Badoda Bank":
                self.accountcode2 = record["accountcode"]
                break

        drs = {self.accountcode1: 200}
        crs = {self.accountcode2: 200}
        self.vouchernumber = 111
        gkdata = {
            "invid": None,
            "attachment": None,
            "attachmentcount": 0,
            "vouchernumber": self.vouchernumber,
            "voucherdate": "2016-03-20",
            "narration": "Test Narration",
            "drs": drs,
            "crs": crs,
            "vouchertype": "purchase",
            "projectcode": int(self.projectcode),
        }
        result_post = requests.post(
            "http://127.0.0.1:6543/transaction",
            data=json.dumps(gkdata),
            headers=self.header,
        )
        print("voucher create: ", result_post.json()["gkstatus"])

        """ Delete voucher """
        vnum = "111"  # string or integer?
        searchby = "vnum"
        result = requests.get(
            "http://127.0.0.1:6543/transaction?searchby=%s&voucherno=%s"
            % (searchby, vnum),
            headers=self.header,
        )
        vouchercode = result.json()["gkresult"][0]["vouchercode"]
        gkdata = {"vouchercode": vouchercode}
        result_delete = requests.delete(
            "http://127.0.0.1:6543/transaction",
            data=json.dumps(gkdata),
            headers=self.header,
        )
        print("voucher delete: ", result_delete.json()["gkstatus"])

        gkdata = {"accountcode": self.accountcode1}
        result = requests.delete(
            "http://127.0.0.1:6543/accounts",
            data=json.dumps(gkdata),
            headers=self.header,
        )
        print("acc 1 delete: ", result.json()["gkstatus"])

        gkdata = {"accountcode": self.accountcode2}
        result = requests.delete(
            "http://127.0.0.1:6543/accounts",
            data=json.dumps(gkdata),
            headers=self.header,
        )
        print("acc 2 delete: ", result.json()["gkstatus"])

        assert (
            result_post.json()["gkstatus"] == 0
            and result_delete.json()["gkstatus"] == 0
            and result.json()["gkstatus"] == 0
        )

    def test_update_voucher(self):
        drs = {self.demo_accountcode2: 66}
        crs = {self.demo_accountcode1: 66}
        gkdata = {
            "vouchercode": self.demo_vouchercode,
            "narration": "Updated Demo Narration",
            "drs": drs,
            "crs": crs,
        }
        result = requests.put(
            "http://127.0.0.1:6543/transaction",
            data=json.dumps(gkdata),
            headers=self.header,
        )
        assert result.json()["gkstatus"] == 0

    def test_get_voucher(self):
        result = requests.get(
            "http://127.0.0.1:6543/transaction?code=%d" % (int(self.demo_vouchercode)),
            headers=self.header,
        )
        v = result.json()["gkresult"]
        # print v
        drs = {"Bank Of India": 100}
        crs = {"Bank Of Badoda": 100}
        assert (
            result.json()["gkstatus"] == 0
            and v["invid"] == None
            and v["vouchernumber"] == "100"
            and v["voucherdate"] == "30-03-2016"
            and v["narration"] == "Demo Narration"
            and v["vouchertype"] == "purchase"
            and v["project"] == int(self.projectcode)
            and cmp(v["drs"], drs) == 0
            and cmp(v["crs"], crs) == 0
        )

    def test_get_last_voucher_details(self):
        vouchertype = "purchase"
        result = requests.get(
            "http://127.0.0.1:6543/transaction?details=last&type=%s" % (vouchertype),
            headers=self.header,
        )
        voucherdetails = result.json()["gkresult"]
        assert (
            result.json()["gkstatus"] == 0
            and voucherdetails["vno"] == "100"
            and voucherdetails["vdate"] == "30-03-2016"
        )

    def test_search_by_voucher_type(self):
        searchby = "type"
        vtype = "purchase"
        result = requests.get(
            "http://127.0.0.1:6543/transaction?searchby=%s&vouchertype=%s"
            % (searchby, vtype),
            headers=self.header,
        )
        assert result.json()["gkstatus"] == 0

    def test_search_by_voucher_number(self):
        searchby = "vnum"
        vnum = "100"
        result = requests.get(
            "http://127.0.0.1:6543/transaction?searchby=%s&voucherno=%s"
            % (searchby, vnum),
            headers=self.header,
        )
        assert result.json()["gkstatus"] == 0

    def test_search_by_voucher_amount(self):
        searchby = "amount"
        amt = "100"
        result = requests.get(
            "http://127.0.0.1:6543/transaction?searchby=%s&total=%s" % (searchby, amt),
            headers=self.header,
        )
        assert result.json()["gkstatus"] == 0

    def test_search_by_voucher_date(self):
        searchby = "date"
        vfrom = "2015-05-01"
        vto = "2016-03-31"
        result = requests.get(
            "http://127.0.0.1:6543/transaction?searchby=%s&from=%s&to=%s"
            % (searchby, vfrom, vto),
            headers=self.header,
        )
        assert result.json()["gkstatus"] == 0

    def test_search_by_voucher_narration(self):
        searchby = "narration"
        nar = "Demo Narration"
        result = requests.get(
            "http://127.0.0.1:6543/transaction?searchby=%s&nartext=%s"
            % (searchby, nar),
            headers=self.header,
        )
        assert result.json()["gkstatus"] == 0
