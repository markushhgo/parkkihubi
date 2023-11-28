from rest_framework import permissions, serializers, viewsets

from parkings.models import EventAreaStatistics
from parkings.pagination import Pagination


class EventAreaTotalStatisticsSerializer(serializers.ModelSerializer):

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
    queryset = EventAreaStatistics.objects.all().order_by('-created_at')
