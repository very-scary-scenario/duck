from copy import copy
from datetime import datetime, timedelta
import os
import random

from camel import Camel
from dateutil.parser import parse as parse_date
from django.contrib.gis.geos import LineString
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
from scenario import (
    Scenario, EXPERIENCE, SPEED, DISTANCE, MOTIVATION, registry,
)


def _length_in_km(ls):
    transformed_ls = copy(ls)
    transformed_ls.transform(3857)
    return transformed_ls.length/1000


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

            last_ls = ls

    def progress_summary(self):
        return (
            '{progress:.1f} / {total:.1f} km travelled\n'
            'Speed: {speed}\n'
            'Motivation: {motivation}\n'
            'Experience: {experience}\n'
            .format(
                total=self.total_distance(),
                **self.__dict__
            )
        ).strip()

    def get_position(self):
        """
        Return the last point of Duck's travelled route.
        """

        return self.get_travel()[-1]

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
                'anchor:center|icon:{icon_prefix}duck_end_icon.png|'
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
            print('I made it!')
            self.success = True
            return

        self.scenario = Scenario.get_random(self)
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
                self.speed = max(1, self.speed + multiplier)
            elif kind == DISTANCE:
                self.progress = max(0, self.progress + (
                    self.speed * multiplier * DELAY_MINIMUM
                ))

            if self.motivation <= 0:
                self.success = False
                yield "I give up, I'm going home."

        hours = DELAY_MINIMUM + (random.random() * DELAY_VARIANCE)
        self.delay_next_activity(hours)
        self.progress += (hours * self.speed)

    def delay_next_activity(self, hours):
        self.next_active = now() + timedelta(hours=hours)

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
                outcome = self.resolve_scenario(answer['answer'])

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
    return Duck(LineString(
        polyline.decode(
            'u_kyH`_XoPx`@`@rTmXd[gFdHnChb@|Dv|@iShj@abA|{AawCpuDquBhkCk|F~kH_UqBuf@~d@eu@`dA{h@tg@uL^qb@a]q]gEys@zb@gmAji@edA|d@]TsChA{\tNuiBpy@{z@f`@s]rIwp@j`@aj@zUks@v\C|@ge@zcAmEvHeJyLqh@ug@}N`f@gi@|y@eUh`@qv@bf@sfApt@ul@hb@ouAxaA}`@j[kMp_@aGnUsLng@oc@n|B{|@dgB_lAn_B_tA|v@wr@|xAsxAtfC_bCvzDcfEdoHihD`kH{o@|xAca@hc@{WfTsK`c@e[trBwQtZw\be@_[nKw`@xKaSp[wGvhA`GfuAoUprAiy@dr@eoBrgDc]z`BaR~pBiWvfAad@jl@cRtl@oQ`zAkBp[}Mrh@qnBjgEexAj|Cm~BdqF_~ApkCkoHf}EygBvoAmcA`gAafApx@y{@drAib@~a@uXaAam@l_@gvAbbA{o@~Qe}@z`As~Ex_Du`@nYyHnYke@rrBqKtp@gK~Dil@dCc}@yOe[_God@jYc_DzhCahBjzAo~BvoBi}Bv|Bs~EldGya@rk@q_@bm@ce@`{Ame@deBwn@j_CkJfc@wVru@kr@xjC{rB`{HexArqGmz@fhEmYzt@qh@|vA@jqAi\hjBej@dlC}p@riD_YfpBdBtLil@rvAso@~`AqTlaAwMllCnLhvC_C||Am\lcAoIj}@e]`yBcg@taCkVlGcHlPie@pTi^_Bie@bk@mw@`b@g}@fj@yg@lbA_Qnj@}e@hf@_x@fiAwcAvj@cTzHaOp`@eLj]}MtEaOz^gSfwANlYyRlIiWpX}CpTw[na@u\re@gb@~_@kEzJaKvTwQjNq]SsKuDkWzr@kWzx@_Mx_Ayg@~z@o~@fr@m{@rmAul@fD{OdGqFrWgYdXwS~j@}e@fr@e^hf@aUh@_r@fkAy\r_CgRvo@gh@df@}WjSeKx`@abAdbCmVfq@{r@~}@mh@t_As\daAuiAfwAkDdPmPeIkK`X{~@`X{f@Cq`@|Iod@pLcPlCeW~Sic@nZe[rM_f@xa@oYnh@}VzIgOnDwThPqp@p]i~@t{@i_@fm@cIhc@a`@`qAmRnTw@|@o@h@sHtk@Bxg@kf@|a@_HdkAgQnjAac@ra@mIje@tAxa@aMh_AuTph@sV`WyWcNcJw@eJlw@uo@dVmMlRiPtVBv`@qHr[{J~OoNtIyFl`@c`@zd@gYhq@z@zc@gUv@sN`x@}LfKkCfd@sH`}@cIjv@mDjp@uCjt@}K~^'  # noqa
        ),
        srid=4326,
    ))

    # route, = directions('london', 'crewe')['routes']
    # polyline = polyline.decode(route['overview_polyline']['points'])


if __name__ == '__main__':
    from sys import argv

    camel = Camel([registry])

    try:
        with open('cli-duck.yaml', 'r') as f:
            duck = camel.load(f.read())
    except FileNotFoundError:
        duck = _sample_duck()

    if duck.success is not None:
        print('your saved duck is no longer journeying; starting a new one...')
        duck = _sample_duck()

    response = ' '.join(argv[1:]) or None
    advancement = duck.advance(response=response)

    if advancement is None:
        if duck.scenario is None:
            print(
                'there is nothing to be done right now, come back when the '
                'duck has made some progress; should be about {}'
                .format(duck.next_active - now())
            )
        if response is None:
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
