from django.contrib.gis.db import models
from django.utils.translation import ugettext_lazy as _

from parkings.models.constants import GK25FIN_SRID
from parkings.models.event_area import EventArea
from parkings.models.parking import (
    AbstractParking, EnforcementDomain, ParkingQuerySet)

from .utils import get_closest_area, normalize_reg_num


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
    # Store location also in GK25, as area geometries are in GK25. This avoids performance intensive
    # SRS transformations when calculating area statistics.
    location_gk25fin = models.PointField(srid=3879, verbose_name=_(
        "location_gk25fin"), db_index=True, null=True, blank=True)

    def save(self, update_fields=None, *args, **kwargs):
        if not self.domain_id:
            self.domain = EnforcementDomain.get_default_domain()

        if (update_fields is None or 'event_area' in update_fields) and not self.event_area:
            self.event_area = get_closest_area(self.location, self.domain, area_model=EventArea)

        if update_fields is None or 'normalized_reg_num' in update_fields:
            self.normalized_reg_num = normalize_reg_num(self.registration_number)

        if update_fields is None or 'location' in update_fields:
            self.location_gk25fin = self.location.transform(GK25FIN_SRID, clone=True)

        super().save(update_fields=update_fields, *args, **kwargs)
