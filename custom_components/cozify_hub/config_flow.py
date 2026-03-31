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
    2. OTP → cloud login, hub tokens fetched
    3. Enter hub local IP address
    4. (optional) Select hub if account has multiple hubs
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
        """Step 2: enter OTP, fetch hub tokens from cloud."""
        errors: dict[str, str] = {}

        if user_input is not None:
            otp = user_input["otp"]
            session = async_get_clientsession(self.hass)
            auth = CozifyHubAuth(session, API_ENVIRONMENT_PRODUCTION)
            try:
                self._cloud_token = await auth.verify_otp(self._email, otp)
                _LOGGER.debug("Cloud login successful")

                hub_keys = await auth.get_hub_keys(self._cloud_token)
                _LOGGER.debug("Found hub keys: %s", list(hub_keys.keys()))

                # Get name for each hub from cloud
                self._hubs = {}
                for hub_id, hub_token in hub_keys.items():
                    name = f"Cozify HUB ({hub_id[:8]})"
                    try:
                        info = await auth.get_hub_info_cloud(self._cloud_token, hub_token)
                        name = info.get("name", name)
                    except Exception as err:
                        _LOGGER.debug("Cloud info failed for %s: %s", hub_id[:8], err)
                    self._hubs[hub_id] = {
                        "token": hub_token,
                        "name": name,
                    }
                    _LOGGER.debug("Hub %s: %s", hub_id[:8], name)

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
        """Step 3a (optional): select hub if multiple on account."""
        if user_input is not None:
            self._selected_hub_id = user_input["hub"]
            return await self.async_step_hub_ip()

        return self.async_show_form(
            step_id="select_hub",
            data_schema=vol.Schema({
                vol.Required("hub"): vol.In({
                    hub_id: info["name"]
                    for hub_id, info in self._hubs.items()
                })
            }),
        )

    async def async_step_hub_ip(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Step 3b: ask for hub local IP address."""
        errors: dict[str, str] = {}
        hub_info = self._hubs[self._selected_hub_id]

        if user_input is not None:
            hub_ip = user_input["hub_ip"].strip()
            session = async_get_clientsession(self.hass)
            auth = CozifyHubAuth(session, API_ENVIRONMENT_PRODUCTION)
            try:
                info = await auth.get_hub_info_local(hub_ip, hub_info["token"])
                if info.get("reachable"):
                    return await self._create_entry(self._selected_hub_id, hub_ip)
                else:
                    errors["base"] = "cannot_connect"
            except Exception as err:
                _LOGGER.error("Hub IP check failed for %s: %s", hub_ip, err)
                errors["base"] = "cannot_connect"

        return self.async_show_form(
            step_id="hub_ip",
            data_schema=vol.Schema({
                vol.Required("hub_ip"): str,
            }),
            errors=errors,
            description_placeholders={"hub_name": hub_info["name"]},
        )

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