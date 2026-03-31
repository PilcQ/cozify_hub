"""Cover platform for Cozify HUB."""
from __future__ import annotations

from typing import Any

from homeassistant.components.cover import (
    CoverDeviceClass, CoverEntity, CoverEntityFeature,
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
        if any(c in caps for c in ("BLINDS", "LIFT", "SHUTTER")):
            entities.append(CozifyHubCover(coordinator, device_id))
    async_add_entities(entities)


class CozifyHubCover(CozifyHubEntity, CoverEntity):
    """Cozify HUB cover."""

    _attr_device_class = CoverDeviceClass.BLIND

    def __init__(self, coordinator: CozifyHubCoordinator, device_id: str) -> None:
        super().__init__(coordinator, device_id)
        self._attr_unique_id = device_id
        self._attr_name = self._device.get("name", device_id)
        caps = self._device.get("capabilities", [])
        features = (CoverEntityFeature.OPEN | CoverEntityFeature.CLOSE |
                    CoverEntityFeature.SET_POSITION)
        if "TILT" in caps:
            features |= CoverEntityFeature.SET_TILT_POSITION
        self._attr_supported_features = features

    @property
    def current_cover_position(self) -> int | None:
        lift = self._device.get("lift_pct")
        if lift is not None:
            return int(lift)
        pos = self._device.get("position")
        return int(pos * 100) if pos is not None else None

    @property
    def current_cover_tilt_position(self) -> int | None:
        return self._device.get("tilt_pct")

    @property
    def is_closed(self) -> bool | None:
        pos = self.current_cover_position
        return pos == 0 if pos is not None else None

    async def async_open_cover(self, **kwargs: Any) -> None:
        await self.coordinator.api.set_cover_position(self._device_id, 1.0)
        await self.coordinator.async_request_refresh()

    async def async_close_cover(self, **kwargs: Any) -> None:
        await self.coordinator.api.set_cover_position(self._device_id, 0.0)
        await self.coordinator.async_request_refresh()

    async def async_set_cover_position(self, **kwargs: Any) -> None:
        await self.coordinator.api.set_cover_position(self._device_id, kwargs["position"] / 100)
        await self.coordinator.async_request_refresh()

    async def async_set_cover_tilt_position(self, **kwargs: Any) -> None:
        await self.coordinator.api.set_cover_tilt(self._device_id, kwargs["tilt_position"])
        await self.coordinator.async_request_refresh()
