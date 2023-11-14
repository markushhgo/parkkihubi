from datetime import timedelta
from decimal import Decimal

from django.contrib.gis.geos import MultiPolygon, Polygon
from django.urls import reverse

from ..utils import check_method_status_codes, get, get_ids_from_results

list_url = reverse('public:v1:eventarea-list')

PROPERTIES_KEYS = {'capacity_estimate', 'time_start', 'time_end', 'price', 'price_unit', 'bus_stop_numbers'}


def get_detail_url(obj):
    return reverse('public:v1:eventarea-detail', kwargs={'pk': obj.pk})


def test_disallowed_methods(api_client, event_area):
    disallowed_methods = ('post', 'put', 'patch', 'delete')
    urls = (list_url, get_detail_url(event_area))
    check_method_status_codes(api_client, urls, disallowed_methods, 405)


def test_get_list_check_data(api_client, event_area):
    data = get(api_client, list_url)
    assert data.keys() == {'type', 'count', 'next', 'previous', 'features'}
    assert data['type'] == 'FeatureCollection'
    assert data['count'] == 1

    feature_data = data['features'][0]
    assert feature_data.keys() == {'id', 'type', 'geometry', 'properties'}
    assert feature_data['type'] == 'Feature'
    assert feature_data['id'] == str(event_area.id)

    geometry_data = feature_data['geometry']
    assert geometry_data.keys() == {'type', 'coordinates'}
    assert geometry_data['type'] == 'MultiPolygon'
    assert len(geometry_data['coordinates']) > 0

    properties_data = feature_data['properties']
    assert properties_data.keys() == PROPERTIES_KEYS
    assert properties_data['capacity_estimate'] == event_area.capacity_estimate


def test_priced_event_area(api_client, event_area):
    event_area.price = Decimal('1.23')
    event_area.save()
    feature_data = get(api_client, get_detail_url(event_area))
    assert feature_data['properties']['price'] == '1.23'


def test_event_area_with_price_unit(api_client, event_area):
    event_area.price_unit = 'h'
    event_area.save()
    feature_data = get(api_client, get_detail_url(event_area))
    assert feature_data['properties']['price_unit'] == 'h'


def test_event_area_with_bus_stop_numbers(api_client, event_area):
    event_area.bus_stop_numbers = [123]
    event_area.save()
    feature_data = get(api_client, get_detail_url(event_area))
    assert feature_data['properties']['bus_stop_numbers'] == [123]

    event_area.bus_stop_numbers.append(456)
    event_area.save()
    feature_data = get(api_client, get_detail_url(event_area))
    assert len(feature_data['properties']['bus_stop_numbers']) == 2
    assert feature_data['properties']['bus_stop_numbers'] == [123, 456]


def test_dated_event_area(api_client, event_area):
    data = get(api_client, list_url)
    data["count"] == 1

    event_area.time_start -= timedelta(days=1)
    event_area.time_end -= timedelta(days=1)
    event_area.refresh_from_db()

    data = get(api_client, list_url)
    data["count"] == 0


def test_overlapping_parking_area(event_area, parking_area_factory):
    assert event_area.parking_areas.count() == 0
    parking_area = parking_area_factory()
    assert event_area.parking_areas.first() == parking_area


def test_get_detail_check_data(api_client, event_area):
    feature_data = get(api_client, get_detail_url(event_area))
    assert feature_data.keys() == {'id', 'type', 'geometry', 'properties'}
    assert feature_data['type'] == 'Feature'
    assert feature_data['id'] == str(event_area.id)

    geometry_data = feature_data['geometry']
    assert geometry_data.keys() == {'type', 'coordinates'}
    assert geometry_data['type'] == 'MultiPolygon'
    assert len(geometry_data['coordinates']) > 0

    properties_data = feature_data['properties']
    assert properties_data.keys() == PROPERTIES_KEYS
    assert properties_data['capacity_estimate'] == event_area.capacity_estimate


def test_bounding_box_filter(api_client, event_area_factory):
    polygon_1 = Polygon([[10, 40], [20, 40], [20, 50], [10, 50], [10, 40]], srid=4326).transform(3879, clone=True)
    polygon_2 = Polygon([[30, 50], [40, 50], [40, 60], [30, 60], [30, 50]], srid=4326).transform(3879, clone=True)

    area_1 = event_area_factory(geom=MultiPolygon(polygon_1))
    area_2 = event_area_factory(geom=MultiPolygon(polygon_2))

    data = get(api_client, list_url)
    assert data['count'] == 2
    assert get_ids_from_results(data['features']) == {area_1.id, area_2.id}

    data = get(api_client, list_url + '?in_bbox=5,5,85,85')
    assert data['count'] == 2
    assert get_ids_from_results(data['features']) == {area_1.id, area_2.id}

    data = get(api_client, list_url + '?in_bbox=5,35,25,55')
    assert data['count'] == 1
    assert get_ids_from_results(data['features']) == {area_1.id}

    data = get(api_client, list_url + '?in_bbox=80,80,85,85')
    assert data['count'] == 0
