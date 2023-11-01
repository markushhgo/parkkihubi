from ...models import EventParking
from .valid_parking import ValidFilter, ValidSerializer, ValidViewSet


class ValidEventParkingSerializer(ValidSerializer):

    class Meta(ValidSerializer.Meta):
        model = EventParking
        fields = ValidSerializer.Meta.fields + ['event_area']


class ValidEventParkingFilter(ValidFilter):

    class Meta:
        model = EventParking
        fields = []


class ValidEventParkingViewSet(ValidViewSet):
    queryset = EventParking.objects.order_by('-time_end')
    serializer_class = ValidEventParkingSerializer
    filterset_class = ValidEventParkingFilter
