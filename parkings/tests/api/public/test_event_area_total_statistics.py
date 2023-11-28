import pytest
from django.urls import reverse

from ..utils import (
    check_list_endpoint_base_fields, check_method_status_codes, get)

list_url = reverse('public:v1:eventareatotalstatistics-list')


def get_detail_url(obj):
    return reverse('public:v1:eventareatotalstatistics-detail', kwargs={'pk': obj.pk})


def test_disallowed_methods(api_client, event_area_statistics):
    disallowed_methods = ('post', 'put', 'patch', 'delete')
    urls = (list_url, get_detail_url(event_area_statistics))
    check_method_status_codes(api_client, urls, disallowed_methods, 405)


def test_list_endpoint_base_fields(api_client):
    stats_data = get(api_client, list_url)
    check_list_endpoint_base_fields(stats_data)


def test_get_list_check_data(api_client, event_parking_factory, event_area_factory):
    num_statistics = 5
    for i in range(1, num_statistics + 1):
        event_area = event_area_factory.create()
        event_parking_factory.create_batch(i, event_area=event_area)

    stats_data = get(api_client, list_url)
    assert stats_data['count'] == num_statistics
    results = stats_data['results']
    for i in range(num_statistics):
        assert results[i]['total_parking_count'] == 5 - i


@pytest.mark.django_db
def test_get_detail_check_data(api_client, event_parking_factory, event_area_factory):
    event_area = event_area_factory.create()
    event_parking_factory.create_batch(9, event_area=event_area)
    stats_data = get(api_client, get_detail_url(event_area.statistics))
    assert stats_data.keys() == {'id', 'total_parking_count'}
    assert stats_data['total_parking_count'] == 9
