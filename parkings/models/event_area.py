from django.contrib.gis.db import models
from django.utils.translation import ugettext_lazy as _

from .enforcement_domain import EnforcementDomain
from .parking_area import AbstractParkingArea, ParkingArea, ParkingAreaQuerySet


class EventAreaQuerySet(ParkingAreaQuerySet):
    pass


class EventArea(AbstractParkingArea):
    domain = models.ForeignKey(EnforcementDomain, on_delete=models.PROTECT,
                               related_name='event_areas')

    time_start = models.DateTimeField(
        verbose_name=_("event start time"), db_index=True,
    )
    time_end = models.DateTimeField(
        verbose_name=_("event end time"), db_index=True, null=True, blank=True,
    )
    parking_areas = models.ManyToManyField(
        ParkingArea, verbose_name=_("overlapping parking areas"), blank=True,
        related_name="overlapping_event_areas",
    )
    price = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)

    objects = EventAreaQuerySet.as_manager()

    class Meta:
        verbose_name = _('event area')
        verbose_name_plural = _('event areas')

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        for parking_area in ParkingArea.objects.all():
            if self.geom.intersects(parking_area.geom):
                self.parking_areas.add(parking_area)

    def __str__(self):
        return 'Event Area %s' % str(self.origin_id)
