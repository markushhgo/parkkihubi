
import django_filters
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import serializers, viewsets

from parkings.models import EventParking
from parkings.pagination import Pagination

from .permissions import IsDataUser


class EventParkingAnonymizedFilterSet(django_filters.FilterSet):

    class Meta:
        model = EventParking
        fields = {
            'time_start': ['lt', 'gt'],
        }


class EventParkingAnonymizedSerializer(serializers.ModelSerializer):

    class Meta:
        model = EventParking
        exclude = ['registration_number', 'normalized_reg_num']


class EventParkingAnonymizedViewSet(viewsets.ReadOnlyModelViewSet):

    queryset = EventParking.objects.all()
    serializer_class = EventParkingAnonymizedSerializer
    pagination_class = Pagination
    permission_classes = [IsDataUser]
    filter_backends = [DjangoFilterBackend]
    filterset_class = EventParkingAnonymizedFilterSet
