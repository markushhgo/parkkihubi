from datetime import timedelta

import pytz

from .faker import fake

CAPITAL_LETTERS = 'ABCDEFGHIJKLMNOPQRSTUVWXYZÅÄÖ'


def generate_registration_number():
    letters = ''.join(fake.random.choice(CAPITAL_LETTERS) for _ in range(3))
    numbers = ''.join(fake.random.choice('0123456789') for _ in range(3))
    return '%s-%s' % (letters, numbers)


def get_time_far_enough_in_past():
    return fake.date_time_this_decade(before_now=True, tzinfo=pytz.utc) - timedelta(days=7, seconds=1)
