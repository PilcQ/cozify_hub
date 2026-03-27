"""Config flow for Cozify HUB integration."""
from __future__ import annotations

import logging
from typing import Any

import aiohttp
import voluptuous as vol
from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.const import CONF_EMAIL

from .const import CONF_CLOUD_TOKEN, CONF_HUB_HOST, CONF_HUB_ID, CONF_HUB_PORT, CONF_HUB_TOKEN, DEFAULT_PORT, DOMAIN
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
                hub_url = f"http://{self._host}:{self._port}/hub"
                _LOGGER.debug("Testing hub connectivity at %s", hub_url)
                async with session.get(hub_url, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                    if resp.status != 200:
                        errors["base"] = "cannot_connect"
                    else:
                        cloud = CozifyCloudAPI(session)
                        await cloud.request_otp(self._email)
                        return await self.async_step_otp()
            except aiohttp.ClientError as err:
                _LOGGER.error("Cannot connect to hub: %s", err)
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

                # Step 1: get cloud token
                _LOGGER.debug("Logging in with email+OTP")
                cloud_token = await cloud.email_login(self._email, otp)
                _LOGGER.debug("Cloud login successful")

                # Step 2: get hub-specific token from cloud
                _LOGGER.debug("Fetching hub keys from cloud")
                hub_keys = await cloud.get_hub_keys(cloud_token)
                _LOGGER.debug("Hub keys received: %s", list(hub_keys.keys()))

                # Step 3: get hub info to find hub_id and name
                # Use cloud token for /hub (public endpoint needs no auth)
                api = CozifyHubAPI(
                    host=self._host,
                    cloud_token=cloud_token,
                    port=self._port,
                    session=session,
                )
                hub_info = await api.get_hub_info()
                hub_id = hub_info.get("hubId", self._host)
                hub_name = hub_info.get("name", f"Cozify HUB ({self._host})")
                _LOGGER.debug("Hub ID: %s, Name: %s", hub_id, hub_name)

                # Step 4: get the hub-specific token for this hub
                hub_token = hub_keys.get(hub_id)
                if not hub_token and hub_keys:
                    hub_token = next(iter(hub_keys.values()))
                    _LOGGER.warning("Hub ID not in keys, using first available key")

                if not hub_token:
                    _LOGGER.error("No hub token found in keys: %s", hub_keys)
                    errors["base"] = "invalid_auth"
                else:
                    # Step 5: verify hub token works for /devices
                    _LOGGER.debug("Testing hub token against /devices")
                    api.update_token(hub_token)
                    devices = await api.get_devices()
                    _LOGGER.debug("Devices fetched successfully: %s devices", len(devices))

                    await self.async_set_unique_id(hub_id)
                    self._abort_if_unique_id_configured()

                    return self.async_create_entry(
                        title=hub_name,
                        data={
                            CONF_EMAIL: self._email,
                            CONF_HUB_HOST: self._host,
                            CONF_HUB_PORT: self._port,
                            CONF_CLOUD_TOKEN: cloud_token,
                            CONF_HUB_TOKEN: hub_token,
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
                _LOGGER.exception("Unexpected error: %s", err)
                errors["base"] = "unknown"
            finally:
                await session.close()

        return self.async_show_form(
            step_id="otp",
            data_schema=STEP_OTP_SCHEMA,
            errors=errors,
            description_placeholders={"email": self._email},
        )