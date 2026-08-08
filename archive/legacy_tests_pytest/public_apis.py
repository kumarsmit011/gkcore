"""
Copyright (C) 2013, 2014, 2015, 2016 Digital Freedom Foundation
Copyright (C) 2017, 2018, 2019, 2020, 2021, 2022 Digital Freedom Foundation & Accion Labs Pvt. Ltd.
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


Contributors
============
Sai Karthik <kskarthik@disroot.org>

"""
import unittest
import requests as r


class TestPublicApis(unittest.TestCase):
    """Test all gkcore pulic API's"""

    def test_state(self):
        result = r.get("http://localhost:6543/state").json()
        self.assertEqual(result["gkstatus"], 0)

        # check if all states are returned
        self.assertGreater(len(result["gkresult"]), 1)

    def test_state_full(self):
        result = r.get("http://localhost:6543/state?full").json()

        self.assertFalse(result["gkstatus"], 0)

        # check if all states are returned
        self.assertGreater(len(result["gkresult"]), 1)

    # def test_org_list(self):
    #     result = r.get("http://localhost:6543/organisations").json()
    #     self.assertFalse(result["gkstatus"], 0)

    # def test_split(self):
    #     s = "hello world"
    #     self.assertEqual(s.split(), ["hello", "world"])
    #     # check that s.split fails when the separator is not a string
    #     with self.assertRaises(TypeError):
    #         s.split(2)


if __name__ == "__main__":
    unittest.main()
