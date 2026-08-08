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


class TestAccountsByRule:
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

        """ Create an account of each type """
        result = requests.get(
            "http://127.0.0.1:6543/groupsubgroups", headers=self.header
        )
        groups = result.json()["gkresult"]
        self.demoaccountcode = {}
        i = 1
        accountname = "India Bank" + str(i)
        for group in groups:
            self.groupname = group["groupname"]
            self.groupcode = group["groupcode"]
            result = requests.get(
                "http://127.0.0.1:6543/groupDetails/%s" % (self.groupcode),
                headers=self.header,
            )
            subgrouplist = result.json()["gkresult"]
            if len(subgrouplist) == 0:
                gkdata = {
                    "accountname": accountname,
                    "openingbal": 500,
                    "groupcode": self.groupcode,
                }
                result = requests.post(
                    "http://127.0.0.1:6543/accounts",
                    data=json.dumps(gkdata),
                    headers=self.header,
                )
                result = requests.get(
                    "http://127.0.0.1:6543/accounts", headers=self.header
                )
                for record in result.json()["gkresult"]:
                    if record["accountname"] == accountname:
                        subgroupof = None
                        self.demoaccountcode.update(
                            {
                                record["accountcode"]: [
                                    accountname,
                                    self.groupname,
                                    subgroupof,
                                ]
                            }
                        )
                        break
                i = i + 1
                accountname = "India Bank" + str(i)
                continue
            for subgroup in subgrouplist:
                self.grpname = subgroup["subgroupname"]
                self.grpcode = subgroup["groupcode"]
                gkdata = {
                    "accountname": accountname,
                    "openingbal": 500,
                    "groupcode": self.grpcode,
                }
                result = requests.post(
                    "http://127.0.0.1:6543/accounts",
                    data=json.dumps(gkdata),
                    headers=self.header,
                )
                result = requests.get(
                    "http://127.0.0.1:6543/accounts", headers=self.header
                )
                accountlist = result.json()["gkresult"]
                for account in accountlist:
                    if account["accountname"] == accountname:
                        subgroupof = self.groupname
                        self.demoaccountcode.update(
                            {
                                account["accountcode"]: [
                                    accountname,
                                    self.grpname,
                                    subgroupof,
                                ]
                            }
                        )
                        break
                i = i + 1
                accountname = "India Bank" + str(i)

        print("no of accounts created: ", i - 1)

    @classmethod
    def teardown_class(self):
        for accountcode in list(self.demoaccountcode.keys()):
            gkdata = {"accountcode": accountcode}
            result = requests.delete(
                "http://127.0.0.1:6543/accounts",
                data=json.dumps(gkdata),
                headers=self.header,
            )

        result = requests.delete(
            "http://127.0.0.1:6543/organisations", headers=self.header
        )

    def test_get_contra(self):
        type = "contra"
        result = requests.get(
            "http://127.0.0.1:6543/accountsbyrule?type=%s" % (type), headers=self.header
        )
        contralist = []
        """ Now the question is : How order of the list items can be put the same way as it will be received in result? """
        for accountcode in list(self.demoaccountcode.keys()):
            accountinfolist = self.demoaccountcode[accountcode]
            if accountinfolist[1] == "Bank" or accountinfolist[1] == "Cash":
                contralist.append(
                    {"accountcode": accountcode, "accountname": accountinfolist[0]}
                )
        receivedlist = result.json()["gkresult"]
        """ Is this guaranteed that dictionary comparisons are performed correctly? """
        contralist = sorted(contralist, key=lambda k: k["accountname"])
        status = cmp(receivedlist, contralist)
        # print "status: ", status
        assert result.json()["gkstatus"] == 0 and status == 0

    def test_get_journal(self):
        type = "journal"
        result = requests.get(
            "http://127.0.0.1:6543/accountsbyrule?type=%s" % (type), headers=self.header
        )
        journallist = []
        """ Now the question is : How order of the list items can be put the same way as it will be received in result? """
        for accountcode in list(self.demoaccountcode.keys()):
            accountinfolist = self.demoaccountcode[accountcode]
            if accountinfolist[1] != "Bank" and accountinfolist[1] != "Cash":
                journallist.append(
                    {"accountcode": accountcode, "accountname": accountinfolist[0]}
                )

        receivedlist = result.json()["gkresult"]
        # print "received list: ", receivedlist
        result = requests.get(
            "http://127.0.0.1:6543/accounts?acclist", headers=self.header
        )
        # print "acclist status: ", result.json()["gkstatus"]
        acclist = result.json()[
            "gkresult"
        ]  # Though it is named as accountlist, it's actually a dictionary containing accountnames as keys and accountcodes as values.
        journallist.append(
            {"accountcode": acclist["Opening Stock"], "accountname": "Opening Stock"}
        )
        journallist.append(
            {"accountcode": acclist["Closing Stock"], "accountname": "Closing Stock"}
        )
        journallist.append(
            {
                "accountcode": acclist["Stock at the Beginning"],
                "accountname": "Stock at the Beginning",
            }
        )
        journallist.append(
            {"accountcode": acclist["Profit & Loss"], "accountname": "Profit & Loss"}
        )
        """ Is this guaranteed that dictionary comparisons are performed correctly? """
        """
		status = cmp(receivedlist, journallist)
		print "status: ", status
		"""
        """
		list1 = [{"code": 20, "name": "aaaa"}, {"code": 18, "name": "bbbb"}, {"code": 21, "name": "cccc"}]
		list2 = [{"code": 18, "name": "bbbb"}, {"code": 20, "name": "aaaa"}, {"code": 21, "name": "cccc"}]
		newlist = sorted(list2, key=lambda k: k['name'])
		print "list2: ", newlist
		#list2.sort()
		print "comparison : ", cmp(list1, newlist)
		"""
        journallist = sorted(journallist, key=lambda k: k["accountname"])
        status = cmp(receivedlist, journallist)
        assert result.json()["gkstatus"] == 0 and status == 0

    def test_get_payment(self):
        type = "payment"

        """ When side == Dr """
        side = "Dr"
        result = requests.get(
            "http://127.0.0.1:6543/accountsbyrule?type=%s&side=%s" % (type, side),
            headers=self.header,
        )
        receivedlist = result.json()["gkresult"]
        paymentlist = []
        for accountcode in list(self.demoaccountcode.keys()):
            accountinfolist = self.demoaccountcode[accountcode]
            if accountinfolist[1] != "Bank" and accountinfolist[1] != "Cash":
                paymentlist.append(
                    {"accountcode": accountcode, "accountname": accountinfolist[0]}
                )
        paymentlist = sorted(paymentlist, key=lambda k: k["accountname"])
        drstatus = cmp(receivedlist, paymentlist)

        """ When side == Cr """
        side = "Cr"
        result = requests.get(
            "http://127.0.0.1:6543/accountsbyrule?type=%s&side=%s" % (type, side),
            headers=self.header,
        )
        receivedlist = result.json()["gkresult"]
        paymentlist = (
            []
        )  # will it work? we have to empty the previous contents of this paymentlist.
        for accountcode in list(self.demoaccountcode.keys()):
            accountinfolist = self.demoaccountcode[accountcode]
            if accountinfolist[1] == "Bank" or accountinfolist[1] == "Cash":
                paymentlist.append(
                    {"accountcode": accountcode, "accountname": accountinfolist[0]}
                )
        paymentlist = sorted(paymentlist, key=lambda k: k["accountname"])
        crstatus = cmp(receivedlist, paymentlist)

        assert result.json()["gkstatus"] == 0 and drstatus == 0 and crstatus == 0

    def test_get_receipt(self):
        type = "receipt"

        """ When side == Cr """
        side = "Cr"
        result = requests.get(
            "http://127.0.0.1:6543/accountsbyrule?type=%s&side=%s" % (type, side),
            headers=self.header,
        )
        receivedlist = result.json()["gkresult"]
        receiptlist = []
        for accountcode in list(self.demoaccountcode.keys()):
            accountinfolist = self.demoaccountcode[accountcode]
            if accountinfolist[1] != "Bank" and accountinfolist[1] != "Cash":
                receiptlist.append(
                    {"accountcode": accountcode, "accountname": accountinfolist[0]}
                )
        receiptlist = sorted(receiptlist, key=lambda k: k["accountname"])
        crstatus = cmp(receivedlist, receiptlist)

        """ When side == Dr """
        side = "Dr"
        result = requests.get(
            "http://127.0.0.1:6543/accountsbyrule?type=%s&side=%s" % (type, side),
            headers=self.header,
        )
        receivedlist = result.json()["gkresult"]
        receiptlist = (
            []
        )  # will it work? we have to empty the previous contents of this receiptlist.
        for accountcode in list(self.demoaccountcode.keys()):
            accountinfolist = self.demoaccountcode[accountcode]
            if accountinfolist[1] == "Bank" or accountinfolist[1] == "Cash":
                receiptlist.append(
                    {"accountcode": accountcode, "accountname": accountinfolist[0]}
                )
        receiptlist = sorted(receiptlist, key=lambda k: k["accountname"])
        drstatus = cmp(receivedlist, receiptlist)

        assert result.json()["gkstatus"] == 0 and crstatus == 0 and drstatus == 0

    def test_get_sales(self):
        type = "sales"

        """ When side == Cr """
        side = "Cr"
        result = requests.get(
            "http://127.0.0.1:6543/accountsbyrule?type=%s&side=%s" % (type, side),
            headers=self.header,
        )
        receivedlist = result.json()["gkresult"]
        saleslist = []
        for accountcode in list(self.demoaccountcode.keys()):
            accountinfolist = self.demoaccountcode[accountcode]
            if (
                accountinfolist[1] == "Current Liabilities"
                or accountinfolist[1] == "Direct Income"
                or accountinfolist[1] == "Indirect Income"
                or accountinfolist[2] == "Current Liabilities"
                or accountinfolist[2] == "Direct Income"
                or accountinfolist[2] == "Indirect Income"
            ):
                saleslist.append(
                    {"accountcode": accountcode, "accountname": accountinfolist[0]}
                )
        """ Here, we do not need to add any of the automatically generated accounts, since they do not meet the criteria. """
        saleslist = sorted(saleslist, key=lambda k: k["accountname"])
        crstatus = cmp(receivedlist, saleslist)

        """ When side == Dr """
        side = "Dr"
        result = requests.get(
            "http://127.0.0.1:6543/accountsbyrule?type=%s&side=%s" % (type, side),
            headers=self.header,
        )
        receivedlist = result.json()["gkresult"]
        saleslist = (
            []
        )  # will it work? we have to empty the previous contents of this saleslist.
        for accountcode in list(self.demoaccountcode.keys()):
            accountinfolist = self.demoaccountcode[accountcode]
            if (
                accountinfolist[1] == "Bank"
                or accountinfolist[1] == "Cash"
                or accountinfolist[1] == "Sundry Debtors"
            ):
                saleslist.append(
                    {"accountcode": accountcode, "accountname": accountinfolist[0]}
                )
        saleslist = sorted(saleslist, key=lambda k: k["accountname"])
        drstatus = cmp(receivedlist, saleslist)

        assert result.json()["gkstatus"] == 0 and crstatus == 0 and drstatus == 0

    def test_get_purchase(self):
        type = "purchase"

        """ When side == Cr """
        side = "Cr"
        result = requests.get(
            "http://127.0.0.1:6543/accountsbyrule?type=%s&side=%s" % (type, side),
            headers=self.header,
        )
        receivedlist = result.json()["gkresult"]
        purchaselist = []
        for accountcode in list(self.demoaccountcode.keys()):
            accountinfolist = self.demoaccountcode[accountcode]
            if (
                accountinfolist[1] == "Bank"
                or accountinfolist[1] == "Cash"
                or accountinfolist[1] == "Current Liabilities"
                or accountinfolist[2] == "Current Liabilities"
            ):
                purchaselist.append(
                    {"accountcode": accountcode, "accountname": accountinfolist[0]}
                )
        """ Here, we do not need to add any of the automatically generated accounts, since they do not meet the criteria. """
        purchaselist = sorted(purchaselist, key=lambda k: k["accountname"])
        crstatus = cmp(receivedlist, purchaselist)

        """ When side == Dr """
        side = "Dr"
        result = requests.get(
            "http://127.0.0.1:6543/accountsbyrule?type=%s&side=%s" % (type, side),
            headers=self.header,
        )
        receivedlist = result.json()["gkresult"]
        purchaselist = (
            []
        )  # will it work? we have to empty the previous contents of this purchaselist.
        for accountcode in list(self.demoaccountcode.keys()):
            accountinfolist = self.demoaccountcode[accountcode]
            if (
                accountinfolist[1] == "Direct Expense"
                or accountinfolist[1] == "Indirect Expense"
                or accountinfolist[1] == "Current Liabilities"
                or accountinfolist[2] == "Direct Expense"
                or accountinfolist[2] == "Indirect Expense"
                or accountinfolist[2] == "Current Liabilities"
            ):
                purchaselist.append(
                    {"accountcode": accountcode, "accountname": accountinfolist[0]}
                )

        """ Here, we do not need to add any of the automatically generated accounts, since they do not meet the criteria. """
        purchaselist = sorted(purchaselist, key=lambda k: k["accountname"])
        drstatus = cmp(receivedlist, purchaselist)

        assert result.json()["gkstatus"] == 0 and crstatus == 0 and drstatus == 0

    def test_get_salesreturn(self):
        type = "salesreturn"

        """ When side == Cr """
        side = "Cr"
        result = requests.get(
            "http://127.0.0.1:6543/accountsbyrule?type=%s&side=%s" % (type, side),
            headers=self.header,
        )
        receivedlist = result.json()["gkresult"]
        salesreturnlist = []
        for accountcode in list(self.demoaccountcode.keys()):
            accountinfolist = self.demoaccountcode[accountcode]
            if (
                accountinfolist[1] == "Bank"
                or accountinfolist[1] == "Cash"
                or accountinfolist[1] == "Sundry Creditors for Purchase"
                or accountinfolist[1] == "Sundry Creditors for Expense"
            ):
                salesreturnlist.append(
                    {"accountcode": accountcode, "accountname": accountinfolist[0]}
                )
        """ Here, we do not need to add any of the automatically generated accounts, since they do not meet the criteria. """
        salesreturnlist = sorted(salesreturnlist, key=lambda k: k["accountname"])
        crstatus = cmp(receivedlist, salesreturnlist)

        """ When side == Dr """
        side = "Dr"
        result = requests.get(
            "http://127.0.0.1:6543/accountsbyrule?type=%s&side=%s" % (type, side),
            headers=self.header,
        )
        receivedlist = result.json()["gkresult"]
        salesreturnlist = (
            []
        )  # will it work? we have to empty the previous contents of this salesreturnlist.
        for accountcode in list(self.demoaccountcode.keys()):
            accountinfolist = self.demoaccountcode[accountcode]
            if (
                accountinfolist[1] == "Direct Expense"
                or accountinfolist[1] == "Indirect Expense"
            ):
                salesreturnlist.append(
                    {"accountcode": accountcode, "accountname": accountinfolist[0]}
                )
        """ Here, we do not need to add any of the automatically generated accounts, since they do not meet the criteria. """
        salesreturnlist = sorted(salesreturnlist, key=lambda k: k["accountname"])
        drstatus = cmp(receivedlist, salesreturnlist)

        assert result.json()["gkstatus"] == 0 and crstatus == 0 and drstatus == 0

    def test_get_purchasereturn(self):
        type = "purchasereturn"

        """ When side == Cr """
        side = "Cr"
        result = requests.get(
            "http://127.0.0.1:6543/accountsbyrule?type=%s&side=%s" % (type, side),
            headers=self.header,
        )
        receivedlist = result.json()["gkresult"]
        purchasereturnlist = []
        for accountcode in list(self.demoaccountcode.keys()):
            accountinfolist = self.demoaccountcode[accountcode]
            if (
                accountinfolist[1] == "Direct Income"
                or accountinfolist[1] == "Indirect Income"
            ):
                purchasereturnlist.append(
                    {"accountcode": accountcode, "accountname": accountinfolist[0]}
                )
        """ Here, we do not need to add any of the automatically generated accounts, since they do not meet the criteria. """
        purchasereturnlist = sorted(purchasereturnlist, key=lambda k: k["accountname"])
        crstatus = cmp(receivedlist, purchasereturnlist)

        """ When side == Dr """
        side = "Dr"
        result = requests.get(
            "http://127.0.0.1:6543/accountsbyrule?type=%s&side=%s" % (type, side),
            headers=self.header,
        )
        receivedlist = result.json()["gkresult"]
        purchasereturnlist = (
            []
        )  # will it work? we have to empty the previous contents of this purchasereturnlist.
        for accountcode in list(self.demoaccountcode.keys()):
            accountinfolist = self.demoaccountcode[accountcode]
            if (
                accountinfolist[1] == "Bank"
                or accountinfolist[1] == "Cash"
                or accountinfolist[1] == "Sundry Debtors"
            ):
                purchasereturnlist.append(
                    {"accountcode": accountcode, "accountname": accountinfolist[0]}
                )
        """ Here, we do not need to add any of the automatically generated accounts, since they do not meet the criteria. """
        purchasereturnlist = sorted(purchasereturnlist, key=lambda k: k["accountname"])
        drstatus = cmp(receivedlist, purchasereturnlist)

        assert result.json()["gkstatus"] == 0 and crstatus == 0 and drstatus == 0

    def test_get_debitnote(self):
        type = "debitnote"

        """ When side == Cr """
        side = "Cr"
        result = requests.get(
            "http://127.0.0.1:6543/accountsbyrule?type=%s&side=%s" % (type, side),
            headers=self.header,
        )
        receivedlist = result.json()["gkresult"]
        debitnotelist = []
        for accountcode in list(self.demoaccountcode.keys()):
            accountinfolist = self.demoaccountcode[accountcode]
            if (
                accountinfolist[1] == "Direct Income"
                or accountinfolist[1] == "Indirect Income"
            ):
                debitnotelist.append(
                    {"accountcode": accountcode, "accountname": accountinfolist[0]}
                )
        """ Here, we do not need to add any of the automatically generated accounts, since they do not meet the criteria. """
        debitnotelist = sorted(debitnotelist, key=lambda k: k["accountname"])
        crstatus = cmp(receivedlist, debitnotelist)

        """ When side == Dr """
        side = "Dr"
        result = requests.get(
            "http://127.0.0.1:6543/accountsbyrule?type=%s&side=%s" % (type, side),
            headers=self.header,
        )
        receivedlist = result.json()["gkresult"]
        debitnotelist = (
            []
        )  # will it work? we have to empty the previous contents of this debitnotelist.
        for accountcode in list(self.demoaccountcode.keys()):
            accountinfolist = self.demoaccountcode[accountcode]
            if (
                accountinfolist[1] == "Bank"
                or accountinfolist[1] == "Cash"
                or accountinfolist[1] == "Sundry Debtors"
            ):
                debitnotelist.append(
                    {"accountcode": accountcode, "accountname": accountinfolist[0]}
                )
        """ Here, we do not need to add any of the automatically generated accounts, since they do not meet the criteria. """
        debitnotelist = sorted(debitnotelist, key=lambda k: k["accountname"])
        drstatus = cmp(receivedlist, debitnotelist)

        assert result.json()["gkstatus"] == 0 and crstatus == 0 and drstatus == 0

    def test_get_creditnote(self):
        type = "creditnote"

        """ When side == Cr """
        side = "Cr"
        result = requests.get(
            "http://127.0.0.1:6543/accountsbyrule?type=%s&side=%s" % (type, side),
            headers=self.header,
        )
        receivedlist = result.json()["gkresult"]
        creditnotelist = []
        for accountcode in list(self.demoaccountcode.keys()):
            accountinfolist = self.demoaccountcode[accountcode]
            if (
                accountinfolist[1] == "Bank"
                or accountinfolist[1] == "Cash"
                or accountinfolist[1] == "Sundry Creditors for Purchase"
                or accountinfolist[1] == "Sundry Creditors for Expense"
            ):
                creditnotelist.append(
                    {"accountcode": accountcode, "accountname": accountinfolist[0]}
                )
        """ Here, we do not need to add any of the automatically generated accounts, since they do not meet the criteria. """
        creditnotelist = sorted(creditnotelist, key=lambda k: k["accountname"])
        crstatus = cmp(receivedlist, creditnotelist)

        """ When side == Dr """
        side = "Dr"
        result = requests.get(
            "http://127.0.0.1:6543/accountsbyrule?type=%s&side=%s" % (type, side),
            headers=self.header,
        )
        receivedlist = result.json()["gkresult"]
        creditnotelist = (
            []
        )  # will it work? we have to empty the previous contents of this creditnotelist.
        for accountcode in list(self.demoaccountcode.keys()):
            accountinfolist = self.demoaccountcode[accountcode]
            if (
                accountinfolist[1] == "Direct Expense"
                or accountinfolist[1] == "Indirect Expense"
            ):
                creditnotelist.append(
                    {"accountcode": accountcode, "accountname": accountinfolist[0]}
                )
        """ Here, we do not need to add any of the automatically generated accounts, since they do not meet the criteria. """
        creditnotelist = sorted(creditnotelist, key=lambda k: k["accountname"])
        drstatus = cmp(receivedlist, creditnotelist)
        assert result.json()["gkstatus"] == 0 and crstatus == 0 and drstatus == 0
