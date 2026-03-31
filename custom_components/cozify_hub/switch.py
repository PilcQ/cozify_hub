"""Switch platform for Cozify HUB."""
from __future__ import annotations

from typing import Any

from homeassistant.components.switch import SwitchEntity
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
        dtype = device.get("type", "")
        caps = device.get("capabilities", [])
        is_switch = (
            dtype in ("SWITCH", "PLUG") or
            ("ON_OFF" in caps and
             "LIGHT" not in caps and
             "BRIGHTNESS" not in caps and
             dtype not in ("LIGHT", "DIMMER"))
        )
        if is_switch:
            entities.append(CozifyHubSwitch(coordinator, device_id))
    async_add_entities(entities)


class CozifyHubSwitch(CozifyHubEntity, SwitchEntity):
    """Cozify HUB switch."""

    def __init__(self, coordinator: CozifyHubCoordinator, device_id: str) -> None:
        super().__init__(coordinator, device_id)
        self._attr_unique_id = device_id
        self._attr_name = self._device.get("name", device_id)

    @property
    def is_on(self) -> bool:
        return self._device.get("is_on", False)

    async def async_turn_on(self, **kwargs: Any) -> None:
        await self.coordinator.api.turn_on(self._device_id)
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self.coordinator.api.turn_off(self._device_id)
        await self.coordinator.async_request_refresh()
