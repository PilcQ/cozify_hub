"""Cozify HUB integration for Home Assistant."""
from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import CONF_CLOUD_TOKEN, CONF_HUB_HOST, CONF_HUB_PORT, DEFAULT_PORT, DOMAIN, PLATFORMS
from .coordinator import CozifyHubCoordinator
from .hub_api import CozifyHubAPI

_LOGGER = logging.getLogger(__name__)

type CozifyHubConfigEntry = ConfigEntry[CozifyHubCoordinator]


async def async_setup_entry(hass: HomeAssistant, entry: CozifyHubConfigEntry) -> bool:
    """Set up Cozify HUB from a config entry."""
    host = entry.data[CONF_HUB_HOST]
    cloud_token = entry.data[CONF_CLOUD_TOKEN]
    port = entry.data.get(CONF_HUB_PORT, DEFAULT_PORT)

    api = CozifyHubAPI(host=host, cloud_token=cloud_token, port=port)
    coordinator = CozifyHubCoordinator(hass, api, entry)

    await coordinator.async_config_entry_first_refresh()

    entry.runtime_data = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: CozifyHubConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        await entry.runtime_data.api.close()
    return unload_ok