from gkcore.utils import get_secret
from pyramid.security import Allowed, Denied
import jwt
from sqlalchemy.sql import select
from gkcore.models.meta import eng
from gkcore.models.gkdb import gkusers


class SecurityPolicy:
    def __init__(self, secret):
        self.secret = secret

    def identity(self, request):
        """ Returns identity as a (user_id, org_code) tuple. """
        token = request.headers.get("gktoken", None)
        if token is None:
            return None
        try:
            identity = jwt.decode(token, self.secret, algorithms=["HS256"])
        except Exception:
            return None ## raise exception token not correct
        else:
            with eng.connect() as connection:
                user = connection.execute(
                    select(gkusers.c).where(
                        gkusers.c.userid == identity["userid"],
                    )
                ).fetchone()
                if user:
                    identity["user"] = dict(user.items())
                    return identity
                return None

    def authenticated_userid(self, request):
        """ Return a user_id of authenticated user. """
        identity = self.identity(request)
        if identity is None:
            return None
        return identity["userid"]

    def permits(self, request, context, permission):
        identity = self.identity(request)
        if identity is None:
            return Denied("User is not signed in.")
        org_code = identity.get("orgcode", None)
        if not org_code:
            return Denied("Organization not found.")
        user_org_role = identity["user"]["orgs"][str(org_code)]["userrole"]
        allowed = ["read"]
        # admin: -1, manager: 0, operator: 1, auditor: 2, godown incharge: 3
        if user_org_role == -1:
            allowed = ["read", "write", "update", "delete", "delete", "admin"]
        if permission in allowed:
            return Allowed(
                "Access granted for user %s.",
                identity["user"]["username"],
            )
        return Denied(
            "Access denied for user %s.",
            identity["user"]["username"],
        )


def includeme(config):
    # Add security policy
    config.set_security_policy(
        SecurityPolicy(secret=get_secret())
    )
