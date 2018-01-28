from collections import Counter
import os

from camel import Camel
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
            # start from where we finished
            return (latest_duck.make_successor(), None)
    else:
        return (_sample_duck(), None)  # start from scratch


def get_latest_duck_tweet():
    tweets = [
        tw for tw in
        twitter.user_timeline(screen_name=auth.username)
        if tw.in_reply_to_status_id is None
        and not tw.retweeted
    ]

    if tweets:
        return tweets[0]


if __name__ == '__main__':
    duck, filename = get_duck()

    latest_tweet = None

    # respecting next_active here makes sense even if similar logic is already
    # in Duck, since on the CLI there's no reason to force the player to wait,
    # but on twitter we really want people to get an opportunity to vote
    if duck.scenario and (now() > duck.next_active):
        latest_tweet = get_latest_duck_tweet()

    if latest_tweet:
        replies = [
            s for s in twitter.mentions_timeline(
                since_id=latest_tweet.id,
                tweet_mode='extended',
            ) if s.in_reply_to_status_id == latest_tweet.id
        ] if duck.scenario and latest_tweet else []

        votes = {}

        for reply in replies:
            if reply.user.id in votes:
                continue

            answer = duck.scenario.answer_for(reply.full_text)
            if answer is None:
                continue
            votes[reply.user.id] = answer['answer']

        if votes:
            counter = Counter(votes.values())
            most_common, = counter.most_common(1)
            response, _ = most_common
        else:
            response = None
    else:
        response = None

    advancement = duck.advance(response)

    if advancement is not None:
        for string in advancement:
            if (
                duck.scenario is None and
                duck.success is None and
                duck.progress > 0
            ):
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
