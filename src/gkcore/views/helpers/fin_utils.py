# License: AGPLv3
# Author: Sai Karthik <kskarthik@disroot.org>
#
# This module contains the utility functions related to ifsc & hsn codes which
# can be used throughout the application
import csv
import json
from gkcore.utils import gk_log
from gkcore import BASE_DIR

_hsn: list = []
_ifsc: list = []


def ifsc_codes():
    """Read IFSC.csv and return the result as a dict"""

    # if the file is already loaded, return
    if len(_ifsc) > 0:
        return _ifsc
    try:
        # else read the file in static/ dir
        f = open(f"{BASE_DIR}/data/IFSC.csv", "r")
        # parse the file as a python dict
        tmp_ifsc = csv.DictReader(f)
        # loop over all items of the list and
        # append them to the _ifsc var which is of type list
        for i in tmp_ifsc:
            _ifsc.append(i)
        f.close()
        return _ifsc
    except Exception as e:
        raise e


def hsn_codes():
    """Read HSN Code file and return an array of hsn codes"""
    # if the file is already loaded, return
    if len(_hsn) > 0:
        return _hsn
    try:
        # else read the file in static/ dir
        with open(f"{BASE_DIR}/data/gst-hsn.json", "r") as f:
            # parse the contents of the file as json
            tmp_hsn = json.load(f)
            # loop over all items of the list and
            # append them to the _hsn var which is of type list
            for i in tmp_hsn:
                _hsn.append(i)

        return _hsn

    except Exception as e:
        gk_log(__name__).warn(e)
        raise e
