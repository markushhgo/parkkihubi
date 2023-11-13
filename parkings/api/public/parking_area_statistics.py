from functools import lru_cache

from django.db.models import Case, Count, F, Q, When
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

    """
    Combining the querys results in erroneous aggregated values. The reason for this
    is that Django generates 4 LEFT OUTER JOIN statements when combining the data which
    results in duplicate rows. Using distinct and distinct=true in Count does not help.
    This is the reason why the query is splitted into two different querys/functions.
    The optimal solution would be a single get_queryset method in the ViewSet that would
    return the aggregated values. This not possible due to limitations in Django ORM. One
    possible  solution that might help, would be writing the query in raw SQL and using
    DISTINCT statements in joins.
    """

    @lru_cache()
    def get_parking_count(self):
        now = timezone.now()
        return ParkingArea.objects.all().annotate(
            parking_count=Count(
                Case(
                    When(
                        Q(parkings__time_start__lte=now) &
                        (Q(parkings__time_end__gte=now) | Q(parkings__time_end__isnull=True)),
                        then=1,
                    )
                )
            )
        )

    @lru_cache()
    def get_event_parking_count(self):
        now = timezone.now()
        return ParkingArea.objects.all().annotate(event_parking_count=Count(
            Case(
                When(
                    Q(overlapping_event_areas__event_parkings__time_start__lte=now) &
                    Q(overlapping_event_areas__event_parkings__time_end__gte=now) &
                    Q(geom__intersects=F("overlapping_event_areas__event_parkings__location_gk25fin")),
                    then=1,
                ),
            )
        )
        )

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        parking_count = self.get_parking_count().get(id=instance.id).parking_count
        event_parking_count = self.get_event_parking_count().get(id=instance.id).event_parking_count
        representation['current_parking_count'] = blur_count(parking_count + event_parking_count)
        return representation

    @classmethod
    def clear_cache(cls):
        cls.get_parking_count.cache_clear()
        cls.get_event_parking_count.cache_clear()


class PublicAPIParkingAreaStatisticsViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [permissions.AllowAny]
    queryset = ParkingArea.objects.all().order_by('origin_id')
    serializer_class = ParkingAreaStatisticsSerializer
    pagination_class = Pagination
    bbox_filter_field = 'geom'
    filter_backends = (WGS84InBBoxFilter,)
    bbox_filter_include_overlapping = True

    def list(self, request, *args, **kwargs):
        ret = super().list(request, *args, **kwargs)
        ParkingAreaStatisticsSerializer.clear_cache()
        return ret
