# -*- coding: utf-8 -*-

import datetime
import json
from copy import deepcopy
from datetime import timedelta

import pytest
from django.contrib.gis.geos import MultiPolygon, Point, Polygon
from django.urls import reverse
from django.utils import timezone
from rest_framework.status import HTTP_200_OK, HTTP_400_BAD_REQUEST

from parkings.api.monitoring.region import WGS84_SRID
from parkings.factories import EnforcerFactory
from parkings.factories.parking import create_payment_zone
from parkings.factories.permit import create_permit_series
from parkings.models import ParkingCheck, Permit, PermitArea
from parkings.models.constants import GK25FIN_SRID
from parkings.tests.api.utils import check_required_fields

from ...utils import approx

list_url = reverse("enforcement:v1:check_parking")


PARKING_DATA = {
    "registration_number": "ABC-123",
    "location": {"longitude": 24.9, "latitude": 60.2},
}

PARKING_DATA_2 = {
    "registration_number": "ABC-123",
    "location": {"longitude": 26.4, "latitude": 64.2},
}


INVALID_PARKING_DATA = {
    "registration_number": "ABC-123",
    "location": {"longitude": 24.9, "latitude": 60.4},
}

GEOM_1 = [
    (24.8, 60.3),  # North West corner
    (25.0, 60.3),  # North East corner
    (25.0, 60.1),  # South East corner
    (24.8, 60.1),  # South West corner
]

GEOM_2 = [
    (26.8, 64.3),  # North West corner
    (26.0, 64.3),  # North East corner
    (26.0, 64.1),  # South East corner
    (26.8, 64.1),  # South West corner
]

GEOM_3 = [
    (23.8, 64.3),  # North West corner
    (24.0, 64.3),  # North East corner
    (24.0, 64.1),  # South East corner
    (23.8, 64.1),  # South West corner
]


def create_permit_area(client=None, domain=None, allowed_user=None, identifier="A", name="Kamppi", geom=None):
    assert client or (domain and allowed_user)
    if geom is None:
        geom = create_area_geom()
    area = PermitArea.objects.create(
        domain=(domain or client.enforcer.enforced_domain),
        identifier=identifier,
        name=name,
        geom=geom)
    area.allowed_users.add(allowed_user or client.auth_user)
    return area


def create_area_geom(geom=GEOM_1):
    area_wgs84 = [Point(x, srid=WGS84_SRID) for x in geom]
    area_gk25fin = [
        x.transform(GK25FIN_SRID, clone=True) for x in area_wgs84
    ]
    points = area_gk25fin
    points.append(area_gk25fin[0])
    polygons = Polygon(points)

    return MultiPolygon(polygons)


def create_permit(domain, permit_series=None, end_time=None, registration_number="ABC-123", area="A", start_time=None):
    end_time = end_time or timezone.now() + datetime.timedelta(days=1)
    if not start_time:
        start_time = timezone.now()
    series = permit_series or create_permit_series(active=True)

    subjects = [
        {
            "end_time": str(end_time),
            "start_time": str(start_time),
            "registration_number": registration_number,
        }
    ]
    areas = [{"area": area, "end_time": str(end_time), "start_time": str(start_time)}]

    return Permit.objects.create(
        domain=domain,
        series=series, external_id=12345, subjects=subjects, areas=areas
    )


def test_check_parking_allowed_event_parking(enforcer_api_client, event_parking_factory, enforcer, event_area_factory):
    event_area = event_area_factory.create(geom=create_area_geom(), domain=enforcer.enforced_domain)
    event_parking = event_parking_factory(registration_number="ABC-123",
                                          domain=enforcer.enforced_domain, event_area=event_area)
    response = enforcer_api_client.post(list_url, data=PARKING_DATA)
    assert response.status_code == HTTP_200_OK
    assert response.data["allowed"] is True
    assert response.data["end_time"] == event_parking.time_end
    assert ParkingCheck.objects.filter(
        registration_number=event_parking.registration_number).first().result["allowed"] is True


def test_check_parking_allowed_event_parking_details(
        enforcer_api_client, event_parking_factory, enforcer, event_area_factory):
    event_area = event_area_factory.create(geom=create_area_geom(), domain=enforcer.enforced_domain)
    event_parking = event_parking_factory(registration_number="ABC-123",
                                          domain=enforcer.enforced_domain, event_area=event_area)
    data = deepcopy(PARKING_DATA)
    data["details"] = ["operator", "time_start", "permissions"]
    response = enforcer_api_client.post(list_url, data=data)

    assert response.status_code == HTTP_200_OK
    assert response.data["allowed"] is True
    assert response.data["end_time"] == event_parking.time_end
    assert response.data["permissions"]["event_areas"][0] == event_area.id
    assert response.data["operator"] == event_parking.operator.name
    assert response.data["time_start"] == event_parking.time_start
    assert ParkingCheck.objects.filter(
        registration_number=event_parking.registration_number).first().result["allowed"] is True


def test_check_parking_not_allowed_event_parking_details(
        enforcer_api_client, event_parking_factory, enforcer, event_area_factory):
    event_area = event_area_factory.create(geom=create_area_geom(), domain=enforcer.enforced_domain)
    event_parking_factory(registration_number="CBA-123", domain=enforcer.enforced_domain, event_area=event_area)
    data = deepcopy(PARKING_DATA)
    data["details"] = ["operator", "time_start", "permissions"]

    response = enforcer_api_client.post(list_url, data=data)
    assert response.status_code == HTTP_200_OK
    assert response.data["allowed"] is False
    assert response.data["end_time"] is None
    assert response.data["permissions"]["event_areas"] == []
    assert response.data["permissions"]["zones"] == []
    assert response.data["operator"] is None
    assert response.data["time_start"] is None
    assert ParkingCheck.objects.filter(
        registration_number=PARKING_DATA["registration_number"]).first().result["allowed"] is False


def test_check_event_parking_parked_in_wrong_event_area_include_details(
        enforcer_api_client, event_parking_factory, enforcer, event_area_factory):
    event_area_1 = event_area_factory.create(geom=create_area_geom(), domain=enforcer.enforced_domain)
    event_area_2 = event_area_factory.create(geom=create_area_geom(geom=GEOM_2), domain=enforcer.enforced_domain)
    # Parked inside event_area_2, i.e., inside GEOM_2, but event_area_1 is assigned
    location = Point(PARKING_DATA_2["location"]["longitude"], PARKING_DATA_2["location"]["latitude"], srid=WGS84_SRID)
    event_parking_factory(registration_number="ABC-123", domain=enforcer.enforced_domain,
                          event_area=event_area_1, location=location)
    data = deepcopy(PARKING_DATA_2)
    data["details"] = ["operator", "time_start", "permissions"]
    response = enforcer_api_client.post(list_url, data=data)

    assert response.status_code == HTTP_200_OK
    assert response.data["location"]["event_area"] == event_area_2.id
    assert response.data["allowed"] is False
    assert response.data["end_time"] is None
    assert len(response.data["permissions"]["event_areas"]) == 1
    assert event_area_1.id in response.data["permissions"]["event_areas"]
    assert response.data["permissions"]["zones"] == []
    assert response.data["operator"] is None
    assert response.data["time_start"] is None
    assert ParkingCheck.objects.filter(
        registration_number=PARKING_DATA["registration_number"]).first().result["allowed"] is False


def test_check_parking_not_allowed_parking_and_event_parking_permission_details(
        enforcer_api_client, event_parking_factory, operator, enforcer, event_area_factory, parking_factory):
    # In this very improbable scenario, the registration number has an active parking and active event parking,
    # but the vehicle is parked outside the active zone and event area.
    event_area = event_area_factory.create(geom=create_area_geom(geom=GEOM_2), domain=enforcer.enforced_domain)
    event_parking_factory(registration_number="ABC-123",
                          domain=enforcer.enforced_domain, event_area=event_area)
    create_payment_zone(domain=enforcer.enforced_domain)
    zone = create_payment_zone(geom=create_area_geom(geom=GEOM_2), number=2, code="2", domain=enforcer.enforced_domain)
    parking = parking_factory(registration_number="ABC-123", operator=operator, zone=zone, domain=zone.domain)
    data = deepcopy(PARKING_DATA)
    data["details"] = ["time_start", "operator", "permissions"]
    response = enforcer_api_client.post(list_url, data=data)

    assert response.status_code == HTTP_200_OK
    assert response.data["allowed"] is False
    assert response.data["permissions"]["event_areas"] == [event_area.id]
    assert response.data["permissions"]["zones"] == [parking.zone.number]
    assert response.data["operator"] is None
    assert response.data["time_start"] is None
    assert ParkingCheck.objects.filter(
        registration_number=PARKING_DATA["registration_number"]).first().result["allowed"] is False


def test_check_parking_not_allowed_multiple_active_parkings_and_permits_permissions_details(
    enforcer_api_client,
    event_parking_factory,
    operator, enforcer,
    event_area_factory,
    parking_factory
):
    # In this very improbable scenario, the registration number has two active event parkings, active parkings
    # and permits, but the vehicle is parked outside its active parkings and permits.
    event_area_1 = event_area_factory.create(geom=create_area_geom(geom=GEOM_3), domain=enforcer.enforced_domain)
    event_parking_factory(registration_number="ABC-123",
                          domain=enforcer.enforced_domain, event_area=event_area_1)
    event_area_2 = event_area_factory.create(geom=create_area_geom(geom=GEOM_2), domain=enforcer.enforced_domain)
    event_parking_factory(registration_number="ABC-123",
                          domain=enforcer.enforced_domain, event_area=event_area_2)

    zone_1 = create_payment_zone(domain=enforcer.enforced_domain)
    zone_2 = create_payment_zone(geom=create_area_geom(geom=GEOM_2), number=2,
                                 code="2", domain=enforcer.enforced_domain)
    zone_3 = create_payment_zone(geom=create_area_geom(geom=GEOM_3), number=3,
                                 code="3", domain=enforcer.enforced_domain)
    parking_factory(registration_number="ABC-123", operator=operator, zone=zone_2, domain=zone_1.domain)
    parking_factory(registration_number="ABC-123", operator=operator, zone=zone_3, domain=zone_2.domain)

    create_permit_area(enforcer_api_client, geom=create_area_geom(geom=GEOM_2))
    create_permit_area(enforcer_api_client, identifier="B", name="Kauppatori", geom=create_area_geom(geom=GEOM_3))

    permit_1 = create_permit(domain=enforcer_api_client.enforcer.enforced_domain,
                             start_time=timezone.now() - datetime.timedelta(days=1))
    permit_2 = create_permit(domain=enforcer_api_client.enforcer.enforced_domain, area="B",
                             start_time=timezone.now() - datetime.timedelta(days=1))

    data = deepcopy(PARKING_DATA)
    data["details"] = ["time_start", "operator", "permissions"]
    response = enforcer_api_client.post(list_url, data=data)

    assert response.status_code == HTTP_200_OK
    assert response.data["allowed"] is False
    assert response.data["location"]["payment_zone"] == zone_1.number
    assert len(response.data["permissions"]["event_areas"]) == 2
    assert event_area_1.id in response.data["permissions"]["event_areas"]
    assert event_area_2.id in response.data["permissions"]["event_areas"]
    assert len(response.data["permissions"]["zones"]) == 2
    assert zone_2.number in response.data["permissions"]["zones"]
    assert zone_3.number in response.data["permissions"]["zones"]
    assert len(response.data["permissions"]["permits"]) == 2
    assert response.data["permissions"]["permits"][0]["subjects"] == permit_1.subjects
    assert response.data["permissions"]["permits"][0]["areas"] == permit_1.areas
    assert response.data["permissions"]["permits"][1]["subjects"] == permit_2.subjects
    assert response.data["permissions"]["permits"][1]["areas"] == permit_2.areas
    assert response.data["operator"] is None
    assert response.data["time_start"] is None
    assert ParkingCheck.objects.filter(
        registration_number=PARKING_DATA["registration_number"]).first().result["allowed"] is False


def test_check_event_parking_outside_event_area(
        enforcer_api_client, event_parking_factory, enforcer, event_area_factory):
    event_area = event_area_factory.create(geom=create_area_geom(), domain=enforcer.enforced_domain)
    location = Point(PARKING_DATA_2["location"]["longitude"], PARKING_DATA_2["location"]["latitude"], srid=WGS84_SRID)
    event_parking_factory(registration_number="ABC-123",
                          domain=enforcer.enforced_domain, event_area=event_area, location=location)
    response = enforcer_api_client.post(list_url, data=PARKING_DATA_2)
    assert response.status_code == HTTP_200_OK
    assert response.data["location"]["event_area"] is None
    assert response.data["allowed"] is False
    assert response.data["end_time"] is None
    assert ParkingCheck.objects.filter(
        registration_number=PARKING_DATA["registration_number"]).first().result["allowed"] is False


def test_check_event_parking_with_time_end_null(
        enforcer_api_client, event_parking_factory, enforcer, event_area_factory):
    time_end = None
    now = timezone.now()
    time_start = now - timedelta(hours=1)
    event_area = event_area_factory.create(geom=create_area_geom(), domain=enforcer.enforced_domain)
    event_parking_factory(registration_number="ABC-123", domain=enforcer.enforced_domain,
                          time_start=time_start, time_end=time_end, event_area=event_area)

    response = enforcer_api_client.post(list_url, data=PARKING_DATA)
    assert response.status_code == HTTP_200_OK
    assert response.data["allowed"] is True
    assert response.data["end_time"] is None
    assert response.data["location"]["event_area"] == event_area.id
    assert ParkingCheck.objects.filter(
        registration_number=PARKING_DATA["registration_number"]).first().result["allowed"] is True


def test_check_parking_required_fields(enforcer_api_client):
    expected_required_fields = {"registration_number", "location"}
    check_required_fields(enforcer_api_client, list_url, expected_required_fields)


def test_check_parking_valid_parking(operator, enforcer, enforcer_api_client, parking_factory):
    zone = create_payment_zone(domain=enforcer.enforced_domain)
    parking = parking_factory(registration_number="ABC-123", operator=operator, zone=zone, domain=zone.domain)

    response = enforcer_api_client.post(list_url, data=PARKING_DATA)

    assert response.status_code == HTTP_200_OK
    assert response.data["allowed"] is True
    assert response.data["end_time"] == parking.time_end


def test_check_parking_details_operator_parameter(operator, enforcer, enforcer_api_client, parking_factory):
    zone = create_payment_zone(domain=enforcer.enforced_domain)
    parking = parking_factory(registration_number="ABC-123", operator=operator, zone=zone, domain=zone.domain)
    data = deepcopy(PARKING_DATA)
    data["details"] = ["operator"]
    response = enforcer_api_client.post(list_url, data=data)

    assert response.status_code == HTTP_200_OK
    assert response.data["operator"] == operator.name
    assert response.data["allowed"] is True
    assert response.data["end_time"] == parking.time_end
    assert ParkingCheck.objects.filter(
        registration_number=PARKING_DATA["registration_number"]).first().result["allowed"] is True


def test_check_parking_details_time_start_parameter(operator, enforcer, enforcer_api_client, parking_factory):
    zone = create_payment_zone(domain=enforcer.enforced_domain)
    parking = parking_factory(registration_number="ABC-123", operator=operator, zone=zone, domain=zone.domain)
    data = deepcopy(PARKING_DATA)
    data["details"] = ["time_start"]
    response = enforcer_api_client.post(list_url, data=data)

    assert response.status_code == HTTP_200_OK
    assert response.data["time_start"] == parking.time_start
    assert response.data["allowed"] is True
    assert response.data["end_time"] == parking.time_end
    assert ParkingCheck.objects.filter(
        registration_number=PARKING_DATA["registration_number"]).first().result["allowed"] is True


def test_check_parking_details_permissions_parameter(operator, enforcer, enforcer_api_client, parking_factory):
    zone = create_payment_zone(domain=enforcer.enforced_domain)
    parking = parking_factory(registration_number="ABC-123", operator=operator, zone=zone, domain=zone.domain)
    data = deepcopy(PARKING_DATA)
    data["details"] = ["permissions"]
    response = enforcer_api_client.post(list_url, data=data)

    assert response.status_code == HTTP_200_OK
    assert response.data["permissions"]["zones"] == [parking.zone.number]
    assert response.data["permissions"]["event_areas"] == []
    assert response.data["allowed"] is True
    assert response.data["end_time"] == parking.time_end


def test_check_parking_details_parking_not_allowed(operator, enforcer, enforcer_api_client, parking_factory):
    data = deepcopy(PARKING_DATA)
    data["details"] = ["operator", "time_start", "permissions"]
    response = enforcer_api_client.post(list_url, data=data)

    assert response.status_code == HTTP_200_OK
    assert response.data["allowed"] is False
    assert response.data["operator"] is None
    assert response.data["time_start"] is None
    assert response.data["permissions"]["zones"] == []
    assert ParkingCheck.objects.filter(
        registration_number=PARKING_DATA["registration_number"]).first().result["allowed"] is False


def test_check_parking_details_invalid_zone(operator, enforcer, enforcer_api_client, parking_factory):
    create_payment_zone(domain=enforcer.enforced_domain)
    zone = create_payment_zone(geom=create_area_geom(geom=GEOM_2), number=2, code="2", domain=enforcer.enforced_domain)
    parking = parking_factory(registration_number="ABC-123", operator=operator, zone=zone, domain=zone.domain)
    data = deepcopy(PARKING_DATA)
    data["details"] = ["operator", "time_start", "permissions"]

    response = enforcer_api_client.post(list_url, data=data)

    assert response.status_code == HTTP_200_OK
    assert response.data["allowed"] is False
    assert response.data["end_time"] is None
    assert response.data["permissions"]["zones"] == [parking.zone.number]
    assert response.data["operator"] is None
    assert response.data["time_start"] is None


def test_check_parking_invalid_time_parking(operator, enforcer, enforcer_api_client, history_parking_factory):
    zone = create_payment_zone(domain=enforcer.enforced_domain)
    history_parking_factory(registration_number="ABC-123", operator=operator, zone=zone, domain=zone.domain)

    response = enforcer_api_client.post(list_url, data=PARKING_DATA)

    assert response.status_code == HTTP_200_OK
    assert response.data["allowed"] is False


def test_check_parking_invalid_zone_parking(operator, enforcer_api_client, parking_factory):
    create_payment_zone(geom=create_area_geom(), number=1, code="1")
    zone = create_payment_zone(geom=create_area_geom(geom=GEOM_2), number=2, code="2")
    parking_factory(registration_number="ABC-123", operator=operator, zone=zone)

    response = enforcer_api_client.post(list_url, data=PARKING_DATA)

    assert response.status_code == HTTP_200_OK
    assert response.data["allowed"] is False


def test_check_parking_valid_permit(enforcer_api_client, staff_user):
    create_permit_area(enforcer_api_client)
    create_permit(domain=enforcer_api_client.enforcer.enforced_domain)

    response = enforcer_api_client.post(list_url, data=PARKING_DATA)

    assert response.status_code == HTTP_200_OK
    assert response.data["allowed"] is True


def test_check_parking_valid_parking_permit_details(enforcer_api_client, staff_user):
    create_permit_area(enforcer_api_client)
    permit = create_permit(domain=enforcer_api_client.enforcer.enforced_domain)
    data = deepcopy(PARKING_DATA)
    data["details"] = ["operator", "time_start", "permissions"]
    response = enforcer_api_client.post(list_url, data=data)

    assert response.status_code == HTTP_200_OK
    assert response.data["allowed"] is True
    assert response.data["operator"] is None
    assert response.data["time_start"] is None
    assert response.data["permissions"]["zones"] == []
    assert response.data["permissions"]["event_areas"] == []
    assert len(response.data["permissions"]["permits"]) == 1
    assert response.data["permissions"]["permits"][0]["subjects"] == permit.subjects
    assert response.data["permissions"]["permits"][0]["areas"] == permit.areas
    assert ParkingCheck.objects.filter(
        registration_number=PARKING_DATA["registration_number"]).first().result["allowed"] is True


def test_check_parking_invalid_location_multiple_permit_details(enforcer_api_client, staff_user):
    create_permit_area(enforcer_api_client)
    create_permit_area(enforcer_api_client, identifier="B", name="Kauppatori", geom=create_area_geom(geom=GEOM_2))

    permit_1 = create_permit(domain=enforcer_api_client.enforcer.enforced_domain,
                             start_time=timezone.now() - datetime.timedelta(days=1))
    permit_2 = create_permit(domain=enforcer_api_client.enforcer.enforced_domain, area="B",
                             start_time=timezone.now() - datetime.timedelta(days=1))

    data = deepcopy(INVALID_PARKING_DATA)
    data["details"] = ["permissions"]
    response = enforcer_api_client.post(list_url, data=data)
    assert response.status_code == HTTP_200_OK
    assert response.data["allowed"] is False
    assert len(response.data["permissions"]["permits"]) == 2
    assert response.data["permissions"]["permits"][0]["subjects"] == permit_1.subjects
    assert response.data["permissions"]["permits"][0]["areas"] == permit_1.areas
    assert response.data["permissions"]["permits"][1]["subjects"] == permit_2.subjects
    assert response.data["permissions"]["permits"][1]["areas"] == permit_2.areas
    assert ParkingCheck.objects.filter(
        registration_number=PARKING_DATA["registration_number"]).first().result["allowed"] is False


def test_check_parking_valid_parking_with_permit_details(enforcer_api_client, parking_factory, operator):
    create_permit_area(enforcer_api_client, identifier="B", name="Kauppatori", geom=create_area_geom(geom=GEOM_2))

    permit_1 = create_permit(domain=enforcer_api_client.enforcer.enforced_domain,
                             start_time=timezone.now() - datetime.timedelta(days=1), area="B")

    zone = create_payment_zone(domain=enforcer_api_client.enforcer.enforced_domain)
    parking = parking_factory(registration_number="ABC-123", operator=operator, zone=zone, domain=zone.domain)
    data = deepcopy(PARKING_DATA)
    data["details"] = ["time_start", "operator", "permissions"]
    response = enforcer_api_client.post(list_url, data=data)
    assert response.status_code == HTTP_200_OK
    assert response.data["allowed"] is True
    assert len(response.data["permissions"]["permits"]) == 1
    assert response.data["permissions"]["permits"][0]["subjects"] == permit_1.subjects
    assert response.data["permissions"]["permits"][0]["areas"] == permit_1.areas
    assert response.data["permissions"]["zones"] == [parking.zone.number]
    assert response.data["time_start"] == parking.time_start
    assert response.data["operator"] == parking.operator.name
    assert ParkingCheck.objects.filter(
        registration_number=PARKING_DATA["registration_number"]).first().result["allowed"] is True


def test_check_parking_invalid_time_permit(enforcer_api_client, staff_user):
    create_permit_area(enforcer_api_client)
    end_time = timezone.now() - datetime.timedelta(days=1)
    create_permit(domain=enforcer_api_client.enforcer.enforced_domain, end_time=end_time)
    response = enforcer_api_client.post(list_url, data=PARKING_DATA)

    assert response.status_code == HTTP_200_OK
    assert response.data["allowed"] is False


def test_check_parking_invalid_location(enforcer_api_client, staff_user):
    create_permit_area(enforcer_api_client)
    create_permit(domain=enforcer_api_client.enforcer.enforced_domain)

    response = enforcer_api_client.post(list_url, data=INVALID_PARKING_DATA)

    assert response.status_code == HTTP_200_OK
    assert response.data["location"] == {
        'event_area': None, 'payment_zone': None, 'permit_area': None}
    assert response.data["allowed"] is False


def test_returned_data_has_correct_schema(enforcer_api_client):
    response = enforcer_api_client.post(list_url, data=PARKING_DATA)

    data = response.data
    assert isinstance(data, dict)
    assert sorted(data.keys()) == ["allowed", "end_time", "location", "time"]
    assert isinstance(data["allowed"], bool)
    assert data["end_time"] is None
    assert isinstance(data["location"], dict)
    assert sorted(data["location"].keys()) == ["event_area", "payment_zone", "permit_area"]
    assert isinstance(data["time"], datetime.datetime)


INVALID_LOCATION_TEST_CASES = {
    "str-location": (
        "foobar",
        "non_field_errors",
        "Invalid data. Expected a dictionary, but got str."),
    "str-latitude": (
        {"latitude": "foobar", "longitude": 33.0},
        "latitude",
        "A valid number is required."),
    "too-big-latitude": (
        {"latitude": 9999, "longitude": 99},
        "latitude",
        "Ensure this value is less than or equal to 90."),
    "too-big-longitude": (
        {"latitude": 90, "longitude": 999},
        "longitude",
        "Ensure this value is less than or equal to 180."),
    "too-small-latitude": (
        {"latitude": -9999, "longitude": 99},
        "latitude",
        "Ensure this value is greater than or equal to -90."),
    "too-small-longitude": (
        {"latitude": 90, "longitude": -999},
        "longitude",
        "Ensure this value is greater than or equal to -180."),
}


@pytest.mark.parametrize("case", INVALID_LOCATION_TEST_CASES.keys())
def test_invalid_location_returns_bad_request(enforcer_api_client, case):
    (location, error_field, error_text) = INVALID_LOCATION_TEST_CASES[case]
    input_data = dict(PARKING_DATA, location=location)
    response = enforcer_api_client.post(list_url, data=input_data)

    assert response.status_code == HTTP_400_BAD_REQUEST
    assert response.data["location"][error_field] == [error_text]


def test_infinite_latitude_returns_bad_request(enforcer_api_client):
    location = {"latitude": float("inf"), "longitude": 0.0},
    input_data = dict(PARKING_DATA, location=location)
    body = json.dumps(input_data).encode("utf-8")
    response = enforcer_api_client.post(
        list_url, data=body, content_type="application/json")

    assert response.status_code == HTTP_400_BAD_REQUEST
    assert response.data["detail"] == (
        "JSON parse error - Out of range float values"
        " are not JSON compliant: 'Infinity'")


@pytest.mark.parametrize("longitude", [-180, 0.0, 180.0])
@pytest.mark.parametrize("latitude", [-90.0, 0.0, 90.0])
def test_extreme_locations_are_ok(
        enforcer_api_client, latitude, longitude):
    location = {"latitude": latitude, "longitude": longitude}
    input_data = dict(PARKING_DATA, location=location)
    response = enforcer_api_client.post(list_url, data=input_data)

    assert response.status_code == HTTP_200_OK
    assert ParkingCheck.objects.first().location.coords == (
        longitude, latitude)


INVALID_REGNUM_TEST_CASES = {
    "too-long": (
        "123456789012345678901",
        "Ensure this field has no more than 20 characters."),
    "blank": (
        "",
        "This field may not be blank."),
    "list": (
        ["ABC-123"],
        "Not a valid string."),
    "dict": (
        {"ABC-123": "ABC-123"},
        "Not a valid string."),
}


@pytest.mark.parametrize("case", INVALID_REGNUM_TEST_CASES.keys())
def test_invalid_regnum_returns_bad_request(enforcer_api_client, case):
    (regnum, error_text) = INVALID_REGNUM_TEST_CASES[case]
    input_data = dict(PARKING_DATA, registration_number=regnum)
    response = enforcer_api_client.post(list_url, data=input_data)

    assert response.status_code == HTTP_400_BAD_REQUEST
    assert response.data["registration_number"] == [error_text]


def test_invalid_timestamp_string_returns_bad_request(enforcer_api_client):
    input_data = dict(PARKING_DATA, time="invalid-timestamp")
    response = enforcer_api_client.post(list_url, data=input_data)

    assert response.status_code == HTTP_400_BAD_REQUEST
    assert response.data["time"] == [
        ("Date has wrong format. Use one of these formats instead:"
         " YYYY-MM-DDThh:mm[:ss[.uuuuuu]][+HH:MM|-HH:MM|Z].")]


def test_requested_time_must_have_timezone(enforcer_api_client):
    naive_dt = datetime.datetime(2011, 1, 31, 12, 34, 56, 123456)
    input_data = dict(PARKING_DATA, time=naive_dt)
    response = enforcer_api_client.post(list_url, data=input_data)

    assert response.status_code == HTTP_400_BAD_REQUEST
    assert response.data["time"] == ["Timezone is required"]


def test_time_is_honored(enforcer_api_client):
    dt = datetime.datetime(2011, 1, 31, 12, 34, 56, 123456,
                           tzinfo=datetime.timezone.utc)
    input_data = dict(PARKING_DATA, time=dt)
    response = enforcer_api_client.post(list_url, data=input_data)

    assert (response.status_code, response.data["time"]) == (HTTP_200_OK, dt)


def test_action_is_logged(enforcer_api_client):
    response = enforcer_api_client.post(list_url, data={
        "registration_number": "XYZ-555",
        "location": {"longitude": 24.1234567, "latitude": 60.2987654},
    })

    assert response.status_code == HTTP_200_OK
    assert ParkingCheck.objects.count() == 1
    recorded_check = ParkingCheck.objects.first()
    assert recorded_check.registration_number == "XYZ-555"
    assert recorded_check.location.coords == approx(
        (24.1234567, 60.2987654), abs=1e-10)
    assert recorded_check.time == response.data["time"]
    assert recorded_check.time_overridden is False
    assert recorded_check.performer


def test_enforcer_can_view_only_own_parking(enforcer_api_client, parking_factory, enforcer):
    zone = create_payment_zone(domain=enforcer.enforced_domain)
    parking = parking_factory(registration_number='ABC-123', zone=zone, domain=zone.domain)
    parking_factory(registration_number='ABC-123')

    response = enforcer_api_client.post(list_url, data=PARKING_DATA)

    assert response.status_code == HTTP_200_OK
    assert response.data["allowed"] is True
    assert response.data["end_time"] == parking.time_end


def test_enforcer_can_view_only_own_permit(enforcer_api_client, staff_user, enforcer):
    create_permit_area(enforcer_api_client)

    end_time = timezone.now() + datetime.timedelta(days=2)
    create_permit(domain=enforcer.enforced_domain, end_time=end_time)

    EnforcerFactory(user=staff_user)
    domain = staff_user.enforcer.enforced_domain
    create_permit_area(domain=domain, allowed_user=staff_user)
    create_permit(domain=domain)

    response = enforcer_api_client.post(list_url, data=PARKING_DATA)

    assert response.status_code == HTTP_200_OK
    assert response.data["allowed"] is True
    assert response.data["end_time"] == end_time
