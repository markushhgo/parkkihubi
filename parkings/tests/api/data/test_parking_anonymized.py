from datetime import datetime, timedelta

import pytest
from django.urls import reverse

from parkings.pagination import DataPagination

from ..utils import (
    check_list_endpoint_base_fields, check_method_status_codes, get)

list_url = reverse('data:v1:parking_anonymized-list')

ITEM_KEYS = {'id', 'created_at', 'modified_at', 'location', 'location_gk25fin', 'time_start', 'time_end',
             'terminal_number', 'is_disc_parking', 'operator', 'domain', 'region', 'parking_area', 'zone',
             'terminal'}


def test_disallowed_methods(data_user_api_client, parking):
    disallowed_methods = ('post', 'put', 'patch', 'delete')
    check_method_status_codes(data_user_api_client, list_url, disallowed_methods, 405)


def test_unauthorized_list(api_client, parking):
    get(api_client, list_url, status_code=401)


def test_get_list_check_data(data_user_api_client, parking):
    data = get(data_user_api_client, list_url)
    check_list_endpoint_base_fields(data)
    assert data['count'] == 1
    assert data['results'][0].keys() == ITEM_KEYS


def test_get_list_data_is_anonymized(data_user_api_client, parking):
    data = get(data_user_api_client, list_url)
    item = data['results'][0]
    with pytest.raises(KeyError):
        _ = item['registration_number']
    with pytest.raises(KeyError):
        _ = item['normalized_reg_num']


def test_filter_time_start(data_user_api_client, parking):
    time_start_str = datetime.strftime(parking.time_start + timedelta(hours=1), '%Y-%m-%dT%H:%M:%S.%fZ')
    data = get(data_user_api_client, list_url + f'?time_start__gte={time_start_str}')
    assert data['count'] == 0
    data = get(data_user_api_client, list_url + f'?time_start__lte={time_start_str}')
    assert data['count'] == 1

    time_start_str = datetime.strftime(parking.time_start - timedelta(hours=1), '%Y-%m-%dT%H:%M:%S.%fZ')
    data = get(data_user_api_client, list_url + f'?time_start__gte={time_start_str}')
    assert data['count'] == 1
    data = get(data_user_api_client, list_url + f'?time_start__lte={time_start_str}')
    assert data['count'] == 0


def test_paginator(data_user_api_client, parking_factory):
    page_size = min(DataPagination.page_size, 5)
    parking_factory.create_batch(page_size)
    data = get(data_user_api_client, list_url + f"?page_size={page_size}")
    assert data['count'] == page_size
    assert data['next'] is None
    assert data['previous'] is None
    data = get(data_user_api_client, list_url + "?page=2&page_size=2")
    assert data['next'] is not None
    assert data['previous'] is not None
