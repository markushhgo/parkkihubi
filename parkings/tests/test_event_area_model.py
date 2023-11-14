from decimal import Decimal

import pytest

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
