from django.db.models import Q
from django.utils import timezone
from rest_framework import permissions, serializers, viewsets

from parkings.models import ParkingArea
from parkings.pagination import Pagination

from ..common import WGS84InBBoxFilter
from .utils import blur_count


class ParkingAreaStatisticsSerializer(serializers.ModelSerializer):

    class Meta:
        model = ParkingArea
        fields = (
            'id',
        )

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        now = timezone.now()
        num_parkings = instance.parkings.filter(Q(time_start__lte=now) & Q(
            time_end__gte=now) | Q(time_end__isnull=True)).count()
        num_event_parkings = 0
        for event_area in instance.overlapping_event_areas.all():
            for event_parking in event_area.event_parkings.all():
                if (instance.geom.intersects(event_parking.location_gk25fin) and
                    event_parking.time_start <= now and
                        event_parking.time_end >= now):
                    num_event_parkings += 1

        total_parkings = num_event_parkings + num_parkings

        representation['current_parking_count'] = blur_count(total_parkings)
        return representation


class PublicAPIParkingAreaStatisticsViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [permissions.AllowAny]
    queryset = ParkingArea.objects.all()
    serializer_class = ParkingAreaStatisticsSerializer
    pagination_class = Pagination
    bbox_filter_field = 'geom'
    filter_backends = (WGS84InBBoxFilter,)
    bbox_filter_include_overlapping = True
