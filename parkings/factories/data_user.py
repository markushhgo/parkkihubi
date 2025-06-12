import factory

from parkings.models import DataUser

from .faker import fake
from .user import UserFactory


class DataUserFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = DataUser

    name = factory.LazyFunction(fake.company)
    user = factory.SubFactory(UserFactory)
