import os


IMAGE_SIZE = (640, 320)
DUCK_IMAGE_DIR = os.path.realpath(os.path.join(
    os.path.dirname(__file__),
    'images',
))
BASE_SPEED = 5
BASE_PADDING = 6
ALIAS_FACTOR = 4
GOOGLE_LOGO_PAD = 26  # the height of the google logo on street view renders
