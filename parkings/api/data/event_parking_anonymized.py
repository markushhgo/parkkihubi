
import django_filters
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import mixins, serializers, viewsets

from parkings.models import EventParking
from parkings.pagination import DataPagination

from .permissions import IsDataUser


class EventParkingAnonymizedFilterSet(django_filters.FilterSet):

    class Meta:
        model = EventParking
        fields = {
            'time_start': ['lte', 'gte'],
            'time_end': ['lte', 'gte'],
        }


class EventParkingAnonymizedSerializer(serializers.ModelSerializer):

    class Meta:
        model = EventParking
        exclude = ['registration_number', 'normalized_reg_num']


class EventParkingAnonymizedViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):

    queryset = EventParking.objects.all().order_by('-time_start')
    serializer_class = EventParkingAnonymizedSerializer
    pagination_class = DataPagination
    permission_classes = [IsDataUser]
    filter_backends = [DjangoFilterBackend]
    filterset_class = EventParkingAnonymizedFilterSet
