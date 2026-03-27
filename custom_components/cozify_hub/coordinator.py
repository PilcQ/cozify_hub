"""Data update coordinator for Cozify HUB."""
from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any

import aiohttp
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import CONF_CLOUD_TOKEN, CONF_EMAIL, DEFAULT_SCAN_INTERVAL, DOMAIN
from .hub_api import CozifyCloudAPI, CozifyHubAPI, CozifyHubAuthError, CozifyHubConnectionError, CozifyHubError

_LOGGER = logging.getLogger(__name__)


class CozifyHubCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Coordinator to manage polling the Cozify HUB."""

    def __init__(
        self,
        hass: HomeAssistant,
        api: CozifyHubAPI,
        entry: ConfigEntry,
    ) -> None:
        self.api = api
        self._entry = entry
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=DEFAULT_SCAN_INTERVAL),
        )

    async def _async_refresh_token(self) -> bool:
        """Re-authenticate and get a fresh cloud token."""
        email = self._entry.data.get(CONF_EMAIL)
        if not email:
            _LOGGER.error("No email stored, cannot refresh token")
            return False

        _LOGGER.warning("Cloud token expired, attempting re-authentication for %s", email)
        try:
            session = aiohttp.ClientSession()
            cloud = CozifyCloudAPI(session)
            await cloud.request_otp(email)
            await session.close()
            _LOGGER.warning(
                "Token expired — an OTP has been sent to %s. "
                "Please re-add the Cozify HUB integration to enter the new OTP.",
                email,
            )
        except Exception as err:
            _LOGGER.error("Failed to request new OTP: %s", err)
        return False

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch device data from the hub."""
        try:
            devices = await self.api.get_devices()
            return devices if isinstance(devices, dict) else {}
        except CozifyHubAuthError as err:
            _LOGGER.warning("Auth error fetching devices: %s — token may have expired", err)
            await self._async_refresh_token()
            raise UpdateFailed(
                f"Authentication failed. Please re-add the integration: {err}"
            ) from err
        except CozifyHubConnectionError as err:
            raise UpdateFailed(f"Cannot connect to Cozify HUB: {err}") from err
        except CozifyHubError as err:
            raise UpdateFailed(f"Cozify HUB error: {err}") from err