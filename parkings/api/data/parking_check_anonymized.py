import django_filters
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import mixins, serializers, viewsets

from parkings.models import ParkingCheck
from parkings.pagination import DataPagination

from .permissions import IsDataUser


class ParkingCheckAnonymizedFilterSet(django_filters.FilterSet):

    class Meta:
        model = ParkingCheck
        fields = {
            'time': ['lte', 'gte'],
        }


class ParkingCheckAnonymizedSerializer(serializers.ModelSerializer):

    class Meta:
        model = ParkingCheck
        exclude = ['registration_number']


class ParkingCheckAnonymizedViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):

    queryset = ParkingCheck.objects.all().order_by('-time')
    serializer_class = ParkingCheckAnonymizedSerializer
    pagination_class = DataPagination
    permission_classes = [IsDataUser]
    filter_backends = [DjangoFilterBackend]
    filterset_class = ParkingCheckAnonymizedFilterSet
