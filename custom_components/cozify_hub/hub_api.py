"""Cozify HUB local API client with cloud authentication."""
from __future__ import annotations

import asyncio
import logging
from typing import Any

import aiohttp

_LOGGER = logging.getLogger(__name__)

CLOUD_BASE = "https://api.cozify.fi/ui/0.2"
HUB_BASE_PATH = "/cc/1.14"
DEFAULT_PORT = 8893
DEFAULT_TIMEOUT = 10


class CozifyHubError(Exception):
    """Base exception for Cozify HUB errors."""


class CozifyHubConnectionError(CozifyHubError):
    """Exception for connection errors."""


class CozifyHubAuthError(CozifyHubError):
    """Exception for authentication errors."""


class CozifyCloudAPI:
    """Cozify Cloud API client for authentication."""

    def __init__(self, session: aiohttp.ClientSession) -> None:
        self._session = session

    async def request_otp(self, email: str) -> None:
        """Request OTP to be sent to email."""
        try:
            async with asyncio.timeout(DEFAULT_TIMEOUT):
                async with self._session.get(
                    f"{CLOUD_BASE}/user/requestlogin",
                    params={"email": email},
                ) as resp:
                    resp.raise_for_status()
        except aiohttp.ClientError as err:
            raise CozifyHubConnectionError(f"Failed to request OTP: {err}") from err

    async def email_login(self, email: str, otp: str) -> str:
        """Login with email and OTP, return cloud token (JWT)."""
        try:
            async with asyncio.timeout(DEFAULT_TIMEOUT):
                async with self._session.post(
                    f"{CLOUD_BASE}/user/emaillogin",
                    data={"email": email, "password": otp},
                ) as resp:
                    if resp.status in (401, 403):
                        raise CozifyHubAuthError("Invalid OTP or email")
                    resp.raise_for_status()
                    token = await resp.text()
                    return token.strip().strip('"')
        except aiohttp.ClientError as err:
            raise CozifyHubConnectionError(f"Login failed: {err}") from err

    async def get_hub_keys(self, cloud_token: str) -> dict[str, str]:
        """Get hub_id -> hub_token mapping from cloud."""
        try:
            async with asyncio.timeout(DEFAULT_TIMEOUT):
                async with self._session.get(
                    f"{CLOUD_BASE}/user/hubkeys",
                    headers={"Authorization": cloud_token},
                ) as resp:
                    if resp.status in (401, 403):
                        raise CozifyHubAuthError("Invalid cloud token")
                    resp.raise_for_status()
                    return await resp.json(content_type=None)
        except aiohttp.ClientError as err:
            raise CozifyHubConnectionError(f"Failed to get hub keys: {err}") from err


class CozifyHubAPI:
    """Cozify HUB local REST API client."""

    def __init__(
        self,
        host: str,
        cloud_token: str,
        port: int = DEFAULT_PORT,
        session: aiohttp.ClientSession | None = None,
    ) -> None:
        self._host = host
        self._port = port
        self._cloud_token = cloud_token
        self._session = session
        self._own_session = session is None
        self._hub_url = f"http://{host}:{port}"
        self._api_url = f"http://{host}:{port}{HUB_BASE_PATH}"

    async def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession()
            self._own_session = True
        return self._session

    async def close(self) -> None:
        if self._own_session and self._session and not self._session.closed:
            await self._session.close()

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": self._cloud_token,
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    def update_token(self, cloud_token: str) -> None:
        """Update the cloud token."""
        self._cloud_token = cloud_token

    async def _get(self, path: str, use_api_base: bool = True) -> Any:
        session = await self._get_session()
        base = self._api_url if use_api_base else self._hub_url
        url = f"{base}{path}"
        try:
            async with asyncio.timeout(DEFAULT_TIMEOUT):
                async with session.get(url, headers=self._headers()) as resp:
                    if resp.status in (401, 403):
                        raise CozifyHubAuthError("Invalid or expired token")
                    resp.raise_for_status()
                    data = await resp.json(content_type=None)
                    if isinstance(data, dict) and data.get("code") == 1:
                        msg = data.get("message", "")
                        if "Authentication" in msg or "auth" in msg.lower():
                            raise CozifyHubAuthError(msg)
                    return data
        except asyncio.TimeoutError as err:
            raise CozifyHubConnectionError(f"Timeout connecting to {url}") from err
        except aiohttp.ClientError as err:
            raise CozifyHubConnectionError(f"Error connecting to {url}: {err}") from err

    async def _put(self, path: str, data: Any) -> Any:
        session = await self._get_session()
        url = f"{self._api_url}{path}"
        try:
            async with asyncio.timeout(DEFAULT_TIMEOUT):
                async with session.put(
                    url, headers=self._headers(), json=data
                ) as resp:
                    if resp.status in (401, 403):
                        raise CozifyHubAuthError("Invalid or expired token")
                    resp.raise_for_status()
                    text = await resp.text()
                    if text:
                        return await resp.json(content_type=None)
                    return None
        except asyncio.TimeoutError as err:
            raise CozifyHubConnectionError(f"Timeout connecting to {url}") from err
        except aiohttp.ClientError as err:
            raise CozifyHubConnectionError(f"Error connecting to {url}: {err}") from err

    async def get_hub_info(self) -> dict[str, Any]:
        """Return hub info — public endpoint, no auth needed."""
        return await self._get("/hub", use_api_base=False)

    async def get_devices(self) -> dict[str, Any]:
        """Return all devices from the hub."""
        return await self._get("/devices")

    async def ping(self) -> bool:
        """Ping the hub using the public /hub endpoint."""
        try:
            await self._get("/hub", use_api_base=False)
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
