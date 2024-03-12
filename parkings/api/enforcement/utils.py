import datetime

from django.conf import settings


def get_grace_duration(default=datetime.timedelta(minutes=15)):
    value = getattr(settings, 'PARKKIHUBI_TIME_OLD_PARKINGS_VISIBLE', None)
    assert value is None or isinstance(value, datetime.timedelta)
    return value if value is not None else default
