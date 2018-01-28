# Duck

A game about a duck that goes on an adventure. Play on Twitter by interacting
with [@duck_trails][tw]. You can only contribute when the most recent tweet
ends with a list of options.

[tw]: https://twitter.com/duck_trails

Made by members of [Very Scary Scenario][vss] for [Global Game Jam 2018][ggj18]

[vss]: https://vscary.co
[ggj18]: https://globalgamejam.org/2018/games/duck

## I want to play locally

It's more sporting to play with others on the canonical verion, but you can if
you like. If you're running macOS or Linux and are comfortable with developing
Python locally, though, here is how to play on the command line:

- Clone and `cd` to this repository
- Make a Python 3.5 or 3.6 virtualenv
- `pip install -r requirements.txt`
- make a file called `secrets.py` containing `GOOGLE_API_KEY = '[your api
  key]'`, where `[your api key]` is a Google API key with access to the Google
  Static Maps API, the Google Stret View Image API, and the Google Maps
  Directions API.
- run `python duck.py`

Sometimes, when you run `python duck.py`, the game will advance on its own.
Sometimes, though, the duck will ask a question. You can respond by providing
your answer as an argument on your next call: `python duck.py quack`.

If you want to run the Twitter version, you'll need to extend your
`secrets.py` with [Twitter API keys][twapps]. Mine looks like this:

[twapps]: https://apps.twitter.com

```python
GOOGLE_API_KEY = '[redacted]'
TWITTER = {
    'consumer_key': '[redacted]',
    'consumer_secret': '[redacted]',
    'access_token': '[redacted]',
    'access_token_secret': '[redacted]',
}
```

Once you've got that all set up, set up `python twitter.py` to run every minute
or so, and you're good.

## License

Duck is released under a Creative Commons [Attribution-NonCommercial][by-nc]
license.

[by-nc]: https://creativecommons.org/licenses/by-nc/4.0/
