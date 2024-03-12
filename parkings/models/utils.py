from django.contrib.gis.db.models.functions import Distance

from .parking_area import ParkingArea


def normalize_reg_num(registration_number):
    if not registration_number:
        return ''
    return registration_number.upper().replace('-', '').replace(' ', '')


def get_closest_area(location, domain, max_distance=50, area_model=ParkingArea):
    if not location:
        return None
    area_srid = area_model._meta.get_field('geom').srid
    location = location.transform(area_srid, clone=True)
    areas = area_model.objects.filter(domain=domain)
    with_distance = areas.annotate(distance=Distance('geom', location))
    within_range = with_distance.filter(distance__lte=max_distance)
    closest_area = within_range.order_by('distance').first()
    return closest_area
