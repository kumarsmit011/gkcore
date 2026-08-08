#!/usr/bin/env python3
"""
This file is part of GNUKhata: A modular,robust and Free Accounting System.
License: GPLv3 https://www.gnu.org/licenses/gpl-3.0-standalone.html

Summary:
========

This script performs two functions:

1. Convert the hsn/sac spreadhseet provided by the GST portal
into valid json file to use within gkcore

2. Downloads latest IFSC codes from https://github.com/razorpay/ifsc

Contributors
============
Sai Karthik <kskarthik@disroot.org>
"""

import requests, io, json, pathlib, openpyxl, sys


def generate_hsn():
    "Downloads hsn/sac codes spreadhseet from GST portal & converts as json"
    try:
        print("📡 Getting HSN/SAC spreadsheet from GST portal ...")

        gkcore_root = pathlib.Path("./").resolve()
        r = requests.get("https://tutorial.gst.gov.in/downloads/HSN_SAC.xlsx").content
        b = io.BytesIO(r)
        wb = openpyxl.load_workbook(b)
        hsn = wb["HSN"]
        sac = wb["SAC"]
        hsn_array = []
        sac_array = []

        print("⚙ Extracting HSN/SAC from the spreadsheet ...")

        for i in hsn.values:
            hsn_array.append({"hsn_code": i[0], "hsn_desc": i[1]})

        for i in sac.values:
            sac_array.append({"hsn_code": str(i[0]), "hsn_desc": i[1]})

        # remove table column names
        hsn_array.pop(0)
        sac_array.pop(0)

        print("HSN codes: ", len(hsn_array))
        print("SAC codes: ", len(sac_array))

        hsn_array.extend(sac_array)

        print("💾 Saving to file ...")
        with open(f"{gkcore_root}/static/gst-hsn.json", "w") as f:
            json.dump(hsn_array, f)

        print("total generated hsn/sac items: ", len(hsn_array))
    except Exception as e:
        print(e)


def download_ifsc_codes():
    "Checks for latest release of IFSC codes from razorpay/ifsc repo & downloads the latest one"
    try:
        api = "https://api.github.com/repos/razorpay/ifsc/releases?per_page=1"

        print("📡Fetching latest IFSC release ...")

        r = requests.get(api)

        if r.status_code == 200:
            body = r.json()

            latest_csv_url = body[0]["assets"][3]["browser_download_url"]

            print("⚙ Downloading", body[0]["tag_name"])

            r = requests.get(latest_csv_url)

            if r.status_code == 200:
                with open("static/IFSC.csv", "wb") as f:
                    f.write(r.content)
                    print("💾Done!")
            else:
                print("failed to download the csv")
        else:
            print("failed to connect with github API")

    except Exception as e:
        print(e)


# parse the cli args
try:
    a = sys.argv[1:]

    arg: str = a[0]

    if arg == "ifsc":
        download_ifsc_codes()

    if arg == "hsn":
        generate_hsn()

except Exception:
    print("valid sub-commands are: ifsc, hsn")
