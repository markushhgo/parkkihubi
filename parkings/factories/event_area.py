import factory
import pytz
from django.utils.crypto import get_random_string

from parkings.models import EventArea

from .faker import fake
from .gis import generate_multi_polygon


def generate_origin_id():
    return get_random_string(32)


class EventAreaFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = EventArea

    geom = factory.LazyFunction(generate_multi_polygon)
    capacity_estimate = factory.LazyFunction(lambda: fake.random.randint(1, 50))
    origin_id = factory.LazyFunction(generate_origin_id)
    event_start = factory.LazyFunction(lambda: fake.date_time_between(
        start_date='-2h', end_date='-1h', tzinfo=pytz.utc))
    event_end = factory.LazyFunction(lambda: fake.date_time_between(start_date='+1h', end_date='+2h', tzinfo=pytz.utc))
