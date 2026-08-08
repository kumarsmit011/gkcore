import logging
import jwt
import traceback
from gkcore.models import eng, gkdb
from sqlalchemy.sql.expression import text
from sqlalchemy.sql import select, and_
from Crypto.PublicKey import RSA
from datetime import date, timedelta
import calendar
from gkcore import enumdict
from sqlalchemy.inspection import inspect


def gk_log(name: str = __name__):
    """
    A wrapper around python's logging library, created for easy use across gkcore to log events
    Supports all `logging` module's methods. First argument must be `__name__`
    """
    return logging.getLogger(name)


def generate_signature(con):
    key = RSA.generate(2560)
    privatekey = key.exportKey("PEM")
    con.execute(gkdb.signature.insert(), [{"secretcode": privatekey}])
    return privatekey


def get_secret():
    with eng.connect() as con:
        return con.execute(select([gkdb.signature])).scalar()


def generateAuthToken(con, tokenItems, tokenType="userorg"):
    try:
        secret = con.execute(select([gkdb.signature])).scalar()
        if not secret:
            secret = generate_signature(con)
        if len(secret) <= 20:
            con.execute(gkdb.signature.delete())
            secret = generate_signature(con)
        if tokenType == "user":
            token = jwt.encode(
                {"username": tokenItems["username"], "userid": tokenItems["userid"]},
                secret,
                algorithm="HS256",
            )
        else:  # if userorg
            token = jwt.encode(
                {"orgcode": tokenItems["orgcode"], "userid": tokenItems["userid"]},
                secret,
                algorithm="HS256",
            )
        token = token.decode("ascii")
        return token
    except:
        print(traceback.format_exc())
        return -1


def userAuthCheck(token):
    """
    Purpose: on every request check if userid and username are valid combinations
    """
    try:
        tokendict = jwt.decode(token, get_secret(), algorithms=["HS256"])
        tokendict["auth"] = True
        tokendict["username"] = tokendict["username"]
        tokendict["userid"] = int(tokendict["userid"])
        return tokendict
    except:
        tokendict = {"auth": False}
        return tokendict


def authCheck(token):
    """
    Purpose: on every request check if userid and orgcode are valid combinations
    """
    try:
        tokendict = jwt.decode(token, get_secret(), algorithms=["HS256"])
        tokendict["auth"] = True
        tokendict["orgcode"] = int(tokendict["orgcode"])
        tokendict["userid"] = int(tokendict["userid"])
        # get the user role of current org
        try:
            user_info = (
                eng.connect()
                .execute(
                    select([gkdb.gkusers]).where(
                        and_(
                            gkdb.gkusers.c.userid == tokendict["userid"],
                        )
                    )
                )
                .fetchone()
            )
            tokendict["userrole"] = user_info["orgs"][str(tokendict["orgcode"])][
                "userrole"
            ]
        except Exception as e:
            print(e)
        return tokendict
    except:
        tokendict = {"auth": False}
        return tokendict


def generate_month_start_end_dates(start_date, end_date):
    """Returns a list of months between the start date and end date as tuples with
    format, ("month name", "start date", "end date").
    """
    month_start_end_dates = []
    while start_date < end_date:
        end_day = calendar.monthrange(start_date.year, start_date.month)[1]
        month_end_date = date(start_date.year, start_date.month, end_day)
        next_month_start_date = month_end_date + timedelta(1)
        if next_month_start_date < end_date:
            month_start_end_dates.append(
                (start_date.strftime('%B'), start_date, month_end_date)
            )
        else:
            month_start_end_dates.append(
                (start_date.strftime('%B'), start_date, end_date)
            )
        start_date = next_month_start_date
    return month_start_end_dates

def getUserRole(userid, orgcode):
    with eng.connect() as con:
        roleQuery = con.execute(
            text("select u.orgs#>'{:orgcode,userrole}' as userrole from gkusers u where userid = :userid;"),
            orgcode = orgcode,
            userid = userid,
        )

        if roleQuery.rowcount == 1:
            row = roleQuery.fetchone()
            User = {"userrole": row["userrole"]}
            return {"gkstatus": enumdict["Success"], "gkresult": User}
        else:
            return {
                "gkstatus": enumdict["ConnectionFailed"],
                "gkmessage": "User may not be part of the Org. Contact admin",
            }


def get_row(con, table, pk):
    """Fetch the table row for the given pk"""
    return con.execute(
        table.select().where(
            list(inspect(table).primary_key)[0] == pk
        )
    ).fetchone()
