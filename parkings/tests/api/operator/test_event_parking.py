
import json
from datetime import datetime, timedelta

import pytest
from django.conf import settings
from django.urls import reverse
from django.utils import timezone
from freezegun import freeze_time

from parkings.models import EnforcementDomain, EventParking
from parkings.models.constants import GK25FIN_SRID

from ..utils import (
    ALL_METHODS, check_method_status_codes, check_required_fields, delete,
    patch, post, put)

list_url = reverse('operator:v1:eventparking-list')


def get_detail_url(obj):
    return reverse('operator:v1:eventparking-detail', kwargs={'pk': obj.pk})


@pytest.fixture
def new_event_parking_data():
    return {
        'registration_number': 'JLH-247',
        'time_start': '2016-12-10T20:34:38Z',
        'time_end': '2016-12-10T23:33:29Z',
        'location': {'coordinates': [24.90, 60.16], 'type': 'Point'},
    }


@pytest.fixture
def updated_event_parking_data():
    return {
        'registration_number': 'ABC-123',
        'time_start': '2016-12-10T20:34:38Z',
        'time_end': '2016-12-10T23:33:29Z',
        'location': {'coordinates': [24.90, 60.16], 'type': 'Point'},
    }


@pytest.fixture
def event_parking_data_outside_event_areas():
    return {
        'registration_number': 'VSM-162',
        'time_start': '2016-12-12T20:34:38Z',
        'time_end': '2016-12-12T23:33:29Z',
        'location': {'coordinates': [60.444052373652376, 22.29251289354579], 'type': 'Point'},
    }


def check_response_data(posted_data, response_data):
    """
    Check that parking data dict in a response has the right fields and matches the posted one.
    """
    expected_keys = {
        'id', 'registration_number',
        'time_start', 'time_end',
        'location', 'created_at', 'modified_at',
        'status', 'event_area_id', 'domain',
    }

    posted_data_keys = set(posted_data)
    returned_data_keys = set(response_data)
    assert returned_data_keys == expected_keys

    # assert common fields equal
    for key in returned_data_keys & posted_data_keys:
        assert response_data[key] == posted_data[key]

    assert 'is_disc_parking' not in set(response_data)


def check_data_matches_object(data, obj):
    """
    Check that a event parking data dict and an actual EventParking object match.
    """

    # string or integer valued fields should match 1:1
    for field in {'registration_number'}:
        assert data[field] == getattr(obj, field)

    assert data['time_start'] == obj.time_start.strftime('%Y-%m-%dT%H:%M:%SZ')

    obj_time_end = obj.time_end.strftime('%Y-%m-%dT%H:%M:%SZ') if obj.time_end else None
    assert data['time_end'] == obj_time_end
    obj_location = json.loads(obj.location.geojson) if obj.location else None
    assert data['location'] == obj_location


def test_disallowed_methods(operator_api_client, parking):
    list_disallowed_methods = ('get', 'put', 'patch', 'delete')
    check_method_status_codes(operator_api_client, list_url, list_disallowed_methods, 405)

    detail_disallowed_methods = ('get', 'post')
    check_method_status_codes(operator_api_client, get_detail_url(parking), detail_disallowed_methods, 405)


def test_unauthenticated_and_normal_users_cannot_do_anything(api_client, user_api_client, event_parking):
    urls = (list_url, get_detail_url(event_parking))
    check_method_status_codes(api_client, urls, ALL_METHODS, 401)
    check_method_status_codes(user_api_client, urls, ALL_METHODS, 403, error_code='permission_denied')


def test_event_parking_required_fields(operator_api_client, event_parking):
    expected_required_fields = {'registration_number', 'time_start'}
    check_required_fields(operator_api_client, list_url, expected_required_fields)
    check_required_fields(operator_api_client, get_detail_url(event_parking),
                          expected_required_fields, detail_endpoint=True)


def test_post_event_parking_with_event_area_id_and_location(operator_api_client, new_event_parking_data, event_area):
    new_event_parking_data['event_area_id'] = str(event_area.id)
    response_data = post(operator_api_client, list_url, new_event_parking_data)
    check_response_data(new_event_parking_data, response_data)
    new_event_parking = EventParking.objects.get(id=response_data['id'])
    check_data_matches_object(new_event_parking_data, new_event_parking)
    assert response_data['event_area_id'] == new_event_parking_data['event_area_id']


def test_post_event_parking_only_with_event_area_id(operator_api_client, new_event_parking_data, event_area):
    new_event_parking_data.pop('location')
    new_event_parking_data.pop('time_end')
    new_event_parking_data['event_area_id'] = str(event_area.id)
    response_data = post(operator_api_client, list_url, new_event_parking_data)
    check_response_data(new_event_parking_data, response_data)
    new_event_parking = EventParking.objects.get(id=response_data['id'])
    assert new_event_parking.event_area.id == event_area.id
    assert response_data['event_area_id'] == new_event_parking_data['event_area_id']


def test_post_event_parking_with_non_existing_event_area_id(operator_api_client, new_event_parking_data):
    new_event_parking_data['event_area_id'] = '5097a7b1-2bf1-4a69-be8a-669f300d993e'
    post(operator_api_client, list_url, new_event_parking_data, 400)


def test_post_event_parking_with_event_area_id_in_other_domain(operator_api_client,
                                                               new_event_parking_data,
                                                               event_area_factory):
    enforcement_domain = EnforcementDomain.objects.create(code='TES', name='Test')
    event_area = event_area_factory(domain=enforcement_domain)
    new_event_parking_data['event_area_id'] = event_area.id
    post(operator_api_client, list_url, new_event_parking_data, 400)


def test_put_event_parking(operator_api_client, event_parking, updated_event_parking_data):
    detail_url = get_detail_url(event_parking)
    assert EventParking.objects.count() == 1
    response_data = put(operator_api_client, detail_url, updated_event_parking_data)
    assert EventParking.objects.count() == 1
    # check data in the response
    check_response_data(updated_event_parking_data, response_data)

    # check the actual object
    event_parking.refresh_from_db()
    check_data_matches_object(updated_event_parking_data, event_parking)


def test_patch_event_parking_event_area_id(operator_api_client, complete_event_parking, event_area_factory):
    detail_url = get_detail_url(complete_event_parking)
    event_area = event_area_factory()
    new_event_area_id = str(event_area.id)
    response_data = patch(operator_api_client, detail_url, {'event_area_id': new_event_area_id})

    # # check data in the response
    check_response_data({'event_area_id': new_event_area_id}, response_data)

    # # check the actual object
    complete_event_parking.refresh_from_db()
    assert str(complete_event_parking.event_area.id) == new_event_area_id


def test_post_event_parking(operator_api_client, new_event_parking_data, event_area):
    response_data = post(operator_api_client, list_url, new_event_parking_data)
    check_response_data(new_event_parking_data, response_data)
    new_event_parking = EventParking.objects.get(id=response_data['id'])
    check_data_matches_object(new_event_parking_data, new_event_parking)
    # Test that event area assigned by location
    assert new_event_parking.event_area.id == event_area.id
    # test location_gk25fin
    location_gk25fin = new_event_parking.location.transform(GK25FIN_SRID, clone=True)
    assert location_gk25fin.wkt == new_event_parking.location_gk25fin.wkt


def test_post_event_parking_with_time_end_null(operator_api_client, new_event_parking_data, event_area):
    new_event_parking_data['time_end'] = None
    response_data = post(operator_api_client, list_url, new_event_parking_data)
    check_response_data(new_event_parking_data, response_data)
    new_event_parking = EventParking.objects.get(id=response_data['id'])
    check_data_matches_object(new_event_parking_data, new_event_parking)


def test_post_event_parking_to_event_area_not_active(operator_api_client, new_event_parking_data, event_area_factory):
    now = timezone.now()
    event_area_factory(time_start=now - timedelta(days=10), time_end=now - timedelta(days=9))
    post(operator_api_client, list_url, new_event_parking_data, 400)


def test_post_event_parking_without_event_area(operator_api_client, event_parking_data_outside_event_areas, event_area):
    post(operator_api_client, list_url, event_parking_data_outside_event_areas, 400)
    assert EventParking.objects.count() == 0
    # Test qthat by adding event_area_id, makes post succeed
    event_parking_data_outside_event_areas['event_area_id'] = event_area.id
    post(operator_api_client, list_url, event_parking_data_outside_event_areas, 201)
    assert EventParking.objects.count() == 1


def test_post_event_parking_without_event_area_and_location(operator_api_client, new_event_parking_data):
    new_event_parking_data.pop('location')
    post(operator_api_client, list_url, new_event_parking_data, 400)
    assert EventParking.objects.count() == 0


def test_patch_event_parking(operator_api_client, event_parking):
    detail_url = get_detail_url(event_parking)
    new_time_end = (event_parking.time_end + timedelta(hours=2)).replace(microsecond=0)
    new_time_end_str = new_time_end.strftime('%Y-%m-%dT%H:%M:%SZ')
    response_data = patch(operator_api_client, detail_url, {'time_end': new_time_end_str})

    # check data in the response
    check_response_data({'time_end': new_time_end_str}, response_data)

    # check the actual object
    event_parking.refresh_from_db()
    assert event_parking.time_end == new_time_end


def test_delete_event_parking(operator_api_client, event_parking):
    detail_url = get_detail_url(event_parking)
    delete(operator_api_client, detail_url)
    assert not EventParking.objects.filter(id=event_parking.id).exists()


def test_cannot_modify_other_than_own_event_parkings(operator_2_api_client, event_parking, new_event_parking_data):
    detail_url = get_detail_url(event_parking)
    put(operator_2_api_client, detail_url, new_event_parking_data, 404)
    patch(operator_2_api_client, detail_url, new_event_parking_data, 404)
    delete(operator_2_api_client, detail_url, 404)


def test_cannot_modify_event_parking_after_modify_period(operator_api_client,
                                                         new_event_parking_data,
                                                         updated_event_parking_data,
                                                         event_area):
    start_time = datetime(2010, 1, 1, 12, 00).replace(tzinfo=timezone.utc)
    event_area.time_start = start_time
    event_area.time_end = start_time + timedelta(hours=1)
    event_area.save()
    error_message = 'Grace period has passed. Only "time_end" can be updated via PATCH.'
    error_code = 'grace_period_over'

    with freeze_time(start_time):
        response_parking_data = post(operator_api_client, list_url, new_event_parking_data)

    new_event_parking = EventParking.objects.get(id=response_parking_data['id'])
    end_time = start_time + settings.PARKKIHUBI_TIME_EVENT_PARKINGS_EDITABLE + timedelta(minutes=1)

    with freeze_time(end_time):

        # PUT
        error_data = put(operator_api_client, get_detail_url(new_event_parking), updated_event_parking_data, 403)
        assert error_message in error_data['detail']
        assert error_data['code'] == error_code

        # PATCH other fields than 'time_end'
        for field_name in updated_event_parking_data:
            if field_name == 'time_end':
                continue
            event_parking_data = {field_name: updated_event_parking_data[field_name]}
            error_data = patch(operator_api_client, get_detail_url(new_event_parking), event_parking_data, 403)
            assert error_message in error_data['detail']
            assert error_data['code'] == error_code


def test_can_modify_time_end_after_modify_period(operator_api_client, new_event_parking_data, event_area):
    start_time = datetime(2010, 1, 1, 12, 00).replace(tzinfo=timezone.utc)
    event_area.time_start = start_time
    event_area.time_end = start_time + timedelta(hours=1)
    event_area.save()

    with freeze_time(start_time):
        response_parking_data = post(operator_api_client, list_url, new_event_parking_data)

    new_event_parking = EventParking.objects.get(id=response_parking_data['id'])
    end_time = start_time + settings.PARKKIHUBI_TIME_EVENT_PARKINGS_EDITABLE + timedelta(minutes=1)

    with freeze_time(end_time):
        event_parking_data = {'time_end': '2016-12-12T23:33:29Z'}
        patch(operator_api_client, get_detail_url(new_event_parking), event_parking_data, 200)
        new_event_parking.refresh_from_db()
        assert new_event_parking.time_end.day == 12  # old day was 10


def test_time_start_cannot_be_after_time_end(operator_api_client, event_parking, new_event_parking_data):
    new_event_parking_data['time_start'] = '2116-12-10T23:33:29Z'
    detail_url = get_detail_url(event_parking)
    error_message = '"time_start" cannot be after "time_end".'

    # POST
    error_data = post(operator_api_client, list_url, new_event_parking_data, status_code=400)
    assert error_message in error_data['non_field_errors']

    # PUT
    error_data = put(operator_api_client, detail_url, new_event_parking_data, status_code=400)
    assert error_message in error_data['non_field_errors']

    # PATCH
    patch_data = {'time_start': '2116-12-10T23:33:29Z'}
    error_data = patch(operator_api_client, detail_url, patch_data, status_code=400)
    assert error_message in error_data['non_field_errors']


def test_default_enforcement_domain_is_used_on_event_parking_creation_if_not_specified(
    operator_api_client, new_event_parking_data, event_area
):
    response_parking_data = post(operator_api_client, list_url, new_event_parking_data)
    assert response_parking_data['domain'] == EnforcementDomain.get_default_domain().code


def test_enforcement_domain_can_be_specified_on_parking_creation(operator_api_client,
                                                                 new_event_parking_data,
                                                                 event_area):
    enforcement_domain = EnforcementDomain.objects.create(code='TKU', name='Turku')
    event_area.domain = enforcement_domain
    event_area.save()
    new_event_parking_data.update(domain=enforcement_domain.code)

    response_event_parking_data = post(operator_api_client, list_url, new_event_parking_data)

    assert not response_event_parking_data['domain'] == EnforcementDomain.get_default_domain().code
    assert response_event_parking_data['domain'] == enforcement_domain.code
