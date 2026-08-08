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

# from gkcore.views.api_login import authCheck
"""
Initially, setup_class() runs and at last, teardown_class() will run.
In between these two methods, initially, setup(), then the method written e.g. test_update_user, and then teardown() will be executed.
The sequence of these methods is decided based on alphabetical order.
"""


class TestUser:
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
        gkdata = {
            "username": "demo_user",
            "userpassword": "demo_passwd",
            "userrole": 0,
            "userquestion": "what is my pet name?",
            "useranswer": "cat",
        }
        result = requests.post(
            "http://127.0.0.1:6543/users", data=json.dumps(gkdata), headers=self.header
        )
        result = requests.get("http://127.0.0.1:6543/users", headers=self.header)
        for record in result.json()["gkresult"]:
            if record["username"] == "demo_user":
                self.demo_userid = record["userid"]
                break

    def teardown(self):
        gkdata = {"userid": self.demo_userid}
        result = requests.delete(
            "http://127.0.0.1:6543/users", data=json.dumps(gkdata), headers=self.header
        )

    def test_create_user(self):
        gkdata = {
            "username": "test_user",
            "userpassword": "test_passwd",
            "userrole": 1,
            "userquestion": "what is my pet name?",
            "useranswer": "moti",
        }
        result = requests.post(
            "http://127.0.0.1:6543/users", data=json.dumps(gkdata), headers=self.header
        )
        assert result.json()["gkstatus"] == 0

    def test_delete_user(self):
        result = requests.get("http://127.0.0.1:6543/users", headers=self.header)
        for record in result.json()["gkresult"]:
            if record["username"] == "test_user":
                self.userid = record["userid"]
                break
        gkdata = {"userid": self.userid}
        result = requests.delete(
            "http://127.0.0.1:6543/users", data=json.dumps(gkdata), headers=self.header
        )
        assert result.json()["gkstatus"] == 0

    def test_update_user(self):
        gkdata = {
            "userid": self.demo_userid,
            "username": "new_demo_user",
            "userpassword": "new_demo_passwd",
        }
        result = requests.put(
            "http://127.0.0.1:6543/users", headers=self.header, data=json.dumps(gkdata)
        )
        assert result.json()["gkstatus"] == 0

    def test_get_all_users(self):
        result = requests.get("http://127.0.0.1:6543/users", headers=self.header)
        assert result.json()["gkstatus"] == 0

    # You can run this file with nosetests -s --verbose test_user.py. It will show the list of users with godowns whenever godown is there.
    def test_get_listof_users(self):
        # godown 1
        gkdata = {
            "goname": "Test Godown 1",
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
            if record["goname"] == "Test Godown 1":
                self.goid = record["goid"]
                break
        # godown 2
        gkdata = {
            "goname": "Test Godown 2",
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
            if record["goname"] == "Test Godown 2":
                self.goid2 = record["goid"]
                break
        gkdata = {
            "username": "test",
            "userpassword": "test",
            "userrole": 3,
            "userquestion": "test",
            "useranswer": "test",
            "golist": json.loads(str([self.goid, self.goid2])),
        }
        result = requests.post(
            "http://127.0.0.1:6543/users", data=json.dumps(gkdata), headers=self.header
        )
        result = requests.get(
            "http://127.0.0.1:6543/users?type=list", headers=self.header
        )
        print(result.json()["gkresult"])
        assert result.json()["gkstatus"] == 0

    def test_get_single_user(self):
        """No need to insert data.
        Because, ultimately, in api_user::getUser(): userid is taken as the currently logged in user's id and
        not the one which we pass it through the below request"""
        result = requests.get("http://127.0.0.1:6543/user", headers=self.header)
        data = result.json()["gkresult"]
        assert (
            data["username"] == "admin"
            and data["userpassword"] == "admin"
            and data["userrole"] == -1
            and data["userquestion"] == "who am i?"
            and data["useranswer"] == "hacker"
        )

    def test_verify_security_answer(self):
        result = requests.get(
            "http://127.0.0.1:6543/forgotpassword?type=securityanswer&userid=%s&useranswer=cat"
            % (self.demo_userid)
        )
        assert result.json()["gkstatus"] == 0

    def test_update_old_password(self):
        gkdata = {
            "userid": self.demo_userid,
            "userpassword": "demo_newpasswd",
            "useranswer": "cat",
        }
        result = requests.put(
            "http://127.0.0.1:6543/forgotpassword", data=json.dumps(gkdata)
        )
        assert result.json()["gkstatus"] == 0

    def test_add_theme(self):
        themename = {"themename": "Cosmo"}
        result = requests.put(
            "http://127.0.0.1:6543/user?type=theme",
            headers=self.header,
            data=json.dumps(themename),
        )
        assert result.json()["gkstatus"] == 0

    def test_get_theme(self):
        result = requests.get(
            "http://127.0.0.1:6543/user?type=theme", headers=self.header
        )
        assert result.json()["gkresult"] == "Cosmo"
