from django.db import transaction
from rest_framework import mixins, serializers
from rest_framework.decorators import action
from rest_framework.response import Response

from parkings.models import Permit, PermitSeries

from ..common_permit import PermitSeriesViewSet
from .permissions import IsOperator


class OperatorPermitSeriesViewSet(mixins.DestroyModelMixin, PermitSeriesViewSet):
    permission_classes = [IsOperator]

    @action(detail=True, methods=['post'])
    def activate(self, request, pk=None):
        activate_payload = PermitSeriesActivateBodySerializer(data=request.data)
        activate_payload.is_valid(raise_exception=True)
        validated_data = activate_payload.validated_data

        with transaction.atomic():
            obj_to_activate = self.get_object()
            old_actives = self.get_queryset().filter(active=True)

            if obj_to_activate.active and old_actives.count() == 1:
                return Response({'status': 'No change'})

            # Always activate the specified permit series regardless of what to deactivate
            if not obj_to_activate.active:
                obj_to_activate.active = True
                obj_to_activate.save()

            if validated_data['deactivate_others']:
                old_actives.exclude(pk=obj_to_activate.pk).update(active=False)
            else:
                ids_to_deactivate = validated_data.get('deactivate_series', [])
                old_actives.filter(id__in=ids_to_deactivate).exclude(
                    pk=obj_to_activate.pk
                ).update(active=False)

            prunable_series = PermitSeries.objects.prunable()
            Permit.objects.filter(series__in=prunable_series).delete()
            prunable_series.delete()

            return Response({'status': 'OK'})


class PermitSeriesActivateBodySerializer(serializers.Serializer):
    deactivate_others = serializers.BooleanField(required=False, default=False)
    deactivate_series = serializers.ListField(
        child=serializers.IntegerField(), required=False
    )
