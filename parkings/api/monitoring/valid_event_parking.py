from ...models import EventParking
from .serializers import EventParkingSerializer
from .valid_parking import ValidFilter, ValidViewSet


class ValidEventParkingFilter(ValidFilter):

    class Meta:
        model = EventParking
        fields = ValidFilter.Meta.fields


class ValidEventParkingViewSet(ValidViewSet):
    queryset = (
        EventParking.objects
        .order_by('time_start')
        .select_related('operator'))
    serializer_class = EventParkingSerializer
    filterset_class = ValidEventParkingFilter
