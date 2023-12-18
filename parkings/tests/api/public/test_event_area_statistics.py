from datetime import timedelta

from django.contrib.gis.geos import MultiPolygon, Point, Polygon
from django.urls import reverse
from django.utils import timezone

from parkings.models import EventArea, EventParking, Parking, ParkingArea

from ..enforcement.test_check_parking import create_area_geom
from ..utils import (
    check_list_endpoint_base_fields, check_method_status_codes, find_by_obj_id,
    get, get_ids_from_results)

list_url = reverse('public:v1:eventareastatistics-list')

GEOM_CENTER = [
    (22.0, 60.5),  # North West corner
    (22.5, 60.5),  # North East corner
    (22.5, 60.0),  # South East corner
    (22.0, 60.0),  # South West corner
]

GEOM_PARTIAL_OVERLAP_ON_WEST = [
    (22.25, 60.5),  # North West corner
    (22.75, 60.5),  # North East corner
    (22.75, 60.0),  # South East corner
    (22.25, 60.0),  # South West corner
]


def create_event_area(origin_id, domain, geom, time_start, time_end):
    return EventArea.objects.create(
        origin_id=origin_id,
        domain=domain,
        geom=create_area_geom(geom=geom),
        time_start=time_start,
        time_end=time_end,
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


def create_parking(location, operator, domain, time_start, time_end):
    return Parking.objects.create(
        location=location,
        operator=operator,
        domain=domain,
        time_start=time_start,
        time_end=time_end
    )


def get_detail_url(obj):
    return reverse('public:v1:eventareastatistics-detail', kwargs={'pk': obj.pk})


def test_overlapping_event_areas(api_client, event_parking_factory, enforcer, operator):
    # Test event area and parking area that exactly overlaps.
    now = timezone.now()
    event_area = create_event_area("center", enforcer.enforced_domain, GEOM_CENTER,
                                   now - timedelta(hours=2), now + timedelta(hours=2))

    results = get(api_client, list_url)['results']
    stats_data = find_by_obj_id(event_area, results)
    assert stats_data['current_parking_count'] == 0
    event_parking_factory.create_batch(4, event_area=event_area)

    results = get(api_client, list_url)['results']
    stats_data = find_by_obj_id(event_area, results)
    assert stats_data['current_parking_count'] == 4
    assert event_area.parking_areas.exists() is False

    parking_area = create_parking_area("center", enforcer.enforced_domain, GEOM_CENTER)

    assert event_area.parking_areas.first() == parking_area
    assert parking_area.overlapping_event_areas.first() == event_area

    centroid = parking_area.geom.centroid.transform(4326, clone=True)
    location = Point(centroid.x, centroid.y)
    parking = create_parking(location, operator, enforcer.enforced_domain,
                             now - timedelta(hours=2), now + timedelta(hours=2))

    assert parking.parking_area == parking_area
    results = get(api_client, list_url)['results']
    stats_data = find_by_obj_id(event_area, results)
    assert stats_data['current_parking_count'] == 5

    parking_area_west = create_parking_area("west", enforcer.enforced_domain, GEOM_PARTIAL_OVERLAP_ON_WEST)
    assert parking_area.overlapping_event_areas.first() == event_area
    ids = ParkingArea.objects.all().values_list("id", flat=True)
    assert EventArea.objects.filter(parking_areas__in=ids).count() == 2

    centroid = parking_area_west.geom.centroid.transform(4326, clone=True)
    location = Point(centroid.x, centroid.y)
    for i in range(5):
        parking = create_parking(location, operator, enforcer.enforced_domain,
                                 now - timedelta(hours=2), now + timedelta(hours=2))

    results = get(api_client, list_url)['results']
    stats_data = find_by_obj_id(event_area, results)
    assert stats_data['current_parking_count'] == 10

    # Test parkings that are in overlapping parking area, but not inside the event parking
    location = Point(GEOM_PARTIAL_OVERLAP_ON_WEST[1])
    for i in range(5):
        create_parking(location, operator, enforcer.enforced_domain,
                       now - timedelta(hours=2), now + timedelta(hours=2))

    results = get(api_client, list_url)['results']
    stats_data = find_by_obj_id(event_area, results)
    assert stats_data['current_parking_count'] == 10
    parking_area_west.refresh_from_db()
    assert parking_area_west.parkings.count() == 5


def test_disallowed_methods(api_client, event_area):
    disallowed_methods = ('post', 'put', 'patch', 'delete')
    urls = (list_url, get_detail_url(event_area))
    check_method_status_codes(api_client, urls, disallowed_methods, 405)


def test_list_endpoint_base_fields(api_client):
    stats_data = get(api_client, list_url)
    check_list_endpoint_base_fields(stats_data)


def test_get_list_check_data(api_client, event_parking_factory, event_area_factory, history_event_parking_factory):
    event_area_1, event_area_2, event_area_3 = event_area_factory.create_batch(3)

    event_parking_factory.create_batch(4, event_area=event_area_1)
    event_parking_factory.create_batch(3, event_area=event_area_2)
    history_event_parking_factory.create_batch(5, event_area=event_area_3)

    results = get(api_client, list_url)['results']
    assert len(results) == 3

    stats_data_1 = find_by_obj_id(event_area_1, results)
    stats_data_2 = find_by_obj_id(event_area_2, results)
    stats_data_3 = find_by_obj_id(event_area_3, results)

    assert stats_data_1.keys() == {'id', 'current_parking_count'}
    assert stats_data_1['current_parking_count'] == 4
    assert stats_data_2['current_parking_count'] == 0  # under 4
    assert stats_data_3['current_parking_count'] == 0  # not valid parkings currently


def test_get_detail_check_data(api_client, event_parking_factory, event_area):
    event_parking_factory.create_batch(3, event_area=event_area)
    stats_data = get(api_client, get_detail_url(event_area))
    assert stats_data.keys() == {'id', 'current_parking_count'}
    assert stats_data['current_parking_count'] == 0

    event_parking_factory(event_area=event_area)
    stats_data = get(api_client, get_detail_url(event_area))
    assert stats_data['current_parking_count'] == 4


def test_get_detail_check_data_time_end_null(api_client, event_parking_factory, event_area):
    event_parking_factory.create_batch(4, event_area=event_area, time_end=None)
    stats_data = get(api_client, get_detail_url(event_area))
    assert stats_data['current_parking_count'] == 4


def test_bounding_box_filter(api_client, event_area_factory):
    polygon_1 = Polygon([[10, 40], [20, 40], [20, 50], [10, 50], [10, 40]], srid=4326).transform(3879, clone=True)
    polygon_2 = Polygon([[30, 50], [40, 50], [40, 60], [30, 60], [30, 50]], srid=4326).transform(3879, clone=True)

    area_1 = event_area_factory(geom=MultiPolygon(polygon_1))
    area_2 = event_area_factory(geom=MultiPolygon(polygon_2))

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
