import os


IMAGE_SIZE = (640, 320)
DUCK_IMAGE_DIR = os.path.realpath(os.path.join(
    os.path.dirname(__file__),
    'images',
))

# in km/h:
BASE_SPEED = 120  # should probably be 5 or something; needs balancing

# image creation stuff:
BASE_PADDING = 6
ALIAS_FACTOR = 4
GOOGLE_LOGO_PAD = 26  # the height of the google logo on street view renders
ICON_PREFIX = (
    'https://raw.githubusercontent.com/very-scary-scenario/duck/master'
    '/icons/'
)

# all of these DELAYs are in hours:
# the smallest possible delay between scenarios
DELAY_MINIMUM = 1/30

# the difference between the smallest and largest delays between scenarios
DELAY_VARIANCE = 1/60

# how long to give people to vote, should be ten minutes or so
DELAY_AUTOPLAY = 1/30
