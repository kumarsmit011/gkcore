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


class TestReports:
    @classmethod
    def setup_class(self):
        orgdata = {
            "orgdetails": {
                "orgname": "Test Organisation",
                "yearend": "2017-03-31",
                "yearstart": "2016-04-01",
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
        """ Initialization of a group-subgroup """
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
        result = requests.get("http://127.0.0.1:6543/accounts", headers=self.header)
        for record in result.json()["gkresult"]:
            if record["accountname"] == "Bank Of India":
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
        result = requests.get("http://127.0.0.1:6543/accounts", headers=self.header)
        for record in result.json()["gkresult"]:
            if record["accountname"] == "Bank Of Badoda":
                self.demo_accountcode2 = record["accountcode"]
                break
        """ Preparing gkdata to pass to Create Voucher """
        drs = {self.demo_accountcode1: 100}
        crs = {self.demo_accountcode2: 100}
        gkdata = {
            "invid": None,
            "vouchernumber": 100,
            "voucherdate": "2016-12-16",
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
        result = requests.get(
            "http://127.0.0.1:6543/transaction?searchby=vnum&voucherno=100",
            headers=self.header,
        )
        self.demo_vouchercode = result.json()["gkresult"][0]["vouchercode"]

    @classmethod
    def teardown_class(self):
        gkdata = {"vouchercode": self.demo_vouchercode}
        result = requests.delete(
            "http://127.0.0.1:6543/transaction",
            data=json.dumps(gkdata),
            headers=self.header,
        )
        gkdata = {"projectcode": self.projectcode}
        result = requests.delete(
            "http://127.0.0.1:6543/projects",
            data=json.dumps(gkdata),
            headers=self.header,
        )
        gkdata = {"accountcode": self.demo_accountcode1}
        result = requests.delete(
            "http://127.0.0.1:6543/accounts",
            data=json.dumps(gkdata),
            headers=self.header,
        )
        gkdata = {"accountcode": self.demo_accountcode2}
        result = requests.delete(
            "http://127.0.0.1:6543/accounts",
            data=json.dumps(gkdata),
            headers=self.header,
        )
        result = requests.delete(
            "http://127.0.0.1:6543/organisations", headers=self.header
        )

    def test_monthly_ledger(self):
        result = requests.get(
            "http://127.0.0.1:6543/report?type=monthlyledger&accountcode=%d"
            % (self.demo_accountcode1),
            headers=self.header,
        )
        monthlyledger = result.json()["gkresult"]
        assert (
            result.json()["gkstatus"] == 0
            and monthlyledger[0]["month"] == "April"
            and monthlyledger[0]["Dr"] == "500.00"
            and monthlyledger[8]["month"] == "December"
            and monthlyledger[8]["Dr"] == "600.00"
            and monthlyledger[8]["vcount"] == 1
        )

    def test_ledger(self):
        drs = {self.demo_accountcode1: 10}
        crs = {self.demo_accountcode2: 10}
        gkdata = {
            "invid": None,
            "vouchernumber": 101,
            "voucherdate": "2016-12-16",
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
        result = requests.get(
            "http://127.0.0.1:6543/transaction?searchby=vnum&voucherno=101",
            headers=self.header,
        )
        vcode = result.json()["gkresult"][0]["vouchercode"]
        result1 = requests.get(
            "http://127.0.0.1:6543/report?type=ledger&accountcode=%d&calculatefrom=%s&calculateto=%s&financialstart=%s&projectcode=%d"
            % (
                self.demo_accountcode1,
                "2016-04-01",
                "2017-03-31",
                "2016-04-01",
                int(self.projectcode),
            ),
            headers=self.header,
        )
        ledger = result1.json()["gkresult"]
        gkdata = {"vouchercode": vcode}
        result = requests.delete(
            "http://127.0.0.1:6543/transaction",
            data=json.dumps(gkdata),
            headers=self.header,
        )
        assert (
            result1.json()["gkstatus"] == 0
            and ledger[0]["vouchernumber"] == "100"
            and ledger[0]["vouchertype"] == "purchase"
            and ledger[0]["Dr"] == "100.00"
            and ledger[1]["vouchernumber"] == "101"
            and ledger[1]["vouchertype"] == "purchase"
            and ledger[1]["Dr"] == "10.00"
            and ledger[2]["Dr"] == "110.00"
            and ledger[2]["particulars"][0] == "Total of Transactions"
        )

    def test_crdrledger(self):
        CrOK = False
        DrOK = False
        result = requests.get(
            "http://127.0.0.1:6543/report?type=crdrledger&accountcode=%d&calculatefrom=%s&calculateto=%s&financialstart=%s&projectcode=&side=%s"
            % (self.demo_accountcode2, "2016-04-01", "2017-03-31", "2016-04-01", "cr"),
            headers=self.header,
        )
        crdata = result.json()["gkresult"]
        if (
            crdata[0]["vouchernumber"] == "100"
            and crdata[0]["Cr"] == "100.00"
            and crdata[0]["particulars"][0] == "Bank Of India"
        ):
            CrOK = True
        result = requests.get(
            "http://127.0.0.1:6543/report?type=crdrledger&accountcode=%d&calculatefrom=%s&calculateto=%s&financialstart=%s&projectcode=&side=%s"
            % (self.demo_accountcode1, "2016-04-01", "2017-03-31", "2016-04-01", "dr"),
            headers=self.header,
        )
        drdata = result.json()["gkresult"]
        if (
            drdata[0]["vouchernumber"] == "100"
            and drdata[0]["Dr"] == "100.00"
            and drdata[0]["particulars"][0] == "Bank Of Badoda"
        ):
            DrOK = True
        assert CrOK == True and DrOK == True

    def test_netTrialBalance(self):
        result = requests.get(
            "http://127.0.0.1:6543/report?type=nettrialbalance&calculateto=%s&financialstart=%s"
            % ("2017-03-31", "2016-04-01"),
            headers=self.header,
        )
        nettrialdata = result.json()["gkresult"]
        testResult = False
        testcount = 0
        for record in nettrialdata:
            if record["accountcode"] == self.demo_accountcode1:
                if (
                    record["Dr"] == "600.00"
                    and record["accountname"] == "Bank Of India"
                ):
                    testcount += 1
                    testResult = True
                else:
                    testResult = False
            if record["accountcode"] == self.demo_accountcode2:
                if (
                    record["Dr"] == "900.00"
                    and record["accountname"] == "Bank Of Badoda"
                ):
                    testcount += 1
                    testResult = True
                else:
                    testResult = False
            if record["accountname"] == "Total":
                if record["Dr"] == "1500.00":
                    testcount += 1
                    testResult = True
                else:
                    testResult = False
            if record["accountname"] == "Difference in Trial balance":
                if record["Cr"] == "1500.00":
                    testcount += 1
                    testResult = True
                else:
                    testResult = False
        assert testResult == True and testcount == 4

    """
		This is not tested with input and returned data Because this module is not used anywhere
		To generate grosstrialbalance report extendedtrialbalance() method is used and it has been modified to work with this.
	"""

    def test_grossTrialBalance(self):
        result = requests.get(
            "http://127.0.0.1:6543/report?type=grosstrialbalance&calculateto=%s&financialstart=%s"
            % ("2017-03-31", "2016-04-01"),
            headers=self.header,
        )
        assert result.json()["gkstatus"] == 0

    def test_extendedTrialBalance(self):
        result = requests.get(
            "http://127.0.0.1:6543/report?type=extendedtrialbalance&calculateto=%s&financialstart=%s"
            % ("2017-03-31", "2016-04-01"),
            headers=self.header,
        )
        extdata = result.json()["gkresult"]
        testResult = False
        testcount = 0
        for record in extdata:
            if record["accountcode"] == self.demo_accountcode1:
                if (
                    record["accountname"] == "Bank Of India"
                    and record["totaldr"] == "100.00"
                    and record["curbaldr"] == "600.00"
                    and record["openingbalance"] == "500.00(Dr)"
                ):
                    testcount += 1
                    testResult = True
                else:
                    testResult = False
            if record["accountcode"] == self.demo_accountcode2:
                if (
                    record["accountname"] == "Bank Of Badoda"
                    and record["totalcr"] == "100.00"
                    and record["curbaldr"] == "900.00"
                    and record["openingbalance"] == "1000.00(Dr)"
                ):
                    testcount += 1
                    testResult = True
                else:
                    testResult = False
            if record["accountname"] == "Total":
                if record["totalcr"] == "100.00":
                    testcount += 1
                    testResult = True
                else:
                    testResult = False
            if record["accountname"] == "Difference in Trial Balance":
                if record["curbalcr"] == "1500.00":
                    testcount += 1
                    testResult = True
                else:
                    testResult = False
        assert testResult == True and testcount == 4

    def test_cashflow(self):
        result = requests.get(
            "http://127.0.0.1:6543/report?type=cashflow&calculateto=%s&financialstart=%s&calculatefrom=%s"
            % (
                "2017-03-31",
                "2016-04-01",
                "2016-04-01",
            ),
            headers=self.header,
        )
        receiptcashdata = result.json()["rcgkresult"]
        paymentcashdata = result.json()["pygkresult"]
        testResult = False
        testcount = 0
        for record in receiptcashdata:
            if record["accountcode"] == self.demo_accountcode1:
                if (
                    record["particulars"] == "Bank Of India"
                    and record["amount"] == "500.00"
                ):
                    testcount += 1
                    testResult = True
                else:
                    testResult = False
            if (
                record["accountcode"] == self.demo_accountcode2
                and record["amount"] == "1000.00"
            ):
                if record["particulars"] == "Bank Of Badoda":
                    testcount += 1
                    testResult = True
                else:
                    testResult = False
            if (
                record["accountcode"] == self.demo_accountcode2
                and record["amount"] == "100.00"
            ):
                if (
                    record["particulars"] == "Bank Of Badoda" and record["toby"] == "To"
                ):  # and record["ttlRunDr"] == "100.0":
                    testcount += 1
                    testResult = True
                else:
                    testResult = False
            if record["particulars"] == "Total":
                if record["amount"] == "1600.00":
                    testcount += 1
                    testResult = True
                else:
                    testResult = False
        for record in paymentcashdata:
            if (
                record["accountcode"] == self.demo_accountcode1
                and record["amount"] == "600.00"
            ):
                if record["particulars"] == "Bank Of India":
                    testcount += 1
                    testResult = True
                else:
                    testResult = False
            if (
                record["accountcode"] == self.demo_accountcode1
                and record["amount"] == "100.00"
            ):
                if (
                    record["particulars"] == "Bank Of India" and record["toby"] == "By"
                ):  # and record["ttlRunCr"] == "100.0":
                    testcount += 1
                    testResult = True
                else:
                    testResult = False
            if record["accountcode"] == self.demo_accountcode2:
                if (
                    record["particulars"] == "Bank Of Badoda"
                    and record["amount"] == "900.00"
                ):
                    testcount += 1
                    testResult = True
                else:
                    testResult = False
            if record["particulars"] == "Total":
                if record["amount"] == "1600.00":
                    testcount += 1
                    testResult = True
                else:
                    testResult = False
        assert testResult == True and testcount == 8

    def test_projectStatement(self):
        result = requests.get(
            "http://127.0.0.1:6543/groupsubgroups", headers=self.header
        )
        for record in result.json()["gkresult"]:
            if record["groupname"] == "Direct Expense":
                grpcode = record["groupcode"]
                break
        gkdata = {"accountname": "SBI", "openingbal": 10000, "groupcode": grpcode}
        result = requests.post(
            "http://127.0.0.1:6543/accounts",
            data=json.dumps(gkdata),
            headers=self.header,
        )
        result = requests.get("http://127.0.0.1:6543/accounts", headers=self.header)
        for record in result.json()["gkresult"]:
            if record["accountname"] == "SBI":
                accountcode = record["accountcode"]
                break
        """ Preparing gkdata to pass to Create Voucher """
        drs = {accountcode: 1000}
        crs = {self.demo_accountcode2: 100}
        gkdata = {
            "invid": None,
            "vouchernumber": 123,
            "voucherdate": "2016-12-16",
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
        result = requests.get(
            "http://127.0.0.1:6543/transaction?searchby=vnum&voucherno=100",
            headers=self.header,
        )
        vouchercode = result.json()["gkresult"][0]["vouchercode"]
        result = requests.get(
            "http://127.0.0.1:6543/report?type=projectstatement&calculateto=%s&financialstart=%s&projectcode=%d"
            % ("2017-03-31", "2016-04-01", self.projectcode),
            headers=self.header,
        )
        projectdata = result.json()["gkresult"]
        testResult = False
        for record in projectdata:
            if record["accountcode"] == accountcode:
                if (
                    record["totalout"] == "1000.00"
                    and record["accountname"] == "SBI"
                    and record["groupname"] == "Direct Expense"
                ):
                    testResult = True
                else:
                    testResult = False
        assert testResult == True

    def test_balanceSheet(self):
        result = requests.get(
            "http://127.0.0.1:6543/report?type=balancesheet&calculateto=%s&baltype=1"
            % ("2017-03-31"),
            headers=self.header,
        )
        rconvbaldata = result.json()["gkresult"]["rightlist"]
        lconvbaldata = result.json()["gkresult"]["leftlist"]
        result = requests.get(
            "http://127.0.0.1:6543/report?type=balancesheet&calculateto=%s&baltype=2"
            % ("2017-03-31"),
            headers=self.header,
        )
        rsourcesdata = result.json()["gkresult"]["rightlist"]
        lsourcesdata = result.json()["gkresult"]["leftlist"]
        testResult = False
        testcount = 0
        for record in rconvbaldata:
            if record["groupAccname"] == "Bank":
                if record["amount"] == "1500.00":
                    testcount += 1
                    testResult = True
                else:
                    testResult = False
            if record["groupAccname"] == "Bank Of Badoda":
                if record["amount"] == "900.00":
                    testcount += 1
                    testResult = True
                else:
                    testResult = False
            if record["groupAccname"] == "Bank Of India":
                if record["amount"] == "600.00":
                    testcount += 1
                    testResult = True
                else:
                    testResult = False
            if record["groupAccname"] == "Total":
                if record["amount"] == "1500.00":
                    testcount += 1
                    testResult = True
                else:
                    testResult = False
        for record in lconvbaldata:
            if record["groupAccname"] == "Difference":
                if record["amount"] == "1500.00":
                    testcount += 1
                    testResult = True
                else:
                    testResult = False
            if record["groupAccname"] == "Total":
                if record["amount"] == "1500.00":
                    testcount += 1
                    testResult = True
                else:
                    testResult = False
        for record in rsourcesdata:
            if record["groupAccname"] == "Bank":
                if record["amount"] == "1500.00":
                    testcount += 1
                    testResult = True
                else:
                    testResult = False
            if record["groupAccname"] == "Bank Of Badoda":
                if record["amount"] == "900.00":
                    testcount += 1
                    testResult = True
                else:
                    testResult = False
            if record["groupAccname"] == "Bank Of India":
                if record["amount"] == "600.00":
                    testcount += 1
                    testResult = True
                else:
                    testResult = False
            if record["groupAccname"] == "Total":
                if record["amount"] == "1500.00":
                    testcount += 1
                    testResult = True
                else:
                    testResult = False
        for record in lsourcesdata:
            if record["groupAccname"] == "Difference":
                if record["amount"] == "1500.00":
                    testcount += 1
                    testResult = True
                else:
                    testResult = False
            if record["groupAccname"] == "Total":
                if record["amount"] == "1500.00":
                    testcount += 1
                    testResult = True
                else:
                    testResult = False
        assert testResult == True and testcount == 12

    def test_reportProfitLoss(self):
        result = requests.get(
            "http://127.0.0.1:6543/report?type=profitloss&calculateto=%s"
            % ("2017-03-31"),
            headers=self.header,
        )
        profitdata = result.json()["income"]
        lossdata = result.json()["expense"]
        testResult = False
        testcount = 0
        for record in profitdata:
            if record["accountname"] == "Gross Loss C/F":
                if record["amount"] == "1000.00" and record["toby"] == "By,":
                    testcount += 1
                    testResult = True
                else:
                    testResult = False
            if record["accountname"] == "Net Loss Carried to B/S":
                if record["amount"] == "1000.00" and record["toby"] == "By,":
                    testcount += 1
                    testResult = True
                else:
                    testResult = False
            if record["accountname"] == "TOTAL":
                if record["amount"] == "1000.00":
                    testcount += 1
                    testResult = True
                else:
                    testResult = False
        for record in lossdata:
            if record["accountname"] == "SBI":
                if record["amount"] == "1000.00" and record["toby"] == "To,":
                    testcount += 1
                    testResult = True
                else:
                    testResult = False
            if record["accountname"] == "Gross Loss B/F":
                if record["amount"] == "1000.00" and record["toby"] == "To,":
                    testcount += 1
                    testResult = True
                else:
                    testResult = False
            if record["accountname"] == "TOTAL":
                if record["amount"] == "1000.00":
                    testcount += 1
                    testResult = True
                else:
                    testResult = False
        assert testResult == True and testcount == 8

    def test_get_deleted_vouchers(self):
        drs = {self.demo_accountcode1: 1000}
        crs = {self.demo_accountcode2: 1000}
        gkdata = {
            "invid": None,
            "vouchernumber": 11,
            "voucherdate": "2016-12-16",
            "narration": "Demo Narration",
            "drs": drs,
            "crs": crs,
            "vouchertype": "purchase",
            "projectcode": int(self.projectcode),
        }
        """ Create a Voucher """
        result = requests.post(
            "http://127.0.0.1:6543/transaction",
            data=json.dumps(gkdata),
            headers=self.header,
        )
        result = requests.get(
            "http://127.0.0.1:6543/transaction?searchby=vnum&voucherno=11",
            headers=self.header,
        )
        vouchercode = result.json()["gkresult"][0]["vouchercode"]
        """ Delete a Voucher """
        gkdata = {"vouchercode": vouchercode}
        result = requests.delete(
            "http://127.0.0.1:6543/transaction",
            data=json.dumps(gkdata),
            headers=self.header,
        )
        result = requests.get(
            "http://127.0.0.1:6543/report?type=deletedvoucher", headers=self.header
        )
        assert result.json()["gkresult"][0]["vouchercode"] == vouchercode

    def test_stockReport(self):
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
                self.godownid = record["goid"]
                break
        proddetails = {
            "productdesc": "Sugar",
            "specs": {self.demospeccode: "Pure"},
            "uomid": self.demouomid,
            "categorycode": self.democategorycode,
        }
        productdetails = {
            "productdetails": proddetails,
            "godetails": {self.godownid: 100},
            "godownflag": True,
        }
        result = requests.post(
            "http://127.0.0.1:6543/products",
            data=json.dumps(productdetails),
            headers=self.header,
        )
        demoproductcode = result.json()["gkresult"]
        stockresult = requests.get(
            "http://127.0.0.1:6543/report?type=stockreport&productcode=%d&startdate=%s&enddate=%s"
            % (demoproductcode, "2016-04-01", "2017-03-31"),
            headers=self.header,
        )
        result = requests.delete(
            "http://127.0.0.1:6543/products",
            data=json.dumps({"productcode": int(demoproductcode)}),
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
        gkdata = {"goid": self.godownid}
        result = requests.delete(
            "http://127.0.0.1:6543/godown", data=json.dumps(gkdata), headers=self.header
        )
        assert (
            stockresult.json()["gkstatus"] == 0
            and stockresult.json()["gkresult"][0]["inward"] == "100.00"
        )

    def test_godown_stock_report(self):
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
                self.godownid = record["goid"]
                break
        proddetails = {
            "productdesc": "Sugar",
            "specs": {self.demospeccode: "Pure"},
            "uomid": self.demouomid,
            "categorycode": self.democategorycode,
        }
        productdetails = {
            "productdetails": proddetails,
            "godetails": {self.godownid: 100},
            "godownflag": True,
        }
        result = requests.post(
            "http://127.0.0.1:6543/products",
            data=json.dumps(productdetails),
            headers=self.header,
        )
        demoproductcode = result.json()["gkresult"]
        gostockreport = requests.get(
            "http://127.0.0.1:6543/report?type=godownstockreport&goid=%d&productcode=%d&startdate=%s&enddate=%s"
            % (self.godownid, demoproductcode, "2016-04-01", "2017-03-31"),
            headers=self.header,
        )
        result = requests.delete(
            "http://127.0.0.1:6543/products",
            data=json.dumps({"productcode": int(demoproductcode)}),
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
        gkdata = {"goid": self.godownid}
        result = requests.delete(
            "http://127.0.0.1:6543/godown", data=json.dumps(gkdata), headers=self.header
        )
        assert (
            gostockreport.json()["gkstatus"] == 0
            and gostockreport.json()["gkresult"][0]["inward"] == "100.00"
        )
