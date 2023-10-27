import factory
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
