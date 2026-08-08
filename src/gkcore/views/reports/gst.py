from gkcore import eng, enumdict
from gkcore.utils import authCheck
from gkcore.models.gkdb import (
    accounts,
    groupsubgroups,
    organisation,
    state,
)
from sqlalchemy.sql import select
from sqlalchemy.engine.base import Connection
from sqlalchemy import and_
from pyramid.request import Request
from pyramid.view import view_defaults, view_config
from gkcore.views.reports.helpers.balance import calculateBalance


@view_defaults(request_method="GET")
class api_gst_calc(object):
    def __init__(self, request):
        self.request = Request
        self.request = request
        self.con = Connection

    @view_config(route_name="gst-calc", renderer="json")
    def GSTCalc(self):
        """
        Purpose:
        takes list of accounts for CGST,SGST,IGST and CESS at Input and Output side,
        Returns list of accounts with their closing balances.
        Description:
        This API will return list of all accounts for input and output side created by the user for GST calculation.
        The function takes json_body which will have 8 key: value pares.
        Each  key denoting the tax and value will be list of accounts.
        The keys of this json_body will be as follows.
        * CGSTIn,
        * CGSTOut,
        * SGSTIn,
        * SGSTOut,
        * IGSTIn,
        * IGSTOut,
        * CESSIn,
        * CESSOut.
        Function will also need the range for which calculatBalance is to be called for getting actual balances.
        The function will loop through every list getting closing balance for all the accounts.
        Then it will sum up all the balances for that list.
        Then it will compare total in amount with total out amount and will decide if it is payable or carried forward.
        Following code will return a dictionary which will have structure like  gstDict = {"cgstin":{"accname":calculated balance,...,"to        talCGSTIn":value},"cgstout":{"accname":calculatebalance ,...,"totalCGSTOut":value},.....,"cgstpayable":value,"sgstpayable":value,        ....,"cgstcrdfwd":value,"sgstcrdfwd":value,.....}
        """

        try:
            token = self.request.headers["gktoken"]
        except:
            return {"gkstatus": enumdict["UnauthorisedAccess"]}
        authDetails = authCheck(token)
        if authDetails["auth"] == False:
            return {"gkstatus": enumdict["UnauthorisedAccess"]}
        else:
            try:
                self.con = eng.connect()
                # check if data is supplied as json or url params
                try:
                    dataset = self.request.json_body
                except:
                    dataset = self.request.params

                stateD = dataset["statename"]
                # Get abbreviation of state
                stateA = self.con.execute(
                    select([state.c.abbreviation]).where(state.c.statename == stateD)
                )
                stateABV = stateA.fetchone()
                # Retrived individual data from dictionary
                startDate = dataset["startdate"]
                endDate = dataset["enddate"]
                result = self.con.execute(
                    select([organisation.c.yearstart]).where(
                        organisation.c.orgcode == authDetails["orgcode"]
                    )
                )
                fStart = result.fetchone()
                financialStart = fStart["yearstart"]

                # get list of accountCodes for each type of taxes for their input and output taxes.
                grp = self.con.execute(
                    select([groupsubgroups.c.groupcode]).where(
                        and_(
                            groupsubgroups.c.groupname == "Duties & Taxes",
                            groupsubgroups.c.orgcode == authDetails["orgcode"],
                        )
                    )
                )
                grpCode = grp.fetchone()

                # Create string which has taxname with state abbreviation for selecting accounts
                Cgstin = "CGSTIN_" + stateABV["abbreviation"]
                cgstout = "CGSTOUT_" + stateABV["abbreviation"]
                sgstin = "SGSTIN_" + stateABV["abbreviation"]
                sgstout = "SGSTOUT_" + stateABV["abbreviation"]
                igstin = "IGSTIN_" + stateABV["abbreviation"]
                igstout = "IGSTOUT_" + stateABV["abbreviation"]
                cessin = "CESSIN_" + stateABV["abbreviation"]
                cessout = "CESSOUT_" + stateABV["abbreviation"]

                # Declare public variables to store total
                totalCGSTIn = 0.00
                totalCGSTOut = 0.00
                totalSGSTOut = 0.00
                totalSGSTIn = 0.00
                totalSGSTOut = 0.00
                totalIGSTIn = 0.00
                totalIGSTOut = 0.00
                totalCESSIn = 0.00
                totalCESSOut = 0.00
                # These variables are to store Payable and carried forward amount
                cgstPayable = 0.00
                cgstCrdFwd = 0.00
                sgstPayable = 0.00
                sgstCrdFwd = 0.00
                igstPayable = 0.00
                igstCrdFwd = 0.00
                cessPayable = 0.00
                cessCrdFwd = 0.00
                gstDict = {}

                cIN = self.con.execute(
                    select([accounts.c.accountname, accounts.c.accountcode]).where(
                        and_(
                            accounts.c.accountname.like(Cgstin + "%"),
                            accounts.c.orgcode == authDetails["orgcode"],
                            accounts.c.groupcode == grpCode["groupcode"],
                        )
                    )
                )
                CGSTIn = cIN.fetchall()
                cgstin = {}
                if CGSTIn != None:
                    for cin in CGSTIn:
                        calbalData = calculateBalance(
                            self.con,
                            cin["accountcode"],
                            financialStart,
                            startDate,
                            endDate,
                        )
                        # fill dictionary with account name and its balance.
                        cgstin[cin["accountname"]] = "%.2f" % (
                            float(calbalData["curbal"])
                        )
                        # calculate total cgst in amount by adding balance of each account in every iteration.
                        totalCGSTIn = totalCGSTIn + calbalData["curbal"]
                # Populate dictionary to be returned with cgstin and total values
                gstDict["cgstin"] = cgstin
                gstDict["totalCGSTIn"] = "%.2f" % (float(totalCGSTIn))

                cOUT = self.con.execute(
                    select([accounts.c.accountname, accounts.c.accountcode]).where(
                        and_(
                            accounts.c.accountname.like(cgstout + "%"),
                            accounts.c.orgcode == authDetails["orgcode"],
                            accounts.c.groupcode == grpCode["groupcode"],
                        )
                    )
                )
                CGSTOut = cOUT.fetchall()
                cgstout = {}
                if CGSTOut != None:
                    for cout in CGSTOut:
                        calbalData = calculateBalance(
                            self.con,
                            cout["accountcode"],
                            financialStart,
                            startDate,
                            endDate,
                        )
                        cgstout[cout["accountname"]] = "%.2f" % (
                            float(calbalData["curbal"])
                        )
                        totalCGSTOut = totalCGSTOut + calbalData["curbal"]
                gstDict["cgstout"] = cgstout
                gstDict["totalCGSTOut"] = "%.2f" % (float(totalCGSTOut))

                # calculate carried forward amount or payable.
                if totalCGSTIn > totalCGSTOut:
                    cgstCrdFwd = totalCGSTIn - totalCGSTOut
                    gstDict["cgstcrdfwd"] = "%.2f" % (float(cgstCrdFwd))
                else:
                    cgstPayable = totalCGSTOut - totalCGSTIn
                    gstDict["cgstpayable"] = "%.2f" % (float(cgstPayable))

                # For state tax
                sIN = self.con.execute(
                    select([accounts.c.accountname, accounts.c.accountcode]).where(
                        and_(
                            accounts.c.accountname.like(sgstin + "%"),
                            accounts.c.orgcode == authDetails["orgcode"],
                            accounts.c.groupcode == grpCode["groupcode"],
                        )
                    )
                )
                SGSTIn = sIN.fetchall()
                sgstin = {}
                if SGSTIn != None:
                    for sin in SGSTIn:
                        calbalData = calculateBalance(
                            self.con,
                            sin["accountcode"],
                            financialStart,
                            startDate,
                            endDate,
                        )
                        sgstin[sin["accountname"]] = "%.2f" % (
                            float(calbalData["curbal"])
                        )
                        totalSGSTIn = totalSGSTIn + calbalData["curbal"]
                    # Populate dictionary to be returned with cgstin and total values
                    gstDict["sgstin"] = sgstin
                    gstDict["totalSGSTIn"] = "%.2f" % (float(totalSGSTIn))

                sOUT = self.con.execute(
                    select([accounts.c.accountname, accounts.c.accountcode]).where(
                        and_(
                            accounts.c.accountname.like(sgstout + "%"),
                            accounts.c.orgcode == authDetails["orgcode"],
                            accounts.c.groupcode == grpCode["groupcode"],
                        )
                    )
                )
                SGSTOut = sOUT.fetchall()
                sgstout = {}
                if SGSTOut != None:
                    for sout in SGSTOut:
                        calbalData = calculateBalance(
                            self.con,
                            sout["accountcode"],
                            financialStart,
                            startDate,
                            endDate,
                        )
                        sgstout[sout["accountname"]] = "%.2f" % (
                            float(calbalData["curbal"])
                        )
                        totalSGSTOut = totalSGSTOut + calbalData["curbal"]
                gstDict["sgstout"] = sgstout
                gstDict["totalSGSTOut"] = "%.2f" % (float(totalSGSTOut))

                # calculate carried forward amount or payable.
                if totalSGSTIn > totalSGSTOut:
                    sgstCrdFwd = totalSGSTIn - totalSGSTOut
                    gstDict["sgstcrdfwd"] = "%.2f" % (float(sgstCrdFwd))
                else:
                    sgstPayable = totalSGSTOut - totalSGSTIn
                    gstDict["sgstpayable"] = "%.2f" % (float(sgstPayable))

                # For Inter state tax

                iIN = self.con.execute(
                    select([accounts.c.accountname, accounts.c.accountcode]).where(
                        and_(
                            accounts.c.accountname.like(igstin + "%"),
                            accounts.c.orgcode == authDetails["orgcode"],
                            accounts.c.groupcode == grpCode["groupcode"],
                        )
                    )
                )
                IGSTIn = iIN.fetchall()
                igstin = {}
                if IGSTIn != None:
                    for iin in IGSTIn:
                        calbalData = calculateBalance(
                            self.con,
                            iin["accountcode"],
                            financialStart,
                            startDate,
                            endDate,
                        )
                        igstin[iin["accountname"]] = "%.2f" % (
                            float(calbalData["curbal"])
                        )
                        totalIGSTIn = totalIGSTIn + calbalData["curbal"]
                gstDict["igstin"] = igstin
                gstDict["totalIGSTIn"] = "%.2f" % (float(totalIGSTIn))

                iOUT = self.con.execute(
                    select([accounts.c.accountname, accounts.c.accountcode]).where(
                        and_(
                            accounts.c.accountname.like(igstout + "%"),
                            accounts.c.orgcode == authDetails["orgcode"],
                            accounts.c.groupcode == grpCode["groupcode"],
                        )
                    )
                )
                IGSTOut = iOUT.fetchall()
                igstout = {}
                if IGSTOut != None:
                    for iout in IGSTOut:
                        calbalData = calculateBalance(
                            self.con,
                            iout["accountcode"],
                            financialStart,
                            startDate,
                            endDate,
                        )
                        igstout[iout["accountname"]] = "%.2f" % (
                            float(calbalData["curbal"])
                        )
                        totalIGSTOut = totalIGSTOut + calbalData["curbal"]
                gstDict["igstout"] = igstout
                gstDict["totalIGSTOut"] = "%.2f" % (float(totalIGSTOut))

                # calculate carried forward amount or payable.
                if totalIGSTIn > totalIGSTOut:
                    igstCrdFwd = totalIGSTIn - totalIGSTOut
                    gstDict["IgstCrdFwd"] = "%.2f" % (float(igstCrdFwd))
                else:
                    igstPayable = totalIGSTOut - totalIGSTIn
                    gstDict["IgstPayable"] = "%.2f" % (float(igstPayable))

                # For cess tax
                csIN = self.con.execute(
                    select([accounts.c.accountname, accounts.c.accountcode]).where(
                        and_(
                            accounts.c.accountname.like(cessin + "%"),
                            accounts.c.orgcode == authDetails["orgcode"],
                            accounts.c.groupcode == grpCode["groupcode"],
                        )
                    )
                )
                CESSIn = csIN.fetchall()
                cssin = {}
                if CESSIn != None:
                    for csin in CESSIn:
                        calbalData = calculateBalance(
                            self.con,
                            csin["accountcode"],
                            financialStart,
                            startDate,
                            endDate,
                        )
                        cssin[csin["accountname"]] = "%.2f" % (
                            float(calbalData["curbal"])
                        )
                        totalCESSIn = totalCESSIn + calbalData["curbal"]
                gstDict["cessin"] = cssin
                gstDict["totalCESSIn"] = "%.2f" % (float(totalCESSIn))

                csOUT = self.con.execute(
                    select([accounts.c.accountname, accounts.c.accountcode]).where(
                        and_(
                            accounts.c.accountname.like(cessout + "%"),
                            accounts.c.orgcode == authDetails["orgcode"],
                            accounts.c.groupcode == grpCode["groupcode"],
                        )
                    )
                )
                CESSOut = csOUT.fetchall()
                cssout = {}
                if CESSOut != None:
                    for csout in CESSOut:
                        calbalData = calculateBalance(
                            self.con,
                            csout["accountcode"],
                            financialStart,
                            startDate,
                            endDate,
                        )
                        cssout[csout["accountname"]] = "%.2f" % (
                            float(calbalData["curbal"])
                        )
                        totalCESSOut = totalCESSOut + calbalData["curbal"]
                gstDict["cessout"] = cssout
                gstDict["totalCESSOut"] = "%.2f" % (float(totalCESSOut))

                # calculate carried forward amount or payable.
                if totalCESSIn > totalCESSOut:
                    cessCrdFwd = totalCESSIn - totalCESSOut
                    gstDict["cessCrdFwd"] = "%.2f" % (float(cessCrdFwd))
                else:
                    cessPayable = totalCESSOut - totalCESSIn
                    gstDict["cesspayable"] = "%.2f" % (float(cessPayable))

                return {"gkstatus": enumdict["Success"], "gkresult": gstDict}
            except:
                return {"gkstatus": enumdict["ConnectionFailed"]}
            finally:
                self.con.close()
