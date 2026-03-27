"""Config flow for Cozify HUB integration."""
from __future__ import annotations

import logging
from typing import Any

import aiohttp
import voluptuous as vol
from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.const import CONF_EMAIL

from .const import CONF_CLOUD_TOKEN, CONF_HUB_HOST, CONF_HUB_ID, CONF_HUB_PORT, DEFAULT_PORT, DOMAIN
from .hub_api import CozifyCloudAPI, CozifyHubAPI, CozifyHubAuthError, CozifyHubConnectionError

_LOGGER = logging.getLogger(__name__)

STEP_USER_SCHEMA = vol.Schema({
    vol.Required(CONF_EMAIL): str,
    vol.Required(CONF_HUB_HOST): str,
    vol.Optional(CONF_HUB_PORT, default=DEFAULT_PORT): int,
})

STEP_OTP_SCHEMA = vol.Schema({
    vol.Required("otp"): str,
})


class CozifyHubConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Cozify HUB."""

    VERSION = 1

    def __init__(self) -> None:
        self._email: str = ""
        self._host: str = ""
        self._port: int = DEFAULT_PORT

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Step 1: ask for email and hub IP."""
        errors: dict[str, str] = {}

        if user_input is not None:
            self._email = user_input[CONF_EMAIL]
            self._host = user_input[CONF_HUB_HOST]
            self._port = user_input.get(CONF_HUB_PORT, DEFAULT_PORT)

            session = aiohttp.ClientSession()
            try:
                # Test hub connectivity using the public /hub endpoint
                hub_url = f"http://{self._host}:{self._port}/hub"
                _LOGGER.debug("Testing hub connectivity at %s", hub_url)
                async with session.get(hub_url, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                    _LOGGER.debug("Hub ping response: %s", resp.status)
                    if resp.status != 200:
                        _LOGGER.error("Hub returned status %s", resp.status)
                        errors["base"] = "cannot_connect"
                    else:
                        # Hub reachable — request OTP
                        _LOGGER.debug("Hub reachable, requesting OTP for %s", self._email)
                        cloud = CozifyCloudAPI(session)
                        await cloud.request_otp(self._email)
                        _LOGGER.debug("OTP requested successfully")
                        return await self.async_step_otp()
            except aiohttp.ClientConnectorError as err:
                _LOGGER.error("Cannot connect to hub at %s:%s - %s", self._host, self._port, err)
                errors["base"] = "cannot_connect"
            except aiohttp.ClientError as err:
                _LOGGER.error("HTTP error connecting to hub: %s", err)
                errors["base"] = "cannot_connect"
            except CozifyHubConnectionError as err:
                _LOGGER.error("OTP request failed: %s", err)
                errors["base"] = "cannot_connect"
            except Exception as err:
                _LOGGER.exception("Unexpected error: %s", err)
                errors["base"] = "unknown"
            finally:
                await session.close()

        return self.async_show_form(
            step_id="user",
            data_schema=STEP_USER_SCHEMA,
            errors=errors,
            description_placeholders={
                "description": "Enter your Cozify account email and the local IP of your hub."
            },
        )

    async def async_step_otp(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Step 2: ask for OTP from email."""
        errors: dict[str, str] = {}

        if user_input is not None:
            otp = user_input["otp"]
            session = aiohttp.ClientSession()
            try:
                cloud = CozifyCloudAPI(session)
                _LOGGER.debug("Attempting email login for %s", self._email)
                cloud_token = await cloud.email_login(self._email, otp)
                _LOGGER.debug("Cloud login successful, got token")

                api = CozifyHubAPI(
                    host=self._host,
                    cloud_token=cloud_token,
                    port=self._port,
                    session=session,
                )
                hub_info = await api.get_hub_info()
                _LOGGER.debug("Hub info: %s", hub_info)
                hub_name = hub_info.get("name", f"Cozify HUB ({self._host})")
                hub_id = hub_info.get("hubId", self._host)

                await self.async_set_unique_id(hub_id)
                self._abort_if_unique_id_configured()

                return self.async_create_entry(
                    title=hub_name,
                    data={
                        CONF_EMAIL: self._email,
                        CONF_HUB_HOST: self._host,
                        CONF_HUB_PORT: self._port,
                        CONF_CLOUD_TOKEN: cloud_token,
                        CONF_HUB_ID: hub_id,
                    },
                )
            except CozifyHubAuthError as err:
                _LOGGER.error("Auth error: %s", err)
                errors["base"] = "invalid_auth"
            except CozifyHubConnectionError as err:
                _LOGGER.error("Connection error: %s", err)
                errors["base"] = "cannot_connect"
            except Exception as err:
                _LOGGER.exception("Unexpected error during OTP login: %s", err)
                errors["base"] = "unknown"
            finally:
                await session.close()

        return self.async_show_form(
            step_id="otp",
            data_schema=STEP_OTP_SCHEMA,
            errors=errors,
            description_placeholders={
                "email": self._email,
            },
        )