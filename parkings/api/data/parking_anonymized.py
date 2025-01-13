
import django_filters
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import serializers, viewsets

from parkings.models import Parking
from parkings.pagination import Pagination

from .permissions import IsDataUser


class ParkingAnonymizedFilterSet(django_filters.FilterSet):

    class Meta:
        model = Parking
        fields = {
            'time_start': ['lte', 'gte'],
        }


class ParkingAnonymizedSerializer(serializers.ModelSerializer):

    class Meta:
        model = Parking
        exclude = ['registration_number', 'normalized_reg_num']


class ParkingAnonymizedViewSet(viewsets.ReadOnlyModelViewSet):

    queryset = Parking.objects.all().order_by('-time_start')
    serializer_class = ParkingAnonymizedSerializer
    pagination_class = Pagination
    permission_classes = [IsDataUser]
    filter_backends = [DjangoFilterBackend]
    filterset_class = ParkingAnonymizedFilterSet
