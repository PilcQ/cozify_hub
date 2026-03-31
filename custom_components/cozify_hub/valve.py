"""Valve platform for Cozify HUB."""
from __future__ import annotations

from typing import Any

from homeassistant.components.valve import ValveDeviceClass, ValveEntity, ValveEntityFeature
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import CozifyHubCoordinator
from .entity import CozifyHubEntity


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry,
                             async_add_entities: AddEntitiesCallback) -> None:
    coordinator: CozifyHubCoordinator = hass.data[DOMAIN][entry.entry_id]
    entities = [
        CozifyHubValve(coordinator, device_id)
        for device_id, device in coordinator.data["devices"].items()
        if "VALVE" in device.get("capabilities", [])
    ]
    async_add_entities(entities)


class CozifyHubValve(CozifyHubEntity, ValveEntity):
    """Cozify HUB valve."""

    _attr_device_class = ValveDeviceClass.WATER
    _attr_supported_features = (
        ValveEntityFeature.OPEN | ValveEntityFeature.CLOSE | ValveEntityFeature.SET_POSITION
    )

    def __init__(self, coordinator: CozifyHubCoordinator, device_id: str) -> None:
        super().__init__(coordinator, device_id)
        self._attr_unique_id = device_id
        self._attr_name = self._device.get("name", device_id)

    @property
    def current_valve_position(self) -> int | None:
        pct = self._device.get("open_pct")
        return int(pct) if pct is not None else None

    @property
    def is_closed(self) -> bool | None:
        pos = self.current_valve_position
        return pos == 0 if pos is not None else None

    async def async_open_valve(self, **kwargs: Any) -> None:
        await self.coordinator.api.set_valve_position(self._device_id, 100.0)
        await self.coordinator.async_request_refresh()

    async def async_close_valve(self, **kwargs: Any) -> None:
        await self.coordinator.api.set_valve_position(self._device_id, 0.0)
        await self.coordinator.async_request_refresh()

    async def async_set_valve_position(self, position: int) -> None:
        await self.coordinator.api.set_valve_position(self._device_id, float(position))
        await self.coordinator.async_request_refresh()
