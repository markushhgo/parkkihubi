from django.contrib.gis.db import models
from django.contrib.postgres.fields import ArrayField
from django.utils.translation import ugettext_lazy as _

from .enforcement_domain import EnforcementDomain
from .parking_area import AbstractParkingArea, ParkingArea, ParkingAreaQuerySet


class EventAreaQuerySet(ParkingAreaQuerySet):
    pass
    


class EventArea(AbstractParkingArea):
    PRICE_UNIT_CHOICES = [
        ('H', 'Hour'),
        ('D', 'Day'),
    ]

    ISO_DAYS_OF_WEEK_CHOICES = [
        (1, 'Monday'),
        (2, 'Tuesday'),
        (3, 'Wednesday'),
        (4, 'Thursday'),
        (5, 'Friday'),
        (6, 'Saturday'),
        (7, 'Sunday'),
    ]

    domain = models.ForeignKey(EnforcementDomain, on_delete=models.PROTECT,
                               related_name='event_areas')

    time_start = models.DateTimeField(verbose_name=_('event start time'), db_index=True)
    time_end = models.DateTimeField(verbose_name=_('event end time'), db_index=True)
    parking_areas = models.ManyToManyField(
        ParkingArea, verbose_name=_('overlapping parking areas'), blank=True,
        related_name='overlapping_event_areas',
    )
    price = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    price_unit = models.CharField(max_length=1, choices=PRICE_UNIT_CHOICES, null=True, blank=True)
    bus_stop_numbers = ArrayField(models.SmallIntegerField(), null=True, blank=True, verbose_name=_('bus stop numbers'),
                                  help_text=_('Comma separated list of bus stop numbers. e.g.: 123,345,678'))

    time_period_time_start = models.TimeField(
        verbose_name=_("time period start time"), db_index=True,
        null=True, blank=True
    )
    time_period_time_end = models.TimeField(
        verbose_name=_("time period end time"), db_index=True,
        null=True, blank=True
    )
    time_period_days_of_week = ArrayField(models.SmallIntegerField(choices=ISO_DAYS_OF_WEEK_CHOICES),
                                          verbose_name=_('time period days of week'), default=list,
                                          null=True, blank=True)

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

    def clean(self):
        pass
