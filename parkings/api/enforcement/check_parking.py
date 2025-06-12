import datetime

from django.conf import settings
from django.contrib.gis.gdal.error import GDALException
from django.contrib.gis.geos import Point
from django.utils import timezone
from rest_framework import generics, serializers
from rest_framework.response import Response

from ...models import (
    EventArea, EventParking, Parking, ParkingCheck, PaymentZone, Permit,
    PermitArea, PermitLookupItem)
from ...models.constants import GK25FIN_SRID, WGS84_SRID
from .permissions import IsEnforcer


class PermitPermissionsSerializer(serializers.ModelSerializer):
    class Meta:
        model = Permit
        fields = [
            "external_id",
            "subjects",
            "areas"
        ]


class AwareDateTimeField(serializers.DateTimeField):
    default_error_messages = dict(
        serializers.DateField.default_error_messages,
        timezone="Timezone is required",
    )

    def enforce_timezone(self, value):
        if not timezone.is_aware(value):
            self.fail('timezone')
        return super().enforce_timezone(value)


class LocationSerializer(serializers.Serializer):
    latitude = serializers.FloatField(min_value=-90, max_value=90)
    longitude = serializers.FloatField(min_value=-180, max_value=180)


class CheckParkingSerializer(serializers.Serializer):
    registration_number = serializers.CharField(max_length=20)
    location = LocationSerializer()
    time = AwareDateTimeField(required=False)
    details = serializers.ListSerializer(child=serializers.CharField(), required=False)


class CheckParking(generics.GenericAPIView):
    """
    Check if parking is valid for given registration number and location.
    """
    permission_classes = [IsEnforcer]

    serializer_class = CheckParkingSerializer

    def post(self, request):
        serializer = self.get_serializer(data=request.data)

        # Parse input parameters with the serializer
        serializer.is_valid(raise_exception=True)
        params = serializer.validated_data

        # Read input parameters to variables
        time = params.get("time") or timezone.now()
        registration_number = params.get("registration_number")
        (wgs84_location, gk25_location) = get_location(params)
        domain = request.user.enforcer.enforced_domain

        zone = get_payment_zone(gk25_location, domain)
        area = get_permit_area(gk25_location, domain)
        event_area = get_event_area(gk25_location, domain)

        (allowed_by, parking, end_time, active_parkings, permit_lookup_items, active_event_parkings) = check_parking(
            registration_number, zone, area, time, domain, event_area)
        allowed = bool(allowed_by)

        if not allowed:
            # If no matching parking or permit was found, try to find
            # one that has just expired, i.e. was valid a few minutes
            # ago (where "a few minutes" is the grace duration)
            past_time = time - get_grace_duration()
            (
                _allowed_by,
                parking,
                end_time,
                active_parkings,
                permit_lookup_items,
                active_event_parkings
            ) = check_parking(
                registration_number,
                zone, area,
                past_time,
                domain,
                event_area
            )

        result = {
            "allowed": allowed,
            "end_time": end_time,
            "location": {
                "payment_zone": zone,
                "permit_area": area.identifier if area else None,
                "event_area": event_area.id if event_area else None,
            },
            "time": time,
        }

        operator_detail, time_start_detail, permissions_detail = get_details(params)

        if operator_detail:
            result["operator"] = parking.operator.name if allowed and parking and parking.operator else None

        if time_start_detail:
            result["time_start"] = parking.time_start if allowed and parking and parking.time_start else None

        if permissions_detail:
            result["permissions"] = {
                "zones": list({p.zone.number for p in active_parkings}),
                "permits": [
                    PermitPermissionsSerializer(item.permit).data for item in permit_lookup_items
                ],
                "event_areas": list({e_p.event_area.id for e_p in active_event_parkings})
            }

        filter = {
            "performer": request.user,
            "time": time,
            "time_overridden": bool(params.get("time")),
            "registration_number": registration_number,
            "location": wgs84_location,
            "result": result,
            "allowed": allowed
        }

        if isinstance(parking, Parking):
            filter["found_parking"] = parking
        if isinstance(parking, EventParking):
            filter["found_event_parking"] = parking

        ParkingCheck.objects.create(**filter)
        return Response(result)


def get_details(params):
    details = params.get("details", [])
    operator = False
    time_start = False
    permissions = False

    for detail in [d.lower() for d in details]:
        if detail == "operator":
            operator = True
        if detail == "time_start":
            time_start = True
        if detail == "permissions":
            permissions = True
    return operator, time_start, permissions


def get_location(params):
    longitude = params["location"]["longitude"]
    latitude = params["location"]["latitude"]
    wgs84_location = Point(longitude, latitude, srid=WGS84_SRID)
    try:
        gk25_location = wgs84_location.transform(GK25FIN_SRID, clone=True)
    except GDALException:
        # GK25-FIN doesn't cover the whole world, and therefore
        # locations outside of its projection plane will raise a
        # GDALException.  In that case return None as the gk25_location.
        return (wgs84_location, None)
    return (wgs84_location, gk25_location)


def get_payment_zone(location, domain):
    if location is None:
        return None
    zone = (
        PaymentZone.objects
        .filter(geom__contains=location, domain=domain)
        .order_by("-number")[:1]
        .values_list("number", flat=True)).first()
    return zone


def get_permit_area(location, domain):
    if location is None:
        return None
    area = PermitArea.objects.filter(geom__contains=location, domain=domain).first()
    return area if area else None


def get_event_area(location, domain):
    if location is None:
        return None
    now = timezone.now()
    area = EventArea.objects.filter(geom__contains=location, domain=domain, time_end__gte=now).first()
    return area if area else None


def check_parking(registration_number, zone, area, time, domain, event_area):
    """
    Check parking allowance from the database.

    :type registration_number: str
    :type zone: int|None
    :type area: str|None
    :type domain: parkings.models.EnforcementDomain
    :type time: datetime.datetime
    :rtype: (str, Parking|None, datetime.datetime, ParkingQuerySet, PermitLookupItemQuerySet, EventParkingQuerySet)
    """
    permit_lookup_items = (
        PermitLookupItem.objects
        .active()
        .by_time(time)
        .by_subject(registration_number)
        .filter(permit__domain=domain))

    active_parkings = (
        Parking.objects
        .registration_number_like(registration_number)
        .valid_at(time)
        .only("id", "zone", "time_end")
        .filter(domain=domain))

    active_event_parkings = (
        EventParking.objects
        .registration_number_like(registration_number)
        .valid_at(time)
        .only("id", "time_end")
        .filter(domain=domain))

    for parking in active_parkings:
        if zone is None or parking.zone.number <= zone:
            return ("parking",
                    parking,
                    parking.time_end,
                    active_parkings,
                    permit_lookup_items,
                    active_event_parkings)

    if area:
        permit_end_time = permit_lookup_items.by_area(area).values_list("end_time", flat=True).first()
        if permit_end_time:
            return ("permit", None, permit_end_time, active_parkings, permit_lookup_items, active_event_parkings)

    for active_event_parking in active_event_parkings:
        if active_event_parking.event_area == event_area:
            return ("event_parking",
                    active_event_parking,
                    active_event_parking.time_end,
                    active_parkings,
                    permit_lookup_items,
                    active_event_parkings)

    return (None, None, None, active_parkings, permit_lookup_items, active_event_parkings)


def get_grace_duration(default=datetime.timedelta(minutes=15)):
    setting = getattr(settings, "PARKKIHUBI_TIME_OLD_PARKINGS_VISIBLE", None)
    result = setting if setting is not None else default
    assert isinstance(result, datetime.timedelta)
    return result
