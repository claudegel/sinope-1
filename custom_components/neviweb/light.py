"""
Support for Neviweb light switch/dimmer.
type 102 = light switch SW2500RF, model 2120
type 112 = light dimmer DM2500RF, model 2130
For more details about this platform, please refer to the documentation at  
https://www.sinopetech.com/en/support/#api
"""
import logging

import voluptuous as vol
import time

import custom_components.neviweb as neviweb
from . import (SCAN_INTERVAL)
from homeassistant.components.light import (
    LightEntity,
    ATTR_BRIGHTNESS,
    ATTR_BRIGHTNESS_PCT,
    SUPPORT_BRIGHTNESS,
)

from homeassistant.const import (
    ATTR_ENTITY_ID,
)

from homeassistant.helpers import (
    config_validation as cv,
    discovery,
    entity_platform,
    service,
)

from homeassistant.helpers.typing import HomeAssistantType
from homeassistant.helpers import (
    entity_platform,
    service,
    entity_component,
    entity_registry,
    device_registry,
)

from datetime import timedelta
from .const import (
    DOMAIN,
    ATTR_POWER_MODE,
    ATTR_INTENSITY,
    ATTR_RSSI,
    ATTR_WATTAGE_OVERRIDE,
    ATTR_OCCUPANCY,
    ATTR_AWAY_MODE,
    ATTR_KEYPAD,
    ATTR_TIMER,
    ATTR_LED_ON,
    ATTR_LED_OFF,
    ATTR_STATE,
    ATTR_RED,
    ATTR_GREEN,
    ATTR_BLUE,
    MODE_AUTO,
    MODE_MANUAL,
    SERVICE_SET_LED_INDICATOR,
    SERVICE_SET_KEYPAD_LOCK,
    SERVICE_SET_TIMER,
)

_LOGGER = logging.getLogger(__name__)

DEFAULT_NAME = 'neviweb'

UPDATE_ATTRIBUTES = [
    ATTR_POWER_MODE,
    ATTR_INTENSITY,
    ATTR_RSSI,
    ATTR_WATTAGE_OVERRIDE,
    ATTR_OCCUPANCY,
    ATTR_AWAY_MODE,
    ATTR_KEYPAD,
    ATTR_TIMER,
    ATTR_LED_ON,
    ATTR_LED_OFF,
]

DEVICE_TYPE_DIMMER = [112]
DEVICE_TYPE_LIGHT = [102]
IMPLEMENTED_DEVICE_TYPES = DEVICE_TYPE_LIGHT + DEVICE_TYPE_DIMMER

SET_KEYPAD_LOCK_SCHEMA = vol.Schema(
    {
         vol.Required(ATTR_ENTITY_ID): cv.entity_id,
         vol.Required(ATTR_KEYPAD): cv.string,
    }
)

SET_TIMER_SCHEMA = vol.Schema(
    {
         vol.Required(ATTR_ENTITY_ID): cv.entity_id,
         vol.Required(ATTR_TIMER): vol.All(
             vol.Coerce(int), vol.Range(min=0, max=255)
         ),
    }
)

SET_LED_INDICATOR_SCHEMA = vol.Schema(
    {
         vol.Required(ATTR_ENTITY_ID): cv.entity_id,
         vol.Required(ATTR_STATE): vol.All(
             vol.Coerce(int), vol.Range(min=0, max=1)
         ),
         vol.Required(ATTR_INTENSITY): vol.All(
             vol.Coerce(int), vol.Range(min=0, max=100)
         ),
         vol.Required(ATTR_RED): vol.All(
             vol.Coerce(int), vol.Range(min=0, max=255)
         ),
         vol.Required(ATTR_GREEN): vol.All(
             vol.Coerce(int), vol.Range(min=0, max=255)
         ),
         vol.Required(ATTR_BLUE): vol.All(
             vol.Coerce(int), vol.Range(min=0, max=255)
         ),
    }
)

async def async_setup_platform(
    hass: HomeAssistantType,
    config_entry,
    async_add_entities,
    discovery_info = None,
) -> None:
    """Set up the neviweb light."""
    data = hass.data[DOMAIN]
    
    entities = []
    for device_info in data.neviweb_client.gateway_data:
        if "signature" in device_info and \
            "type" in device_info["signature"] and \
            device_info["signature"]["type"] in IMPLEMENTED_DEVICE_TYPES:
            device_name = '{} {} {}'.format(DEFAULT_NAME, 
                "dimmer" if device_info["signature"]["type"] in DEVICE_TYPE_DIMMER 
                else "light", device_info["name"])
            entities.append(NeviwebLight(data, device_info, device_name))
    for device_info in data.neviweb_client.gateway_data2:
        if "signature" in device_info and \
            "type" in device_info["signature"] and \
            device_info["signature"]["type"] in IMPLEMENTED_DEVICE_TYPES:
            device_name = '{} {} {}'.format(DEFAULT_NAME, 
                "dimmer" if device_info["signature"]["type"] in DEVICE_TYPE_DIMMER 
                else "light", device_info["name"])
            entities.append(NeviwebLight(data, device_info, device_name))
            
    async_add_entities(entities, True)

    def set_keypad_lock_service(service):
        """ lock/unlock keypad device"""
        entity_id = service.data[ATTR_ENTITY_ID]
        value = {}
        for light in entities:
            if light.entity_id == entity_id:
                value = {"id": light.unique_id, "lock": service.data[ATTR_KEYPAD]}
                light.set_keypad_lock(value)
                light.schedule_update_ha_state(True)
                break

    def set_timer_service(service):
        """ set timer for light device"""
        entity_id = service.data[ATTR_ENTITY_ID]
        value = {}
        for light in entities:
            if light.entity_id == entity_id:
                value = {"id": light.unique_id, "time": service.data[ATTR_TIMER]}
                light.set_timer(value)
                light.schedule_update_ha_state(True)
                break

    def set_led_indicator_service(service):
        """ set led color and intensity for light indicator """
        entity_id = service.data[ATTR_ENTITY_ID]
        value = {}
        for light in entities:
            if light.entity_id == entity_id:
                value = {"id": light.unique_id, "state": service.data[ATTR_STATE], "intensity": service.data[ATTR_INTENSITY], "red": service.data[ATTR_RED], "green": service.data[ATTR_GREEN], "blue": service.data[ATTR_BLUE]}
                light.set_led_indicator(value)
                light.schedule_update_ha_state(True)
                break

    hass.services.async_register(
        DOMAIN,
        SERVICE_SET_KEYPAD_LOCK,
        set_keypad_lock_service,
        schema=SET_KEYPAD_LOCK_SCHEMA,
    )

    hass.services.async_register(
        DOMAIN,
        SERVICE_SET_TIMER,
        set_timer_service,
        schema=SET_TIMER_SCHEMA,
    )

    hass.services.async_register(
        DOMAIN,
        SERVICE_SET_LED_INDICATOR,
        set_led_indicator_service,
        schema=SET_LED_INDICATOR_SCHEMA,
    )

def brightness_to_percentage(brightness):
    """Convert brightness from absolute 0..255 to percentage."""
    return int((brightness * 100.0) / 255.0)

def brightness_from_percentage(percent):
    """Convert percentage to absolute value 0..255."""
    return int((percent * 255.0) / 100.0)

class NeviwebLight(LightEntity):
    """Implementation of a neviweb light."""

    def __init__(self, data, device_info, name):
        """Initialize."""
        self._name = name
        self._client = data.neviweb_client
        self._id = device_info["id"]
        self._wattage_override = 0
        self._brightness_pct = 0
        self._operation_mode = 1
        self._rssi = None
        self._occupancy = None
        self._away_mode = None
        self._keypad = "Unlocked"
        self._timer = 0
        self._led_on = "0,0,0,0"
        self._led_off = "0,0,0,0"
        self._is_dimmable = device_info["signature"]["type"] in \
            DEVICE_TYPE_DIMMER
        _LOGGER.debug("Setting up %s: %s", self._name, device_info)
        
    def update(self):
        """Get the latest data from neviweb and update the state."""
        start = time.time()
        device_data = self._client.get_device_attributes(self._id,
            UPDATE_ATTRIBUTES)
        end = time.time()
        elapsed = round(end - start, 3)
        _LOGGER.debug("Updating %s (%s sec): %s",
            self._name, elapsed, device_data)
        if "error" not in device_data:
            if "errorCode" not in device_data:
                self._brightness_pct = device_data[ATTR_INTENSITY] if \
                    device_data[ATTR_INTENSITY] is not None else 0.0
                self._operation_mode = device_data[ATTR_POWER_MODE] if \
                    device_data[ATTR_POWER_MODE] is not None else MODE_MANUAL
                self._rssi = device_data[ATTR_RSSI]
                self._wattage_override = device_data[ATTR_WATTAGE_OVERRIDE]
                self._occupancy = device_data[ATTR_OCCUPANCY]
                self._away_mode = device_data[ATTR_AWAY_MODE]["value"]["action"]
                self._keypad = device_data[ATTR_KEYPAD]
                self._timer = device_data[ATTR_TIMER]
                self._led_on = str(device_data[ATTR_LED_ON]["intensity"])+","+str(device_data[ATTR_LED_ON]["red"])+","+str(device_data[ATTR_LED_ON]["green"])+","+str(device_data[ATTR_LED_ON]["blue"])
                self._led_off = str(device_data[ATTR_LED_OFF]["intensity"])+","+str(device_data[ATTR_LED_OFF]["red"])+","+str(device_data[ATTR_LED_OFF]["green"])+","+str(device_data[ATTR_LED_OFF]["blue"])
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
            elif device_data["error"]["code"] == "DVCACTNSPTD":
                _LOGGER.warning("Device action not supported, %s:",  device_data)
            elif device_data["error"]["code"] == "DVCUNVLB":
                _LOGGER.warning("Device %s unavailable, Neviweb maintnance update, %s:", self._name, device_data)
            elif device_data["error"]["code"] == "SVCERR":
                _LOGGER.warning("Device %s statistics unavailables, %s:", self._name, device_data)
            else:
                _LOGGER.warning("Unknown error, device: %s, error: %s", self._name, device_data)   
        
    @property
    def supported_features(self):
        """Return the list of supported features."""
        if self._is_dimmable:
            return SUPPORT_BRIGHTNESS
        return 0
    
    @property
    def unique_id(self):
        """Return unique ID based on Neviweb device ID."""
        return self._id

    @property
    def name(self):
        """Return the name of the light."""
        return self._name

    @property
    def device_class(self):
        """Return the device class of this entity."""
        return "light"

    @property
    def device_state_attributes(self):
        """Return the state attributes."""
        data = {}
        if self._is_dimmable and self._brightness_pct:
            data = {ATTR_BRIGHTNESS_PCT: self._brightness_pct}
        data.update({#'alarm': self._alarm,
                     'operation_mode': self.operation_mode,
                     'rssi': self._rssi,
                     'keypad': self._keypad,
                     'timer': self._timer,
                     'occupancy': self._occupancy,
                     'away_mode': self._away_mode,
                     'wattage_override': self._wattage_override,
                     'led_on': self._led_on,
                     'led_off': self._led_off,
                     'id': self._id})
        return data

    @property
    def brightness(self):
        """Return intensity of light"""
        return brightness_from_percentage(self._brightness_pct)

    @property
    def is_on(self):
        """Return true if device is on."""
        return self._brightness_pct != 0

    def turn_on(self, **kwargs):
        """Turn the light on."""
        brightness_pct = 100
        if kwargs.get(ATTR_BRIGHTNESS):
            brightness_pct = \
                brightness_to_percentage(int(kwargs.get(ATTR_BRIGHTNESS)))
        elif self._is_dimmable:
            brightness_pct = 101 # Sets the light to last known brightness.
        self._client.set_brightness(self._id, brightness_pct)

    def turn_off(self, **kwargs):
        """Turn the light off."""
        self._client.set_brightness(self._id, 0)
 
    def set_keypad_lock(self, value):
        """Lock or unlock device's keypad, lock = locked, unlock = unlocked"""
        lock = value["lock"]
        entity = value["id"]
        if lock == "lock":
            lock_commande = "locked"
            lock_name = "Locked"
        else:
            lock_commande = "unlocked"
            lock_name = "Unlocked"
        self._client.set_keypad_lock(
            entity, lock_commande)
        self._keypad = lock_name

    def set_timer(self, value):
        """Set device timer, 0 = off, 1 to 255 = timer length"""
        time = value["time"]
        entity = value["id"]
        self._client.set_timer(
            entity, time)
        self._timer = time

    def set_led_indicator(self, value):
        """Set led indicator color and intensity, base on RGB red, green, blue color (0-255) and intensity from 0 to 100"""
        state = value["state"]
        entity = value["id"]
        intensity = value["intensity"]
        red = value["red"]
        green = value["green"]
        blue = value["blue"]
        self._client.set_led_indicator(
            entity, state, intensity, red, green, blue)
        if state == 0:
            self._led_off = str(value["intensity"])+","+str(value["red"])+","+str(value["green"])+","+str(value["blue"])
        else:
            self._led_on = str(value["intensity"])+","+str(value["red"])+","+str(value["green"])+","+str(value["blue"])

    @property
    def operation_mode(self):
        return self._operation_mode
