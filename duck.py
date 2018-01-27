from copy import copy

from django.contrib.gis.geos import LineString
import polyline

from google import directions, streetview_url


class Duck:
    def __init__(self, route):
        self.route = route
        self.progress = 0
        self.speed = 5

    def get_travel(self):
        """
        Return a LineString of the route Duck has walked.
        """

        last_ls = None

        for i in range(1, len(self.route)):
            ls = LineString(self.route[:i+1], srid=4326)
            transformed_ls = copy(ls)
            transformed_ls.transform(3857)
            km = transformed_ls.length/1000
            if km > self.progress and last_ls:
                return last_ls

            last_ls = ls

    def get_position(self):
        """
        Return the last point of Duck's travelled route.
        """

        return self.get_travel()[-1]

    def get_current_view_url(self):
        return streetview_url(*self.get_position())

    def step(self, hours):
        self.progress += (hours * self.speed)


if __name__ == '__main__':
    route, = directions('london', 'crewe')['routes']
    duck = Duck(LineString(
        polyline.decode(route['overview_polyline']['points']),
        srid=4326,
    ))

    print(duck.get_position())
    for i in range(50):
        duck.step(5)
        print(duck.get_current_view_url())
