"""Config flow for Cozify HUB."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol
from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import CozifyHubAuth, CozifyHubApiError, CozifyHubAuthError
from .const import (
    API_ENVIRONMENT_DEVELOPMENT,
    API_ENVIRONMENT_PRODUCTION,
    CONF_API_ENVIRONMENT,
    CONF_CLOUD_TOKEN,
    CONF_CONNECTION_MODE,
    CONF_EMAIL,
    CONF_HUB_HOST,
    CONF_HUB_ID,
    CONF_HUB_NAME,
    CONF_HUB_TOKEN,
    CONNECTION_MODE_CLOUD,
    CONNECTION_MODE_LOCAL,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)


class CozifyHubConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle config flow for Cozify HUB."""

    VERSION = 2

    def __init__(self) -> None:
        self._connection_mode = CONNECTION_MODE_LOCAL
        self._api_environment = API_ENVIRONMENT_PRODUCTION
        self._email: str | None = None
        self._cloud_token: str | None = None
        self._hubs: dict[str, dict[str, Any]] = {}

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Step 1: choose connection mode."""
        if user_input is not None:
            self._connection_mode = user_input["connection_mode"]
            self._api_environment = user_input.get("api_environment", API_ENVIRONMENT_PRODUCTION)
            if self._connection_mode == CONNECTION_MODE_LOCAL:
                return await self.async_step_local()
            return await self.async_step_cloud_email()

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({
                vol.Required("connection_mode", default=CONNECTION_MODE_LOCAL): vol.In({
                    CONNECTION_MODE_LOCAL: "Local (direct to HUB on LAN)",
                    CONNECTION_MODE_CLOUD: "Cloud (via Cozify Cloud)",
                }),
                vol.Required("api_environment", default=API_ENVIRONMENT_PRODUCTION): vol.In({
                    API_ENVIRONMENT_PRODUCTION: "Production",
                    API_ENVIRONMENT_DEVELOPMENT: "Development",
                }),
            }),
        )

    # ── LOCAL MODE ──

    async def async_step_local(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Local: enter hub IP and token."""
        errors: dict[str, str] = {}

        if user_input is not None:
            hub_host = user_input["hub_host"]
            hub_token = user_input["hub_token"]
            session = async_get_clientsession(self.hass)
            auth = CozifyHubAuth(session, self._api_environment)
            try:
                info = await auth.get_hub_info_local(hub_host, hub_token)
                if not info.get("reachable"):
                    errors["base"] = "cannot_connect"
                elif not info.get("online"):
                    errors["base"] = "hub_offline"
                else:
                    hub_name = info.get("name", f"Cozify HUB ({hub_host})")
                    hub_id = info.get("hubId", hub_host)
                    await self.async_set_unique_id(hub_id)
                    self._abort_if_unique_id_configured()
                    return self.async_create_entry(
                        title=f"{hub_name} (Local)",
                        data={
                            CONF_CONNECTION_MODE: CONNECTION_MODE_LOCAL,
                            CONF_API_ENVIRONMENT: self._api_environment,
                            CONF_HUB_ID: hub_id,
                            CONF_HUB_TOKEN: hub_token,
                            CONF_HUB_NAME: hub_name,
                            CONF_HUB_HOST: hub_host,
                        },
                    )
            except Exception as err:
                _LOGGER.error("Local connection failed: %s", err)
                errors["base"] = "cannot_connect"

        return self.async_show_form(
            step_id="local",
            data_schema=vol.Schema({
                vol.Required("hub_host"): str,
                vol.Required("hub_token"): str,
            }),
            errors=errors,
        )

    # ── CLOUD MODE ──

    async def async_step_cloud_email(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Cloud: enter email."""
        errors: dict[str, str] = {}

        if user_input is not None:
            email = user_input["email"]
            session = async_get_clientsession(self.hass)
            auth = CozifyHubAuth(session, self._api_environment)
            try:
                await auth.request_otp(email)
                self._email = email
                return await self.async_step_cloud_otp()
            except Exception as err:
                _LOGGER.error("OTP request failed: %s", err)
                errors["base"] = "cannot_connect"

        return self.async_show_form(
            step_id="cloud_email",
            data_schema=vol.Schema({vol.Required("email"): str}),
            errors=errors,
        )

    async def async_step_cloud_otp(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Cloud: enter OTP."""
        errors: dict[str, str] = {}

        if user_input is not None:
            otp = user_input["otp"]
            session = async_get_clientsession(self.hass)
            auth = CozifyHubAuth(session, self._api_environment)
            try:
                self._cloud_token = await auth.verify_otp(self._email, otp)
                hub_keys = await auth.get_hub_keys(self._cloud_token)
                _LOGGER.debug("Hub keys: %s", list(hub_keys.keys()))

                for hub_id, hub_token in hub_keys.items():
                    info = await auth.get_hub_info_cloud(self._cloud_token, hub_token)
                    self._hubs[hub_id] = {
                        "token": hub_token,
                        "name": info.get("name", hub_id[:8]),
                        "online": info.get("online", False),
                    }

                if not self._hubs:
                    errors["base"] = "no_hubs"
                elif len(self._hubs) == 1:
                    hub_id = list(self._hubs.keys())[0]
                    return await self._create_cloud_entry(hub_id)
                else:
                    return await self.async_step_select_hub()

            except CozifyHubAuthError:
                errors["base"] = "invalid_auth"
            except Exception as err:
                _LOGGER.exception("OTP verification failed: %s", err)
                errors["base"] = "unknown"

        return self.async_show_form(
            step_id="cloud_otp",
            data_schema=vol.Schema({vol.Required("otp"): str}),
            errors=errors,
            description_placeholders={"email": self._email or ""},
        )

    async def async_step_select_hub(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Cloud: select which hub if multiple."""
        if user_input is not None:
            return await self._create_cloud_entry(user_input["hub"])

        return self.async_show_form(
            step_id="select_hub",
            data_schema=vol.Schema({
                vol.Required("hub"): vol.In({
                    hub_id: f"{info['name']} ({'Online' if info['online'] else 'Offline'})"
                    for hub_id, info in self._hubs.items()
                })
            }),
        )

    async def _create_cloud_entry(self, hub_id: str) -> ConfigFlowResult:
        hub_info = self._hubs[hub_id]
        await self.async_set_unique_id(hub_id)
        self._abort_if_unique_id_configured()
        return self.async_create_entry(
            title=f"{hub_info['name']} (Cloud)",
            data={
                CONF_CONNECTION_MODE: CONNECTION_MODE_CLOUD,
                CONF_API_ENVIRONMENT: self._api_environment,
                CONF_CLOUD_TOKEN: self._cloud_token,
                CONF_HUB_ID: hub_id,
                CONF_HUB_TOKEN: hub_info["token"],
                CONF_HUB_NAME: hub_info["name"],
                CONF_EMAIL: self._email,
            },
        )
