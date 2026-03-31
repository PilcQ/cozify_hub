"""Cozify HUB integration — supports ION, ZEN, DIN."""
from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import CozifyHubApi
from .const import (
    API_ENVIRONMENT_PRODUCTION,
    CONF_API_ENVIRONMENT,
    CONF_CLOUD_TOKEN,
    CONF_CONNECTION_MODE,
    CONF_HUB_HOST,
    CONF_HUB_NAME,
    CONF_HUB_TOKEN,
    CONNECTION_MODE_CLOUD,
    CONNECTION_MODE_LOCAL,
    DOMAIN,
    PLATFORMS,
)
from .coordinator import CozifyHubCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Cozify HUB."""
    session = async_get_clientsession(hass)
    connection_mode = entry.data.get(CONF_CONNECTION_MODE, CONNECTION_MODE_LOCAL)
    api_environment = entry.data.get(CONF_API_ENVIRONMENT, API_ENVIRONMENT_PRODUCTION)

    if connection_mode == CONNECTION_MODE_LOCAL:
        api = CozifyHubApi(
            session=session,
            hub_token=entry.data[CONF_HUB_TOKEN],
            connection_mode=CONNECTION_MODE_LOCAL,
            hub_host=entry.data[CONF_HUB_HOST],
            api_environment=api_environment,
        )
    else:
        api = CozifyHubApi(
            session=session,
            hub_token=entry.data[CONF_HUB_TOKEN],
            connection_mode=CONNECTION_MODE_CLOUD,
            cloud_token=entry.data[CONF_CLOUD_TOKEN],
            api_environment=api_environment,
        )

    coordinator = CozifyHubCoordinator(
        hass, api,
        hub_name=entry.data.get(CONF_HUB_NAME, "Cozify HUB"),
        connection_mode=connection_mode,
        entry=entry,
    )

    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload Cozify HUB."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id)
    return unload_ok
