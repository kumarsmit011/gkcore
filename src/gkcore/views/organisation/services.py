from sqlalchemy import select
from gkcore import eng
from gkcore.models.gkdb import organisation

def get_organisation_profile(org_code):
    """Return basic details of an organisation based on the given org code."""
    with eng.connect() as con:
        org_details = con.execute(
            select([organisation])
            .where(organisation.c.orgcode == org_code)
        ).fetchone()
        organisation_profile = {
            "orgcode": org_details["orgcode"],
            "orgname": org_details["orgname"],
            "orgaddr": org_details["orgaddr"],
            "orgcity": org_details["orgcity"],
            "orgstate": org_details["orgstate"],
            "orgpincode": org_details["orgpincode"],
            "orgcountry": org_details["orgcountry"],
            "orgtelno": org_details["orgtelno"],
            "orgemail": org_details["orgemail"],
            "orgwebsite": org_details["orgwebsite"],
            "orgpan": org_details["orgpan"],
            "gstin": org_details["gstin"],
            "tin": org_details["tin"],
            "bankdetails": org_details["bankdetails"],
        }
        return organisation_profile
