"""
Copyright (C) 2013, 2014, 2015, 2016 Digital Freedom Foundation
Copyright (C) 2017, 2018, 2019, 2020 Digital Freedom Foundation & Accion Labs Pvt. Ltd.
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
"Krishnakant Mane" <kkmane@riseup.net>
"Ishan Masdekar " <imasdekar@dff.org.in>
"Navin Karkera" <navin@dff.org.in>
'Prajkta Patkar'<prajakta@dff.org.in>
'Reshma Bhatwadekar'<reshma_b@riseup.net>
"Sanket Kolnoorkar"<Sanketf123@gmail.com>
'Aditya Shukla' <adityashukla9158.as@gmail.com>
'Pravin Dake' <pravindake24@gmail.com>

"""

from pyramid.view import view_defaults, view_config
from gkcore.utils import authCheck, generateAuthToken, userAuthCheck, getUserRole
from gkcore import eng, enumdict
from gkcore.models import gkdb
from gkcore.models.gkdb import organisation
from sqlalchemy.sql import select
from sqlalchemy import func, desc
from sqlalchemy.engine.base import Connection
from sqlalchemy import and_, or_
import jwt
import gkcore
import json
from datetime import datetime, timedelta
import os

from gkcore.views.organisation.schemas import OrgCreate, OrgUpdate

con = Connection


@view_defaults(route_name="organisation")
class api_organisation(object):
    def __init__(self, request):
        self.request = request
        self.is_org_registration_disabled = os.environ.get(
            "GKCORE_DISABLE_ORG_REGISTRATION",
            "false",
        )

    @view_config(
        request_method="GET",
        request_param="type=orgcodelist",
        renderer="json",
    )
    def getsubOrgs(self):
        with eng.connect() as con:
            result = con.execute(
                select(
                    [
                        gkdb.organisation.c.orgname,
                        gkdb.organisation.c.orgtype,
                        gkdb.organisation.c.orgcode,
                        gkdb.organisation.c.yearstart,
                        gkdb.organisation.c.yearend,
                    ]
                ).order_by(gkdb.organisation.c.orgcode)
            )
            orgs = []
            for row in result:
                orgs.append(
                    {
                        "orgname": row["orgname"],
                        "orgtype": row["orgtype"],
                        "orgcode": row["orgcode"],
                        "yearstart": str(row["yearstart"]),
                        "yearend": str(row["yearend"]),
                    }
                )
                orgs.sort()
            return {"gkstatus": enumdict["Success"], "gkdata": orgs}


    @view_config(route_name="orgyears", request_method="GET", renderer="json")
    def getYears(self):
        with eng.connect() as con:
            result = con.execute(
                select(
                    [
                        gkdb.organisation.c.yearstart,
                        gkdb.organisation.c.yearend,
                        gkdb.organisation.c.orgcode,
                    ]
                )
                .where(
                    and_(
                        gkdb.organisation.c.orgname
                        == self.request.matchdict["orgname"],
                        gkdb.organisation.c.orgtype
                        == self.request.matchdict["orgtype"],
                    )
                )
                .order_by(desc(gkdb.organisation.c.yearend))
            )
            years = []
            for row in result:
                years.append(
                    {
                        "yearstart": str(row["yearstart"]),
                        "yearend": str(row["yearend"]),
                        "orgcode": row["orgcode"],
                    }
                )
            return {"gkstatus": enumdict["Success"], "gkdata": years}


    @view_config(
        request_method="GET",
        renderer="json",
        route_name="organisation_registration",
    )
    def checkRegistrationStatus(self):
        """
        This function checks if registrations are disabled by server admin & return corresponding gkstatus code
        """
        if self.is_org_registration_disabled == "true":
            return {"gkstatus": enumdict["ActionDisallowed"]}
        else:
            return {"gkstatus": enumdict["Success"]}


    @view_config(
        request_method="POST",
        renderer="json",
    )
    def postOrg(self):
        """
        This function checks if registrations are disabled by server admin & return corresponding gkstatus code
        else create org based on parameters provided
        """
        if self.is_org_registration_disabled == "true":
            return {"gkstatus": enumdict["ActionDisallowed"]}

        try:
            token = self.request.headers["gkusertoken"]
        except:
            return {"gkstatus": gkcore.enumdict["UnauthorisedAccess"]}
        authDetails = userAuthCheck(token)
        if authDetails["auth"] == False:
            return {"gkstatus": gkcore.enumdict["UnauthorisedAccess"]}
        else:
            with eng.begin() as con:
                dataset = self.request.json_body
                orgdata = dataset["orgdetails"]

                validated_data = OrgCreate.model_validate(self.request.json_body)
                dataset = validated_data.model_dump(exclude_none=True)

                result = con.execute(gkdb.organisation.insert(), [orgdata])
                code = con.execute(
                    select([gkdb.organisation.c.orgcode]).where(
                        and_(
                            gkdb.organisation.c.orgname == orgdata["orgname"],
                            gkdb.organisation.c.orgtype == orgdata["orgtype"],
                            gkdb.organisation.c.yearstart == orgdata["yearstart"],
                            gkdb.organisation.c.yearend == orgdata["yearend"],
                        )
                    )
                )
                orgcode = code.fetchone()
                currentassets = {
                    "groupname": "Current Assets",
                    "orgcode": orgcode["orgcode"],
                }
                result = con.execute(
                    gkdb.groupsubgroups.insert(), currentassets
                )
                result = con.execute(
                    select([gkdb.groupsubgroups.c.groupcode]).where(
                        and_(
                            gkdb.groupsubgroups.c.groupname == "Current Assets",
                            gkdb.groupsubgroups.c.orgcode == orgcode["orgcode"],
                        )
                    )
                )
                grpcode = result.fetchone()
                result = con.execute(
                    gkdb.groupsubgroups.insert(),
                    [
                        {
                            "groupname": "Bank",
                            "orgcode": orgcode["orgcode"],
                            "subgroupof": grpcode["groupcode"],
                        },
                        {
                            "groupname": "Cash",
                            "orgcode": orgcode["orgcode"],
                            "subgroupof": grpcode["groupcode"],
                        },
                        {
                            "groupname": "Inventory",
                            "orgcode": orgcode["orgcode"],
                            "subgroupof": grpcode["groupcode"],
                        },
                        {
                            "groupname": "Loans & Advance",
                            "orgcode": orgcode["orgcode"],
                            "subgroupof": grpcode["groupcode"],
                        },
                        {
                            "groupname": "Sundry Debtors",
                            "orgcode": orgcode["orgcode"],
                            "subgroupof": grpcode["groupcode"],
                        },
                    ],
                )
                # Create account Cash in hand under subgroup Cash.
                csh = con.execute(
                    select([gkdb.groupsubgroups.c.groupcode]).where(
                        and_(
                            gkdb.groupsubgroups.c.groupname == "Cash",
                            gkdb.groupsubgroups.c.orgcode == orgcode["orgcode"],
                        )
                    )
                )
                cshgrpcd = csh.fetchone()
                resultc = con.execute(
                    gkdb.accounts.insert(),
                    {
                        "accountname": "Cash in hand",
                        "groupcode": cshgrpcd["groupcode"],
                        "orgcode": orgcode["orgcode"],
                        "defaultflag": 3,
                    },
                )

                currentliability = {
                    "groupname": "Current Liabilities",
                    "orgcode": orgcode["orgcode"],
                }
                result = con.execute(
                    gkdb.groupsubgroups.insert(), currentliability
                )
                result = con.execute(
                    select([gkdb.groupsubgroups.c.groupcode]).where(
                        and_(
                            gkdb.groupsubgroups.c.groupname
                            == "Current Liabilities",
                            gkdb.groupsubgroups.c.orgcode == orgcode["orgcode"],
                        )
                    )
                )
                grpcode = result.fetchone()
                result = con.execute(
                    gkdb.groupsubgroups.insert(),
                    [
                        {
                            "groupname": "Provisions",
                            "orgcode": orgcode["orgcode"],
                            "subgroupof": grpcode["groupcode"],
                        },
                        {
                            "groupname": "Sundry Creditors for Expense",
                            "orgcode": orgcode["orgcode"],
                            "subgroupof": grpcode["groupcode"],
                        },
                        {
                            "groupname": "Sundry Creditors for Purchase",
                            "orgcode": orgcode["orgcode"],
                            "subgroupof": grpcode["groupcode"],
                        },
                        {
                            "groupname": "Duties & Taxes",
                            "orgcode": orgcode["orgcode"],
                            "subgroupof": grpcode["groupcode"],
                        },
                    ],
                )
                resultDT = con.execute(
                    select([gkdb.groupsubgroups.c.groupcode]).where(
                        and_(
                            gkdb.groupsubgroups.c.groupname == "Duties & Taxes",
                            gkdb.groupsubgroups.c.orgcode == orgcode["orgcode"],
                        )
                    )
                )
                grpcd = resultDT.fetchone()
                resultL = con.execute(
                    gkdb.accounts.insert(),
                    [
                        {
                            "accountname": "VAT_OUT",
                            "groupcode": grpcd["groupcode"],
                            "orgcode": orgcode["orgcode"],
                            "sysaccount": 1,
                        },
                        {
                            "accountname": "VAT_IN",
                            "groupcode": grpcd["groupcode"],
                            "orgcode": orgcode["orgcode"],
                            "sysaccount": 1,
                        },
                    ],
                )

                # Create Direct expense group , get it's group code and create subgroups under it.
                directexpense = {
                    "groupname": "Direct Expense",
                    "orgcode": orgcode["orgcode"],
                }
                result = con.execute(
                    gkdb.groupsubgroups.insert(), directexpense
                )
                result = con.execute(
                    select([gkdb.groupsubgroups.c.groupcode]).where(
                        and_(
                            gkdb.groupsubgroups.c.groupname == "Direct Expense",
                            gkdb.groupsubgroups.c.orgcode == orgcode["orgcode"],
                        )
                    )
                )
                DEGrpCodeData = result.fetchone()
                DEGRPCode = DEGrpCodeData["groupcode"]
                insData = con.execute(
                    gkdb.groupsubgroups.insert(),
                    [
                        {
                            "groupname": "Purchase",
                            "subgroupof": DEGRPCode,
                            "orgcode": orgcode["orgcode"],
                        },
                        {
                            "groupname": "Consumables",
                            "subgroupof": DEGRPCode,
                            "orgcode": orgcode["orgcode"],
                        },
                    ],
                )
                purchgrp = con.execute(
                    select([gkdb.groupsubgroups.c.groupcode]).where(
                        and_(
                            gkdb.groupsubgroups.c.groupname == "Purchase",
                            gkdb.groupsubgroups.c.orgcode == orgcode["orgcode"],
                        )
                    )
                )
                purchgrpcd = purchgrp.fetchone()
                resultp = con.execute(
                    gkdb.accounts.insert(),
                    {
                        "accountname": "Purchase A/C",
                        "groupcode": purchgrpcd["groupcode"],
                        "orgcode": orgcode["orgcode"],
                        "defaultflag": 16,
                    },
                )

                directincome = {
                    "groupname": "Direct Income",
                    "orgcode": orgcode["orgcode"],
                }
                result = con.execute(
                    gkdb.groupsubgroups.insert(), directincome
                )
                results = con.execute(
                    select([gkdb.groupsubgroups.c.groupcode]).where(
                        and_(
                            gkdb.groupsubgroups.c.groupname == "Direct Income",
                            gkdb.groupsubgroups.c.orgcode == orgcode["orgcode"],
                        )
                    )
                )
                DIGrpCodeData = results.fetchone()
                insData = con.execute(
                    gkdb.groupsubgroups.insert(),
                    {
                        "groupname": "Sales",
                        "subgroupof": DIGrpCodeData["groupcode"],
                        "orgcode": orgcode["orgcode"],
                    },
                )
                slgrp = con.execute(
                    select([gkdb.groupsubgroups.c.groupcode]).where(
                        and_(
                            gkdb.groupsubgroups.c.groupname == "Sales",
                            gkdb.groupsubgroups.c.orgcode == orgcode["orgcode"],
                        )
                    )
                )
                slgrpcd = slgrp.fetchone()
                resultsl = con.execute(
                    gkdb.accounts.insert(),
                    {
                        "accountname": "Sale A/C",
                        "groupcode": slgrpcd["groupcode"],
                        "orgcode": orgcode["orgcode"],
                        "defaultflag": 19,
                    },
                )

                fixedassets = {
                    "groupname": "Fixed Assets",
                    "orgcode": orgcode["orgcode"],
                }
                result = con.execute(
                    gkdb.groupsubgroups.insert(), fixedassets
                )
                result = con.execute(
                    select([gkdb.groupsubgroups.c.groupcode]).where(
                        and_(
                            gkdb.groupsubgroups.c.groupname == "Fixed Assets",
                            gkdb.groupsubgroups.c.orgcode == orgcode["orgcode"],
                        )
                    )
                )
                grpcode = result.fetchone()
                result = con.execute(
                    gkdb.groupsubgroups.insert(),
                    [
                        {
                            "groupname": "Building",
                            "orgcode": orgcode["orgcode"],
                            "subgroupof": grpcode["groupcode"],
                        },
                        {
                            "groupname": "Furniture",
                            "orgcode": orgcode["orgcode"],
                            "subgroupof": grpcode["groupcode"],
                        },
                        {
                            "groupname": "Land",
                            "orgcode": orgcode["orgcode"],
                            "subgroupof": grpcode["groupcode"],
                        },
                        {
                            "groupname": "Plant & Machinery",
                            "orgcode": orgcode["orgcode"],
                            "subgroupof": grpcode["groupcode"],
                        },
                    ],
                )
                resultad = con.execute(
                    gkdb.accounts.insert(),
                    {
                        "accountname": "Accumulated Depreciation",
                        "groupcode": grpcode["groupcode"],
                        "orgcode": orgcode["orgcode"],
                    },
                )

                indirectexpense = {
                    "groupname": "Indirect Expense",
                    "orgcode": orgcode["orgcode"],
                }
                result = con.execute(
                    gkdb.groupsubgroups.insert(), indirectexpense
                )
                resultie = con.execute(
                    select([gkdb.groupsubgroups.c.groupcode]).where(
                        and_(
                            gkdb.groupsubgroups.c.groupname
                            == "Indirect Expense",
                            gkdb.groupsubgroups.c.orgcode == orgcode["orgcode"],
                        )
                    )
                )
                iegrpcd = resultie.fetchone()
                resultDP = con.execute(
                    gkdb.accounts.insert(),
                    [
                        {
                            "accountname": "Bank Charges",
                            "groupcode": grpcode["groupcode"],
                            "orgcode": orgcode["orgcode"],
                        },
                        {
                            "accountname": "Salary",
                            "groupcode": grpcode["groupcode"],
                            "orgcode": orgcode["orgcode"],
                        },
                        {
                            "accountname": "Miscellaneous Expense",
                            "groupcode": grpcode["groupcode"],
                            "orgcode": orgcode["orgcode"],
                        },
                        {
                            "accountname": "Rent",
                            "groupcode": grpcode["groupcode"],
                            "orgcode": orgcode["orgcode"],
                        },
                        {
                            "accountname": "Travel Expense",
                            "groupcode": grpcode["groupcode"],
                            "orgcode": orgcode["orgcode"],
                        },
                        {
                            "accountname": "Electricity Expense",
                            "groupcode": grpcode["groupcode"],
                            "orgcode": orgcode["orgcode"],
                        },
                        {
                            "accountname": "Professional Fees",
                            "groupcode": grpcode["groupcode"],
                            "orgcode": orgcode["orgcode"],
                        },
                        {
                            "accountname": "Discount Paid",
                            "groupcode": iegrpcd["groupcode"],
                            "orgcode": orgcode["orgcode"],
                        },
                        {
                            "accountname": "Bonus",
                            "groupcode": iegrpcd["groupcode"],
                            "orgcode": orgcode["orgcode"],
                        },
                        {
                            "accountname": "Depreciation Expense",
                            "groupcode": iegrpcd["groupcode"],
                            "orgcode": orgcode["orgcode"],
                        },
                    ],
                )
                resultROP = con.execute(
                    gkdb.accounts.insert(),
                    {
                        "accountname": "Round Off Paid",
                        "groupcode": iegrpcd["groupcode"],
                        "orgcode": orgcode["orgcode"],
                        "defaultflag": 180,
                    },
                )

                indirectincome = {
                    "groupname": "Indirect Income",
                    "orgcode": orgcode["orgcode"],
                }
                result = con.execute(
                    gkdb.groupsubgroups.insert(), indirectincome
                )
                resultii = con.execute(
                    select([gkdb.groupsubgroups.c.groupcode]).where(
                        and_(
                            gkdb.groupsubgroups.c.groupname
                            == "Indirect Income",
                            gkdb.groupsubgroups.c.orgcode == orgcode["orgcode"],
                        )
                    )
                )
                iigrpcd = resultii.fetchone()
                resultDS = con.execute(
                    gkdb.accounts.insert(),
                    {
                        "accountname": "Discount Received",
                        "groupcode": iigrpcd["groupcode"],
                        "orgcode": orgcode["orgcode"],
                    },
                )
                resultROR = con.execute(
                    gkdb.accounts.insert(),
                    {
                        "accountname": "Round Off Received",
                        "groupcode": iigrpcd["groupcode"],
                        "orgcode": orgcode["orgcode"],
                        "defaultflag": 181,
                    },
                )

                investment = {
                    "groupname": "Investments",
                    "orgcode": orgcode["orgcode"],
                }
                result = con.execute(
                    gkdb.groupsubgroups.insert(), investment
                )
                result = con.execute(
                    select([gkdb.groupsubgroups.c.groupcode]).where(
                        and_(
                            gkdb.groupsubgroups.c.groupname == "Investments",
                            gkdb.groupsubgroups.c.orgcode == orgcode["orgcode"],
                        )
                    )
                )
                grpcode = result.fetchone()
                result = con.execute(
                    gkdb.groupsubgroups.insert(),
                    [
                        {
                            "groupname": "Investment in Bank Deposits",
                            "orgcode": orgcode["orgcode"],
                            "subgroupof": grpcode["groupcode"],
                        },
                        {
                            "groupname": "Investment in Shares & Debentures",
                            "orgcode": orgcode["orgcode"],
                            "subgroupof": grpcode["groupcode"],
                        },
                    ],
                )

                loansasset = {
                    "groupname": "Loans(Asset)",
                    "orgcode": orgcode["orgcode"],
                }
                result = con.execute(
                    gkdb.groupsubgroups.insert(), loansasset
                )

                loansliab = {
                    "groupname": "Loans(Liability)",
                    "orgcode": orgcode["orgcode"],
                }
                result = con.execute(
                    gkdb.groupsubgroups.insert(), loansliab
                )
                result = con.execute(
                    select([gkdb.groupsubgroups.c.groupcode]).where(
                        and_(
                            gkdb.groupsubgroups.c.groupname
                            == "Loans(Liability)",
                            gkdb.groupsubgroups.c.orgcode == orgcode["orgcode"],
                        )
                    )
                )
                grpcode = result.fetchone()
                result = con.execute(
                    gkdb.groupsubgroups.insert(),
                    [
                        {
                            "groupname": "Secured",
                            "orgcode": orgcode["orgcode"],
                            "subgroupof": grpcode["groupcode"],
                        },
                        {
                            "groupname": "Unsecured",
                            "orgcode": orgcode["orgcode"],
                            "subgroupof": grpcode["groupcode"],
                        },
                    ],
                )

                reserves = {
                    "groupname": "Reserves",
                    "orgcode": orgcode["orgcode"],
                }
                result = con.execute(
                    gkdb.groupsubgroups.insert(), reserves
                )

                result = con.execute(
                    select([gkdb.groupsubgroups.c.groupcode]).where(
                        and_(
                            gkdb.groupsubgroups.c.groupname == "Direct Income",
                            gkdb.groupsubgroups.c.orgcode == orgcode["orgcode"],
                        )
                    )
                )
                grpcode = result.fetchone()
                if orgdata["orgtype"] == "Profit Making":
                    result = con.execute(
                        gkdb.groupsubgroups.insert(),
                        [
                            {
                                "groupname": "Capital",
                                "orgcode": orgcode["orgcode"],
                            },
                            {
                                "groupname": "Miscellaneous Expenses(Asset)",
                                "orgcode": orgcode["orgcode"],
                            },
                        ],
                    )

                    result = con.execute(
                        gkdb.accounts.insert(),
                        {
                            "accountname": "Profit & Loss",
                            "groupcode": grpcode["groupcode"],
                            "orgcode": orgcode["orgcode"],
                            "sysaccount": 1,
                        },
                    )

                else:
                    result = con.execute(
                        gkdb.groupsubgroups.insert(),
                        {"groupname": "Corpus", "orgcode": orgcode["orgcode"]},
                    )

                    result = con.execute(
                        gkdb.accounts.insert(),
                        {
                            "accountname": "Income & Expenditure",
                            "groupcode": grpcode["groupcode"],
                            "orgcode": orgcode["orgcode"],
                            "sysaccount": 1,
                        },
                    )

                result = con.execute(
                    select([gkdb.groupsubgroups.c.groupcode]).where(
                        and_(
                            gkdb.groupsubgroups.c.groupname == "Inventory",
                            gkdb.groupsubgroups.c.orgcode == orgcode["orgcode"],
                        )
                    )
                )
                grpcode = result.fetchone()
                result = con.execute(
                    gkdb.accounts.insert(),
                    [
                        {
                            "accountname": "Closing Stock",
                            "groupcode": grpcode["groupcode"],
                            "orgcode": orgcode["orgcode"],
                            "sysaccount": 1,
                        },
                        {
                            "accountname": "Stock at the Beginning",
                            "groupcode": grpcode["groupcode"],
                            "orgcode": orgcode["orgcode"],
                            "sysaccount": 1,
                        },
                    ],
                )

                result = con.execute(
                    select([gkdb.groupsubgroups.c.groupcode]).where(
                        and_(
                            gkdb.groupsubgroups.c.groupname == "Direct Expense",
                            gkdb.groupsubgroups.c.orgcode == orgcode["orgcode"],
                        )
                    )
                )
                grpcode = result.fetchone()
                result = con.execute(
                    gkdb.accounts.insert(),
                    {
                        "accountname": "Opening Stock",
                        "groupcode": grpcode["groupcode"],
                        "orgcode": orgcode["orgcode"],
                        "sysaccount": 1,
                    },
                )

                # Update organisation table about its admin user
                users = {}
                users[authDetails["userid"]] = True
                con.execute(
                    gkdb.organisation.update()
                    .where(gkdb.organisation.c.orgcode == orgcode["orgcode"])
                    .values(users=users)
                )
                # Update gkusers table about newly added org
                orgs = {
                    "invitestatus": True,
                    "userconf": {},
                    "userrole": -1,
                }
                con.execute(
                    "update gkusers set orgs = jsonb_set(orgs, '{%s}', '%s') where userid = %d;"
                    % (
                        str(orgcode["orgcode"]),
                        json.dumps(orgs),
                        authDetails["userid"],
                    )
                )

                token = generateAuthToken(
                    con,
                    {"userid": authDetails["userid"], "orgcode": orgcode["orgcode"]},
                )
                return {
                    "gkstatus": enumdict["Success"],
                    "token": token,
                    "orgcode": orgcode["orgcode"],
                }


    @view_config(request_method="GET", renderer="json")
    def getOrg(self):
        try:
            token = self.request.headers["gktoken"]
        except:
            return {"gkstatus": enumdict["UnauthorisedAccess"]}
        authDetails = authCheck(token)
        if authDetails["auth"] == False:
            return {"gkstatus": enumdict["UnauthorisedAccess"]}
        else:
            with eng.connect() as con:
                result = con.execute(
                    select([organisation]).where(
                        gkdb.organisation.c.orgcode == authDetails["orgcode"]
                    )
                )
                row = result.fetchone()

                orgDetails = {
                    "orgname": row["orgname"],
                    "orgtype": row["orgtype"],
                    "yearstart": str(row["yearstart"]),
                    "yearend": str(row["yearend"]),
                    "orgcity": row.orgcity,
                    "orgaddr": row.orgaddr,
                    "orgpincode": row.orgpincode,
                    "orgstate": row.orgstate,
                    "orgcountry": row.orgcountry,
                    "orgtelno": row.orgtelno,
                    "orgfax": row.orgfax,
                    "orgwebsite": row.orgwebsite,
                    "orgemail": row.orgemail,
                    "orgpan": row.orgpan,
                    "orgmvat": row.orgmvat,
                    "orgstax": row.orgstax,
                    "orgregno": row.orgregno,
                    "orgregdate": row.orgregdate,
                    "orgfcrano": row.orgfcrano,
                    "orgfcradate": row.orgfcradate,
                    "roflag": row["roflag"],
                    "booksclosedflag": row["booksclosedflag"],
                    "invflag": row["invflag"],
                    "billflag": row["billflag"],
                    "invsflag": row["invsflag"],
                    "gstin": row["gstin"],
                    "tin": row["tin"],
                    "cin": row["cin"],
                    "bankdetails": row["bankdetails"],
                    "avflag": row["avflag"],
                    "maflag": row["maflag"],
                    "avnoflag": row["avnoflag"],
                    "ainvnoflag": row["ainvnoflag"],
                    "modeflag": row["modeflag"],
                }

                return {"gkstatus": enumdict["Success"], "gkdata": orgDetails}


    @view_config(request_method="GET", request_param="type=genstats", renderer="json")
    def getGeneralStats(self):
        try:
            token = self.request.headers["gktoken"]
        except:
            return {"gkstatus": enumdict["UnauthorisedAccess"]}
        authDetails = authCheck(token)
        if authDetails["auth"] == False:
            return {"gkstatus": enumdict["UnauthorisedAccess"]}
        else:
            with eng.connect() as con:
                inv = con.execute(
                    "select count(invid) as invcount from invoice where orgcode = %d"
                    % int(authDetails["orgcode"])
                ).fetchone()
                party = con.execute(
                    "select count(custid) as pcount from customerandsupplier where orgcode = %d"
                    % int(authDetails["orgcode"])
                ).fetchone()
                prod = con.execute(
                    "select count(productcode) as prodcount from product where orgcode = %d"
                    % int(authDetails["orgcode"])
                ).fetchone()
                voucher = con.execute(
                    "select count(vouchercode) vcount from vouchers where orgcode = %d"
                    % int(authDetails["orgcode"])
                ).fetchone()
                data = {
                    "inv_count": inv["invcount"],
                    "party_count": party["pcount"],
                    "prod_count": prod["prodcount"],
                    "vouchercount": voucher["vcount"],
                }

                return {"gkstatus": enumdict["Success"], "gkresult": data}


        """
        This function returns Organisation Details for Invoicing.
        'statecode' receiving from frontend view & depending on statecode gstin will get.
        """

    @view_config(request_method="GET", renderer="json", request_param="billingdetails")
    def getbillingdetails(self):
        token = self.request.headers["gktoken"]
        authDetails = authCheck(token)
        if authDetails["auth"] == False:
            return {"gkstatus": enumdict["UnauthorisedAccess"]}
        else:
            with eng.connect() as con:
                statecode = self.request.params["statecode"]
                result = con.execute(
                    select([gkdb.organisation]).where(
                        gkdb.organisation.c.orgcode == authDetails["orgcode"]
                    )
                )
                row = result.fetchone()
                if row["orgcity"] == None:
                    orgcity = ""
                else:
                    orgcity = row["orgcity"]
                if row["orgaddr"] == None:
                    orgaddr = ""
                else:
                    orgaddr = row["orgaddr"]
                if row["orgpincode"] == None:
                    orgpincode = ""
                else:
                    orgpincode = row["orgpincode"]
                if row["orgstate"] == None:
                    orgstate = ""
                else:
                    orgstate = row["orgstate"]
                if row["orgwebsite"] == None:
                    orgwebsite = ""
                else:
                    orgwebsite = row["orgwebsite"]
                if row["orgpan"] == None:
                    orgpan = ""
                else:
                    orgpan = row["orgpan"]
                if row["orgtelno"] == None:
                    orgtelno = ""
                else:
                    orgtelno = row["orgtelno"]
                if row["orgfax"] == None:
                    orgfax = ""
                else:
                    orgfax = row["orgfax"]
                if row["orgemail"] == None:
                    orgemail = ""
                else:
                    orgemail = row["orgemail"]
                if row["gstin"] == None:
                    gstin = ""
                elif str(statecode) in row["gstin"]:
                    gstin = row["gstin"][str(statecode)]
                else:
                    gstin = ""
                if row["bankdetails"] == None:
                    bankdetails = ""
                else:
                    bankdetails = row["bankdetails"]

                orgDetails = {
                    "orgname": row["orgname"],
                    "orgaddr": orgaddr,
                    "orgpincode": orgpincode,
                    "orgstate": orgstate,
                    "orgwebsite": orgwebsite,
                    "orgpan": orgpan,
                    "orgstategstin": gstin,
                    "orgcity": orgcity,
                    "bankdetails": bankdetails,
                    "orgtelno": orgtelno,
                    "orgfax": orgfax,
                    "orgemail": orgemail,
                }
                return {"gkstatus": enumdict["Success"], "gkdata": orgDetails}


    # code for saving null values of bankdetails and updation in database
    # variable created for orgcode so that query will work easily
    # TODO: duplicate of editOrg(), must merge both
    @view_config(
        request_method="PUT",
        renderer="json",
    )
    def putOrg(self):
        token = self.request.headers["gktoken"]
        authDetails = authCheck(token)
        orgcode = authDetails["orgcode"]
        if authDetails["auth"] == False:
            return {"gkstatus": enumdict["UnauthorisedAccess"]}
        else:
            with eng.begin() as con:

                userRoleData = getUserRole(
                    authDetails["userid"], authDetails["orgcode"]
                )
                userRole = userRoleData["gkresult"]["userrole"]
                validated_data = OrgUpdate.model_validate(self.request.json_body)
                dataset = validated_data.model_dump(exclude_none=True)

                org_data = con.execute(
                    select([organisation.c.yearstart, organisation.c.yearend])
                    .where(organisation.c.orgcode == orgcode)
                ).fetchone()
                # Check for duplicate entry before insertion
                result_duplicate_check = con.execute(
                    select([organisation.c.orgname]).where(
                        and_(
                            func.lower(organisation.c.orgname) == func.lower(dataset["orgname"]),
                            organisation.c.orgcode != orgcode,
                            or_(
                                organisation.c.yearstart.between(
                                    org_data["yearstart"], org_data["yearend"]
                                ),
                                organisation.c.yearend.between(
                                    org_data["yearstart"], org_data["yearend"]
                                ),
                            )
                        )
                    )
                )
                
                if result_duplicate_check.rowcount > 0:
                    # Duplicate entry found, handle accordingly
                    return {"gkstatus": enumdict["DuplicateEntry"]}

                if userRole == -1 or userRole == 0:
                    con.execute(
                        gkdb.organisation.update()
                        .where(
                            gkdb.organisation.c.orgcode == authDetails["orgcode"]
                        )
                        .values(dataset)
                    )

                    if "bankdetails" not in dataset:
                        con.execute(
                            "update organisation set bankdetails=NULL where bankdetails IS NOT NULL and orgcode=%d"
                            % int(orgcode)
                        )
                    if "gstin" not in dataset:
                        con.execute(
                            "update organisation set gstin=NULL where orgcode=%d"
                            % int(orgcode)
                        )
                    return {"gkstatus": enumdict["Success"]}
                else:
                    return {"gkstatus": enumdict["BadPrivilege"]}


    @view_config(
        request_method="PUT", request_param="type=editorganisation", renderer="json"
    )
    def editOrg(self):
        token = self.request.headers["gktoken"]
        authDetails = authCheck(token)
        if authDetails["auth"] == False:
            return {"gkstatus": enumdict["UnauthorisedAccess"]}
        else:
            with eng.begin() as con:
                dataset = self.request.json_body
                result = con.execute(
                    gkdb.organisation.update()
                    .where(gkdb.organisation.c.orgcode == dataset["orgcode"])
                    .values(dataset)
                )
                return {"gkstatus": enumdict["Success"]}


    @view_config(request_method="DELETE", renderer="json")
    def deleteOrg(self):
        """Deletes an organisation. Only admin role can delete"""
        token = self.request.headers["gktoken"]
        authDetails = authCheck(token)
        if authDetails["auth"] == False:
            return {"gkstatus": enumdict["UnauthorisedAccess"]}
        userRoleData = getUserRole(
            authDetails["userid"], authDetails["orgcode"]
        )
        userRole = userRoleData["gkresult"]["userrole"]
        if userRole != -1:
            return {"gkstatus": enumdict["BadPrivilege"]}

        with eng.begin() as con:
            orgdata = con.execute(
                "select orgname as orgname, yearstart as yearstart, orgtype as orgtype from organisation where orgcode=%d"
                % authDetails["orgcode"]
            )
            getorgdata = orgdata.fetchone()
            lastdate = datetime.strftime(
                getorgdata["yearstart"] - timedelta(1), "%Y-%m-%d"
            )
            checkorg = con.execute(
                "select orgcode from organisation where orgname='%s' and orgtype='%s' and yearend='%s'"
                % (
                    str(getorgdata["orgname"]),
                    str(getorgdata["orgtype"]),
                    lastdate,
                )
            )
            checkorgcode = checkorg.fetchone()
            # remove the orgcode from all users who are part of it
            orgUsers = con.execute(
                select([gkdb.organisation.c.users]).where(
                    gkdb.organisation.c.orgcode == authDetails["orgcode"]
                )
            ).fetchone()
            if type(orgUsers["users"]) == str:
                orgUsers = json.loads(orgUsers["users"])
            elif type(orgUsers["users"]) == dict:
                orgUsers = orgUsers["users"]
            else:
                orgUsers = {}
            for orgUser in orgUsers:
                con.execute(
                    "update gkusers set orgs = orgs - '%s' WHERE userid = %d;"
                    % (str(authDetails["orgcode"]), int(orgUser))
                )

            # delete the org
            result = con.execute(
                gkdb.organisation.delete().where(
                    gkdb.organisation.c.orgcode == authDetails["orgcode"]
                )
            )
            if result.rowcount == 1:
                result = con.execute(
                    select(
                        [
                            func.count(gkdb.organisation.c.orgcode).label(
                                "ocount"
                            )
                        ]
                    )
                )
                orgcount = result.fetchone()
                if orgcount["ocount"] == 0:
                    result = con.execute(gkdb.signature.delete())
            if checkorgcode != None:
                resetroflag = con.execute(
                    "update organisation set roflag = 0 where orgcode='%d'"
                    % (checkorgcode["orgcode"])
                )

            return {"gkstatus": enumdict["Success"]}


    @view_config(request_method="GET", request_param="type=exists", renderer="json")
    def Orgexists(self):
        with eng.connect() as con:
            orgtype = self.request.params["orgtype"]
            orgname = self.request.params["orgname"]
            finstart = self.request.params["finstart"]
            finend = self.request.params["finend"]
            orgncount = con.execute(
                select(
                    [func.count(gkdb.organisation.c.orgcode).label("orgcode")]
                ).where(
                    and_(
                        gkdb.organisation.c.orgname == orgname,
                        gkdb.organisation.c.orgtype == orgtype,
                        gkdb.organisation.c.yearstart == finstart,
                        gkdb.organisation.c.yearend == finend,
                    )
                )
            )
            org = orgncount.fetchone()
            if org["orgcode"] != 0:
                return {"gkstatus": enumdict["DuplicateEntry"]}
            else:
                return {"gkstatus": enumdict["Success"]}


    @view_config(
        request_method="GET", route_name="organisation_orgname", renderer="json"
    )
    def orgNameExists(self):
        # check if user is valid
        try:
            user_token = self.request.headers["gkusertoken"]
        except:
            return {"gkstatus": gkcore.enumdict["UnauthorisedAccess"]}

        userAuthDetails = userAuthCheck(user_token)

        if userAuthDetails["auth"] == False:
            return {"gkstatus": enumdict["UnauthorisedAccess"]}
        # proceed to check if org name exists
        with eng.connect() as con:
            org_exists = con.execute(
                gkdb.organisation
                .select()
                .where(
                    gkdb.organisation.c.orgname == self.request.matchdict["orgname"],
                )
            ).rowcount
            if bool(org_exists):
                return {"gkstatus": enumdict["DuplicateEntry"]}
            else:
                return {"gkstatus": enumdict["Success"]}


    @view_config(request_param="orgcode", request_method="GET", renderer="json")
    def getOrgcode(self):
        try:
            token = self.request.headers["gktoken"]
        except:
            return {"gkstatus": enumdict["UnauthorisedAccess"]}
        authDetails = authCheck(token)
        if authDetails["auth"] == False:
            return {"gkstatus": enumdict["UnauthorisedAccess"]}
        else:
            return {"gkstatus": enumdict["Success"], "gkdata": authDetails["orgcode"]}


    @view_config(
        request_method="PUT", request_param="type=getinventory", renderer="json"
    )
    def getinventory(self):
        token = self.request.headers["gktoken"]
        authDetails = authCheck(token)
        if authDetails["auth"] == False:
            return {"gkstatus": enumdict["UnauthorisedAccess"]}
        else:
            with eng.begin() as con:
                userRoleData = getUserRole(
                    authDetails["userid"], authDetails["orgcode"]
                )
                userRole = userRoleData["gkresult"]["userrole"]
                dataset = self.request.json_body
                if userRole == -1:
                    result = con.execute(
                        gkdb.organisation.update()
                        .where(gkdb.organisation.c.orgcode == authDetails["orgcode"])
                        .values(dataset)
                    )
                    return {"gkstatus": enumdict["Success"]}
                return {"gkstatus": enumdict["BadPrivilege"]}


    @view_config(
        route_name="organisation_attachment",
        request_method="GET",
        renderer="json",
    )
    def getattachment(self):
        try:
            token = self.request.headers["gktoken"]
        except:
            return {"gkstatus": enumdict["UnauthorisedAccess"]}
        authDetails = authCheck(token)
        if authDetails["auth"] == False:
            return {"gkstatus": enumdict["UnauthorisedAccess"]}
        else:
            with eng.connect() as con:
                result = con.execute(
                    select([gkdb.organisation.c.logo]).where(
                        gkdb.organisation.c.orgcode == authDetails["orgcode"]
                    )
                )
                row = result.fetchone()
                return {"gkstatus": enumdict["Success"], "logo": row["logo"]}


    # Code for fetching organisations bankdetails depending on organisation code.
    @view_config(
        request_method="GET",
        request_param="orgbankdetails",
        renderer="json",
    )
    def getorgbankdetails(self):
        token = self.request.headers["gktoken"]
        authDetails = authCheck(token)
        if authDetails["auth"] == False:
            return {"gkstatus": enumdict["UnauthorisedAccess"]}
        else:
            with eng.connect() as con:
                result = con.execute(
                    select([gkdb.organisation.c.bankdetails]).where(
                        gkdb.organisation.c.orgcode == authDetails["orgcode"]
                    )
                )
                row = result.fetchone()
                if row["bankdetails"] == None:
                    bankdetails = ""
                else:
                    bankdetails = row["bankdetails"]

                orgbankDetails = {"bankdetails": bankdetails}
                return {"gkstatus": enumdict["Success"], "gkbankdata": orgbankDetails}


    """
    Purpose: Get groupcode of group 'Current Liabilities' and subgroup 'Duties & Taxes'
    We have a default subgroup 'Duties & Taxes' under group 'Current Liabilities'.
    All accounts for GST are created under this subgroup.
    This function returns the groupcode of that group and subgroup so that front end can trigger creation of accounts.
    """

    @view_config(
        request_method="GET",
        renderer="json",
        route_name="organisation_gst_accounts_codes",
    )
    def getGSTGroupCode(self):
        token = self.request.headers["gktoken"]
        authDetails = authCheck(token)
        if authDetails["auth"] == False:
            return {"gkstatus": enumdict["UnauthorisedAccess"]}
        else:
            with eng.connect() as con:
                result = con.execute(
                    select([gkdb.groupsubgroups.c.groupcode]).where(
                        and_(
                            gkdb.groupsubgroups.c.orgcode == authDetails["orgcode"],
                            gkdb.groupsubgroups.c.groupname == "Duties & Taxes",
                        )
                    )
                )
                grOup = con.execute(
                    select([gkdb.groupsubgroups.c.groupcode]).where(
                        and_(
                            gkdb.groupsubgroups.c.orgcode == authDetails["orgcode"],
                            gkdb.groupsubgroups.c.groupname == "Current Liabilities",
                        )
                    )
                )
                grOupName = grOup.fetchone()
                row = result.fetchone()
                if result.rowcount != 0 and row["groupcode"] != None:
                    return {
                        "gkstatus": enumdict["Success"],
                        "subgroupcode": int(row["groupcode"]),
                        "groupcode": int(grOupName["groupcode"]),
                    }
                else:
                    return {
                        "gkstatus": enumdict["Success"],
                        "subgroupcode": "New",
                        "groupcode": int(grOupName["groupcode"]),
                    }


    """
    Purpose: Get all accounts of group 'Current Liabilities' and subgroup 'Duties & Taxes' created for GST.
    We have a default subgroup 'Duties & Taxes' under group 'Current Liabilities'.
    All accounts for GST are created under this subgroup.
    This function returns those accounts.
    """

    @view_config(
        request_method="GET",
        renderer="json",
        route_name="organisation_gst_accounts",
    )
    def getGSTGaccounts(self):
        token = self.request.headers["gktoken"]
        authDetails = authCheck(token)
        if authDetails["auth"] == False:
            return {"gkstatus": enumdict["UnauthorisedAccess"]}
        else:
            with eng.connect() as con:
                result = con.execute(
                    select([gkdb.groupsubgroups.c.groupcode]).where(
                        and_(
                            gkdb.groupsubgroups.c.orgcode == authDetails["orgcode"],
                            gkdb.groupsubgroups.c.groupname == "Duties & Taxes",
                        )
                    )
                )
                row = result.fetchone()
                accounts = []
                if result.rowcount != 0 and row["groupcode"] != None:
                    accountsdata = con.execute(
                        select([gkdb.accounts.c.accountname]).where(
                            and_(
                                gkdb.accounts.c.orgcode == authDetails["orgcode"],
                                gkdb.accounts.c.groupcode == row["groupcode"],
                            )
                        )
                    )
                    accountslist = accountsdata.fetchall()
                    for account in accountslist:
                        accounts.append(account["accountname"])
                    return {"gkstatus": enumdict["Success"], "accounts": accounts}
                else:
                    return {"gkstatus": enumdict["ConnectionFailed"]}


    # returns avfalag , to decide auto voucher creation
    @view_config(request_method="GET", request_param="autovoucher", renderer="json")
    def getAVflag(self):
        token = self.request.headers["gktoken"]
        authDetails = authCheck(token)
        if authDetails["auth"] == False:
            return {"gkstatus": enumdict["UnauthorisedAccess"]}
        else:
            with eng.connect() as con:
                result = con.execute(
                    select([gkdb.organisation.c.avflag]).where(
                        gkdb.organisation.c.orgcode == authDetails["orgcode"]
                    )
                )
                return {
                    "gkstatus": enumdict["Success"],
                    "autovoucher": result["avflag"],
                }


    @view_config(
        request_method="GET",
        request_param="type=sameyear",
        renderer="json",
    )
    def sameYear(self):
        token = self.request.headers["gktoken"]
        authDetails = authCheck(token)
        if authDetails["auth"] == False:
            return {"gkstatus": enumdict["UnauthorisedAccess"]}
        else:
            with eng.connect() as con:
                result = con.execute(
                    select(
                        [gkdb.organisation.c.yearstart, gkdb.organisation.c.yearend]
                    ).where(gkdb.organisation.c.orgcode == authDetails["orgcode"])
                )
                orgfy = result.fetchall()
                allorg = con.execute(
                    "select orgcode, orgname, orgtype from organisation where yearstart='%s' and yearend= '%s'"
                    % (orgfy[0]["yearstart"], orgfy[0]["yearend"])
                )
                allorgname = allorg.fetchall()
                orgs = []
                for row in allorgname:
                    orgs.append(
                        {
                            "orgname": row["orgname"],
                            "orgtype": row["orgtype"],
                            "orgcode": row["orgcode"],
                            "yearstart": str(orgfy[0]["yearstart"]),
                            "yearend": str(orgfy[0]["yearend"]),
                        }
                    )
                    orgs.sort()

                return {"gkstatus": enumdict["Success"], "gkdata": orgs}


    # TODO: does the same as getOrgStateGstin, must merge the two methods
    @view_config(
        request_method="GET",
        renderer="json",
        route_name="organisation_gstin",
    )
    def getGstin(self):
        token = self.request.headers["gktoken"]
        authDetails = authCheck(token)
        if authDetails["auth"] == False:
            return {"gkstatus": enumdict["UnauthorisedAccess"]}
        else:
            with eng.connect() as con:
                result = con.execute(
                    select(
                        [gkdb.organisation.c.gstin, gkdb.organisation.c.orgstate]
                    ).where(gkdb.organisation.c.orgcode == authDetails["orgcode"])
                ).fetchone()

                stateCode = con.execute(
                    select([gkdb.state.c.statecode]).where(
                        gkdb.state.c.statename == result["orgstate"]
                    )
                ).scalar()

                payload = {
                    "gstin": result["gstin"],
                    "stateCode": stateCode,
                }

                return {"gkstatus": enumdict["Success"], "gkresult": payload}


    @view_config(
        request_method="GET",
        renderer="json",
        request_param="type=gstin_by_state",
    )
    def getOrgStateGstin(self):
        token = self.request.headers["gktoken"]
        authDetails = authCheck(token)
        if authDetails["auth"] == False:
            return {"gkstatus": enumdict["UnauthorisedAccess"]}
        else:
            with eng.connect() as con:
                gstinResult = con.execute(
                    "select gstin ->> '%d' as stgstin from organisation where gstin ? '%d' and orgcode = %d "
                    % (
                        int(self.request.params["statecode"]),
                        int(self.request.params["statecode"]),
                        int(authDetails["orgcode"]),
                    )
                )
                gstinval = ""
                if gstinResult.rowcount > 0:
                    gstinrow = gstinResult.fetchone()
                    gstinval = str(gstinrow["stgstin"])
                return {"gkstatus": enumdict["Success"], "gkresult": gstinval}


    @view_config(
        request_method="DELETE", route_name="organisation_rm_user", renderer="json"
    )
    def removeUserfromOrg(self):
        """Removes a user from the current organisation

        Conditions:
        1. Only admin can delete other users
        2. If the user to delete has admin role, Make sure the org should have atleast 1 admin before deleting the user
        """
        # auth checks
        try:
            token = self.request.headers["gktoken"]
            user_token = self.request.headers["gkusertoken"]
            request_body = self.request.json_body
        except:
            return {"gkstatus": gkcore.enumdict["UnauthorisedAccess"]}
        authDetails = authCheck(token)
        userAuthDetails = userAuthCheck(user_token)
        if authDetails["auth"] == False:
            return {"gkstatus": enumdict["UnauthorisedAccess"]}
        if userAuthDetails["auth"] == False:
            return {"gkstatus": enumdict["UnauthorisedAccess"]}
        # check if the user is admin of the current org
        if authDetails["userrole"] != -1:
            return {"gkstatus": enumdict["BadPrivilege"]}

        with eng.begin() as con:
        # remove user keys in org table & org keys in user table
            admin_count = len(self.orgAdminList(con, authDetails["orgcode"]))
            # check if user is trying to remove self
            # do not allow self removal if org has one admin only
            if authDetails["userid"] == request_body["userid"] and admin_count == 1:
                return {"gkstatus": enumdict["ActionDisallowed"]}
            # delete user from organisation users jsonb list
            con.execute(
                f"update organisation set users = users - '{request_body['userid']}' WHERE orgcode = {authDetails['orgcode']}"
            )
            # delete org key in corresponding gkuser column
            con.execute(
                f"update gkusers set orgs = orgs - '{authDetails['orgcode']}' WHERE userid = {request_body['userid']}"
            )
            return {"gkstatus": enumdict["Success"]}


    def orgAdminList(self, con, org_code):
        """
        Get the list of all admins of an org
        """
        # first, get the org users
        org_info = con.execute(
            select([gkdb.organisation]).where(
                and_(
                    gkdb.organisation.c.orgcode == org_code,
                )
            )
        ).fetchone()
        # loop throught the users & look for users with
        # admin roles & append them to admin_list array
        admin_list: list = []
        for usr_code in org_info["users"].keys():
            user_info = con.execute(
                select([gkdb.gkusers]).where(
                    and_(gkdb.gkusers.c.userid == usr_code)
                )
            ).fetchone()
            if user_info["orgs"][str(org_code)]["userrole"] == -1:
                admin_list.append(usr_code)
        return admin_list
