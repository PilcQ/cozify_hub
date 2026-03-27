"""Light platform for Cozify HUB."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.light import (
    ATTR_BRIGHTNESS,
    ATTR_COLOR_TEMP_KELVIN,
    ATTR_HS_COLOR,
    ColorMode,
    LightEntity,
    LightEntityFeature,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import CozifyHubConfigEntry
from .const import CAP_BRIGHTNESS, CAP_COLOR_HS, CAP_COLOR_TEMP, CAP_ON_OFF
from .coordinator import CozifyHubCoordinator
from .entity import CozifyHubEntity

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: CozifyHubConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Cozify HUB lights."""
    coordinator = entry.runtime_data

    entities = []
    for device_id, device in coordinator.data.items():
        caps = device.get("capabilities", {}).get("values", [])
        if CAP_ON_OFF in caps and (
            CAP_BRIGHTNESS in caps or CAP_COLOR_HS in caps or CAP_COLOR_TEMP in caps
            or device.get("type", "").lower() in ("light", "dimmer", "rgb", "rgbw")
        ):
            entities.append(CozifyHubLight(coordinator, device_id))

    async_add_entities(entities)


class CozifyHubLight(CozifyHubEntity, LightEntity):
    """Representation of a Cozify HUB light."""

    _attr_name = None

    def __init__(self, coordinator: CozifyHubCoordinator, device_id: str) -> None:
        super().__init__(coordinator, device_id)
        caps = self.device_data.get("capabilities", {}).get("values", [])
        self._update_color_modes(caps)

    def _update_color_modes(self, caps: list[str]) -> None:
        """Determine supported color modes from capabilities."""
        modes: set[ColorMode] = set()
        if CAP_COLOR_HS in caps:
            modes.add(ColorMode.HS)
        if CAP_COLOR_TEMP in caps:
            modes.add(ColorMode.COLOR_TEMP)
        if CAP_BRIGHTNESS in caps and not modes:
            modes.add(ColorMode.BRIGHTNESS)
        if not modes:
            modes.add(ColorMode.ONOFF)
        self._attr_supported_color_modes = modes
        # Set default color mode
        if ColorMode.HS in modes:
            self._attr_color_mode = ColorMode.HS
        elif ColorMode.COLOR_TEMP in modes:
            self._attr_color_mode = ColorMode.COLOR_TEMP
        elif ColorMode.BRIGHTNESS in modes:
            self._attr_color_mode = ColorMode.BRIGHTNESS
        else:
            self._attr_color_mode = ColorMode.ONOFF

    @property
    def is_on(self) -> bool | None:
        state = self.device_data.get("state", {})
        return state.get("isOn")

    @property
    def brightness(self) -> int | None:
        state = self.device_data.get("state", {})
        bri = state.get("brightness")
        if bri is not None:
            return round(bri / 100 * 255)
        return None

    @property
    def hs_color(self) -> tuple[float, float] | None:
        state = self.device_data.get("state", {})
        color = state.get("color")
        if color:
            return (color.get("hue", 0), color.get("saturation", 0))
        return None

    @property
    def color_temp_kelvin(self) -> int | None:
        state = self.device_data.get("state", {})
        return state.get("colorTemperature")

    @property
    def min_color_temp_kelvin(self) -> int:
        return 2700

    @property
    def max_color_temp_kelvin(self) -> int:
        return 6500

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn on the light."""
        api = self.coordinator.api
        await api.device_on(self._device_id)

        if ATTR_BRIGHTNESS in kwargs:
            bri = round(kwargs[ATTR_BRIGHTNESS] / 255 * 100)
            await api.set_brightness(self._device_id, bri)

        if ATTR_HS_COLOR in kwargs:
            h, s = kwargs[ATTR_HS_COLOR]
            await api.set_color(self._device_id, h, s)

        if ATTR_COLOR_TEMP_KELVIN in kwargs:
            await api.set_color_temp(self._device_id, kwargs[ATTR_COLOR_TEMP_KELVIN])

        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn off the light."""
        await self.coordinator.api.device_off(self._device_id)
        await self.coordinator.async_request_refresh()
