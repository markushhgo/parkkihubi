from datetime import timedelta
from decimal import Decimal

import pytest
from django.core.exceptions import ValidationError
from django.utils import timezone

from parkings.models import EventArea


def test_str():
    assert str(EventArea(origin_id='TEST_ID')) == 'Event Area TEST_ID'


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
    event_area.save()
    event_area.refresh_from_db()
    assert event_area.price == Decimal('4.56')

    # Test too many decimals
    event_area.price = Decimal('4.12345')
    event_area.save()
    event_area.refresh_from_db()
    assert event_area.price == Decimal('4.12')


@pytest.mark.django_db
def test_model_clean(event_area):
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
    with pytest.raises(ValidationError, match='"time_start" cannot be after "time_end".'):
        event_area.save()

    event_area.time_start = now - timedelta(hours=1)
    event_area.time_period_time_start = now + timedelta(hours=1)
    event_area.time_period_time_end = now
    with pytest.raises(ValidationError, match='"time_period_time_start" cannot be after'):
        event_area.save()
