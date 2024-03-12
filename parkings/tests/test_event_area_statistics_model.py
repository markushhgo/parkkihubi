from datetime import timedelta
from decimal import Decimal

import pytest
from django.utils import timezone

from parkings.factories.gis import generate_location, generate_multi_polygon

from ..models import (
    EnforcementDomain, EventArea, EventAreaStatistics, EventParking)


@pytest.fixture
def event_area_data():
    now = timezone.now()
    return {
        'domain': EnforcementDomain.get_default_domain(),
        'geom': generate_multi_polygon(),
        'time_start': now - timedelta(days=10),
        'time_end': now + timedelta(days=10)
    }


@pytest.mark.django_db
def test_event_area_statistics_is_created(event_area_data):
    event_area = EventArea.objects.create(**event_area_data)
    statistics = EventAreaStatistics.objects.first()
    assert event_area.statistics.id == statistics.id
    assert statistics.total_parking_income == Decimal('0.00')
    assert statistics.total_parking_charges == 0
    assert statistics.total_parking_count == 0


@pytest.mark.django_db
def test_event_area_statistics_is_not_deleted(event_area_data):
    event_area = EventArea.objects.create(**event_area_data)
    statistics = EventAreaStatistics.objects.first()
    assert event_area.statistics.id == statistics.id
    EventArea.objects.all().delete()
    assert EventAreaStatistics.objects.first() == statistics
    statistics.refresh_from_db
    with pytest.raises(EventArea.DoesNotExist, match='EventArea matching query does not exist.'):
        statistics.event_area


@pytest.mark.django_db
def test_event_area_statistics_is_populated(event_area_data, event_parking_factory):
    price = 2.50
    event_area_data['price'] = Decimal(str(price))
    event_area_data['price_unit_length'] = 2
    event_area = EventArea.objects.create(**event_area_data)
    statistics = event_area.statistics
    now = timezone.now()
    event_parking_factory.create(event_area=event_area, time_start=now, time_end=now + timedelta(hours=1, minutes=11))
    statistics.refresh_from_db()
    assert statistics.total_parking_charges == 1
    assert statistics.total_parking_income == Decimal(str(statistics.total_parking_charges * price))
    assert statistics.total_parking_count == 1

    # Add event parking with two charges.
    event_parking_factory.create(event_area=event_area, time_start=now, time_end=now + timedelta(hours=2, minutes=21))
    statistics.refresh_from_db()
    assert statistics.total_parking_charges == 3  # 1 + 2
    assert statistics.total_parking_income == Decimal(str(statistics.total_parking_charges * price))
    assert statistics.total_parking_count == 2


@pytest.mark.django_db
def test_event_area_statisics_when_event_parkings_are_deleted(event_area_data, event_parking_factory):
    price = 1.50
    event_area_data['price'] = Decimal(price)
    event_area_data['price_unit_length'] = 8
    event_area = EventArea.objects.create(**event_area_data)
    now = timezone.now()
    num_parkings = 5
    parking_length_h = 9
    event_parking_factory.create_batch(num_parkings, event_area=event_area, time_start=now,
                                       time_end=now + timedelta(hours=parking_length_h))
    statistics = event_area.statistics
    statistics.refresh_from_db()

    assert statistics.total_parking_count == num_parkings
    assert statistics.total_parking_charges == num_parkings * 2
    assert statistics.total_parking_income == Decimal(str(statistics.total_parking_charges * price))

    EventParking.objects.first().delete()
    num_parkings -= 1
    statistics.refresh_from_db()
    assert statistics.total_parking_count == num_parkings
    assert statistics.total_parking_charges == num_parkings * 2
    assert statistics.total_parking_income == Decimal(str(statistics.total_parking_charges * price))

    EventParking.objects.all().delete()
    num_parkings = 0
    statistics.refresh_from_db()
    assert statistics.total_parking_count == num_parkings
    assert statistics.total_parking_charges == num_parkings * 2
    assert statistics.total_parking_income == Decimal(str(statistics.total_parking_charges * price))


@pytest.mark.django_db
def test_event_area_statisics_event_parking_time_end_null(event_area_data, operator, event_parking_factory):
    now = timezone.now()
    price = 0.5
    price_unit_length = 5
    event_area_data['price'] = Decimal(price)
    event_area_data['price_unit_length'] = price_unit_length
    event_area = EventArea.objects.create(**event_area_data)
    num_parkings = 3
    event_parking_factory.create_batch(num_parkings, event_area=event_area,
                                       time_start=now - timedelta(hours=4), time_end=None)
    event_area.refresh_from_db()
    statistics = event_area.statistics
    assert statistics.total_parking_count == num_parkings
    assert statistics.total_parking_charges == num_parkings
    assert statistics.total_parking_income == Decimal(str(statistics.total_parking_charges * price))
    num_parkings_to_add = 3
    num_parkings += num_parkings_to_add
    event_parking_factory.create_batch(num_parkings_to_add, event_area=event_area,
                                       time_start=now - timedelta(hours=7), time_end=None)
    event_area.refresh_from_db()
    statistics = event_area.statistics
    assert statistics.total_parking_count == num_parkings
    assert statistics.total_parking_charges == num_parkings + num_parkings_to_add
    assert statistics.total_parking_income == Decimal(str(statistics.total_parking_charges * price))


@pytest.mark.django_db
def test_event_area_statistics_multiple_additions_and_deletions(event_area_data, operator, event_parking_factory):
    now = timezone.now()
    price = 1.5
    price_unit_length = 2
    event_area_data['price'] = Decimal(price)
    event_area_data['price_unit_length'] = price_unit_length
    event_area = EventArea.objects.create(**event_area_data)
    num_parkings = 10
    for i in range(1, num_parkings + 1):
        event_parking_data = {
            'domain': EnforcementDomain.get_default_domain(),
            'location': generate_location(),
            'operator': operator,
            'time_start': now,
            'time_end': now + timedelta(hours=i * price_unit_length)
        }
        EventParking.objects.create(**event_parking_data)
    event_area.refresh_from_db()
    statistics = event_area.statistics
    assert statistics.total_parking_count == num_parkings
    # 1+2+3+4+5..10 hours = (10*11) / price_unit_length = 55 charges
    assert statistics.total_parking_charges == 55
    assert statistics.total_parking_income == Decimal(str(statistics.total_parking_charges * price))

    event_parking = event_parking_factory.create(
        event_area=event_area, time_start=now, time_end=now + timedelta(hours=10, minutes=11))
    num_parkings += 1
    statistics.refresh_from_db()
    assert statistics.total_parking_charges == 61
    assert statistics.total_parking_count == num_parkings
    assert statistics.total_parking_income == Decimal(str(61 * price))

    event_parking.delete()
    num_parkings -= 1
    statistics.refresh_from_db()
    assert statistics.total_parking_count == num_parkings
    assert statistics.total_parking_charges == 55
    assert statistics.total_parking_income == Decimal(str(statistics.total_parking_charges * price))

    EventParking.objects.all().delete()
    statistics.refresh_from_db()
    assert statistics.total_parking_count == 0
    assert statistics.total_parking_charges == 0
    assert statistics.total_parking_income == Decimal('0.00')
