"""
Support for Neviweb sensor.

model 125, GT125 gateway
For more details about this platform, please refer to the documentation at
https://www.sinopetech.com/en/support/#api
"""

import asyncio
import datetime
import logging

import voluptuous as vol
import time

from homeassistant.const import (
    ATTR_ENTITY_ID,
)

from homeassistant.core import ServiceCall
from homeassistant.helpers import config_validation as cv

from homeassistant.components.binary_sensor import BinarySensorDeviceClass

from homeassistant.helpers.entity import Entity
from . import SCAN_INTERVAL as scan_interval
from .const import (
    DOMAIN,
    ATTR_LOCAL_SYNC,
    ATTR_MODE,
    ATTR_OCCUPANCY,
    ATTR_STATUS,
    SERVICE_SET_NEVIWEB_STATUS,
)
from .helpers import get_daily_request_count

_LOGGER = logging.getLogger(__name__)

DEFAULT_NAME = "neviweb sensor"
SCAN_INTERVAL = scan_interval

UPDATE_ATTRIBUTES = [
    ATTR_LOCAL_SYNC,
]

IMPLEMENTED_DEVICE_MODEL = [125]  # GT125

SET_NEVIWEB_STATUS_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_ENTITY_ID): cv.entity_id,
        vol.Required(ATTR_MODE): vol.In(["home", "away"]),
    }
)


async def async_setup_platform(
    hass,
    config,
    async_add_entities,
    discovery_info=None,
) -> None:
    """Set up the Neviweb sensor."""
    data = hass.data[DOMAIN]["data"]

    # Wait for async migration to be done
    await data.migration_done.wait()

    entities: list[Entity] = []
    entities.append(NeviwebDailyRequestSensor(hass))
    for device_info in data.neviweb_client.gateway_data:
        if (
            "signature" in device_info
            and "model" in device_info["signature"]
            and device_info["signature"]["model"] in IMPLEMENTED_DEVICE_MODEL
        ):
            device_name = "{} {}".format(DEFAULT_NAME, device_info["name"])
            device_sku = device_info["sku"]
            location_id = device_info["location$id"]
            entities.append(
                NeviwebSensor(data, device_info, device_name, device_sku, location_id)
            )
    for device_info in data.neviweb_client.gateway_data2:
        if (
            "signature" in device_info
            and "model" in device_info["signature"]
            and device_info["signature"]["model"] in IMPLEMENTED_DEVICE_MODEL
        ):
            device_name = "{} {}".format(DEFAULT_NAME, device_info["name"])
            device_sku = device_info["sku"]
            location_id = device_info["location$id"]
            entities.append(
                NeviwebSensor(data, device_info, device_name, device_sku, location_id)
            )

    async_add_entities(entities)

    async def _refresh_entities_initially() -> None:
        """Refresh entities one by one after startup, without blocking setup."""
        for entity in entities:
            if hass.is_stopping:
                return
            try:
                await entity.async_device_update()
                entity.async_write_ha_state()
            except Exception:  # noqa: BLE001 - one bad device must not abort the sweep
                _LOGGER.warning("Initial refresh failed for %s", entity.name)

    hass.async_create_task(_refresh_entities_initially())

    def set_neviweb_status_service(service: ServiceCall) -> None:
        """Set Neviweb global status, home or away."""
        entity_id = service.data[ATTR_ENTITY_ID]
        value = {}
        for sensor in entities:
            if sensor.entity_id == entity_id:
                value = {"id": sensor.unique_id, "mode": service.data[ATTR_MODE]}
                sensor.set_neviweb_status(value)
                sensor.schedule_update_ha_state(True)
                break

    hass.services.async_register(
        DOMAIN,
        SERVICE_SET_NEVIWEB_STATUS,
        set_neviweb_status_service,
        schema=SET_NEVIWEB_STATUS_SCHEMA,
    )


class NeviwebSensor(Entity):
    """Implementation of a Neviweb sensor."""

    def __init__(self, data, device_info, name, sku, location):
        """Initialize."""
        self._name = name
        self._sku = sku
        self._location = location
        self._client = data.neviweb_client
        self._id = str(device_info["id"])
        self._gateway_status = None
        self._occupancyMode = None
        self._sync = None
        _LOGGER.debug("Setting up %s: %s", self._name, device_info)

    def update(self):
        """Get the latest data from Neviweb and update the state."""
        start = time.time()
        device_status = self._client.get_device_status(self._id)
        neviweb_status = self._client.get_neviweb_status(self._location)
        device_data = self._client.get_device_attributes(self._id, UPDATE_ATTRIBUTES)
        end = time.time()
        elapsed = round(end - start, 3)
        _LOGGER.debug("Updating %s (%s sec): %s", self._name, elapsed, device_data)
        _LOGGER.debug("Updating %s (%s sec): %s", self._name, elapsed, device_status)
        self._gateway_status = device_status[ATTR_STATUS]
        self._occupancyMode = neviweb_status[ATTR_OCCUPANCY]
        if "error" not in device_data:
            if "errorCode" not in device_data:
                self._sync = device_data[ATTR_LOCAL_SYNC]
            else:
                if device_data["errorCode"] == "ReadTimeout":
                    _LOGGER.warning(
                        "Error in reading device %s: (%s), too slow to respond or busy.",
                        self._name,
                        device_data,
                    )
                else:
                    _LOGGER.warning(
                        "Unknown errorCode, device: %s, error: %s",
                        self._name,
                        device_data,
                    )
        else:
            if device_data["error"]["code"] == "USRSESSEXP":
                _LOGGER.warning("Session expired... reconnecting...")
                self._client.reconnect()
            elif device_data["error"]["code"] == "DVCCOMMTO":
                _LOGGER.warning(
                    "Cannot update %s: %s. Device is busy or does not respond quickly enough.",
                    self._name,
                    device_data,
                )
            elif device_data["error"]["code"] == "SVCINVREQ":
                _LOGGER.warning(
                    "Invalid or malformed request to Neviweb, %s:", device_data
                )
            elif device_data["error"]["code"] == "DVCACTNSPTD":
                _LOGGER.warning("Device action not supported, %s:", device_data)
            elif device_data["error"]["code"] == "DVCUNVLB":
                _LOGGER.warning(
                    "Device %s unavailable, Neviweb maintnance update, %s:",
                    self._name,
                    device_data,
                )
            elif device_data["error"]["code"] == "SVCERR":
                _LOGGER.warning(
                    "Device %s statistics unavailables, %s:", self._name, device_data
                )
            else:
                _LOGGER.warning(
                    "Unknown error, device: %s, error: %s", self._name, device_data
                )

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
        """Return current operation i.e. ON, OFF."""
        return self._gateway_status is not None

    @property
    def extra_state_attributes(self):
        """Return the state attributes."""
        return {
            "gateway_status": self._gateway_status,
            "neviweb_occupancyMode": self._occupancyMode,
            "local_sync": self._sync,
            "sku": self._sku,
            "id": self._id,
        }

    @property
    def state(self):
        """Return the state of the sensor."""
        return self._gateway_status

    def set_neviweb_status(self, value):
        """Set Neviweb global mode away or home."""
        mode = value["mode"]
        entity = value["id"]
        self._client.post_neviweb_status(entity, str(self._location), mode)
        self._occupancyMode = mode


class NeviwebDailyRequestSensor(Entity):
    """Internal sensor : Number of daily requests to Neviweb."""

    def __init__(self, hass):
        """Initialize."""
        self._hass = hass
        self._attr_name = "Neviweb Daily Requests"
        self._attr_unique_id = f"{DOMAIN}_daily_requests"
        self._notified = False

    @property
    def name(self):
        """Return device name."""
        return self._attr_name

    @property
    def unique_id(self):
        """Return device unique_id."""
        return self._attr_unique_id

    @property
    def state(self):
        """Return total daily requests."""
        return get_daily_request_count(self._hass)

    @property
    def icon(self):
        """Return device icon."""
        return "mdi:counter"

    @property
    def extra_state_attributes(self):
        """Return device extra state attributes."""
        data = self._hass.data[DOMAIN]["request_data"]
        return {
            "date": data["date"],
            "limit": 30000,
        }

    def update(self):
        """Send notification if we reach limit for request."""
        count = get_daily_request_count(self._hass)

        # Secure limit for notification
        if count > 25000 and not self._notified:
            self._notified = True

            asyncio.run_coroutine_threadsafe(
                self._hass.services.async_call(
                    "persistent_notification",
                    "create",
                    {
                        "title": "Neviweb",
                        "message": f"Warning : {count} today request. Limit : 30000.",
                    },
                ),
                self._hass.loop,
            )

        # Reset du flag si on change de jour
        data = self._hass.data[DOMAIN]["request_data"]
        today = datetime.date.today().isoformat()

        if data["date"] != today:
            self._notified = False
