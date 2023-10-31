# -*- coding: utf-8 -*-

from datetime import timedelta

import factory
import pytz

from parkings.models import EventParking
from parkings.models.parking import AbstractParking

from .enforcement_domain import EnforcementDomainFactory
from .event_area import EventAreaFactory
from .faker import fake
from .gis import generate_location
from .operator import OperatorFactory
from .utils import generate_registration_number


class AbstractParkingFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = AbstractParking

    location = factory.LazyFunction(generate_location)
    operator = factory.SubFactory(OperatorFactory)
    registration_number = factory.LazyFunction(generate_registration_number)
    time_start = factory.LazyFunction(lambda: fake.date_time_between(start_date='-2h', end_date='-1h', tzinfo=pytz.utc))
    time_end = factory.LazyFunction(lambda: fake.date_time_between(start_date='+1h', end_date='+2h', tzinfo=pytz.utc))


class EventParkingFactory(AbstractParkingFactory):
    class Meta:
        model = EventParking


class CompleteEventParkingFactory(EventParkingFactory):
    domain = factory.SubFactory(EnforcementDomainFactory)

    event_area = factory.SubFactory(
        EventAreaFactory, domain=factory.SelfAttribute('..domain'))


def get_time_far_enough_in_past():
    return fake.date_time_this_decade(before_now=True, tzinfo=pytz.utc) - timedelta(days=7, seconds=1)
