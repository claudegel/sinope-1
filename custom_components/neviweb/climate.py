"""
Support for Neviweb thermostat.
type 10 = thermostat TH1120RF 3000W and 4000W, model 1120, 1122
type 10 = thermostat TH1121RF 3000W and 4000W, (Public place) model 1121, 1123
type 20 = thermostat TH1300RF 3600W floor, 
type 20 = thermostat TH1500RF double pole thermostat,
type 21 = thermostat TH1400RF low voltage,
type 10 = thermostat OTH2750-GT Ouellet,
type 20 = thermostat OTH3600-GA-GT Ouellet floor,
type 10 = thermostat OTH4000-GT Ouellet,
type 20 = thermostat INSTINCT Connect, Flextherm,
For more details about this platform, please refer to the documentation at  
https://www.sinopetech.com/en/support/#api
"""
import logging

import voluptuous as vol
import time

import custom_components.neviweb as neviweb
from . import (SCAN_INTERVAL)
from homeassistant.components.climate import ClimateEntity
from homeassistant.components.climate.const import (
    HVAC_MODE_HEAT,
    HVAC_MODE_OFF,
    HVAC_MODE_AUTO,
    SUPPORT_TARGET_TEMPERATURE,
    SUPPORT_PRESET_MODE,
    PRESET_AWAY,
    PRESET_NONE,
    CURRENT_HVAC_HEAT,
    CURRENT_HVAC_IDLE,
    CURRENT_HVAC_OFF,
)

from homeassistant.const import (
    ATTR_ENTITY_ID,
    DEVICE_CLASS_TEMPERATURE,
    TEMP_CELSIUS,
    TEMP_FAHRENHEIT,
    ATTR_TEMPERATURE,
)

from homeassistant.helpers import (
    config_validation as cv,
    discovery,
    service,
    entity_platform,
    entity_component,
    entity_registry,
    device_registry,
)

from homeassistant.helpers.typing import HomeAssistantType

from datetime import timedelta
from homeassistant.helpers.event import track_time_interval
from .const import (
    DOMAIN,
    ATTR_RSSI,
    ATTR_SETPOINT_MODE,
    ATTR_ROOM_SETPOINT,
    ATTR_OUTPUT_PERCENT_DISPLAY,
    ATTR_ROOM_TEMPERATURE,
    ATTR_ROOM_SETPOINT_MIN,
    ATTR_ROOM_SETPOINT_MAX,
    ATTR_WATTAGE,
    ATTR_ALARM,
    ATTR_AWAY_SETPOINT,
    ATTR_EARLY_START,
    ATTR_KEYPAD,
    ATTR_DISPLAY_2,
    ATTR_BACKLIGHT,
    ATTR_TIME,
    ATTR_TEMP,
    MODE_AUTO,
    MODE_AUTO_BYPASS,
    MODE_MANUAL,
    MODE_OFF,
    MODE_AWAY,
    SERVICE_SET_SECOND_DISPLAY,
    SERVICE_SET_BACKLIGHT,
    SERVICE_SET_KEYPAD_LOCK,
    SERVICE_SET_EARLY_START,
    SERVICE_SET_TIME_FORMAT,
    SERVICE_SET_TEMPERATURE_FORMAT,
    SERVICE_SET_SETPOINT_MAX,
    SERVICE_SET_SETPOINT_MIN,
)

_LOGGER = logging.getLogger(__name__)

SUPPORT_FLAGS = (SUPPORT_TARGET_TEMPERATURE | SUPPORT_PRESET_MODE)

DEFAULT_NAME = "neviweb climate"

UPDATE_ATTRIBUTES = [
    ATTR_SETPOINT_MODE,
    ATTR_RSSI,
    ATTR_ROOM_SETPOINT,
    ATTR_OUTPUT_PERCENT_DISPLAY,
    ATTR_ROOM_TEMPERATURE,
    ATTR_ROOM_SETPOINT_MIN,
    ATTR_ROOM_SETPOINT_MAX,
    ATTR_ALARM,
    ATTR_AWAY_SETPOINT,
    ATTR_EARLY_START,
    ATTR_KEYPAD,
    ATTR_DISPLAY_2,
    ATTR_BACKLIGHT,
    ATTR_TIME,
    ATTR_TEMP,
]

SUPPORTED_HVAC_MODES = [
    HVAC_MODE_OFF,
    HVAC_MODE_AUTO,
    HVAC_MODE_HEAT,
]

PRESET_BYPASS = 'temporary'
PRESET_MODES = [
    PRESET_NONE,
    PRESET_AWAY,
    PRESET_BYPASS,
]

IMPLEMENTED_LOW_VOLTAGE = [21]
IMPLEMENTED_THERMOSTAT = [10, 20]
IMPLEMENTED_DEVICE_TYPES = IMPLEMENTED_THERMOSTAT + IMPLEMENTED_LOW_VOLTAGE

SET_SECOND_DISPLAY_SCHEMA = vol.Schema(
    {
         vol.Required(ATTR_ENTITY_ID): cv.entity_id,
         vol.Required(ATTR_DISPLAY_2): cv.string,
    }
)

SET_BACKLIGHT_SCHEMA = vol.Schema(
    {
         vol.Required(ATTR_ENTITY_ID): cv.entity_id,
         vol.Required(ATTR_BACKLIGHT): vol.All(
             vol.Coerce(int), vol.Range(min=0, max=100)
         ),
    }
)

SET_KEYPAD_LOCK_SCHEMA = vol.Schema(
    {
         vol.Required(ATTR_ENTITY_ID): cv.entity_id,
         vol.Required(ATTR_KEYPAD): cv.string,
    }
)

SET_TIME_FORMAT_SCHEMA = vol.Schema(
    {
         vol.Required(ATTR_ENTITY_ID): cv.entity_id,
         vol.Required(ATTR_TIME): vol.All(
             vol.Coerce(int), vol.Range(min=12, max=24)
         ),
    }
)

SET_TEMPERATURE_FORMAT_SCHEMA = vol.Schema(
    {
         vol.Required(ATTR_ENTITY_ID): cv.entity_id,
         vol.Required(ATTR_TEMP): cv.string,
    }
)

SET_EARLY_START_SCHEMA = vol.Schema(
    {
         vol.Required(ATTR_ENTITY_ID): cv.entity_id,
         vol.Required(ATTR_EARLY_START): cv.string,
    }
)

SET_SETPOINT_MAX_SCHEMA = vol.Schema(
    {
         vol.Required(ATTR_ENTITY_ID): cv.entity_id,
         vol.Required(ATTR_ROOM_SETPOINT_MAX): vol.All(
             vol.Coerce(float), vol.Range(min=10, max=30)
         ),
    }
)

SET_SETPOINT_MIN_SCHEMA = vol.Schema(
    {
         vol.Required(ATTR_ENTITY_ID): cv.entity_id,
         vol.Required(ATTR_ROOM_SETPOINT_MIN): vol.All(
             vol.Coerce(float), vol.Range(min=5, max=24)
         ),
    }
)

async def async_setup_platform(
    hass,
    config,
    async_add_entities,
    discovery_info=None,
):
    """Set up the neviweb thermostats."""
    data = hass.data[DOMAIN]
    
    entities = []
    for device_info in data.neviweb_client.gateway_data:
        if "signature" in device_info and \
            "type" in device_info["signature"] and \
            device_info["signature"]["type"] in IMPLEMENTED_DEVICE_TYPES:
            device_name = "{} {}".format(DEFAULT_NAME, device_info["name"])
            entities.append(NeviwebThermostat(data, device_info, device_name))
    for device_info in data.neviweb_client.gateway_data2:
        if "signature" in device_info and \
            "type" in device_info["signature"] and \
            device_info["signature"]["type"] in IMPLEMENTED_DEVICE_TYPES:
            device_name = "{} {}".format(DEFAULT_NAME, device_info["name"])
            entities.append(NeviwebThermostat(data, device_info, device_name))
            
    async_add_entities(entities, True)

    def set_second_display_service(service):
        """Set to outside or setpoint temperature display"""
        entity_id = service.data[ATTR_ENTITY_ID]
        value = {}
        for thermostat in entities:
            if thermostat.entity_id == entity_id:
                value = {"id": thermostat.unique_id, "display": service.data[ATTR_DISPLAY_2]}
                thermostat.set_second_display(value)
                thermostat.schedule_update_ha_state(True)
                break

    def set_backlight_service(service):
        """Set backlight action off on idle or always on"""
        entity_id = service.data[ATTR_ENTITY_ID]
        value = {}
        for thermostat in entities:
            if thermostat.entity_id == entity_id:
                value = {"id": thermostat.unique_id, "level": service.data[ATTR_BACKLIGHT]}
                thermostat.set_backlight(value)
                thermostat.schedule_update_ha_state(True)
                break

    def set_keypad_lock_service(service):
        """ lock/unlock keypad device"""
        entity_id = service.data[ATTR_ENTITY_ID]
        value = {}
        for thermostat in entities:
            if thermostat.entity_id == entity_id:
                value = {"id": thermostat.unique_id, "lock": service.data[ATTR_KEYPAD]}
                thermostat.set_keypad_lock(value)
                thermostat.schedule_update_ha_state(True)
                break

    def set_early_start_service(service):
        """ Set early start heating of device """
        entity_id = service.data[ATTR_ENTITY_ID]
        value = {}
        for thermostat in entities:
            if thermostat.entity_id == entity_id:
                value = {"id": thermostat.unique_id, "start": service.data[ATTR_EARLY_START]}
                thermostat.set_early_start(value)
                thermostat.schedule_update_ha_state(True)
                break

    def set_time_format_service(service):
        """ Set time format 12h or 24h """
        entity_id = service.data[ATTR_ENTITY_ID]
        value = {}
        for thermostat in entities:
            if thermostat.entity_id == entity_id:
                value = {"id": thermostat.unique_id, "time": service.data[ATTR_TIME]}
                thermostat.set_time_format(value)
                thermostat.schedule_update_ha_state(True)
                break

    def set_temperature_format_service(service):
        """ Set temperature format, celsius or fahrenheit of device"""
        entity_id = service.data[ATTR_ENTITY_ID]
        value = {}
        for thermostat in entities:
            if thermostat.entity_id == entity_id:
                value = {"id": thermostat.unique_id, "temp": service.data[ATTR_TEMP]}
                thermostat.set_temperature_format(value)
                thermostat.schedule_update_ha_state(True)
                break

    def set_setpoint_max_service(service):
        """ set maximum setpoint for device"""
        entity_id = service.data[ATTR_ENTITY_ID]
        value = {}
        for thermostat in entities:
            if thermostat.entity_id == entity_id:
                value = {"id": thermostat.unique_id, "temp": service.data[ATTR_ROOM_SETPOINT_MAX]}
                thermostat.set_setpoint_max(value)
                thermostat.schedule_update_ha_state(True)
                break

    def set_setpoint_min_service(service):
        """ set minimum setpoint for device"""
        entity_id = service.data[ATTR_ENTITY_ID]
        value = {}
        for thermostat in entities:
            if thermostat.entity_id == entity_id:
                value = {"id": thermostat.unique_id, "temp": service.data[ATTR_ROOM_SETPOINT_MIN]}
                thermostat.set_setpoint_min(value)
                thermostat.schedule_update_ha_state(True)
                break

    hass.services.async_register(
        DOMAIN,
        SERVICE_SET_SECOND_DISPLAY,
        set_second_display_service,
        schema=SET_SECOND_DISPLAY_SCHEMA,
    )

    hass.services.async_register(
        DOMAIN,
        SERVICE_SET_BACKLIGHT,
        set_backlight_service,
        schema=SET_BACKLIGHT_SCHEMA,
    )

    hass.services.async_register(
        DOMAIN,
        SERVICE_SET_KEYPAD_LOCK,
        set_keypad_lock_service,
        schema=SET_KEYPAD_LOCK_SCHEMA,
    )

    hass.services.async_register(
        DOMAIN,
        SERVICE_SET_EARLY_START,
        set_early_start_service,
        schema=SET_EARLY_START_SCHEMA,
    )

    hass.services.async_register(
        DOMAIN,
        SERVICE_SET_TIME_FORMAT,
        set_time_format_service,
        schema=SET_TIME_FORMAT_SCHEMA,
    )

    hass.services.async_register(
        DOMAIN,
        SERVICE_SET_TEMPERATURE_FORMAT,
        set_temperature_format_service,
        schema=SET_TEMPERATURE_FORMAT_SCHEMA,
    )

    hass.services.async_register(
        DOMAIN,
        SERVICE_SET_SETPOINT_MAX,
        set_setpoint_max_service,
        schema=SET_SETPOINT_MAX_SCHEMA,
    )

    hass.services.async_register(
        DOMAIN,
        SERVICE_SET_SETPOINT_MIN,
        set_setpoint_min_service,
        schema=SET_SETPOINT_MIN_SCHEMA,
    )

class NeviwebThermostat(ClimateEntity):
    """Implementation of a Neviweb thermostat."""

    def __init__(self, data, device_info, name):
        """Initialize."""
        self._name = name
        self._client = data.neviweb_client
        self._id = device_info["id"]
        self._wattage = 0
        self._min_temp = 0
        self._max_temp = 0
        self._target_temp = None
        self._cur_temp = None
        self._cur_temp_before = None
        self._rssi = None
        self._alarm = None
        self._early_start = None
        self._operation_mode = None
        self._heat_level = 0
        self._away_temp = None
        self._keypad = "unlocked"
        self._display_2 = None
        self._backlight = None
        self._time_format = "24h"
        self._temperature_format = TEMP_CELSIUS
        self._is_low_voltage = device_info["signature"]["type"] in \
            IMPLEMENTED_LOW_VOLTAGE
        _LOGGER.debug("Setting up %s: %s", self._name, device_info)

    def update(self):
        """Get the latest data from Neviweb and update the state."""
        if not self._is_low_voltage:
            WATT_ATTRIBUTE = [ATTR_WATTAGE]
        else:
            WATT_ATTRIBUTE = []
        start = time.time()
        device_data = self._client.get_device_attributes(self._id,
            UPDATE_ATTRIBUTES + WATT_ATTRIBUTE)
        end = time.time()
        elapsed = round(end - start, 3)
        _LOGGER.debug("Updating %s (%s sec): %s",
            self._name, elapsed, device_data)

        if "error" not in device_data:
            if "errorCode" not in device_data:
                self._cur_temp_before = self._cur_temp
                self._cur_temp = float(device_data[ATTR_ROOM_TEMPERATURE]["value"]) if \
                    device_data[ATTR_ROOM_TEMPERATURE]["value"] != None else self._cur_temp_before
                self._target_temp = float(device_data[ATTR_ROOM_SETPOINT]) if \
                    device_data[ATTR_SETPOINT_MODE] != MODE_OFF else 0.0
                if ATTR_AWAY_SETPOINT in device_data:
                    self._away_temp = float(device_data[ATTR_AWAY_SETPOINT])
                else:
                    _LOGGER.debug("Attribute roomSetpointAway is missing: %s", device_data)
                self._heat_level = device_data[ATTR_OUTPUT_PERCENT_DISPLAY]
                self._alarm = device_data[ATTR_ALARM]["type"]
                self._rssi = device_data[ATTR_RSSI]
                self._operation_mode = device_data[ATTR_SETPOINT_MODE]
                self._min_temp = float(device_data[ATTR_ROOM_SETPOINT_MIN])
                self._max_temp = float(device_data[ATTR_ROOM_SETPOINT_MAX])
                self._early_start = device_data[ATTR_EARLY_START]
                self._keypad = device_data[ATTR_KEYPAD]
                self._display_2 = device_data[ATTR_DISPLAY_2]
                self._temperature_format = device_data[ATTR_TEMP]
                self._time_format = device_data[ATTR_TIME]
                if ATTR_BACKLIGHT in device_data:
                    self._backlight = device_data[ATTR_BACKLIGHT]
                else:
                    _LOGGER.debug("Attribute backlightIntensityIdle is missing: %s", device_data)
                if not self._is_low_voltage:
                    self._wattage = device_data[ATTR_WATTAGE]["value"]
                return
            else:
                if device_data["errorCode"] == "ReadTimeout":
                    _LOGGER.warning("Error in reading device %s: (%s), too slow to respond or busy.", self._name, device_data)
                else:
                    _LOGGER.warning("Unknown errorCode, device: %s, error: %s", self._name, device_data)
            return
        else:
            if device_data["error"]["code"] == "DVCCOMMTO":  
                _LOGGER.warning("Cannot update %s: %s. Device is busy or does not respond quickly enough.", self._name, device_data)
            elif device_data["error"]["code"] == "SVCINVREQ":
                _LOGGER.warning("Invalid or malformed request to Neviweb, %s:",  device_data)
            elif device_data["error"]["code"] == "DVCUNVLB":
                _LOGGER.warning("Device %s unavailable, Neviweb maintnance update, %s:", self._name, device_data)
            elif device_data["error"]["code"] == "SVCERR":
                _LOGGER.warning("Device %s statistics unavailables, %s:", self._name, device_data)
            else:
                _LOGGER.warning("Unknown error, device: %s, error: %s", self._name, device_data)

    @property
    def unique_id(self):
        """Return unique ID based on Neviweb device ID."""
        return self._id

    @property
    def name(self):
        """Return the name of the thermostat."""
        return self._name

    @property
    def unit_of_measurement(self):
        """Return the unit of measurement of this entity, if any."""
        return TEMP_CELSIUS

    @property
    def device_class(self):
        """Return the device class of this entity."""
        return DEVICE_CLASS_TEMPERATURE

    @property
    def device_state_attributes(self):
        """Return the state attributes."""
        data = {}
        if not self._is_low_voltage:
            data = {'wattage': self._wattage}
        data.update ({'heat_level': self._heat_level,
                      'rssi': self._rssi,
                      'alarm': self._alarm,
                      'keypad': self._keypad,
                      'away_setpoint': self._away_temp,
                      'setpoint_max': self._max_temp,
                      'setpoint_min': self._min_temp,
                      'early_start': self._early_start,
                      'sec._display': self._display_2,
                      'backlight': self._backlight,
                      'time_format': self._time_format,
                      'temperature_format': self._temperature_format,
                      'id': self._id})
        return data

    @property
    def supported_features(self):
        """Return the list of supported features."""
        return SUPPORT_FLAGS

    @property
    def min_temp(self):
        """Return the min temperature."""
        return self._min_temp

    @property
    def max_temp(self):
        """Return the max temperature."""
        return self._max_temp

    @property
    def temperature_unit(self):
        """Return the unit of measurement."""
        return TEMP_CELSIUS

    @property
    def hvac_mode(self):
        """Return current operation"""
        if self._operation_mode == MODE_OFF:
            return HVAC_MODE_OFF
        elif self._operation_mode in [MODE_AUTO, MODE_AUTO_BYPASS]:
            return HVAC_MODE_AUTO
        else:
            return HVAC_MODE_HEAT

    @property
    def hvac_modes(self):
        """Return the list of available operation modes."""
        return SUPPORTED_HVAC_MODES

    @property
    def current_temperature(self):
        """Return the current temperature."""
        return self._cur_temp
    
    @property
    def target_temperature (self):
        """Return the temperature we try to reach."""
        return self._target_temp

    @property
    def preset_modes(self):
        """Return available preset modes."""
        return PRESET_MODES

    @property
    def preset_mode(self):
        """Return current preset mode."""
        if self._operation_mode in [MODE_AUTO_BYPASS]:
            return PRESET_BYPASS
        elif self._operation_mode == MODE_AWAY:
            return PRESET_AWAY
        else:
            return PRESET_NONE

    @property
    def hvac_action(self):
        """Return current HVAC action."""
        if self._operation_mode == MODE_OFF:
            return CURRENT_HVAC_OFF
        elif self._heat_level == 0:
            return CURRENT_HVAC_IDLE
        else:
            return CURRENT_HVAC_HEAT

    def set_temperature(self, **kwargs):
        """Set new target temperature."""
        temperature = kwargs.get(ATTR_TEMPERATURE)
        if temperature is None:
            return
        self._client.set_temperature(self._id, temperature)
        self._target_temp = temperature

    def set_second_display(self, value):
        """ Set thermostat second display between outside and setpoint temperature. """
        display = value["display"]
        entity = value["id"]
        if display == "default":
            display_command = "default"
            display_name = "Setpoint"
        else:
            display_command = "outsideTemperature"
            display_name = "Outside"
        self._client.set_second_display(
            entity, display_command)
        self._display_2 = display_name

    def set_backlight(self, value):
        """ Set thermostat backlight intensity when idle, 0 = off, 100 = always on. """
        level = value["level"]
        entity = value["id"]
        self._client.set_backlight(
            entity, level)
        self._backlight = level

    def set_keypad_lock(self, value):
        """ Lock or unlock device's keypad, «locked» = Locked, «unlocked» = Unlocked. """
        lock = value["lock"]
        entity = value["id"]
        _LOGGER.debug("lock.data.before = %s", lock)
        self._client.set_keypad_lock(
            entity, lock)
        self._keypad = lock

    def set_early_start(self, value):
        """set early start heating for thermostat, On = early start set to on, Off = set to Off"""
        start = value["start"]
        entity = value["id"]
        self._client.set_early_start(
            entity, start)
        self._early_start = start

    def set_time_format(self, value):
        """set time format 12h or 24h"""
        time = value["time"]
        entity = value["id"]
        if time == 12:
            time_commande = "12h"
        else:
            time_commande = "24h"
        self._client.set_time_format(
            entity, time_commande)
        self._time_format = time_commande

    def set_temperature_format(self, value):
        """set temperature format celsius or fahrenheit"""
        temp = value["temp"]
        entity = value["id"]
        self._client.set_temperature_format(
            entity, temp)
        if temp == "celsius":
            self._temperature_format = TEMP_CELSIUS
        else:
            self._temperature_format = TEMP_FAHRENHEIT

    def set_setpoint_max(self, value):
        """set maximum setpoint temperature"""
        temp = value["temp"]
        entity = value["id"]
        self._client.set_setpoint_max(
            entity, temp)
        self._max_temp = temp

    def set_setpoint_min(self, value):
        """set minimum setpoint temperature"""
        temp = value["temp"]
        entity = value["id"]
        self._client.set_setpoint_min(
            entity, temp)
        self._min_temp = temp

    def set_hvac_mode(self, hvac_mode):
        """Set new hvac mode."""
        if hvac_mode == HVAC_MODE_OFF:
            self._client.set_setpoint_mode(self._id, MODE_OFF)
        elif hvac_mode == HVAC_MODE_HEAT:
            self._client.set_setpoint_mode(self._id, MODE_MANUAL)
        elif hvac_mode == HVAC_MODE_AUTO:
            self._client.set_setpoint_mode(self._id, MODE_AUTO)
        else:
            _LOGGER.error("Unable to set hvac mode: %s.", hvac_mode)

    def set_preset_mode(self, preset_mode):
        """Activate a preset."""
        if preset_mode == self.preset_mode:
            return

        if preset_mode == PRESET_AWAY:
            self._client.set_setpoint_mode(self._id, MODE_AWAY)
        elif preset_mode == PRESET_BYPASS:
            if self._operation_mode == MODE_AUTO:
                self._client.set_setpoint_mode(self._id, MODE_AUTO_BYPASS)
        elif preset_mode == PRESET_NONE:
            # Re-apply current hvac_mode without any preset
            self.set_hvac_mode(self.hvac_mode)
        else:
            _LOGGER.error("Unable to set preset mode: %s.", preset_mode)
