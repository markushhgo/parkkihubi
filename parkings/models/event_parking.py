from django.contrib.gis.db import models
from django.utils.translation import ugettext_lazy as _

from parkings.models.event_area import EventArea
from parkings.models.parking import (
    AbstractParking, EnforcementDomain, ParkingQuerySet)

from .utils import get_closest_area, normalize_reg_num


class EventParkingQuerySet(ParkingQuerySet):
    pass


class EventParking(AbstractParking):
    objects = EventParkingQuerySet.as_manager()
    event_area = models.ForeignKey(
        EventArea, on_delete=models.SET_NULL, verbose_name=_("event area"), null=True,
        blank=True,
    )

    def save(self, update_fields=None, *args, **kwargs):
        if not self.domain_id:
            self.domain = EnforcementDomain.get_default_domain()

        if (update_fields is None or 'event_area' in update_fields) and not self.event_area:
            self.event_area = get_closest_area(self.location, self.domain, area_model=EventArea)

        if update_fields is None or 'normalized_reg_num' in update_fields:
            self.normalized_reg_num = normalize_reg_num(self.registration_number)

        super().save(update_fields=update_fields, *args, **kwargs)
