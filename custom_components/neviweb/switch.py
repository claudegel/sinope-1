"""
Support for Neviweb switch.
type 120 = load controller device, RM3250RF and RM3200RF model 2505

For more details about this platform, please refer to the documentation at  
https://www.sinopetech.com/en/support/#api
"""
import logging

import voluptuous as vol
import time

import custom_components.neviweb as neviweb
from . import (SCAN_INTERVAL)
from homeassistant.components.switch import (
    SwitchEntity,
)

from homeassistant.const import (
    ATTR_ENTITY_ID,
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

from homeassistant.components.sensor import SensorDeviceClass

from datetime import timedelta
from homeassistant.helpers.event import track_time_interval
from .const import (
    DOMAIN,
    ATTR_POWER_MODE,
    ATTR_INTENSITY,
    ATTR_RSSI,
    ATTR_WATTAGE,
    ATTR_WATTAGE_INSTANT,
    ATTR_KEYPAD,
    ATTR_TIMER,
    ATTR_OCCUPANCY,
    ATTR_AWAY_MODE,
    ATTR_SHED_PLANNING,
    ATTR_STATUS,
    MODE_AUTO,
    MODE_MANUAL,
    SERVICE_SET_SWITCH_KEYPAD_LOCK,
    SERVICE_SET_SWITCH_TIMER,
    SERVICE_SET_SWITCH_AWAY_MODE,
    SERVICE_SET_SWITCH_ECO_STATUS,
)

_LOGGER = logging.getLogger(__name__)

DEFAULT_NAME = 'neviweb switch'

UPDATE_ATTRIBUTES = [
    ATTR_POWER_MODE,
    ATTR_INTENSITY,
    ATTR_RSSI,
    ATTR_WATTAGE,
    ATTR_WATTAGE_INSTANT,
    ATTR_TIMER,
    ATTR_KEYPAD,
    ATTR_OCCUPANCY,
    ATTR_AWAY_MODE,
    ATTR_SHED_PLANNING,
]

IMPLEMENTED_DEVICE_TYPES = [120] #power control device

SET_SWITCH_KEYPAD_LOCK_SCHEMA = vol.Schema(
    {
         vol.Required(ATTR_ENTITY_ID): cv.entity_id,
         vol.Required(ATTR_KEYPAD): vol.In(["locked", "unlocked"]),
    }
)

SET_SWITCH_TIMER_SCHEMA = vol.Schema(
    {
         vol.Required(ATTR_ENTITY_ID): cv.entity_id,
         vol.Required(ATTR_TIMER): vol.All(
             vol.Coerce(int), vol.Range(min=0, max=10800)
         ),
    }
)

SET_SWITCH_AWAY_MODE_SCHEMA = vol.Schema(
    {
         vol.Required(ATTR_ENTITY_ID): cv.entity_id,
         vol.Required(ATTR_AWAY_MODE): vol.In(["auto", "manualOn", "manualOff"]),
    }
)

SET_SWITCH_ECO_STATUS_SCHEMA = vol.Schema(
    {
         vol.Required(ATTR_ENTITY_ID): cv.entity_id,
         vol.Required(ATTR_STATUS): vol.In(["none", "planned"]),
    }
)

async def async_setup_platform(
    hass,
    config,
    async_add_entities,
    discovery_info=None,
):
    """Set up the Neviweb switch."""
    data = hass.data[DOMAIN]
    
    entities = []
    for device_info in data.neviweb_client.gateway_data:
        if "signature" in device_info and \
            "type" in device_info["signature"] and \
            device_info["signature"]["type"] in IMPLEMENTED_DEVICE_TYPES:
            device_name = '{} {}'.format(DEFAULT_NAME, device_info["name"])
            device_sku = device_info["sku"]
            entities.append(NeviwebSwitch(data, device_info, device_name, device_sku))
    for device_info in data.neviweb_client.gateway_data2:
        if "signature" in device_info and \
            "type" in device_info["signature"] and \
            device_info["signature"]["type"] in IMPLEMENTED_DEVICE_TYPES:
            device_name = '{} {}'.format(DEFAULT_NAME, device_info["name"])
            device_sku = device_info["sku"]
            entities.append(NeviwebSwitch(data, device_info, device_name, device_sku))

    async_add_entities(entities, True)

    def set_switch_keypad_lock_service(service):
        """ lock/unlock keypad device"""
        entity_id = service.data[ATTR_ENTITY_ID]
        value = {}
        for switch in entities:
            if switch.entity_id == entity_id:
                value = {"id": switch.unique_id, "lock": service.data[ATTR_KEYPAD]}
                switch.set_keypad_lock(value)
                switch.schedule_update_ha_state(True)
                break

    def set_switch_timer_service(service):
        """ set timer for switch device"""
        entity_id = service.data[ATTR_ENTITY_ID]
        value = {}
        for switch in entities:
            if switch.entity_id == entity_id:
                value = {"id": switch.unique_id, "time": service.data[ATTR_TIMER]}
                switch.set_timer(value)
                switch.schedule_update_ha_state(True)
                break

    def set_switch_away_mode_service(service):
        """ set light action in away mode """
        entity_id = service.data[ATTR_ENTITY_ID]
        value = {}
        for switch in entities:
            if switch.entity_id == entity_id:
                value = {"id": switch.unique_id, "away": service.data[ATTR_AWAY_MODE]}
                switch.set_away_mode(value)
                switch.schedule_update_ha_state(True)
                break

    def set_switch_eco_status_service(service):
        """ set switch eco status """
        entity_id = service.data[ATTR_ENTITY_ID]
        value = {}
        for switch in entities:
            if switch.entity_id == entity_id:
                value = {"id": switch.unique_id, "status": service.data[ATTR_STATUS]}
                switch.set_switch_eco_status(value)
                switch.schedule_update_ha_state(True)
                break

    hass.services.async_register(
        DOMAIN,
        SERVICE_SET_SWITCH_KEYPAD_LOCK,
        set_switch_keypad_lock_service,
        schema=SET_SWITCH_KEYPAD_LOCK_SCHEMA,
    )

    hass.services.async_register(
        DOMAIN,
        SERVICE_SET_SWITCH_TIMER,
        set_switch_timer_service,
        schema=SET_SWITCH_TIMER_SCHEMA,
    )

    hass.services.async_register(
        DOMAIN,
        SERVICE_SET_SWITCH_AWAY_MODE,
        set_switch_away_mode_service,
        schema=SET_SWITCH_AWAY_MODE_SCHEMA,
    )

    hass.services.async_register(
        DOMAIN,
        SERVICE_SET_SWITCH_ECO_STATUS,
        set_switch_eco_status_service,
        schema=SET_SWITCH_ECO_STATUS_SCHEMA,
    )

class NeviwebSwitch(SwitchEntity):
    """Implementation of a Neviweb switch."""

    def __init__(self, data, device_info, name, sku):
        """Initialize."""
        self._name = name
        self._sku = sku
        self._client = data.neviweb_client
        self._id = device_info["id"]
        self._wattage = 0
        self._brightness = 0
        self._operation_mode = 1
        self._current_power_w = 0
        self._today_energy_kwh = None
        self._hour_energy_kwh = None
        self._rssi = None
        self._timer = 0
        self._occupancy = None
        self._away_mode = None
        self._keypad = "unlocked"
        self._shed_planning_status = None
        self._energy_stat_time = time.time() - 1500
        _LOGGER.debug("Setting up %s: %s", self._name, device_info)

    def update(self):
        """Get the latest data from Neviweb and update the state."""
        start = time.time()
        device_data = self._client.get_device_attributes(self._id,
            UPDATE_ATTRIBUTES)
        end = time.time()
        elapsed = round(end - start, 3)
        _LOGGER.debug("Updating %s (%s sec): %s",
            self._name, elapsed, device_data)
        if "error" not in device_data:
            if "errorCode" not in device_data:
                self._brightness = device_data[ATTR_INTENSITY] if \
                    device_data[ATTR_INTENSITY] is not None else 0
                self._operation_mode = device_data[ATTR_POWER_MODE] if \
                    device_data[ATTR_POWER_MODE] is not None else MODE_MANUAL
                self._current_power_w = device_data[ATTR_WATTAGE_INSTANT]["value"]
                self._wattage = device_data[ATTR_WATTAGE]["value"]
                self._rssi = device_data[ATTR_RSSI]
                self._timer = device_data[ATTR_TIMER]
                self._occupancy = device_data[ATTR_OCCUPANCY]
                self._away_mode = device_data[ATTR_AWAY_MODE]["value"]["action"]
                self._keypad = device_data[ATTR_KEYPAD]
                if ATTR_SHED_PLANNING in device_data:
                    self._shed_planning_status = device_data[ATTR_SHED_PLANNING]
            else:
                if device_data["errorCode"] == "ReadTimeout":
                    _LOGGER.warning("Error in reading device %s: (%s), too slow to respond or busy.", self._name, device_data)
                else:
                    _LOGGER.warning("Unknown errorCode, device: %s, error: %s", self._name, device_data)
        else:
            if device_data["error"]["code"] == "USRSESSEXP":
                _LOGGER.warning("Session expired... reconnecting...")
                self._client.reconnect()
            elif device_data["error"]["code"] == "DVCCOMMTO":  
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
        if start - self._energy_stat_time > 1800 and self._energy_stat_time != 0:
            device_hourly_stats = self._client.get_device_hourly_stats(self._id)
            if device_hourly_stats is not None:
                self._hour_energy_kwh = round(device_hourly_stats[0] / 1000, 3)
            else:
                _LOGGER.warning("Got None for device_hourly_stats")
            device_daily_stats = self._client.get_device_daily_stats(self._id)
            if device_daily_stats is not None:
                self._today_energy_kwh = round(device_daily_stats[0] / 1000, 3)
            else:
                _LOGGER.warning("Got None for device_daily_stats")
            self._energy_stat_time = time.time()
        if self._energy_stat_time == 0:
            self._energy_stat_time = start

    @property
    def unique_id(self):
        """Return unique ID based on Neviweb device ID."""
        return self._id

    @property
    def name(self):
        """Return the name of the switch."""
        return self._name

    @property
    def device_class(self):
        """Return the device class of this entity."""
        return SensorDeviceClass.POWER

    @property  
    def is_on(self):
        """Return current operation i.e. ON, OFF """
        return self._brightness != 0

    def turn_on(self, **kwargs):
        """Turn the device on."""
        self._client.set_brightness(self._id, 100)
        self._brightness = 100

    def turn_off(self, **kwargs):
        """Turn the device off."""
        self._client.set_brightness(self._id, 0)
        self._brightness = 0

    @property
    def extra_state_attributes(self):
        """Return the state attributes."""
        return {'operation_mode': self.operation_mode,
                'eco_status': self._shed_planning_status,
                'rssi': self._rssi,
                'timer': self._timer,
                'occupancy': self._occupancy,
                'away_mode': self._away_mode,
                'keypad': self._keypad,
                'wattage': self._wattage,
                'wattage_instant': self._current_power_w,
                'hourly_kwh': self._hour_energy_kwh,
                'daily_kwh': self._today_energy_kwh,
                'sku': self._sku,
                'id': self._id}

    @property
    def operation_mode(self):
        return self._operation_mode

    @property
    def is_standby(self):
        """Return true if device is in standby."""
        return self._current_power_w == 0

    def set_keypad_lock(self, value):
        """Lock or unlock device's keypad, lock = locked, unlock = unlocked"""
        lock = value["lock"]
        entity = value["id"]
        self._client.set_keypad_lock(
            entity, lock)
        self._keypad = lock

    def set_timer(self, value):
        """Set device timer, 0 = off, 1 to 10800 seconds = timer length"""
        time = value["time"]
        entity = value["id"]
        self._client.set_timer(
            entity, time)
        self._timer = time

    def set_away_mode(self, value):
        """ Set device away mode, On, Off, Auto, None """
        away = value["away"]
        entity = value["id"]
        self._client.set_mode_away(
            entity, away)
        self._away_mode = away

def set_switch_eco_status(self, value):
        """ Set switch eco status on/off """
        status = value["status"]
        entity = value["id"]
        self._client.set_switch_eco_status(
            entity, status)
        self._shed_planning_status = status
