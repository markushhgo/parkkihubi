from rest_framework import permissions, serializers, viewsets

from parkings.models import EventAreaStatistics
from parkings.pagination import Pagination

from .utils import blur_count


class EventAreaTotalStatisticsSerializer(serializers.ModelSerializer):

    total_parking_count = serializers.SerializerMethodField()

    def get_total_parking_count(self, area):
        return blur_count(area.total_parking_count)

    class Meta:
        model = EventAreaStatistics
        fields = (
            'id',
            'total_parking_count'
        )


class PublicAPIEventAreaTotalStatisticsViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [permissions.AllowAny]
    serializer_class = EventAreaTotalStatisticsSerializer
    pagination_class = Pagination
    queryset = EventAreaStatistics.objects.filter(event_area__is_test=False).order_by('-created_at')
