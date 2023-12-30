"""The SyncSign eInk Display Integration integration."""
from __future__ import annotations

import syncsign.client

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady

from .const import DOMAIN

PLATFORMS: list[Platform] = [Platform.BINARY_SENSOR]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up SyncSign eInk Display Integration from a config entry."""

    hass.data.setdefault(DOMAIN, {})

    def api_setup(api_key: str) -> bool:
        try:
            hass.data[DOMAIN][entry.entry_id] = syncsign.client.Client(api_key=api_key)

        except ConnectionError as err:
            raise ConfigEntryNotReady("Config entry not yet ready") from err

        return True

    await hass.async_add_executor_job(api_setup, entry.data["api_key"])

    hass.config_entries.async_setup_platforms(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok
