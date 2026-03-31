"""Fan platform for Cozify HUB."""
from __future__ import annotations

from typing import Any

from homeassistant.components.fan import FanEntity, FanEntityFeature
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.util.percentage import (
    ordered_list_item_to_percentage,
    percentage_to_ordered_list_item,
)

from .const import DOMAIN
from .coordinator import CozifyHubCoordinator
from .entity import CozifyHubEntity

VU_SPEEDS = ["min", "standard", "max", "boost"]  # modes 1–4
FAN_SPEEDS = ["low", "medium", "high"]            # modes 1–3


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry,
                             async_add_entities: AddEntitiesCallback) -> None:
    coordinator: CozifyHubCoordinator = hass.data[DOMAIN][entry.entry_id]
    entities = []
    for device_id, device in coordinator.data["devices"].items():
        caps = device.get("capabilities", [])
        if "VU" in caps:
            entities.append(CozifyHubVentilationFan(coordinator, device_id))
        elif "FAN_MODE" in caps:
            entities.append(CozifyHubFan(coordinator, device_id))
    async_add_entities(entities)


class CozifyHubVentilationFan(CozifyHubEntity, FanEntity):
    """Ventilation unit (VU capability). Modes: STOPPED=0 MIN=1 STANDARD=2 MAX=3 BOOST=4."""

    _attr_supported_features = FanEntityFeature.SET_SPEED | FanEntityFeature.PRESET_MODE
    _attr_speed_count = len(VU_SPEEDS)

    def __init__(self, coordinator: CozifyHubCoordinator, device_id: str) -> None:
        super().__init__(coordinator, device_id)
        self._attr_unique_id = device_id
        self._attr_name = self._device.get("name", device_id)
        caps = self._device.get("capabilities", [])
        self._attr_preset_modes = ["fireplace"] if "VU_FN_FIREPLACE" in caps else []

    @property
    def is_on(self) -> bool:
        return (self._device.get("ventilation_mode") or 0) > 0

    @property
    def percentage(self) -> int | None:
        mode = self._device.get("ventilation_mode") or 0
        if mode == 0:
            return 0
        speed = {1: "min", 2: "standard", 3: "max", 4: "boost"}.get(mode)
        return ordered_list_item_to_percentage(VU_SPEEDS, speed) if speed else None

    @property
    def preset_mode(self) -> str | None:
        return "fireplace" if self._device.get("fn_fireplace") else None

    async def async_set_percentage(self, percentage: int) -> None:
        if percentage == 0:
            await self.coordinator.api.set_ventilation_mode(self._device_id, 0)
        else:
            speed = percentage_to_ordered_list_item(VU_SPEEDS, percentage)
            mode = {"min": 1, "standard": 2, "max": 3, "boost": 4}[speed]
            await self.coordinator.api.set_ventilation_mode(self._device_id, mode)
        await self.coordinator.async_request_refresh()

    async def async_turn_on(self, percentage: int | None = None, **kwargs: Any) -> None:
        if percentage is not None:
            await self.async_set_percentage(percentage)
        else:
            await self.coordinator.api.set_ventilation_mode(self._device_id, 2)
            await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self.coordinator.api.set_ventilation_mode(self._device_id, 0)
        await self.coordinator.async_request_refresh()


class CozifyHubFan(CozifyHubEntity, FanEntity):
    """Generic fan (FAN_MODE capability). Modes: OFF=0 LOW=1 MEDIUM=2 HIGH=3 AUTO=5."""

    _attr_supported_features = FanEntityFeature.SET_SPEED | FanEntityFeature.PRESET_MODE
    _attr_speed_count = len(FAN_SPEEDS)
    _attr_preset_modes = ["auto", "smart"]

    def __init__(self, coordinator: CozifyHubCoordinator, device_id: str) -> None:
        super().__init__(coordinator, device_id)
        self._attr_unique_id = device_id
        self._attr_name = self._device.get("name", device_id)

    @property
    def is_on(self) -> bool:
        return (self._device.get("fan_mode") or 0) > 0

    @property
    def percentage(self) -> int | None:
        mode = self._device.get("fan_mode") or 0
        speed = {1: "low", 2: "medium", 3: "high"}.get(mode)
        return ordered_list_item_to_percentage(FAN_SPEEDS, speed) if speed else 0

    async def async_set_percentage(self, percentage: int) -> None:
        if percentage == 0:
            await self.coordinator.api.set_fan_mode(self._device_id, 0)
        else:
            speed = percentage_to_ordered_list_item(FAN_SPEEDS, percentage)
            mode = {"low": 1, "medium": 2, "high": 3}[speed]
            await self.coordinator.api.set_fan_mode(self._device_id, mode)
        await self.coordinator.async_request_refresh()

    async def async_turn_on(self, percentage: int | None = None, **kwargs: Any) -> None:
        if percentage is not None:
            await self.async_set_percentage(percentage)
        else:
            await self.coordinator.api.set_fan_mode(self._device_id, 5)  # AUTO
            await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self.coordinator.api.set_fan_mode(self._device_id, 0)
        await self.coordinator.async_request_refresh()
