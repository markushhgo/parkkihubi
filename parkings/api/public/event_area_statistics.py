from functools import lru_cache

from django.db.models import Case, Count, F, Q, When
from django.utils import timezone
from rest_framework import permissions, serializers, viewsets

from parkings.models import EventArea
from parkings.pagination import Pagination

from ..common import WGS84InBBoxFilter
from .utils import blur_count


class EventAreaStatisticsSerializer(serializers.ModelSerializer):

    class Meta:
        model = EventArea
        fields = (
            'id',
        )

    @lru_cache()
    def get_event_parking_count(self):
        now = timezone.now()
        return EventArea.objects.get_active_queryset().annotate(
            event_parking_count=Count(
                Case(
                    When(
                        Q(event_parkings__time_start__lte=now) &
                        (Q(event_parkings__time_end__gte=now) | Q(event_parkings__time_end__isnull=True)),
                        then=1,
                    )
                )
            )
        )

    @lru_cache()
    def get_parking_count(self):
        now = timezone.now()
        return EventArea.objects.get_active_queryset().annotate(parking_count=Count(
            Case(
                When(
                    (Q(parking_areas__parkings__time_start__lte=now) &
                     Q(parking_areas__parkings__time_end__gte=now) |
                     Q(parking_areas__parkings__time_end__isnull=True)) &
                    Q(geom__intersects=F("parking_areas__parkings__location_gk25fin")),
                    then=1,
                ),
            )
        )
        )

    @classmethod
    def clear_cache(cls):
        cls.get_parking_count.cache_clear()
        cls.get_event_parking_count.cache_clear()

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        event_parking_count = self.get_event_parking_count().get(id=instance.id).event_parking_count
        parking_count = self.get_parking_count().get(id=instance.id).parking_count
        representation['current_parking_count'] = blur_count(event_parking_count + parking_count)
        return representation


class PublicAPIEventAreaStatisticsViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [permissions.AllowAny]
    serializer_class = EventAreaStatisticsSerializer
    pagination_class = Pagination
    bbox_filter_field = 'geom'
    filter_backends = (WGS84InBBoxFilter,)
    bbox_filter_include_overlapping = True

    def get_queryset(self):
        return EventArea.objects.get_active_queryset()

    def list(self, request, *args, **kwargs):
        ret = super().list(request, *args, **kwargs)
        EventAreaStatisticsSerializer.clear_cache()
        return ret
