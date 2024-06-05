from datetime import datetime
from decimal import Decimal

from django.contrib.gis.db import models
from django.contrib.postgres.fields import ArrayField
from django.core.exceptions import ValidationError
from django.db.models import Q
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _

from parkings.models.mixins import TimestampedModelMixin, UUIDPrimaryKeyMixin

from .enforcement_domain import EnforcementDomain
from .parking_area import AbstractParkingArea, ParkingArea, ParkingAreaQuerySet


class EventAreaQuerySet(ParkingAreaQuerySet):

    def get_active_queryset(self):
        now = timezone.now()
        iso_weekday = now.isoweekday()
        qs = self.filter(Q(time_end__gte=now) & Q(time_start__lte=now))
        qs = qs.filter(
            Q(time_period_time_end__isnull=True) & Q(time_period_time_start__isnull=True)
            |
            Q(time_period_time_end__gte=now) & Q(time_period_time_start__lte=now) & Q(
                time_period_days_of_week__contains=[iso_weekday])
        )
        return qs.order_by('origin_id')


class EventArea(AbstractParkingArea):

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
    price_unit_length = models.PositiveIntegerField(null=True, blank=True, verbose_name=_('price unit length in hours'))
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
                                          verbose_name=_('time period days of week'),
                                          null=True, blank=True, default=list)

    description = models.TextField(null=True, blank=True, verbose_name=_('description'))
    is_test_event_area = models.BooleanField(default=False, verbose_name=_('is test event area'), help_text=_(
        'if set to True the event area is ment only for testing purposes, can be deleted and'
        ' is ignored in event_area statistics '))
    objects = EventAreaQuerySet.as_manager()

    @property
    def is_active(self):
        now = timezone.now()
        active = self.time_start <= now and self.time_end >= now
        if self.time_period_time_start and self.time_period_time_end:
            iso_weekday = now.isoweekday()
            active_period = (self.time_period_time_start <= now.time() and
                             self.time_period_time_end >= now.time() and
                             iso_weekday in self.time_period_days_of_week)
            active = active & active_period
        return active

    class Meta:
        verbose_name = _('event area')
        verbose_name_plural = _('event areas')

    def save(self, *args, **kwargs):
        # Force custom validation, so it can be used for both admin and model.
        self.clean()
        super().save(*args, **kwargs)
        # Add overlapping parking areas
        for parking_area in ParkingArea.objects.all():
            if self.geom.intersects(parking_area.geom):
                self.parking_areas.add(parking_area)

        if not EventAreaStatistics.objects.filter(event_area=self).exists():
            EventAreaStatistics.objects.create(event_area=self)

    def __str__(self):
        return 'Event Area %s' % str(self.origin_id)

    def clean(self):
        days_of_week = self.time_period_days_of_week if self.time_period_days_of_week else []
        has_time_period = bool(
            self.time_period_time_start is not None or self.time_period_time_end is not None or len(days_of_week) > 0)

        if (has_time_period and
                not bool(self.time_period_time_start and self.time_period_time_end and self.time_period_days_of_week)):
            raise ValidationError(_('Provide "start time", "end time" and "days of week" for Time period.'))

        if self.time_start and self.time_end:
            if self.time_start > self.time_end:
                raise ValidationError(_('"time_start" cannot be after "time_end"'))

        if self.time_period_time_start and self.time_period_time_end:
            if self.time_period_time_start > self.time_period_time_end:
                raise ValidationError(_('"time_period_time_start" cannot be after "time_period_time_end".'))

        if (not self.price and self.price_unit_length is not None or
                self.price is not None and not self.price_unit_length):
            raise ValidationError(_('If chargeable, both "price" and "price unit length" must be set'))

        if self.price is not None and self.price < 0:
            raise ValidationError(_('"price" cannot be negative'))

        # Validate that the time period is not shorter than the price_unit_length,
        # if shorter, the price_unit_length would be obsolete.
        if self.price_unit_length is not None and has_time_period:
            time_start = datetime.combine(datetime.today(), self.time_period_time_start)
            time_end = datetime.combine(datetime.today(), self.time_period_time_end)
            time_delta = time_end - time_start
            if time_delta.total_seconds() / 3600 < self.price_unit_length:
                raise ValidationError(_('Time period is shorter than "price unit length"'))


class EventAreaStatistics(TimestampedModelMixin, UUIDPrimaryKeyMixin):

    event_area = models.OneToOneField(EventArea, on_delete=models.SET_NULL,
                                      blank=True, null=True, related_name='statistics',
                                      verbose_name=_('event area statistics'))
    total_parking_count = models.PositiveIntegerField(
        default=0, verbose_name=_('total parking count'))
    total_parking_income = models.DecimalField(
        max_digits=10, decimal_places=2, default=Decimal('0.00'), verbose_name=_('total parking income'))
    total_parking_charges = models.PositiveIntegerField(default=0, verbose_name=_('total number of charges'))
