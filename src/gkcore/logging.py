from json import JSONDecodeError
import logging

def request_logger_tween_factory(handler, registry):
    """This logger will give information about request method, request path,
    response status, response content length and gkstatus if available.

    Log Structure Example: `/invoice/drcr/83 200 OK 27 0`
    Path: `/invoice/drcr/83`
    Response Status: `200 OK`
    Content Length: `27`
    gkstatus: `0`
    """

    logger = logging.getLogger('gkcore')

    def request_logger_tween(request):
        response = handler(request)

        try:
            response_json = getattr(response, "json_body", None)
        except (JSONDecodeError, UnicodeDecodeError, TypeError):
            response_json = None
        gkstatus = response_json.get("gkstatus") if response_json else None

        logger.info(
            "%s %s %s %s %s",
            request.method,
            request.path_qs,
            response.status,
            response.content_length,
            gkstatus,
        )
        return response

    return request_logger_tween

def includeme(config):
    config.add_tween('.logging.request_logger_tween_factory')
