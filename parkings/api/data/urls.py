from rest_framework.routers import DefaultRouter

from ..url_utils import versioned_url
from .event_parking_anonymized import EventParkingAnonymizedViewSet

router = DefaultRouter()

router.register('event_parking_anonymized', EventParkingAnonymizedViewSet, basename='event_parking_anonymized')


app_name = 'data'
urlpatterns = [
    versioned_url('v1', router.urls),
]
