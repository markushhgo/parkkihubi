from datetime import timedelta
from unittest.mock import patch

from django.contrib.gis.geos import MultiPolygon, Point, Polygon
from django.urls import reverse
from django.utils import timezone

from parkings.models import EventArea, EventParking, ParkingArea

from ..enforcement.test_check_parking import create_area_geom
from ..utils import (
    check_list_endpoint_base_fields, check_method_status_codes, get,
    get_ids_from_results)

list_url = reverse('public:v1:parkingareastatistics-list')

GEOM_CENTER = [
    (22.0, 60.5),  # North West corner
    (22.5, 60.5),  # North East corner
    (22.5, 60.0),  # South East corner
    (22.0, 60.0),  # South West corner
]

GEOM_PARTIAL_OVERLAP_ON_WEST = [
    (21.8, 60.5),  # North West corner
    (22.25, 60.5),  # North East corner
    (22.25, 60.0),  # South East corner
    (21.8, 60.0),  # South West corner
]


def create_event_area(origin_id, domain, geom, event_start, event_end):
    return EventArea.objects.create(
        origin_id=origin_id,
        domain=domain,
        geom=create_area_geom(geom=geom),
        event_start=event_start,
        event_end=event_end,
    )


def create_parking_area(origin_id, domain, geom):
    return ParkingArea.objects.create(
        origin_id=origin_id,
        domain=domain,
        geom=create_area_geom(geom=geom)
    )


def create_event_parking(location, operator, domain, time_start, time_end):
    return EventParking.objects.create(
        location=location,
        operator=operator,
        domain=domain,
        time_start=time_start,
        time_end=time_end
    )


def get_detail_url(obj):
    return reverse('public:v1:parkingareastatistics-detail', kwargs={'pk': obj.pk})


def find_by_obj_id(obj, iterable):
    return [x for x in iterable if x['id'] == str(obj.id)][0]


def test_overlapping_event_areas(api_client, parking_factory, enforcer, operator):
    parking_area = create_parking_area("center", enforcer.enforced_domain, GEOM_CENTER,)
    results = get(api_client, list_url)['results']
    stats_data = find_by_obj_id(parking_area, results)
    assert stats_data['current_parking_count'] == 0

    with patch('parkings.models.parking.get_closest_area', return_value=parking_area):
        parking_factory.create_batch(4)

    results = get(api_client, list_url)['results']
    stats_data = find_by_obj_id(parking_area, results)
    assert stats_data['current_parking_count'] == 4

    now = timezone.now()
    event_area = create_event_area("center", enforcer.enforced_domain, GEOM_CENTER,
                                   now - timedelta(hours=2), now + timedelta(hours=2))
    assert event_area.parking_areas.first() == parking_area
    assert parking_area.overlapping_event_areas.first() == event_area
    centroid = event_area.geom.centroid.transform(4326, clone=True)
    location = Point(centroid.x, centroid.y)
    event_parking = create_event_parking(location, operator, enforcer.enforced_domain,
                                         now - timedelta(hours=2), now + timedelta(hours=2))
    event_parking.event_area = event_area
    event_parking.save()
    results = get(api_client, list_url)['results']
    stats_data = find_by_obj_id(parking_area, results)
    assert stats_data['current_parking_count'] == 5
    event_area_west = create_event_area("west", enforcer.enforced_domain,
                                        GEOM_PARTIAL_OVERLAP_ON_WEST, now - timedelta(hours=2),
                                        now + timedelta(hours=2))
    assert event_area.parking_areas.first() == parking_area
    ids = EventArea.objects.all().values_list("id", flat=True)
    assert ParkingArea.objects.filter(overlapping_event_areas__in=ids).count() == 2

    centroid = event_area_west.geom.centroid.transform(4326, clone=True)
    location = Point(centroid.x, centroid.y)
    for i in range(5):
        event_parking = create_event_parking(location, operator, enforcer.enforced_domain,
                                             now - timedelta(hours=2), now + timedelta(hours=2))
        event_parking.event_area = event_area_west
        event_parking.save()
    results = get(api_client, list_url)['results']
    stats_data = find_by_obj_id(parking_area, results)
    assert stats_data['current_parking_count'] == 10

    # Test event parkings that are in overlapping event area, but not in the event parking
    location = Point(GEOM_PARTIAL_OVERLAP_ON_WEST[0])
    for i in range(5):
        event_parking = create_event_parking(location, operator, enforcer.enforced_domain,
                                             now - timedelta(hours=2), now + timedelta(hours=2))
        event_parking.event_area = event_area_west
        event_parking.save()
    results = get(api_client, list_url)['results']
    stats_data = find_by_obj_id(parking_area, results)
    assert stats_data['current_parking_count'] == 10


def test_disallowed_methods(api_client, parking_area):
    disallowed_methods = ('post', 'put', 'patch', 'delete')
    urls = (list_url, get_detail_url(parking_area))
    check_method_status_codes(api_client, urls, disallowed_methods, 405)


def test_list_endpoint_base_fields(api_client):
    stats_data = get(api_client, list_url)
    check_list_endpoint_base_fields(stats_data)


def test_get_list_check_data(mocker, api_client, parking_factory, parking_area_factory, history_parking_factory):
    parking_area_1, parking_area_2, parking_area_3, parking_area_4 = parking_area_factory.create_batch(4)

    with patch('parkings.models.parking.get_closest_area', return_value=parking_area_1):
        parking_factory.create_batch(4)

    with patch('parkings.models.parking.get_closest_area', return_value=parking_area_2):
        parking_factory.create_batch(3)

    with patch('parkings.models.parking.get_closest_area', return_value=parking_area_3):
        history_parking_factory.create_batch(5)

    with patch('parkings.models.parking.get_closest_area', return_value=parking_area_4):
        history_parking_factory.create_batch(5, time_end=None)

    results = get(api_client, list_url)['results']
    assert len(results) == 4

    stats_data_1 = find_by_obj_id(parking_area_1, results)
    stats_data_2 = find_by_obj_id(parking_area_2, results)
    stats_data_3 = find_by_obj_id(parking_area_3, results)
    stats_data_4 = find_by_obj_id(parking_area_4, results)

    assert stats_data_1.keys() == {'id', 'current_parking_count'}
    assert stats_data_1['current_parking_count'] == 4
    assert stats_data_2['current_parking_count'] == 0  # under 4
    assert stats_data_3['current_parking_count'] == 0  # not valid parkings currently
    assert stats_data_4['current_parking_count'] == 5  # no end time so valid


def test_get_detail_check_data(api_client, parking_factory, parking_area):
    with patch('parkings.models.parking.get_closest_area', return_value=parking_area):
        parking_factory.create_batch(3)

    stats_data = get(api_client, get_detail_url(parking_area))
    assert stats_data.keys() == {'id', 'current_parking_count'}
    assert stats_data['current_parking_count'] == 0

    with patch('parkings.models.parking.get_closest_area', return_value=parking_area):
        parking_factory()

    stats_data = get(api_client, get_detail_url(parking_area))
    assert stats_data['current_parking_count'] == 4


def test_bounding_box_filter(api_client, parking_area_factory):
    polygon_1 = Polygon([[10, 40], [20, 40], [20, 50], [10, 50], [10, 40]], srid=4326).transform(3879, clone=True)
    polygon_2 = Polygon([[30, 50], [40, 50], [40, 60], [30, 60], [30, 50]], srid=4326).transform(3879, clone=True)

    area_1 = parking_area_factory(geom=MultiPolygon(polygon_1))
    area_2 = parking_area_factory(geom=MultiPolygon(polygon_2))

    data = get(api_client, list_url)
    assert len(data['results']) == 2
    assert get_ids_from_results(data['results']) == {area_1.id, area_2.id}

    data = get(api_client, list_url + '?in_bbox=5,5,85,85')
    assert len(data['results']) == 2

    data = get(api_client, list_url + '?in_bbox=5,35,25,55')
    assert len(data['results']) == 1
    assert get_ids_from_results(data['results']) == {area_1.id}

    data = get(api_client, list_url + '?in_bbox=80,80,85,85')
    assert len(data['results']) == 0
