import pytz
from django.conf import settings
from django.utils.timezone import now
from django.utils.translation import ugettext_lazy as _
from rest_framework import mixins, serializers, viewsets

from parkings.models import EnforcementDomain, EventArea, EventParking

from ..common import ParkingException
from .permissions import IsOperator

DEFAULT_DOMAIN_CODE = EnforcementDomain.get_default_domain_code()


class OperatorAPIEventParkingSerializer(serializers.ModelSerializer):
    status = serializers.ReadOnlyField(source='get_state')
    domain = serializers.SlugRelatedField(
        slug_field='code', queryset=EnforcementDomain.objects.all(),
        default=EnforcementDomain.get_default_domain)
    event_area_id = serializers.CharField(max_length=50, required=False)

    class Meta:
        model = EventParking
        fields = (
            'id', 'created_at', 'modified_at',
            'location',
            'registration_number',
            'time_start', 'time_end',
            'status',
            'domain',
            'event_area_id',
        )

        # these are needed because by default a PUT request that does not contain some optional field
        # works the same way as PATCH would, ie. not updating that field to null on the target object,
        # which seems wrong. see https://github.com/encode/django-rest-framework/issues/3648
        extra_kwargs = {
            'location': {'default': None},
            'time_end': {'default': None},
        }

    def __init__(self, *args, **kwargs):
        super(OperatorAPIEventParkingSerializer, self).__init__(*args, **kwargs)
        self.fields['time_start'].timezone = pytz.utc
        self.fields['time_end'].timezone = pytz.utc

        initial_data = getattr(self, 'initial_data', None)

        if initial_data:
            self.fields['location'].required = True

    def validate(self, data):
        if self.instance and (now() - self.instance.created_at) > settings.PARKKIHUBI_TIME_PARKINGS_EDITABLE:
            if set(data.keys()) != {'time_end'}:
                raise ParkingException(
                    _('Grace period has passed. Only "time_end" can be updated via PATCH.'),
                    code='grace_period_over',
                )

        if self.instance:
            # a partial update might be missing one or both of the time fields
            time_start = data.get('time_start', self.instance.time_start)
            time_end = data.get('time_end', self.instance.time_end)
        else:
            time_start = data['time_start']
            time_end = data['time_end']

        if time_end is not None and time_start > time_end:
            raise serializers.ValidationError(_('"time_start" cannot be after "time_end".'))
        if data.get('event_area_id', False):
            if not EventArea.objects.filter(id=data.get('event_area_id')).exists():
                raise serializers.ValidationError(
                    _('EventArea with event_area_id: {} does not exist.').format(data.get('event_area_id')))
        return data

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        field = 'event_area'
        if getattr(instance, field) is not None:
            representation['event_area_id'] = getattr(instance, field).id
        else:
            representation['event_area_id'] is None
        return representation


class OperatorAPIEventParkingPermission(IsOperator):
    def has_object_permission(self, request, view, obj):
        """
        Allow operators to modify only their own parkings.
        """
        return request.user.operator == obj.operator


class OperatorAPIEventParkingViewSet(mixins.CreateModelMixin, mixins.UpdateModelMixin, mixins.DestroyModelMixin,
                                     viewsets.GenericViewSet):
    permission_classes = [OperatorAPIEventParkingPermission]
    queryset = EventParking.objects.order_by('time_start')
    serializer_class = OperatorAPIEventParkingSerializer

    def perform_create(self, serializer):
        serializer.save(operator=self.request.user.operator)

    def get_queryset(self):
        return super().get_queryset().filter(operator=self.request.user.operator)
