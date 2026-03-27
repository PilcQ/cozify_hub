"""Constants for Cozify HUB integration."""

DOMAIN = "cozify_hub"

CONF_HUB_HOST = "hub_host"
CONF_HUB_PORT = "hub_port"
CONF_CLOUD_TOKEN = "cloud_token"
CONF_HUB_ID = "hub_id"

DEFAULT_PORT = 8893
DEFAULT_SCAN_INTERVAL = 30

# Device capability flags
CAP_ON_OFF = "ON_OFF"
CAP_BRIGHTNESS = "BRIGHTNESS"
CAP_COLOR_HS = "COLOR_HS"
CAP_COLOR_TEMP = "COLOR_TEMPERATURE"
CAP_TEMPERATURE = "TEMPERATURE"
CAP_HUMIDITY = "HUMIDITY"
CAP_MOTION = "MOTION"
CAP_CONTACT = "CONTACT"
CAP_LOCK = "LOCK"
CAP_COVER = "COVER"

PLATFORMS = ["light", "sensor", "binary_sensor", "lock", "cover"]
