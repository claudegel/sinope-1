"""
Support for Neviweb light switch/dimmer.
type 102 = light switch SW2500RF
type 112 = light dimmer DM2500RF
For more details about this platform, please refer to the documentation at  
https://www.sinopetech.com/en/support/#api
"""
import logging

import voluptuous as vol
import time

import custom_components.neviweb as neviweb
from . import (SCAN_INTERVAL)
from homeassistant.components.light import (LightEntity, ATTR_BRIGHTNESS,
    ATTR_BRIGHTNESS_PCT, SUPPORT_BRIGHTNESS)
from datetime import timedelta
from .const import (DOMAIN, ATTR_POWER_MODE, ATTR_INTENSITY, ATTR_RSSI,
    ATTR_WATTAGE_OVERRIDE, MODE_AUTO, MODE_MANUAL, ATTR_OCCUPANCY)

_LOGGER = logging.getLogger(__name__)

DEFAULT_NAME = 'neviweb'

UPDATE_ATTRIBUTES = [ATTR_POWER_MODE, ATTR_INTENSITY, ATTR_RSSI, 
    ATTR_WATTAGE_OVERRIDE, ATTR_OCCUPANCY]

# STATE_AUTO = 'auto'
# STATE_MANUAL = 'manual'
# STATE_AWAY = 'away'
# STATE_STANDBY = 'bypass'
# NEVIWEB_TO_HA_STATE = {
#     1: STATE_MANUAL,
#     2: STATE_AUTO,
#     3: STATE_AWAY,
#     130: STATE_STANDBY
# }

DEVICE_TYPE_DIMMER = [112]
DEVICE_TYPE_LIGHT = [102]
IMPLEMENTED_DEVICE_TYPES = DEVICE_TYPE_LIGHT + DEVICE_TYPE_DIMMER

async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    """Set up the neviweb light."""
    data = hass.data[DOMAIN]
    
    devices = []
    for device_info in data.neviweb_client.gateway_data:
        if "signature" in device_info and \
            "type" in device_info["signature"] and \
            device_info["signature"]["type"] in IMPLEMENTED_DEVICE_TYPES:
            device_name = '{} {} {}'.format(DEFAULT_NAME, 
                "dimmer" if device_info["signature"]["type"] in DEVICE_TYPE_DIMMER 
                else "light", device_info["name"])
            devices.append(NeviwebLight(data, device_info, device_name))
    for device_info in data.neviweb_client.gateway_data2:
        if "signature" in device_info and \
            "type" in device_info["signature"] and \
            device_info["signature"]["type"] in IMPLEMENTED_DEVICE_TYPES:
            device_name = '{} {} {}'.format(DEFAULT_NAME, 
                "dimmer" if device_info["signature"]["type"] in DEVICE_TYPE_DIMMER 
                else "light", device_info["name"])
            devices.append(Neviweb2Light(data, device_info, device_name))
            
    async_add_entities(devices, True)

def brightness_to_percentage(brightness):
    """Convert brightness from absolute 0..255 to percentage."""
    return int((brightness * 100.0) / 255.0)

def brightness_from_percentage(percent):
    """Convert percentage to absolute value 0..255."""
    return int((percent * 255.0) / 100.0)

# def keyCheck(key, arr, default, name):
#     if key in arr.keys():
#         return arr[key]
#     else:
#         _LOGGER.debug("Neviweb missing %s for %s", key, name)
#         return default

class NeviwebLight(LightEntity):
    """Implementation of a neviweb light."""

    def __init__(self, data, device_info, name):
        """Initialize."""
        self._name = name
        self._client = data.neviweb_client
        self._id = device_info["id"]
        self._wattage_override = 0 # keyCheck("wattageOverride", device_info, 0, name)
        self._brightness_pct = 0
        self._operation_mode = 1
        #self._alarm = None
        self._rssi = None
        self._occupancy = None
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
                #self._alarm = device_data["alarm"]
                self._rssi = device_data[ATTR_RSSI]
                self._wattage_override = device_data[ATTR_WATTAGE_OVERRIDE]
                self._occupancy = device_data[ATTR_OCCUPANCY]
                return
            _LOGGER.warning("Error in reading device %s: (%s)", self._name, device_data)
            return
        _LOGGER.warning("Cannot update %s: %s", self._name, device_data)   
        
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
    def brightness(self):
        """Return intensity of light"""
        return brightness_from_percentage(self._brightness_pct)

    @property
    def is_on(self):
        """Return true if device is on."""
        return self._brightness_pct != 0
    
    # For the turn_on and turn_off functions, we would normally check if the
    # the requested state is different from the actual state to issue the 
    # command. But since we update the state every 15 minutes, there is good
    # chance that the current stored state doesn't match with real device 
    # state. So we force the set_brightness each time.
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

    @property
    def device_state_attributes(self):
        """Return the state attributes."""
        data = {}
        if self._is_dimmable and self._brightness_pct:
            data = {ATTR_BRIGHTNESS_PCT: self._brightness_pct}
        data.update({#'alarm': self._alarm,
                     'operation_mode': self.operation_mode,
                     'rssi': self._rssi,
                     'occupancy': self._occupancy,
                     'wattage_override': self._wattage_override,
                     'id': self._id})
        return data
 
    @property
    def operation_mode(self):
        return self._operation_mode

    # def to_hass_operation_mode(self, mode):
    #     """Translate neviweb operation modes to hass operation modes."""
    #     if mode in NEVIWEB_TO_HA_STATE:
    #         return NEVIWEB_TO_HA_STATE[mode]
    #     _LOGGER.error("Operation mode %s could not be mapped to hass", mode)
    #     return None
