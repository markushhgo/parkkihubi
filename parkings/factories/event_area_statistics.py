from decimal import Decimal

import factory

from parkings.models import EventAreaStatistics


class EventAreaStatisticsFactory(factory.django.DjangoModelFactory):

    class Meta:
        model = EventAreaStatistics

    total_parking_count = 0
    total_parking_charges = 0
    total_parking_income = Decimal(str('0.00'))
