from rest_framework import permissions, viewsets
from rest_framework_gis.pagination import GeoJsonPagination
from rest_framework_gis.serializers import (
    GeoFeatureModelSerializer, GeometrySerializerMethodField)

from parkings.models import EventArea

from ..common import WGS84InBBoxFilter


class AreaSerializer(GeoFeatureModelSerializer):
    wgs84_areas = GeometrySerializerMethodField()

    def get_wgs84_areas(self, area):
        return area.geom.transform(4326, clone=True)

    class Meta:
        abstact = True
        geo_field = 'wgs84_areas'
        fields = (
            'id',
            'capacity_estimate',
        )


class EventAreaSerializer(AreaSerializer):

    class Meta(AreaSerializer.Meta):
        model = EventArea
        fields = AreaSerializer.Meta.fields + (
            'time_start',
            'time_end',
            'price',
            'price_unit_length',
            'bus_stop_numbers',
            'time_period_time_start',
            'time_period_time_end',
            'time_period_days_of_week',
        )


class PublicAPIEventAreaViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [permissions.AllowAny]
    serializer_class = EventAreaSerializer
    pagination_class = GeoJsonPagination
    bbox_filter_field = 'geom'
    filter_backends = (WGS84InBBoxFilter,)
    bbox_filter_include_overlapping = True

    def get_queryset(self):
        return EventArea.objects.get_active_queryset()
