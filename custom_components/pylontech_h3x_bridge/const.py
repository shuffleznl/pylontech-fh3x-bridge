"""Constants for the Pylontech H3X Bridge integration."""
from datetime import timedelta

DOMAIN = "pylontech_h3x_bridge"
MANUFACTURER = "Pylontech"
MODEL = "Force H3X"

DEFAULT_NAME = "Pylontech H3X Bridge"
DEFAULT_HOST = "172.22.184.210"
DEFAULT_PORT = 502
DEFAULT_SCAN_INTERVAL = 10

# polling interval for DataUpdateCoordinator
SCAN_INTERVAL = timedelta(seconds=DEFAULT_SCAN_INTERVAL)


CONF_HOST = "host"
CONF_PORT = "port"
