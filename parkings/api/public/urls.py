from rest_framework import permissions
from rest_framework.routers import APIRootView, DefaultRouter

from ..url_utils import versioned_url
from .event_area import PublicAPIEventAreaViewSet
from .event_area_statistics import PublicAPIEventAreaStatisticsViewSet
from .parking_area import PublicAPIParkingAreaViewSet
from .parking_area_statistics import PublicAPIParkingAreaStatisticsViewSet


class PublicApiRootView(APIRootView):
    permission_classes = [permissions.AllowAny]


class Router(DefaultRouter):
    APIRootView = PublicApiRootView


router = Router()
router.register(
    r'event_area',
    PublicAPIEventAreaViewSet, basename='eventarea')
router.register(
    r'event_area_statistics',
    PublicAPIEventAreaStatisticsViewSet, basename='eventareastatistics')
router.register(
    r'parking_area',
    PublicAPIParkingAreaViewSet, basename='parkingarea')
router.register(
    r'parking_area_statistics',
    PublicAPIParkingAreaStatisticsViewSet, basename='parkingareastatistics')

app_name = 'public'
urlpatterns = [
    versioned_url('v1', router.urls),
]
