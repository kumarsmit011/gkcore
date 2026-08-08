from sqlalchemy.sql.expression import text
from sqlalchemy import select
from gkcore.models.gkdb import organisation


def get_conf(con, confType, orgcode, userid, pageid, confid):
    config = {}
    if confType == "user":
        orgconf = [str(orgcode), "userconf"]

        if pageid:
            orgconf.append(pageid)
            if confid:
                orgconf.append(confid)
        configRow = con.execute(
            text("select u.orgs#>:orgconf as userconf from gkusers u where userid = :userid;"),
            orgconf = "{"+",".join(orgconf)+"}",
            userid = userid,
        ).fetchone()
        config = configRow["userconf"]
    elif confType == "org":
        if pageid:
            if confid:
                orgconf = "{"+pageid+","+confid+"}"
            else:
                orgconf = "{"+pageid+"}"
            configRow = con.execute(
                text("select org.orgconf#>:orgconf as orgconf from organisation org where orgcode = :orgcode;"),
                orgconf = orgconf,
                orgcode = orgcode,
            ).fetchone()
        else:
            configRow = con.execute(
                select([organisation.c.orgconf]).where(
                    organisation.c.orgcode == orgcode,
                )
            ).fetchone()
        config = configRow["orgconf"]
    return config
