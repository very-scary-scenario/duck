from random import random
from urllib.parse import urlencode

import requests

from config import IMAGE_SIZE
from secrets import GOOGLE_API_KEY


def directions(start, finish):
    return requests.get(
        'https://maps.googleapis.com/maps/api/directions/json',
        params={
            'origin': start,
            'mode': 'walking',
            'destination': finish,
            'key': GOOGLE_API_KEY,
        }
    ).json()


def streetview_url(*coords):
    return (
        'https://maps.googleapis.com/maps/api/streetview?{}'.format(
            urlencode({
                'size': '{}x{}'.format(*IMAGE_SIZE),
                'location': '{},{}'.format(*coords),
                'fov': 90,
                'heading': int(random() * 360),
                'pitch': 10,
                'key': GOOGLE_API_KEY,
            })
        )
    )


def static_map_url(**params):
    return (
        'https://maps.googleapis.com/maps/api/staticmap?{}'.format(
            urlencode({
                **params,
                'key': GOOGLE_API_KEY,
            }, doseq=True)
        )
    )
