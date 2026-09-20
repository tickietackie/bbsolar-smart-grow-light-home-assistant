"""Constants for the BBSolar Smart Grow Light integration."""

DOMAIN = "bbsolar"

CONF_HOST = "host"
CONF_KEY = "key"
CONF_UUID = "uuid"
CONF_MODEL = "model"
CONF_SW_VERSION = "sw_version"

NS_ABILITY = "Appliance.System.Ability"
NS_ALL = "Appliance.System.All"
NS_TOGGLEX = "Appliance.Control.ToggleX"
NS_LUMINANCE = "Appliance.Control.Luminance"

METHOD_GET = "GET"
METHOD_SET = "SET"

TOGGLE_CHANNEL_ALL = 0xFFFFFFFF

LUMINANCE_CHANNELS = (3, 4, 5, 6, 7, 8, 9, 10)

STRIPS = (
    {"toggle": 1, "white": 3, "blue": 4, "red": 5},
    {"toggle": 2, "white": 7, "blue": 8, "red": 9},
)

LIGHTS = (
    {
        "key": "main",
        "name": "Main",
        "strips": STRIPS,
    },
    {
        "key": "light_a",
        "name": "Light A",
        "strips": (STRIPS[0],),
    },
    {
        "key": "light_b",
        "name": "Light B",
        "strips": (STRIPS[1],),
    },
)

MEROSS_LAN_DOMAIN = "meross_lan"
MEROSS_LAN_HOST = "host"
MEROSS_LAN_KEY = "key"
MEROSS_LAN_DEVICE_ID = "device_id"
MEROSS_LAN_PAYLOAD = "payload"
