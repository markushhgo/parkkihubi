from django.contrib.gis.db import models
from django.utils.translation import ugettext_lazy as _

from .enforcement_domain import EnforcementDomain
from .parking_area import AbstractParkingArea, ParkingArea, ParkingAreaQuerySet


class EventAreaQuerySet(ParkingAreaQuerySet):
    pass


class EventArea(AbstractParkingArea):
    domain = models.ForeignKey(EnforcementDomain, on_delete=models.PROTECT,
                               related_name='event_areas')

    event_start = models.DateTimeField(
        verbose_name=_("event start time"), db_index=True,
    )
    event_end = models.DateTimeField(
        verbose_name=_("event end time"), db_index=True, null=True, blank=True,
    )
    parking_areas = models.ForeignKey(
        ParkingArea, null=True, blank=True, on_delete=models.SET_NULL,
        verbose_name=_("overlapping parking areas"), related_name="event_areas")

    objects = EventAreaQuerySet.as_manager()

    class Meta:
        verbose_name = _('event area')
        verbose_name_plural = _('event areas')

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)

    def __str__(self):
        return 'Event Area %s' % str(self.origin_id)
