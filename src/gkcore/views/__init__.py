from pyramid.view import view_config
import sys, traceback
from gkcore import enumdict
from sqlalchemy.exc import IntegrityError
from pydantic import ValidationError


@view_config(context=ValidationError, renderer="json_extended")
def validation_error(error, request):
    """To handle ValidationError from Pydantic. This will not be logged in console and
    the validaiton errors are passed in response as a dict.
    """
    return {
        "gkstatus": enumdict["ValidationError"],
        "error": error.errors(),
    }


@view_config(context=Exception, renderer="json")
def exception_view(error, request):
    """To handle exceptions from views. This is a temperory solution untill a proper
    Exception handling mechanism is designed for both back end and front end.
    """
    traceback.print_exc(file=sys.stdout) # logs the exception

    gkstatus = enumdict["ConnectionFailed"]

    # Integrity error originates from the database driver (DBAPI)
    # https://docs.sqlalchemy.org/en/13/errors.html#error-dbapi
    # We will have to manually fetch the errorcode to understand the
    # database error.
    if (type(error) == IntegrityError):
        errorcode = error.orig.pgcode
        # Handling duplicate entry error. 23505 is the error code
        # for postgres "unique_violation".
        # https://www.postgresql.org/docs/current/errcodes-appendix.html
        if errorcode == "23505":
            gkstatus = enumdict["DuplicateEntry"]

    if request.registry.settings.get('development'):
        return {
            "gkstatus": gkstatus,
            "error": f"{error}",
        }
    return {
        "gkstatus": gkstatus,
    }
