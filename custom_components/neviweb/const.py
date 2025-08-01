"""Constants for neviweb component."""

import json
import pathlib

# Base component constants, some loaded directly from the manifest
_LOADER_PATH = pathlib.Path(__loader__.path)
_MANIFEST_PATH = _LOADER_PATH.parent / "manifest.json"
with pathlib.Path.open(_MANIFEST_PATH, encoding="Latin1") as json_file:
    data = json.load(json_file)
NAME = f"{data['name']}"
DOMAIN = f"{data['domain']}"
VERSION = f"{data['version']}"
ISSUE_URL = f"{data['issue_tracker']}"
REQUIRE = f"{data['homeassistant']}"
DOC_URL = f"{data['documentation']}"

STARTUP_MESSAGE = f"""
-------------------------------------------------------------------
{NAME} ({DOMAIN})
Version: {VERSION}
Requirement: Home Assistant {REQUIRE}
This is a custom integration!
If you have any issues with this you need to open an issue here: {ISSUE_URL}
Documentation: {DOC_URL}
-------------------------------------------------------------------
"""

CONF_NETWORK = "network"
CONF_NETWORK2 = "network2"

ATTR_SIGNATURE = "signature"
ATTR_POWER_MODE = "powerMode"
ATTR_INTENSITY = "intensity"
ATTR_RSSI = "rssi"
ATTR_MODE = "mode"
ATTR_WATTAGE = "wattage"
ATTR_WATTAGE_INSTANT = "wattageInstant"
ATTR_WATTAGE_OVERRIDE = "wattageOverride"
ATTR_SETPOINT_MODE = "setpointMode"
ATTR_ROOM_SETPOINT = "roomSetpoint"
ATTR_ROOM_TEMPERATURE = "roomTemperature"
ATTR_OUTPUT_PERCENT_DISPLAY = "outputPercentDisplay"
ATTR_ROOM_SETPOINT_MIN = "roomSetpointMin"
ATTR_ROOM_SETPOINT_MAX = "roomSetpointMax"
ATTR_OCCUPANCY = "occupancyMode"
ATTR_ALARM = "alarmsActive0"
ATTR_AWAY_SETPOINT = "roomSetpointAway"
ATTR_LED_OFF = "statusLedOff" # intensity,red,green,blue
ATTR_LED_ON = "statusLedOn"
ATTR_KEYPAD = "lockKeypad"
ATTR_AWAY_MODE = "awayMode" # action
ATTR_TIMER = "powerTimer"
ATTR_MIN_INTENSITY = "intensityMin"
ATTR_EARLY_START = "earlyStart"
ATTR_DISPLAY_2 = "secondaryDisplay"
ATTR_STATE = "state"
ATTR_RED = "red"
ATTR_GREEN = "green"
ATTR_BLUE = "blue"
ATTR_ALERT_LOW = "alertLowAirTemp"
ATTR_BACKLIGHT = "backlightIntensityIdle"
ATTR_TIME = "timeFormat"
ATTR_TEMP = "temperatureFormat"
ATTR_FLOOR_MODE = "airFloorMode"
ATTR_FLOOR_MAX = "floorLimitHigh"
ATTR_FLOOR_MIN = "floorLimitLow"
ATTR_FLOOR_AIR_LIMIT = "floorMaxAirTemperature"
ATTR_FLOOR_SETPOINT_MIN = "floorSetpointMin"
ATTR_FLOOR_SETPOINT_MAX = "floorSetpointMax"
ATTR_BACKLIGHT_MODE = "backlightAdaptive"
ATTR_AUX_WATTAGE_OVERRIDE = "auxWattageOverride"
ATTR_FLOOR_SETPOINT = "floorSetpoint"
ATTR_FLOOR_TEMP = "floorTemperature"
ATTR_FLOOR_SENSOR_TYPE = "floorSensorType"
ATTR_CYCLE_LENGTH = "cycleLength"
ATTR_AUX_CONFIG = "auxOutputConfig"
ATTR_AUX_CYCLE_LENGTH = "auxOutputCycleLength"
ATTR_AUX_OUTPUT_STAGE = "auxOutputStage"
ATTR_PUMP_PROTEC = "pumpProtection"
ATTR_ALARM_1 = "alarmsActive1"
ATTR_SHED_STATUS = "shedStatus"
ATTR_STATUS = "status"
ATTR_SHED_PLANNING = "shedDayPlanningStatus"
ATTR_LOCAL_SYNC = "localSync"
ATTR_VALUE = "value"

MODE_AUTO = "auto"
MODE_AUTO_BYPASS = "autoBypass"
MODE_MANUAL = "manual"
MODE_AWAY = "away"
MODE_OFF = "off"
MODE_HOME = "home"
MODE_FROST_PROTEC = "frostProtection"
MODE_EM_HEAT = "emergencyHeat"

SERVICE_SET_LED_INDICATOR = "set_led_indicator"
SERVICE_SET_CLIMATE_KEYPAD_LOCK = "set_climate_keypad_lock"
SERVICE_SET_LIGHT_KEYPAD_LOCK = "set_light_keypad_lock"
SERVICE_SET_SWITCH_KEYPAD_LOCK = "set_switch_keypad_lock"
SERVICE_SET_LIGHT_TIMER = "set_light_timer"
SERVICE_SET_SWITCH_TIMER = "set_switch_timer"
SERVICE_SET_SECOND_DISPLAY = "set_second_display"
SERVICE_SET_BACKLIGHT = "set_backlight"
SERVICE_SET_EARLY_START = "set_early_start"
SERVICE_SET_TIME_FORMAT = "set_time_format"
SERVICE_SET_TEMPERATURE_FORMAT = "set_temperature_format"
SERVICE_SET_WATTAGE = "set_wattage"
SERVICE_SET_SETPOINT_MAX = "set_setpoint_max"
SERVICE_SET_SETPOINT_MIN = "set_setpoint_min"
SERVICE_SET_LIGHT_AWAY_MODE = "set_light_away_mode"
SERVICE_SET_SWITCH_AWAY_MODE = "set_switch_away_mode"
SERVICE_SET_AIR_FLOOR_MODE = "set_air_floor_mode"
SERVICE_SET_AUX_CYCLE_LENGTH = "set_aux_cycle_length"
SERVICE_SET_CYCLE_LENGTH = "set_cycle_length"
SERVICE_SET_ECO_STATUS = "set_eco_status"
SERVICE_SET_SWITCH_ECO_STATUS = "set_switch_eco_status"
SERVICE_SET_EM_HEAT = "set_em_heat"
SERVICE_SET_NEVIWEB_STATUS = "set_neviweb_status"
