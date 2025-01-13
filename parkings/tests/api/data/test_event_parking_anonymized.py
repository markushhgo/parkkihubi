from datetime import datetime, timedelta

import pytest
from django.urls import reverse

from parkings.pagination import DataPagination

from ..utils import (
    check_list_endpoint_base_fields, check_method_status_codes, get)

list_url = reverse('data:v1:event_parking_anonymized-list')

ITEM_KEYS = {'id', 'created_at', 'modified_at', 'location', 'location_gk25fin', 'time_start', 'time_end',
                   'operator', 'domain', 'event_area'}


def test_disallowed_methods(data_user_api_client, event_parking):
    disallowed_methods = ('post', 'put', 'patch', 'delete')
    check_method_status_codes(data_user_api_client, list_url, disallowed_methods, 405)


def test_unauthorized_list(api_client, event_parking):
    get(api_client, list_url, status_code=401)


def test_get_list_check_data(data_user_api_client, event_parking):
    data = get(data_user_api_client, list_url)
    check_list_endpoint_base_fields(data)
    assert data['count'] == 1
    assert data['results'][0].keys() == ITEM_KEYS


def test_get_list_data_is_anonymized(data_user_api_client, event_parking):
    data = get(data_user_api_client, list_url)
    item = data['results'][0]
    with pytest.raises(KeyError):
        _ = item['registration_number']
    with pytest.raises(KeyError):
        _ = item['normalized_reg_num']


def test_filter_time_start(data_user_api_client, event_parking):
    time_start_str = datetime.strftime(event_parking.time_start + timedelta(hours=1), '%Y-%m-%dT%H:%M:%S.%fZ')
    data = get(data_user_api_client, list_url + f'?time_start__gte={time_start_str}')
    assert data['count'] == 0
    data = get(data_user_api_client, list_url + f'?time_start__lte={time_start_str}')
    assert data['count'] == 1

    time_start_str = datetime.strftime(event_parking.time_start - timedelta(hours=1), '%Y-%m-%dT%H:%M:%S.%fZ')
    data = get(data_user_api_client, list_url + f'?time_start__gte={time_start_str}')
    assert data['count'] == 1
    data = get(data_user_api_client, list_url + f'?time_start__lte={time_start_str}')
    assert data['count'] == 0


def test_filter_time_end(data_user_api_client, event_parking):
    time_end_str = datetime.strftime(event_parking.time_end + timedelta(hours=1), '%Y-%m-%dT%H:%M:%S.%fZ')
    data = get(data_user_api_client, list_url + f'?time_end__gte={time_end_str}')
    assert data['count'] == 0
    data = get(data_user_api_client, list_url + f'?time_end__lte={time_end_str}')
    assert data['count'] == 1

    time_end_str = datetime.strftime(event_parking.time_end - timedelta(hours=1), '%Y-%m-%dT%H:%M:%S.%fZ')
    data = get(data_user_api_client, list_url + f'?time_end__gte={time_end_str}')
    assert data['count'] == 1
    data = get(data_user_api_client, list_url + f'?time_end__lte={time_end_str}')
    assert data['count'] == 0


def test_paginator(data_user_api_client, event_parking_factory):
    page_size = min(DataPagination.page_size, 5)
    event_parking_factory.create_batch(page_size)
    data = get(data_user_api_client, list_url + f"?page_size={page_size}")
    assert data['count'] == page_size
    assert data['next'] is None
    assert data['previous'] is None
    data = get(data_user_api_client, list_url + "?page=2&page_size=2")
    assert data['next'] is not None
    assert data['previous'] is not None
