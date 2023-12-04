from datetime import timedelta
from decimal import Decimal

import pytest
from django.core.exceptions import ValidationError
from django.utils import timezone

from parkings.models import EventArea


def test_str():
    assert str(EventArea(origin_id='TEST_ID')) == 'Event Area TEST_ID'


@pytest.mark.django_db
def test_event_area_is_active_property(event_area_factory):
    now = timezone.now()
    event_area = event_area_factory(time_start=now - timedelta(hours=1), time_end=now + timedelta(hours=1))
    assert event_area.is_active is True

    event_area = event_area_factory(time_start=now - timedelta(hours=2), time_end=now - timedelta(hours=1))
    assert event_area.is_active is False

    # Test time periods
    iso_weekday = now.isoweekday()
    event_area = event_area_factory(time_start=now - timedelta(hours=1),
                                    time_end=now + timedelta(hours=1),
                                    time_period_days_of_week=[iso_weekday],
                                    time_period_time_start=now - timedelta(hours=1),
                                    time_period_time_end=now + timedelta(hours=1))
    assert event_area.is_active is True
    # Correct day of week, but time_period_time_start and time_period_time_end is past now
    event_area = event_area_factory(time_start=now - timedelta(hours=1),
                                    time_end=now + timedelta(hours=1),
                                    time_period_days_of_week=[iso_weekday],
                                    time_period_time_start=now - timedelta(hours=2),
                                    time_period_time_end=now - timedelta(hours=1))
    assert event_area.is_active is False
    # Time periods are correct, but incorrect day of week
    event_area = event_area_factory(time_start=now - timedelta(hours=1),
                                    time_end=now + timedelta(hours=1),
                                    time_period_days_of_week=[iso_weekday + 1],
                                    time_period_time_start=now - timedelta(hours=1),
                                    time_period_time_end=now + timedelta(hours=1))
    assert event_area.is_active is False


@pytest.mark.django_db
def test_estimated_capacity(event_area):
    event_area.capacity_estimate = 123
    assert event_area.estimated_capacity == 123
    event_area.capacity_estimate = None
    by_area = event_area.estimate_capacity_by_area()
    assert event_area.estimated_capacity == by_area


@pytest.mark.django_db
def test_estimate_capacity_by_area(event_area):
    assert event_area.estimate_capacity_by_area() == int(
        round(event_area.geom.area * 0.07328))


@pytest.mark.django_db
def test_price(event_area):
    event_area.price = Decimal('4.56')
    event_area.price_unit_length = 1
    event_area.save()
    event_area.refresh_from_db()
    assert event_area.price == Decimal('4.56')

    # Test too many decimals
    event_area.price = Decimal('4.12345')
    event_area.save()
    event_area.refresh_from_db()
    assert event_area.price == Decimal('4.12')


@pytest.mark.django_db
def test_description(event_area):
    test_description = "Test"
    event_area.description = test_description
    event_area.save()
    event_area.refresh_from_db()
    assert event_area.description == test_description


@pytest.mark.django_db
def test_model_clean_on_time_fields(event_area):
    now = timezone.now()
    event_area.time_period_time_end = now + timedelta(hours=2)
    with pytest.raises(ValidationError, match='Provide "start time",'):
        event_area.save()

    event_area.time_period_time_start = now + timedelta(hours=2)
    with pytest.raises(ValidationError, match='Provide "start time",'):
        event_area.save()

    event_area.time_period_days_of_week = [1]
    # All time period field are now set, no exception should be thrown.
    try:
        event_area.save()
    except ValidationError as exc:
        assert False, 'event_area.save() raised and exception {}'.format(exc)

    event_area.time_start = event_area.time_end + timedelta(hours=1)
    with pytest.raises(ValidationError, match='"time_start" cannot be after "time_end"'):
        event_area.save()

    event_area.time_start = now - timedelta(hours=1)
    event_area.time_period_time_start = now + timedelta(hours=1)
    event_area.time_period_time_end = now
    with pytest.raises(ValidationError, match='"time_period_time_start" cannot be after'):
        event_area.save()


@pytest.mark.django_db
def test_model_clean_on_fields_price_and_price_unit_length(event_area):
    now = timezone.now()

    event_area.price = Decimal(str('0.50'))
    with pytest.raises(ValidationError, match='If chargeable, both "price" and'):
        event_area.save()

    event_area.price = None
    event_area.price_unit_length = 2
    with pytest.raises(ValidationError, match='If chargeable, both "price" and'):
        event_area.save()

    event_area.price = Decimal(str('-0.50'))
    event_area.price_unit_length = 4
    with pytest.raises(ValidationError, match='"price" can not be negative'):
        event_area.save()

    event_area.price = Decimal(str('0.50'))
    # Time period one minute longer than price_unit_length
    event_area.time_period_time_start = (now - timedelta(hours=2)).time()
    event_area.time_period_time_end = (now + timedelta(hours=2, minutes=1)).time()
    event_area.time_period_days_of_week = [1, 2, 3, 4, 5]
    event_area.save()

    # Time period shorter than price_unit_length
    event_area.time_period_time_start = (now - timedelta(hours=1)).time()
    event_area.time_period_time_end = (now + timedelta(hours=1)).time()
    with pytest.raises(ValidationError, match='Time period is shorter than "price unit length"'):
        event_area.save()
