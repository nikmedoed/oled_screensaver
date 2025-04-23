import logging
import sys

CURSOR_CHECK_TIMEOUT = 5000  # ms
MIN_TOGGLE_INTERVAL = 0.3  # s
DEV_MODE = 'dev' in sys.argv
TIMEOUT = 5 if DEV_MODE else 120
SECONDS_IN_MINUTE = 1 if DEV_MODE else 60
durations_in_minutes = [15, 30, 60, 120, 180, 240, 480, 720]

logging.basicConfig(
    level=logging.DEBUG if DEV_MODE else logging.INFO,
    format='[%(levelname)s] %(asctime)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logging.getLogger("PIL").setLevel(logging.WARNING)


