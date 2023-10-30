from rest_framework import permissions, viewsets
from rest_framework_gis.pagination import GeoJsonPagination

from parkings.models import ParkingArea

from ..common import WGS84InBBoxFilter
from .event_area import AreaSerializer


class ParkingAreaSerializer(AreaSerializer):

    class Meta(AreaSerializer.Meta):
        model = ParkingArea


class PublicAPIParkingAreaViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [permissions.AllowAny]
    queryset = ParkingArea.objects.order_by('origin_id')
    serializer_class = ParkingAreaSerializer
    pagination_class = GeoJsonPagination
    bbox_filter_field = 'geom'
    filter_backends = (WGS84InBBoxFilter,)
    bbox_filter_include_overlapping = True
