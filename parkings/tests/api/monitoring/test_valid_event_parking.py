import pytest
from django.contrib.gis.geos import Point
from django.urls import reverse
from django.utils import timezone
from rest_framework.status import (
    HTTP_401_UNAUTHORIZED, HTTP_403_FORBIDDEN, HTTP_405_METHOD_NOT_ALLOWED)

from parkings.api.monitoring.region import WGS84_SRID

from ..enforcement.test_check_parking import (
    GEOM_2, PARKING_DATA, PARKING_DATA_2, create_area_geom)
from ..utils import ALL_METHODS, check_method_status_codes

list_url = reverse('monitoring:v1:valid_event_parking-list')


def detail_url(event_parking):
    return reverse('monitoring:v1:valid_event_parking-detail',
                   kwargs={'pk': event_parking.pk})


@pytest.mark.parametrize('kind', ['list', 'detail'])
def test_permission_checks(api_client, operator_api_client, event_parking, kind):
    url = list_url if kind == 'list' else detail_url(event_parking)
    check_method_status_codes(
        api_client, [url], ALL_METHODS, HTTP_401_UNAUTHORIZED)
    check_method_status_codes(
        operator_api_client, [url], ALL_METHODS, HTTP_403_FORBIDDEN,
        error_code='permission_denied')


@pytest.mark.parametrize('kind', ['list', 'detail'])
def test_disallowed_methods(monitoring_api_client, event_parking, kind):
    url = list_url if kind == 'list' else detail_url(event_parking)
    methods = [x for x in ALL_METHODS if x != 'get']
    check_method_status_codes(
        monitoring_api_client, [url], methods, HTTP_405_METHOD_NOT_ALLOWED)


def test_list_endpoint_data(monitoring_api_client, event_parking, event_area_factory):
    event_area = event_area_factory.create(geom=create_area_geom(), domain=monitoring_api_client.monitor.domain)
    event_parking.event_area = event_area
    event_parking.domain = monitoring_api_client.monitor.domain
    event_parking.save()

    result = monitoring_api_client.get(
        list_url, data={'time': event_parking.time_start.isoformat()})
    assert set(result.data.keys()) == {
        'type', 'count', 'next', 'previous', 'features'}
    assert result.data['type'] == 'FeatureCollection'
    assert result.data['next'] is None
    assert result.data['previous'] is None
    assert result.data['count'] == 1
    assert len(result.data['features']) == 1
    parking_feature = result.data['features'][0]
    check_parking_feature_shape(parking_feature)
    check_parking_feature_matches_parking_object(parking_feature, event_parking)


def test_list_endpoint_event_parking_not_in_assigned_event_area(
        monitoring_api_client, event_parking, event_area_factory):
    event_area = event_area_factory.create(geom=create_area_geom(), domain=monitoring_api_client.monitor.domain)
    location = Point(PARKING_DATA_2["location"]["longitude"], PARKING_DATA_2["location"]["latitude"], srid=WGS84_SRID)
    event_parking.location = location
    event_parking.domain = monitoring_api_client.monitor.domain
    event_parking.event_area = event_area
    event_parking.save()
    result = monitoring_api_client.get(list_url, data={'time': event_parking.time_start.isoformat()})
    assert result.data["features"] == []
    # # Test with location inside the event area
    location = Point(PARKING_DATA["location"]["longitude"], PARKING_DATA["location"]["latitude"], srid=WGS84_SRID)
    event_parking.location = location
    event_parking.save()
    result = monitoring_api_client.get(list_url, data={'time': event_parking.time_start.isoformat()})
    parking_feature = result.data['features'][0]
    check_parking_feature_shape(parking_feature)
    check_parking_feature_matches_parking_object(parking_feature, event_parking)


def check_parking_feature_shape(parking_feature):
    assert set(parking_feature.keys()) == {
        'id', 'type', 'geometry', 'properties'}
    assert parking_feature['type'] == 'Feature'
    assert set(parking_feature['geometry'].keys()) == {
        'type', 'coordinates'}
    assert parking_feature['geometry']['type'] == 'Point'
    assert len(parking_feature['geometry']['coordinates']) == 2
    assert set(parking_feature['properties'].keys()) == {
        'created_at', 'modified_at',
        'time_start', 'time_end',
        'registration_number',
        'operator_name',
    }


def check_parking_feature_matches_parking_object(parking_feature, parking_obj):
    assert parking_feature['id'] == str(parking_obj.id)
    assert parking_feature['geometry']['coordinates'] == list(
        parking_obj.location.coords)
    props = parking_feature['properties']
    direct_fields = ['registration_number']
    for field in direct_fields:
        assert props[field] == getattr(parking_obj, field)

    assert props['created_at'] == iso8601_us(parking_obj.created_at)
    assert props['modified_at'] == iso8601_us(parking_obj.modified_at)
    assert props['time_start'] == iso8601_us(parking_obj.time_start)
    assert props['time_end'] == iso8601_us(parking_obj.time_end)
    assert props['operator_name'] == parking_obj.operator.name


def iso8601(dt):
    return dt.strftime('%Y-%m-%dT%H:%M:%SZ')


def iso8601_us(dt):
    return dt.strftime('%Y-%m-%dT%H:%M:%S.%fZ')


def test_monitor_can_view_only_parkings_from_their_domain(
        monitoring_api_client, staff_api_client, staff_user, event_parking_factory, monitor_factory, event_area_factory
):
    monitor_factory(user=staff_user)
    event_area_1 = event_area_factory.create(geom=create_area_geom(), domain=monitoring_api_client.monitor.domain)
    event_area_2 = event_area_factory.create(geom=create_area_geom(geom=GEOM_2), domain=staff_user.monitor.domain)

    location_1 = Point(PARKING_DATA["location"]["longitude"], PARKING_DATA["location"]["latitude"], srid=WGS84_SRID)
    location_2 = Point(PARKING_DATA_2["location"]["longitude"], PARKING_DATA_2["location"]["latitude"], srid=WGS84_SRID)

    parking_1 = event_parking_factory(domain=monitoring_api_client.monitor.domain,
                                      event_area=event_area_1, location=location_1)
    parking_2 = event_parking_factory(domain=staff_user.monitor.domain, event_area=event_area_2, location=location_2)

    result_1 = monitoring_api_client.get(list_url, data={'time': iso8601(timezone.now())})
    result_2 = staff_api_client.get(list_url, data={'time': iso8601(timezone.now())})

    assert result_1.data['count'] == 1
    parking_feature_1 = result_1.data['features'][0]
    assert parking_feature_1['id'] == str(parking_1.id)

    assert result_2.data['count'] == 1
    parking_feature_2 = result_2.data['features'][0]
    assert parking_feature_2['id'] == str(parking_2.id)
