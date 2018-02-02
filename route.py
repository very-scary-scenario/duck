from copy import copy
import os
import random
import re

from django.contrib.gis.geos import Point
from django.contrib.gis.geos import LineString
import polyline

from google import directions


def _length_in_km(ls):
    transformed_ls = copy(ls)
    transformed_ls.transform(3857)
    return transformed_ls.length/1000


def _distance_between(point_a, point_b):
    assert point_a.srid == point_b.srid
    return _length_in_km(LineString([point_a, point_b], srid=point_a.srid))


def get_places():
    with open(os.path.join(os.path.dirname(__file__), 'places.txt')) as f:
        return [
            {
                **p,
                'point': Point(float(p['lat']), float(p['lon']), srid=4326),
            }
            for p in
            (
                re.match(
                    r'(?P<name>[^/]+)/(?P<lat>.*), ?(?P<lon>.*)?',
                    line.strip()
                ).groupdict()
                for line in f.readlines()
                if line.strip() and not line.strip().startswith('==')
            )
        ]


PLACES = get_places()


def random_route():
    starting_place = random.choice(PLACES)
    return random_route_from(
        starting_place['point'], experience=0,
    )


def random_point_near(point, experience=None, exclude=()):
    annotated_places = sorted(({
        **p,
        'distance': _distance_between(point, p['point'])
    } for p in PLACES), key=lambda p: p['distance'])

    options = []

    for place in annotated_places:
        if (experience is not None) and (len(options) >= (experience + 3)):
            # we don't have the confidence to attempt a journey this long
            break

        if place['distance'] < 0.2:
            # this is close enough that it's probably literally the spot we're
            # starting from
            continue

        for excluded in exclude:
            if _distance_between(excluded, place['point']) < 0.2:
                # this is an excluded point, or close enough that we should
                # not allow it
                continue

        options.append(place)

    return random.choice(options)['point']


def _googlify(point):
    # take a point and return a string we can hand to google maps as a lat/lon
    # search query
    return '{},{}'.format(point.x, point.y)


def random_route_from(point, experience=None, exclude=()):
    destination = random_point_near(point, experience=experience, exclude=())
    route, = directions(_googlify(point), _googlify(destination))['routes']
    return LineString(
        polyline.decode(route['overview_polyline']['points']),
        srid=4326,
    )


if __name__ == '__main__':
    print('made a {} km route'.format(_length_in_km(random_route())))
