"""Config flow for Cozify HUB integration."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol
from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.const import CONF_HOST, CONF_PORT, CONF_TOKEN

from .const import CONF_HUB_HOST, CONF_HUB_PORT, CONF_HUB_TOKEN, DEFAULT_PORT, DOMAIN
from .hub_api import CozifyHubAPI, CozifyHubAuthError, CozifyHubConnectionError

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_HUB_HOST): str,
        vol.Required(CONF_HUB_TOKEN): str,
        vol.Optional(CONF_HUB_PORT, default=DEFAULT_PORT): int,
    }
)


class CozifyHubConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Cozify HUB."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            host = user_input[CONF_HUB_HOST]
            token = user_input[CONF_HUB_TOKEN]
            port = user_input.get(CONF_HUB_PORT, DEFAULT_PORT)

            # Unique ID based on host
            await self.async_set_unique_id(host)
            self._abort_if_unique_id_configured()

            api = CozifyHubAPI(host=host, hub_token=token, port=port)
            try:
                hub_info = await api.get_hub_info()
                hub_name = hub_info.get("name", f"Cozify HUB ({host})")
            except CozifyHubAuthError:
                errors["base"] = "invalid_auth"
            except CozifyHubConnectionError:
                errors["base"] = "cannot_connect"
            except Exception:
                _LOGGER.exception("Unexpected error connecting to Cozify HUB")
                errors["base"] = "unknown"
            else:
                await api.close()
                return self.async_create_entry(
                    title=hub_name,
                    data={
                        CONF_HUB_HOST: host,
                        CONF_HUB_TOKEN: token,
                        CONF_HUB_PORT: port,
                    },
                )
            await api.close()

        return self.async_show_form(
            step_id="user",
            data_schema=STEP_USER_DATA_SCHEMA,
            errors=errors,
        )
