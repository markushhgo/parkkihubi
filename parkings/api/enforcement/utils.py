import datetime

from django.conf import settings

from .check_parking import get_event_area


def get_grace_duration(default=datetime.timedelta(minutes=15)):
    value = getattr(settings, 'PARKKIHUBI_TIME_OLD_PARKINGS_VISIBLE', None)
    assert value is None or isinstance(value, datetime.timedelta)
    return value if value is not None else default


def get_event_parkings_in_assigned_event_areas(queryset):
    in_assigned_event_area = []
    for event_parking in queryset.all():
        if get_event_area(event_parking.location_gk25fin, domain=event_parking.domain) == event_parking.event_area:
            in_assigned_event_area.append(event_parking.id)
    return queryset.filter(id__in=in_assigned_event_area)
