"""
Support for Neviweb sensor.
model 125, GT125 gateway
For more details about this platform, please refer to the documentation at  
https://www.sinopetech.com/en/support/#api
"""
import logging

import voluptuous as vol
import time

import custom_components.neviweb as neviweb
from . import (SCAN_INTERVAL)
from homeassistant.components.sensor import PLATFORM_SCHEMA

from homeassistant.const import (
    ATTR_ENTITY_ID,
    STATE_OK,
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

from homeassistant.components.binary_sensor import BinarySensorDeviceClass

from datetime import timedelta
from homeassistant.helpers.event import track_time_interval
from homeassistant.helpers.entity import Entity
from .const import (
    DOMAIN,
    ATTR_LOCALSYNC,
    ATTR_OCCUPANCY,
    ATTR_STATUS,
)

_LOGGER = logging.getLogger(__name__)

DEFAULT_NAME = 'neviweb sensor'

UPDATE_ATTRIBUTES = [
    ATTR_LOCALSYNC,
]

IMPLEMENTED_DEVICE_MODEL = [125] #GT125

async def async_setup_platform(
    hass,
    config,
    async_add_entities,
    discovery_info=None,
):
    """Set up the Neviweb sensor."""
    data = hass.data[DOMAIN]
    
    entities = []
    for device_info in data.neviweb_client.gateway_data:
        if "signature" in device_info and \
            "model" in device_info["signature"] and \
            device_info["signature"]["model"] in IMPLEMENTED_DEVICE_MODEL:
            device_name = '{} {}'.format(DEFAULT_NAME, device_info["name"])
            device_sku = device_info["sku"]
            location_id = device_info["location$id"]
            entities.append(NeviwebSensor(data, device_info, device_name, device_sku, location_id))
    for device_info in data.neviweb_client.gateway_data2:
        if "signature" in device_info and \
            "model" in device_info["signature"] and \
            device_info["signature"]["model"] in IMPLEMENTED_DEVICE_MODEL:
            device_name = '{} {}'.format(DEFAULT_NAME, device_info["name"])
            device_sku = device_info["sku"]
            location_id = device_info["location$id"]
            entities.append(NeviwebSensor(data, device_info, device_name, device_sku, location_id))

    async_add_entities(entities, True)

class NeviwebSensor(Entity):
    """Implementation of a Neviweb sensor."""

    def __init__(self, data, device_info, name, sku, location):
        """Initialize."""
        self._name = name
        self._sku = sku
        self._location = location
        self._client = data.neviweb_client
        self._id = device_info["id"]
        self._gateway_status = None
        self._occupancyMode = None
        self._sync = None
        _LOGGER.debug("Setting up %s: %s", self._name, device_info)

    def update(self):
        """Get the latest data from Neviweb and update the state."""
        start = time.time()
        device_status = self._client.get_device_status(self._id)
        neviweb_status = self._client.get_neviweb_status(self._location)
        device_data = self._client.get_device_attributes(self._id,
            UPDATE_ATTRIBUTES)
        end = time.time()
        elapsed = round(end - start, 3)
        _LOGGER.debug("Updating %s (%s sec): %s",
            self._name, elapsed, device_data)
        _LOGGER.debug("Updating %s (%s sec): %s",
            self._name, elapsed, device_status)
        self._gateway_status = device_status[ATTR_STATUS]
        self._occupancyMode = neviweb_status[ATTR_OCCUPANCY]
        if "error" not in device_data:
            if "errorCode" not in device_data:
                self._sync = device_data[ATTR_LOCALSYNC]
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

    @property
    def unique_id(self):
        """Return unique ID based on Neviweb device ID."""
        return self._id

    @property
    def name(self):
        """Return the name of the sensor."""
        return self._name

    @property
    def device_class(self):
        """Return the device class of this entity."""
        return BinarySensorDeviceClass.CONNECTIVITY

    @property  
    def is_on(self):
        """Return current operation i.e. ON, OFF """
        return self._gateway_status != None

    @property
    def extra_state_attributes(self):
        """Return the state attributes."""
        return {'gateway_status': self._gateway_status,
                'neviweb_occupancyMode': self._occupancyMode,
                'local_sync': self._sync,
                'sku': self._sku,
                'id': self._id}

    @property
    def state(self):
        """Return the state of the sensor."""
        return self._gateway_status
