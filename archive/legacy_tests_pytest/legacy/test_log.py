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
"Bhavesh Bawadhane" <bbhavesh07@gmail.com>
"""
import requests, json


class TestLog:
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
        gkdata = {"activity": "Bank Of India account added"}
        result = requests.post(
            "http://127.0.0.1:6543/log", data=json.dumps(gkdata), headers=self.header
        )
        result = requests.get("http://127.0.0.1:6543/log", headers=self.header)
        for record in result.json()["gkresult"]:
            if record["activity"] == "Bank Of India account added":
                self.demologid = record["logid"]
                break

    def teardown(self):
        gkdata = {"logid": self.demologid}
        result = requests.delete(
            "http://127.0.0.1:6543/log", data=json.dumps(gkdata), headers=self.header
        )

    def test_create_log(self):
        gkdata = {"activity": "Bank Of India account deleted"}
        result = requests.post(
            "http://127.0.0.1:6543/log", data=json.dumps(gkdata), headers=self.header
        )
        assert result.json()["gkstatus"] == 0

    def test_delete_log(self):
        gkdata = {"activity": "Bank Of India account added"}
        result = requests.post(
            "http://127.0.0.1:6543/log", data=json.dumps(gkdata), headers=self.header
        )
        result = requests.get("http://127.0.0.1:6543/log", headers=self.header)
        for record in result.json()["gkresult"]:
            if record["activity"] == "Bank Of India account added":
                self.logid = record["logid"]
                break
        gkdata = {"logid": self.logid}
        result = requests.delete(
            "http://127.0.0.1:6543/log", data=json.dumps(gkdata), headers=self.header
        )
        assert result.json()["gkstatus"] == 0

    """ No need to update log, as it is log it cannot be updated
	def test_update_log(self):
		gkdata = {"logid":self.demologid,"time":"20-02-2016","activity":"deleted account SBI", "orgcode": "1", "userid":"1"}
		result = requests.put("http://127.0.0.1:6543/log", data =json.dumps(gkdata),headers=self.header)
		assert result.json()["gkstatus"]==0
	"""

    def test_get_single_log(self):
        result = requests.get(
            "http://127.0.0.1:6543/log?qty=single&logid=%s" % (self.demologid),
            headers=self.header,
        )
        assert result.json()["gkresult"]["activity"] == "Bank Of India account added"

    def test_get_all_logs(self):
        result = requests.get("http://127.0.0.1:6543/log", headers=self.header)
        assert result.json()["gkstatus"] == 0

    def test_get_log_byuser(self):
        result = requests.get("http://127.0.0.1:6543/user", headers=self.header)
        result = requests.get(
            "http://127.0.0.1:6543/log?type=byuser&userid=%s"
            % (result.json()["gkresult"]["userid"]),
            headers=self.header,
        )
        assert result.json()["gkstatus"] == 0

    """ while testing and checking output of following two methods please specify current date and tomorrow's date in calculatefrom and calculateto respectively"""

    def test_get_orgLogReport(self):
        result = requests.get(
            "http://127.0.0.1:6543/report?type=logbyorg&calculatefrom=2017-03-04&calculateto=2017-03-05",
            headers=self.header,
        )
        # print result.json()["gkresult"]
        assert result.json()["gkstatus"] == 0

    def test_get_log_Reportbyuser(self):
        result = requests.get("http://127.0.0.1:6543/user", headers=self.header)
        result = requests.get(
            "http://127.0.0.1:6543/report?type=logbyuser&userid=%s&calculatefrom=2017-03-04&calculateto=2017-03-05"
            % (result.json()["gkresult"]["userid"]),
            headers=self.header,
        )
        # print result.json()["gkresult"]
        assert result.json()["gkstatus"] == 0
