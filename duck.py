from copy import copy
import os
import random

from django.contrib.gis.geos import LineString
import PIL
import polyline
import requests

from config import IMAGE_SIZE, DUCK_IMAGE_DIR
from google import directions, streetview_url
from scenario import Scenario


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

    def progress_summary(self):
        return (
            '{} km travelled\n'
            '{} km still remaining'
        )

    def get_position(self):
        """
        Return the last point of Duck's travelled route.
        """

        return self.get_travel()[-1]

    def make_image(self):
        streetview = requests.get(
            streetview_url(*self.get_position()),
            stream=True,
        )
        image = PIL.Image.new(mode='RGBA', size=IMAGE_SIZE)
        streetview_image = PIL.Image.open(streetview.raw)
        image.paste(streetview_image)

        duck_image = PIL.Image.open(
            os.path.join(DUCK_IMAGE_DIR, random.choice([
                fn for fn in
                os.listdir(DUCK_IMAGE_DIR)
                if fn.endswith('.png') and not fn.startswith('.')
            ]))
        )
        target_height = int(IMAGE_SIZE[1]*0.75)
        target_width = int(
            duck_image.width * (target_height / duck_image.height)
        )
        duck_image = duck_image.resize((
            target_width, target_height,
        ), resample=PIL.Image.BICUBIC)

        image.paste(duck_image, (
            IMAGE_SIZE[0]-duck_image.width, IMAGE_SIZE[1]-duck_image.height
        ), duck_image)

        return image

    def advance(self):
        hours = random.random() * 5
        print('{:.2f} hours pass'.format(hours))
        self.progress += (hours * self.speed)
        scenario = Scenario.get_random()
        print(scenario)
        duck.make_image().save('image.png')


if __name__ == '__main__':
    route, = directions('london', 'crewe')['routes']
    duck = Duck(LineString(
        polyline.decode(route['overview_polyline']['points']),
        srid=4326,
    ))

    duck.advance()
