"""Config flow for Cozify HUB."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol
from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import CozifyHubAuth, CozifyHubAuthError, CozifyHubConnectionError
from .const import (
    API_ENVIRONMENT_PRODUCTION,
    CONF_API_ENVIRONMENT,
    CONF_CLOUD_TOKEN,
    CONF_CONNECTION_MODE,
    CONF_EMAIL,
    CONF_HUB_HOST,
    CONF_HUB_ID,
    CONF_HUB_NAME,
    CONF_HUB_TOKEN,
    CONNECTION_MODE_LOCAL,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)


class CozifyHubConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle config flow for Cozify HUB.

    Setup flow:
    1. Email → OTP sent to email
    2. OTP → cloud login, hub tokens + LAN IPs fetched automatically
    3. Select HUB (if multiple)
    4. Confirm or enter IP address
    """

    VERSION = 2

    def __init__(self) -> None:
        self._email: str | None = None
        self._cloud_token: str | None = None
        self._hubs: dict[str, dict[str, Any]] = {}
        self._selected_hub_id: str | None = None

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Step 1: ask for email address."""
        errors: dict[str, str] = {}

        if user_input is not None:
            email = user_input["email"]
            session = async_get_clientsession(self.hass)
            auth = CozifyHubAuth(session, API_ENVIRONMENT_PRODUCTION)
            try:
                await auth.request_otp(email)
                self._email = email
                return await self.async_step_otp()
            except CozifyHubConnectionError as err:
                _LOGGER.error("OTP request failed: %s", err)
                errors["base"] = "cannot_connect"
            except Exception as err:
                _LOGGER.exception("Unexpected error: %s", err)
                errors["base"] = "unknown"

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({vol.Required("email"): str}),
            errors=errors,
        )

    async def async_step_otp(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Step 2: enter OTP."""
        errors: dict[str, str] = {}

        if user_input is not None:
            otp = user_input["otp"]
            session = async_get_clientsession(self.hass)
            auth = CozifyHubAuth(session, API_ENVIRONMENT_PRODUCTION)
            try:
                self._cloud_token = await auth.verify_otp(self._email, otp)
                _LOGGER.debug("Cloud login successful")

                hub_keys = await auth.get_hub_keys(self._cloud_token)
                _LOGGER.debug("Found hubs: %s", list(hub_keys.keys()))

                # Get LAN IPs — returned in same order as hub_keys
                lan_ips: list[str] = []
                try:
                    lan_ips = await auth.get_hub_lan_ips(self._cloud_token)
                    _LOGGER.debug("LAN IPs from cloud: %s", lan_ips)
                except Exception as err:
                    _LOGGER.debug("LAN IP discovery failed: %s", err)

                # Build hub list — IP index matches hub_keys order
                self._hubs = {}
                for i, (hub_id, hub_token) in enumerate(hub_keys.items()):
                    lan_ip = lan_ips[i] if i < len(lan_ips) else None
                    name = f"Cozify HUB ({hub_id[:8]})"
                    try:
                        info = await auth.get_hub_info_cloud(self._cloud_token, hub_token)
                        name = info.get("name", name)
                    except Exception as err:
                        _LOGGER.debug("Cloud info failed for %s: %s", hub_id[:8], err)

                    self._hubs[hub_id] = {
                        "token": hub_token,
                        "name": name,
                        "lan_ip": lan_ip,
                    }
                    _LOGGER.debug("Hub %s: name=%s lan_ip=%s", hub_id[:8], name, lan_ip)

                if not self._hubs:
                    errors["base"] = "no_hubs"
                elif len(self._hubs) == 1:
                    self._selected_hub_id = list(self._hubs.keys())[0]
                    return await self.async_step_hub_ip()
                else:
                    return await self.async_step_select_hub()

            except CozifyHubAuthError:
                errors["base"] = "invalid_auth"
            except CozifyHubConnectionError as err:
                _LOGGER.error("Connection error: %s", err)
                errors["base"] = "cannot_connect"
            except Exception as err:
                _LOGGER.exception("Unexpected error: %s", err)
                errors["base"] = "unknown"

        return self.async_show_form(
            step_id="otp",
            data_schema=vol.Schema({vol.Required("otp"): str}),
            errors=errors,
            description_placeholders={"email": self._email or ""},
        )

    async def async_step_select_hub(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Step 3 (optional): select hub if multiple."""
        if user_input is not None:
            self._selected_hub_id = user_input["hub"]
            return await self.async_step_hub_ip()

        def _label(hub_id: str, info: dict) -> str:
            if info.get("lan_ip"):
                return f"{info['name']} — {info['lan_ip']} — Paikallinen"
            return f"{info['name']} — Ei paikallista IP:tä — Vain pilvi"

        return self.async_show_form(
            step_id="select_hub",
            data_schema=vol.Schema({
                vol.Required("hub"): vol.In({
                    hub_id: _label(hub_id, info)
                    for hub_id, info in self._hubs.items()
                })
            }),
        )

    async def async_step_hub_ip(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Step 4: confirm or enter hub IP address."""
        errors: dict[str, str] = {}
        hub_info = self._hubs[self._selected_hub_id]

        if user_input is not None:
            hub_ip = user_input["hub_ip"].strip()
            verified = await self._verify_hub_ip(hub_ip, hub_info["token"])
            if verified:
                return await self._create_entry(self._selected_hub_id, hub_ip)
            errors["base"] = "cannot_connect"

        return self.async_show_form(
            step_id="hub_ip",
            data_schema=vol.Schema({
                vol.Required("hub_ip", default=hub_info.get("lan_ip") or ""): str,
            }),
            errors=errors,
            description_placeholders={"hub_name": hub_info["name"]},
        )

    async def _verify_hub_ip(self, hub_ip: str, hub_token: str) -> bool:
        """Test local connection to hub."""
        session = async_get_clientsession(self.hass)
        auth = CozifyHubAuth(session, API_ENVIRONMENT_PRODUCTION)
        try:
            info = await auth.get_hub_info_local(hub_ip, hub_token)
            reachable = info.get("reachable", False)
            _LOGGER.debug("Hub at %s reachable: %s", hub_ip, reachable)
            return reachable
        except Exception as err:
            _LOGGER.debug("Hub IP verification failed for %s: %s", hub_ip, err)
            return False

    async def _create_entry(self, hub_id: str, hub_ip: str) -> ConfigFlowResult:
        """Create the config entry."""
        hub_info = self._hubs[hub_id]
        await self.async_set_unique_id(hub_id)
        self._abort_if_unique_id_configured()
        return self.async_create_entry(
            title=hub_info["name"],
            data={
                CONF_CONNECTION_MODE: CONNECTION_MODE_LOCAL,
                CONF_API_ENVIRONMENT: API_ENVIRONMENT_PRODUCTION,
                CONF_EMAIL: self._email,
                CONF_CLOUD_TOKEN: self._cloud_token,
                CONF_HUB_ID: hub_id,
                CONF_HUB_TOKEN: hub_info["token"],
                CONF_HUB_NAME: hub_info["name"],
                CONF_HUB_HOST: hub_ip,
            },
        )