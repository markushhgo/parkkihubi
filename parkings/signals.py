from decimal import Decimal
from math import ceil

from django.db import transaction
from django.db.models.signals import post_delete, post_save, pre_delete
from django.dispatch import receiver
from django.utils import timezone

from parkings.models import EventArea, EventAreaStatistics, EventParking


@transaction.atomic
def update_statistics(event_area):
    price = getattr(event_area, 'price', 0)
    statistics = getattr(event_area, 'statistics', None)
    if not statistics:
        return
    qs = EventParking.objects.filter(event_area=event_area)
    statistics.total_parking_count = qs.count()
    num_charges = 0
    if event_area.price_unit_length:
        for event_parking in qs:
            if event_parking.time_start:
                time_end = event_parking.time_end
                if not time_end:
                    time_end = timezone.now()
                time_delta = time_end - event_parking.time_start
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


@receiver(pre_delete, sender=EventArea)
def event_area_on_delete(sender, **kwargs):
    obj = kwargs["instance"]
    # Only test event areas can be deleted.
    if obj.is_test:
        EventAreaStatistics.objects.filter(event_area=obj).delete()
