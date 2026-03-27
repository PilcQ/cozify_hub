"""Cozify HUB local API client."""
from __future__ import annotations

import asyncio
import logging
from typing import Any

import aiohttp

_LOGGER = logging.getLogger(__name__)

BASE_PATH = "/cc/1.14"
DEFAULT_PORT = 8893
DEFAULT_TIMEOUT = 10


class CozifyHubError(Exception):
    """Base exception for Cozify HUB errors."""


class CozifyHubConnectionError(CozifyHubError):
    """Exception for connection errors."""


class CozifyHubAuthError(CozifyHubError):
    """Exception for authentication errors."""


class CozifyHubAPI:
    """Cozify HUB local REST API client."""

    def __init__(
        self,
        host: str,
        hub_token: str,
        port: int = DEFAULT_PORT,
        session: aiohttp.ClientSession | None = None,
    ) -> None:
        self._host = host
        self._port = port
        self._hub_token = hub_token
        self._session = session
        self._own_session = session is None
        self._base_url = f"http://{host}:{port}{BASE_PATH}"

    async def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession()
            self._own_session = True
        return self._session

    async def close(self) -> None:
        if self._own_session and self._session and not self._session.closed:
            await self._session.close()

    def _headers(self) -> dict[str, str]:
        return {"Content-Type": "application/json"}

    def _params(self, extra: dict | None = None) -> dict[str, str]:
        """Return query params including the hub token."""
        params = {"token": self._hub_token}
        if extra:
            params.update(extra)
        return params

    def _check_auth_error(self, data: Any) -> None:
        """Raise auth error if the hub returned an authentication failure."""
        if isinstance(data, dict) and data.get("code") == 1:
            msg = data.get("message", "")
            if "Authentication" in msg:
                raise CozifyHubAuthError(msg)

    async def _get(self, path: str) -> Any:
        session = await self._get_session()
        url = f"{self._base_url}{path}"
        try:
            async with asyncio.timeout(DEFAULT_TIMEOUT):
                async with session.get(
                    url, headers=self._headers(), params=self._params()
                ) as resp:
                    if resp.status == 401:
                        raise CozifyHubAuthError("Invalid hub token")
                    resp.raise_for_status()
                    data = await resp.json(content_type=None)
                    self._check_auth_error(data)
                    return data
        except asyncio.TimeoutError as err:
            raise CozifyHubConnectionError(f"Timeout connecting to {url}") from err
        except aiohttp.ClientError as err:
            raise CozifyHubConnectionError(f"Error connecting to {url}: {err}") from err

    async def _put(self, path: str, data: Any) -> Any:
        session = await self._get_session()
        url = f"{self._base_url}{path}"
        try:
            async with asyncio.timeout(DEFAULT_TIMEOUT):
                async with session.put(
                    url, headers=self._headers(), params=self._params(), json=data
                ) as resp:
                    if resp.status == 401:
                        raise CozifyHubAuthError("Invalid hub token")
                    resp.raise_for_status()
                    text = await resp.text()
                    if text:
                        result = await resp.json(content_type=None)
                        self._check_auth_error(result)
                        return result
                    return None
        except asyncio.TimeoutError as err:
            raise CozifyHubConnectionError(f"Timeout connecting to {url}") from err
        except aiohttp.ClientError as err:
            raise CozifyHubConnectionError(f"Error connecting to {url}: {err}") from err

    async def get_devices(self) -> dict[str, Any]:
        """Return all devices from the hub."""
        return await self._get("/devices")

    async def get_hub_info(self) -> dict[str, Any]:
        """Return hub information by fetching devices (no /hub endpoint)."""
        return await self._get("/devices")

    async def ping(self) -> bool:
        """Ping the hub to verify connectivity."""
        try:
            await self._get("/devices")
            return True
        except CozifyHubError:
            return False

    async def device_command(self, device_id: str, command: dict[str, Any]) -> None:
        """Send a command to a device."""
        await self._put(f"/devices/{device_id}/command", command)

    async def device_on(self, device_id: str) -> None:
        """Turn device on."""
        await self.device_command(device_id, {"isOn": True})

    async def device_off(self, device_id: str) -> None:
        """Turn device off."""
        await self.device_command(device_id, {"isOn": False})

    async def set_brightness(self, device_id: str, brightness: int) -> None:
        """Set brightness (0-100)."""
        await self.device_command(device_id, {"brightness": brightness})

    async def set_color_temp(self, device_id: str, color_temp: int) -> None:
        """Set color temperature in Kelvin."""
        await self.device_command(device_id, {"colorTemperature": color_temp})

    async def set_color(self, device_id: str, hue: float, saturation: float) -> None:
        """Set hue (0-360) and saturation (0-100)."""
        await self.device_command(
            device_id, {"color": {"hue": hue, "saturation": saturation}}
        )
