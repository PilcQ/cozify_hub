"""Data update coordinator for Cozify HUB."""
from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DEFAULT_SCAN_INTERVAL, DOMAIN
from .hub_api import CozifyHubAPI, CozifyHubConnectionError, CozifyHubError

_LOGGER = logging.getLogger(__name__)


class CozifyHubCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Coordinator to manage polling the Cozify HUB."""

    def __init__(self, hass: HomeAssistant, api: CozifyHubAPI) -> None:
        self.api = api
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=DEFAULT_SCAN_INTERVAL),
        )

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch device data from the hub."""
        try:
            devices = await self.api.get_devices()
            return devices if isinstance(devices, dict) else {}
        except CozifyHubConnectionError as err:
            raise UpdateFailed(f"Cannot connect to Cozify HUB: {err}") from err
        except CozifyHubError as err:
            raise UpdateFailed(f"Cozify HUB error: {err}") from err
