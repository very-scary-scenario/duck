from copy import copy
import os
import random

from django.contrib.gis.geos import LineString
import PIL
import polyline
import requests

from config import IMAGE_SIZE, DUCK_IMAGE_DIR
from google import streetview_url
from scenario import Scenario, EXPERIENCE, SPEED, DISTANCE, MOTIVATION


def _length_in_km(ls):
    transformed_ls = copy(ls)
    transformed_ls.transform(3857)
    return transformed_ls.length/1000


class Duck:
    def __init__(self, route):
        self.route = route
        self.progress = 0
        self.speed = 4
        self.motivation = 10
        self.experience = 0

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
            '{progress:.1f} km travelled\n'
            '{remaining:.1f} km still remaining'
            .format(
                progress=self.progress,
                remaining=self.total_distance() - self.progress,
            )
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
        print('\n{:.2f} hours pass'.format(hours))
        self.progress += (hours * self.speed)
        if self.progress > self.total_distance():
            print('I made it!')
            return

        print(self.progress_summary())
        print()
        scenario = Scenario.get_random(self)
        # duck.make_image().save('image.png')

        print('{}\n\n{}'.format(
            scenario.prompt,
            '\n'.join(('> {}'.format(a['answer']) for a in scenario.answers)),
        ))

        while True:
            outcome = scenario.outcome_for(input('\nreply: ').lower())
            if outcome:
                break

        print('\n{}\n\n{}'.format(outcome['flavour'], ' '.join([
            e['source'] for e in outcome['effects']
        ])).strip())

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
                self.progress = max(
                    0, self.progress + (self.speed * multiplier),
                )

            if self.motivation <= 0:
                print("I give up, I'm going home.")
                return

        self.advance()


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
    duck = _sample_duck()
    duck.advance()
