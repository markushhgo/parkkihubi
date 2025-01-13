import pytest
from pytest_factoryboy import register

from parkings.factories import (
    AdminUserFactory, CompleteEventParkingFactory, DataUserFactory,
    DiscParkingFactory, EnforcementDomainFactory, EnforcerFactory,
    EventAreaFactory, EventAreaStatisticsFactory, EventParkingFactory,
    HistoryEventParkingFactory, HistoryParkingFactory, MonitorFactory,
    OperatorFactory, ParkingAreaFactory, ParkingCheckFactory, ParkingFactory,
    RegionFactory, StaffUserFactory, UserFactory)

register(OperatorFactory)
register(ParkingFactory, 'parking')
register(EventAreaFactory, 'event_area')
register(ParkingCheckFactory, 'parking_check')
register(EventAreaStatisticsFactory, 'event_area_statistics')
register(EventParkingFactory, 'event_parking')
register(CompleteEventParkingFactory, 'complete_event_parking')
register(HistoryEventParkingFactory, 'history_event_parking')
register(HistoryParkingFactory, 'history_parking')
register(AdminUserFactory, 'admin_user')
register(StaffUserFactory, 'staff_user')
register(UserFactory)
register(ParkingAreaFactory)
register(RegionFactory)
register(DiscParkingFactory, 'disc_parking')
register(EnforcementDomainFactory, 'enforcement_domain')
register(EnforcerFactory)
register(MonitorFactory)
register(DataUserFactory)


@pytest.fixture(autouse=True)
def set_faker_random_seed():
    from parkings.factories.faker import fake
    fake.seed(777)
