from rest_framework.routers import DefaultRouter

from ..url_utils import versioned_url
from .event_parking_anonymized import EventParkingAnonymizedViewSet
from .parking_anonymized import ParkingAnonymizedViewSet
from .parking_check_anonymized import ParkingCheckAnonymizedViewSet

router = DefaultRouter()

router.register('event_parking_anonymized', EventParkingAnonymizedViewSet, basename='event_parking_anonymized')
router.register('parking_anonymized', ParkingAnonymizedViewSet, basename='parking_anonymized')
router.register('parking_check_anonymized', ParkingCheckAnonymizedViewSet, basename='parking_check_anonymized')


app_name = 'data'
urlpatterns = [
    versioned_url('v1', router.urls),
]
