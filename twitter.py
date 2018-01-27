from camel import Camel
import os

import tweepy

from duck import now, registry, _sample_duck
from secrets import TWITTER

DUCK_DIR = os.path.join(
    os.path.dirname(__file__),
    'duck-storage',
)
if not os.path.exists(DUCK_DIR):
    os.mkdir(DUCK_DIR)

DUCK_IMAGE_LOCATION = os.path.join(
    os.path.dirname(__file__),
    'duck.png',
)

camel = Camel([registry])

auth = tweepy.OAuthHandler(TWITTER['consumer_key'], TWITTER['consumer_secret'])
auth.set_access_token(TWITTER['access_token'], TWITTER['access_token_secret'])
twitter = tweepy.API(auth)


def get_duck():
    duck_filenames = [
        fn for fn in os.listdir(DUCK_DIR)
        if fn.endswith('.yaml') and not fn.startswith('.')
    ]

    if duck_filenames:
        latest_duck_filename = sorted(duck_filenames)[-1]

        with open(os.path.join(DUCK_DIR, latest_duck_filename)) as f:
            latest_duck = camel.load(f.read())

        if latest_duck.success is None:
            return (latest_duck, latest_duck_filename)
        else:
            return (_sample_duck(), None)
    else:
        return (_sample_duck(), None)


if __name__ == '__main__':
    duck, filename = get_duck()

    tweets = [
        tw for tw in
        twitter.user_timeline(twitter.me())
        if tw.in_reply_to_status_id is None
        and not tw.retweeted
    ]

    if tweets:
        latest_tweet = tweets[0]
    else:
        latest_tweet is None

    advancement = duck.advance()

    if advancement is not None:
        for string in advancement:
            if duck.scenario is None and duck.success is None:
                twitter.update_status(
                    string,
                    in_reply_to_status_id=latest_tweet.id
                    if latest_tweet else None
                )
            else:
                image = duck.make_image()
                image.save(DUCK_IMAGE_LOCATION)
                twitter.update_with_media(DUCK_IMAGE_LOCATION, string)

    if filename is None:
        filename = '{}.yaml'.format(now().isoformat())

    with open(os.path.join(DUCK_DIR, filename), 'w') as f:
        f.write(camel.dump(duck))
