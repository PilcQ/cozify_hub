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
    3. Enter hub local IP address → hub identified by IP, entry created
    """

    VERSION = 2

    def __init__(self) -> None:
        self._email: str | None = None
        self._cloud_token: str | None = None
        self._hub_keys: dict[str, str] = {}  # hub_id -> hub_token

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

                self._hub_keys = await auth.get_hub_keys(self._cloud_token)
                _LOGGER.debug("Got %d hub keys", len(self._hub_keys))

                if not self._hub_keys:
                    errors["base"] = "no_hubs"
                else:
                    return await self.async_step_hub_ip()

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

    async def async_step_hub_ip(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Step 3: ask for hub local IP address, identify hub by connecting to it."""
        errors: dict[str, str] = {}

        if user_input is not None:
            hub_ip = user_input["hub_ip"].strip()
            session = async_get_clientsession(self.hass)
            auth = CozifyHubAuth(session, API_ENVIRONMENT_PRODUCTION)

            # Try each hub token until one works with this IP
            for hub_id, hub_token in self._hub_keys.items():
                try:
                    info = await auth.get_hub_info_local(hub_ip, hub_token)
                    if info.get("reachable"):
                        hub_name = info.get("name", f"Cozify HUB ({hub_id[:8]})")
                        _LOGGER.debug("Hub identified: %s at %s", hub_name, hub_ip)
                        return await self._create_entry(hub_id, hub_token, hub_name, hub_ip)
                except Exception as err:
                    _LOGGER.debug("Token %s failed for %s: %s", hub_id[:8], hub_ip, err)

            errors["base"] = "cannot_connect"

        return self.async_show_form(
            step_id="hub_ip",
            data_schema=vol.Schema({
                vol.Required("hub_ip"): str,
            }),
            errors=errors,
        )

    async def _create_entry(
        self, hub_id: str, hub_token: str, hub_name: str, hub_ip: str
    ) -> ConfigFlowResult:
        """Create the config entry."""
        await self.async_set_unique_id(hub_id)
        self._abort_if_unique_id_configured()
        return self.async_create_entry(
            title=hub_name,
            data={
                CONF_CONNECTION_MODE: CONNECTION_MODE_LOCAL,
                CONF_API_ENVIRONMENT: API_ENVIRONMENT_PRODUCTION,
                CONF_EMAIL: self._email,
                CONF_CLOUD_TOKEN: self._cloud_token,
                CONF_HUB_ID: hub_id,
                CONF_HUB_TOKEN: hub_token,
                CONF_HUB_NAME: hub_name,
                CONF_HUB_HOST: hub_ip,
            },
        )
