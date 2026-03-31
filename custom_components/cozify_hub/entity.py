"""Base entity for Cozify HUB."""
from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, MANUFACTURER
from .coordinator import CozifyHubCoordinator


class CozifyHubEntity(CoordinatorEntity[CozifyHubCoordinator]):
    """Base class for Cozify HUB entities."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: CozifyHubCoordinator, device_id: str) -> None:
        super().__init__(coordinator)
        self._device_id = device_id

    @property
    def _device(self) -> dict:
        return self.coordinator.data["devices"].get(self._device_id, {})

    @property
    def available(self) -> bool:
        return self.coordinator.last_update_success and self._device.get("reachable", True)

    @property
    def device_info(self) -> DeviceInfo:
        return DeviceInfo(
            identifiers={(DOMAIN, self._device_id)},
            name=self._device.get("name"),
            manufacturer=self._device.get("manufacturer", MANUFACTURER),
            model=self._device.get("model"),
            suggested_area=self._device.get("room_name"),
        )
