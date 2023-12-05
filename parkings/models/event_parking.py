from django.contrib.gis.db import models
from django.utils.translation import ugettext_lazy as _
from rest_framework.exceptions import ValidationError

from parkings.models.event_area import EventArea
from parkings.models.parking import (
    AbstractParking, EnforcementDomain, ParkingQuerySet)

from .utils import get_closest_area


class EventParkingQuerySet(ParkingQuerySet):
    pass


class EventParking(AbstractParking):

    class Meta:
        verbose_name = _("event parking")
        verbose_name_plural = _("event parkings")
        default_related_name = "event_parkings"

    objects = EventParkingQuerySet.as_manager()
    event_area = models.ForeignKey(
        EventArea, on_delete=models.SET_NULL, verbose_name=_("event area"), null=True,
        blank=True,
    )

    def save(self, update_fields=None, *args, **kwargs):
        if not self.domain_id:
            self.domain = EnforcementDomain.get_default_domain()

        if (update_fields is None or 'event_area' in update_fields) and not hasattr(self, 'event_area'):
            self.event_area = get_closest_area(self.location, self.domain, area_model=EventArea)

        if not hasattr(self, 'event_area'):
            raise ValidationError(_('No event area found in location or no "event_area_id" paramater provided'))

        if not self.event_area.is_active:
            raise ValidationError(_('EventArea {} is not active').format(str(self.event_area.id)))

        super().save(update_fields=update_fields, *args, **kwargs)
