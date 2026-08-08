from pyramid.renderers import JSON
from datetime import date, datetime
from decimal import Decimal


def includeme(config):
    json_renderer = JSON()

    def date_adapter(obj, request):
        return datetime.strftime(obj, "%d-%m-%Y")

    def decimal_adapter(obj, request):
        return float(obj)

    def set_adapter(obj, request):
        return list(obj)

    def exception_adapter(obj, request):
        return f"{obj}"

    json_renderer.add_adapter(date, date_adapter)
    json_renderer.add_adapter(Decimal, decimal_adapter)
    json_renderer.add_adapter(set, set_adapter)
    json_renderer.add_adapter(Exception, exception_adapter)

    config.add_renderer('json_extended', json_renderer)
