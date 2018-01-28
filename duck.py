from datetime import datetime, timedelta
import os
import random

from camel import Camel
from dateutil.parser import parse as parse_date
from django.contrib.gis.geos import LineString, Point
import PIL
import PIL.ImageDraw
import PIL.ImageFont
import polyline
from pytz import utc
import requests

from config import (
    IMAGE_SIZE, DUCK_IMAGE_DIR, BASE_SPEED, BASE_PADDING, ALIAS_FACTOR,
    GOOGLE_LOGO_PAD, ICON_PREFIX, DELAY_MINIMUM, DELAY_VARIANCE,
    DELAY_AUTOPLAY,
)
from google import streetview_url, static_map_url
from route import _length_in_km, random_route_from
from scenario import (
    Scenario, EXPERIENCE, SPEED, DISTANCE, MOTIVATION, registry,
)


def now():
    dt = datetime.utcnow()
    return dt.replace(tzinfo=utc)


class Duck:
    def __init__(self, route):
        self.route = route
        self.progress = 0
        self.speed = BASE_SPEED
        self.motivation = 10
        self.experience = 0
        self.scenario = None
        self.last_scenario = None
        self.success = None
        self.next_active = now()

    def total_distance(self):
        return _length_in_km(self.route)

    def get_travel(self):
        """
        Return a LineString of the route Duck has walked.
        """

        last_ls = None

        for i in range(1, len(self.route)):
            ls = LineString(self.route[:i+1], srid=4326)
            km = _length_in_km(ls)
            if km > self.progress and last_ls:
                return last_ls

            if ls is not None:
                last_ls = ls

    def progress_summary(self):
        total = self.total_distance()

        return (
            '{progress:.1f} / {total:.1f} km travelled\n'
            'Speed: {speed} km/h\n'
            'Motivation: {motivation}\n'
            'Experience: {experience}\n'
            .format(
                **self.__dict__,
                total=total,
                progress=min(self.progress, total),
            )
        ).strip()

    def get_position(self):
        """
        Return the last point of Duck's travelled route.
        """

        if self.success is True:
            return self.route[-1]

        travel = self.get_travel()

        if travel is None:
            return self.route[0]
        else:
            return travel[-1]

    def get_map_url(self):
        marker_fmt = dict(
            icon_prefix=ICON_PREFIX,
            finish='{},{}'.format(*self.route[-1]),
            duck='{},{}'.format(*self.get_position()),
        )
        return static_map_url(
            path='color:0x6666DDCC|weight:3|enc:{}'.format(
                polyline.encode(self.route)
            ),
            markers=[(
                'anchor:bottomleft|icon:{icon_prefix}duck_end_icon.png|'
                '{finish}'
            ).format(**marker_fmt), (
                'anchor:center|icon:{icon_prefix}duck_location_icon.png|'
                '{duck}'
            ).format(**marker_fmt)],
            size='{0}x{0}'.format(int(IMAGE_SIZE[1]/2)),
        )

    def make_image(self):
        image = PIL.Image.new(mode='RGBA', size=IMAGE_SIZE)
        streetview_image = PIL.Image.open(requests.get(
            streetview_url(*self.get_position()),
            stream=True,
        ).raw)
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
        ), resample=PIL.Image.ANTIALIAS)

        image.paste(duck_image, (
            IMAGE_SIZE[0]-duck_image.width, IMAGE_SIZE[1]-duck_image.height
        ), duck_image)

        text_image = PIL.Image.new(
            mode='RGBA',
            size=(IMAGE_SIZE[0]*ALIAS_FACTOR, IMAGE_SIZE[1]*ALIAS_FACTOR)
        )
        font = PIL.ImageFont.truetype(os.path.join(
            os.path.dirname(__file__), 'fonts', 'lato', 'Lato-Bold.ttf',
        ), int(text_image.height/70))
        text_draw = PIL.ImageDraw.Draw(text_image)

        text_draw.text((  # drop shadow
            int(BASE_PADDING + font.size/9),
            int(BASE_PADDING + font.size/9),
        ), self.progress_summary(), (0, 0, 0), font=font)
        text_draw.text((  # the text itself
            BASE_PADDING, BASE_PADDING,
        ), self.progress_summary(), (255, 255, 255), font=font)

        text_image.resize((image.width, image.height),
                          resample=PIL.Image.ANTIALIAS)

        image.paste(text_image, (0, 0), text_image)

        map_image = PIL.Image.open(requests.get(
            self.get_map_url(), stream=True,
        ).raw)
        image.paste(map_image, (
            BASE_PADDING, (image.height - GOOGLE_LOGO_PAD) - map_image.height,
        ))

        return image

    def initiate_scenario(self):
        if self.progress > self.total_distance():
            self.success = True
            yield 'I made it!'
            return

        self.last_scenario = self.scenario = Scenario.get_random(
            self, avoid=self.last_scenario,
        )
        self.delay_next_activity(DELAY_AUTOPLAY)

        yield '{}\n\n{}'.format(self.scenario.prompt, '\n'.join((
            '> {}'.format(a['answer']) for a in self.scenario.answers
        )))

    def resolve_scenario(self, outcome):
        self.scenario = None

        yield '{}\n\n{}'.format(outcome['flavour'], ' '.join([
            e['source'] for e in outcome['effects']
        ])).strip()

        self.speed = BASE_SPEED

        for effect in outcome['effects']:
            kind = effect['kind']
            multiplier = (
                1 if effect['positive'] else -1
            ) * effect['multiplier']

            if kind == MOTIVATION:
                self.motivation += multiplier
            elif kind == EXPERIENCE:
                self.experience += multiplier
            elif kind == SPEED:
                self.speed = max(1, self.speed + int(
                    multiplier * self.speed * 0.5
                ))
            elif kind == DISTANCE:
                self.progress = max(0, self.progress + (
                    self.speed * multiplier * DELAY_MINIMUM
                ))

            if self.motivation <= 0:
                self.success = False
                self.experience = min(0, self.experience - 5)
                yield "I give up. I'm going somewhere else."

        hours = DELAY_MINIMUM + (random.random() * DELAY_VARIANCE)
        self.delay_next_activity(hours)
        self.progress += (hours * self.speed)

    def delay_next_activity(self, hours):
        self.next_active = now() + timedelta(hours=hours)

    def make_successor(self):
        successor = Duck(random_route_from(
            Point(*self.get_position(), srid=4326),
            experience=self.experience,
        ))
        successor.experience = self.experience
        return successor

    def advance(self, response=None):
        if self.success is not None:
            raise RuntimeError('this game is already over')

        if self.scenario is None:
            if self.next_active < now():
                return self.initiate_scenario()
        else:
            outcome = None

            if response is not None:
                outcome = self.scenario.outcome_for(response.lower())

            elif self.next_active < now():
                answer = random.choice(self.scenario.answers)
                outcome = self.scenario.outcome_for(answer['answer'])

            if outcome is None:
                return
            else:
                return self.resolve_scenario(outcome)


@registry.dumper(Duck, 'duck', version=None)
def _dump_duck(duck):
    return {
        'route': polyline.encode(duck.route),
        'progress': duck.progress,
        'speed': duck.speed,
        'motivation': duck.motivation,
        'experience': duck.experience,
        'scenario': duck.scenario,
        'last_scenario': duck.last_scenario,
        'success': duck.success,
        'next_active': duck.next_active.isoformat(),
    }


@registry.loader('duck', version=None)
def _load_duck(data, version):
    duck = Duck(LineString(
        polyline.decode(data.pop('route')), srid=4326,
    ))

    duck.next_active = parse_date(data.pop('next_active'))

    for k, v in data.items():
        setattr(duck, k, v)

    return duck


def _sample_duck():
    return Duck(random_route_from(Point(
        53.095943, -2.469436,  # a nice spot in the middle of Valley Brook
        srid=4326,
    ), experience=0))


if __name__ == '__main__':
    from sys import argv

    camel = Camel([registry])

    try:
        with open('cli-duck.yaml', 'r') as f:
            duck = camel.load(f.read())
    except FileNotFoundError:
        duck = _sample_duck()

    if duck.success is not None:
        print('your saved journey ended, starting a new one...')
        duck = Duck.make_successor()

    response = ' '.join(argv[1:]) or None

    advancement = duck.advance(response=response)
    print(duck.progress_summary(), end='\n\n')

    if advancement is None:
        if duck.scenario is None:
            print(
                'there is nothing to be done right now, come back when the '
                'duck has made some progress; should be about {}'
                .format(duck.next_active - now())
            )
        elif response is None:
            print('please provide an instruction as an argument')
        else:
            print(
                '{!r} is not a response we are expecting right now; please '
                'try one of:\n\n{}'.format(
                    response,
                    '\n'.join([a['answer'] for a in duck.scenario.answers])
                )
            )
    else:
        for string in advancement:
            print(string)

    with open('cli-duck.yaml', 'w') as f:
        f.write(camel.dump(duck))
