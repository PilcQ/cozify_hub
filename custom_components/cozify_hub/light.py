"""Light platform for Cozify HUB."""
from __future__ import annotations

import math
from typing import Any

from homeassistant.components.light import (
    ATTR_BRIGHTNESS,
    ATTR_COLOR_TEMP_KELVIN,
    ATTR_HS_COLOR,
    ColorMode,
    LightEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import CozifyHubCoordinator
from .entity import CozifyHubEntity


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry,
                             async_add_entities: AddEntitiesCallback) -> None:
    coordinator: CozifyHubCoordinator = hass.data[DOMAIN][entry.entry_id]
    entities = []
    for device_id, device in coordinator.data["devices"].items():
        caps = device.get("capabilities", [])
        dtype = device.get("type", "")
        if (dtype in ("LIGHT", "DIMMER") or
                any(c in caps for c in ("BRIGHTNESS", "COLOR_HS", "COLOR_TEMP"))):
            entities.append(CozifyHubLight(coordinator, device_id))
    async_add_entities(entities)


class CozifyHubLight(CozifyHubEntity, LightEntity):
    """Cozify HUB light."""

    _attr_min_color_temp_kelvin = 2000
    _attr_max_color_temp_kelvin = 6500

    def __init__(self, coordinator: CozifyHubCoordinator, device_id: str) -> None:
        super().__init__(coordinator, device_id)
        self._attr_unique_id = device_id
        self._attr_name = self._device.get("name", device_id)
        caps = self._device.get("capabilities", [])
        modes: set[ColorMode] = set()
        if "COLOR_HS" in caps:
            modes.add(ColorMode.HS)
        if "COLOR_TEMP" in caps:
            modes.add(ColorMode.COLOR_TEMP)
        if not modes and "BRIGHTNESS" in caps:
            modes.add(ColorMode.BRIGHTNESS)
        if not modes:
            modes.add(ColorMode.ONOFF)
        self._attr_supported_color_modes = modes
        if ColorMode.HS in modes:
            self._attr_color_mode = ColorMode.HS
        elif ColorMode.COLOR_TEMP in modes:
            self._attr_color_mode = ColorMode.COLOR_TEMP
        elif ColorMode.BRIGHTNESS in modes:
            self._attr_color_mode = ColorMode.BRIGHTNESS
        else:
            self._attr_color_mode = ColorMode.ONOFF

    @property
    def is_on(self) -> bool:
        return self._device.get("is_on", False)

    @property
    def brightness(self) -> int | None:
        b = self._device.get("brightness")
        return int(b * 255) if b is not None else None

    @property
    def hs_color(self) -> tuple[float, float] | None:
        hue = self._device.get("hue")
        sat = self._device.get("saturation")
        if hue is not None and sat is not None:
            return (hue * 180.0 / math.pi, sat * 100.0)
        return None

    @property
    def color_temp_kelvin(self) -> int | None:
        if self._device.get("color_mode") == "ct":
            return self._device.get("color_temperature")
        return None

    async def async_turn_on(self, **kwargs: Any) -> None:
        api = self.coordinator.api
        if ATTR_HS_COLOR in kwargs:
            h_deg, s_pct = kwargs[ATTR_HS_COLOR]
            h_rad = h_deg * math.pi / 180.0
            sat = s_pct / 100.0
            bri = kwargs[ATTR_BRIGHTNESS] / 255.0 if ATTR_BRIGHTNESS in kwargs else None
            await api.set_color_hs(self._device_id, h_rad, sat, bri)
        elif ATTR_COLOR_TEMP_KELVIN in kwargs:
            bri = kwargs[ATTR_BRIGHTNESS] / 255.0 if ATTR_BRIGHTNESS in kwargs else None
            await api.set_color_temperature(self._device_id, kwargs[ATTR_COLOR_TEMP_KELVIN], bri)
        elif ATTR_BRIGHTNESS in kwargs:
            await api.set_brightness(self._device_id, kwargs[ATTR_BRIGHTNESS] / 255.0)
        else:
            await api.turn_on(self._device_id)
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self.coordinator.api.turn_off(self._device_id)
        await self.coordinator.async_request_refresh()
