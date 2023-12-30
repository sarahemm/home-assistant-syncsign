"""A sensor platform which reports connected status for SyncSign devices."""
import logging

import syncsign
import voluptuous as vol

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import ATTR_ENTITY_ID
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_platform
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.entity import DeviceInfo, EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import ATTR_CONTENTS, DOMAIN, SERVICE_UPDATE_DISPLAY

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up syncsign connected binary sensor."""

    def device_setup():
        # add entities for devices (hubs, etc.)
        client = hass.data[DOMAIN][entry.entry_id]
        result = client.devices.list_devices()
        for device in result.body.get("data"):
            async_add_entities(
                [
                    SyncSignConnectedSensor(
                        client,
                        "device",
                        device["thingName"],
                        device["info"]["friendlyName"],
                        device,
                    )
                ],
                update_before_add=True,
            )

        # add entities for nodes (which connect to devices, displays etc.)
        result = client.nodes.list_nodes()
        for node in result.body.get("data"):
            async_add_entities(
                [
                    SyncSignConnectedSensor(
                        client, "node", node["nodeId"], node["name"], node
                    )
                ],
                update_before_add=True,
            )

    await hass.async_add_executor_job(device_setup)

    platform = entity_platform.async_get_current_platform()
    platform.async_register_entity_service(
        SERVICE_UPDATE_DISPLAY,
        {
            vol.Required(ATTR_CONTENTS): cv.string,
            vol.Required(ATTR_ENTITY_ID): cv.entity_ids,
        },
        "handle_update_display",
    )


class SyncSignConnectedSensor(BinarySensorEntity):
    """Binary sensor representing the connected status of SyncSign devices and nodes."""

    _attr_device_class = BinarySensorDeviceClass.CONNECTIVITY
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_icon = "mdi:wifi"

    def __init__(
        self,
        client: syncsign.client,
        thing_type: str,
        thing_id: str,
        friendly_name: str,
        raw_json: dict,
    ) -> None:
        """Initialize the binary sensor."""
        self._attr_name = "%s Connected" % friendly_name
        self._attr_unique_id = thing_id
        self._attr_is_on = False
        self._client = client
        self._type = thing_type

        if thing_type == "device":
            model = "Unknown"
            if raw_json["info"]["model"] == "mrd":
                model = "SyncSign Hub (mrd)"
            self._attr_device_info = DeviceInfo(
                identifiers={(DOMAIN, thing_id)},
                name=friendly_name,
                manufacturer="SyncSign",
                model=model,
                sw_version="%s+%s"
                % (
                    raw_json["info"]["version"]["systemVersion"],
                    raw_json["info"]["version"]["appVersion"],
                ),
                hw_version=raw_json["info"]["version"]["hardwareVersion"],
            )
        elif thing_type == "node":
            model = "Unknown"
            if raw_json["model"][0:3] == "D29":
                model = 'SyncSign 2.9" Display (%s)' % raw_json["model"]
            if raw_json["model"][0:3] == "D42":
                model = 'SyncSign 4.2" Display (%s)' % raw_json["model"]
            if raw_json["model"][0:3] == "D75":
                model = 'SyncSign 7.5" Display (%s)' % raw_json["model"]
            self._attr_device_info = DeviceInfo(
                identifiers={(DOMAIN, thing_id)},
                name=friendly_name,
                manufacturer="SyncSign",
                model=model,
                via_device=(DOMAIN, raw_json["thingName"]),
            )

    def update(self) -> None:
        """Update the state."""
        if self._type == "device":
            result = self._client.devices.get_device(self._attr_unique_id)
            self._attr_is_on = result.body.get("data")["network"]["connected"]
        elif self._type == "node":
            result = self._client.nodes.get_node(self._attr_unique_id)
            self._attr_is_on = result.body.get("data")["onlined"]

    def handle_update_display(self, contents: str) -> None:
        """Update the contents of the display."""
        renderer = self._client.display_render
        renderer.one_node_rendering(self._attr_unique_id, contents)
