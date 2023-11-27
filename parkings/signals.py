from decimal import Decimal
from math import ceil

from django.db import transaction
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from parkings.models import EventParking


@transaction.atomic
def update_statistics(event_area):
    price = getattr(event_area, 'price', 0)
    statistics = event_area.statistics
    qs = EventParking.objects.filter(event_area=event_area)
    statistics.total_parking_count = qs.count()
    num_charges = 0
    if event_area.price_unit_length:
        for event_parking in qs:
            time_delta = event_parking.time_end - event_parking.time_start
            time_delta = event_parking.time_end - event_parking.time_start
            hours_parked = ceil(time_delta.total_seconds() / 3600)
            num_charges += ceil(hours_parked / event_area.price_unit_length)

        statistics.total_parking_charges = num_charges
        statistics.total_parking_income = Decimal(str(num_charges * price))
    statistics.save()


@receiver(post_save, sender=EventParking)
def event_parking_on_save(sender, **kwargs):
    obj = kwargs["instance"]
    update_statistics(obj.event_area)


@receiver(post_delete, sender=EventParking)
def event_parking_on_delete(sender, **kwargs):
    obj = kwargs["instance"]
    update_statistics(obj.event_area)
