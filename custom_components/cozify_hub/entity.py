"""Base entity for Cozify HUB."""
from __future__ import annotations

from typing import Any

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import CozifyHubCoordinator


class CozifyHubEntity(CoordinatorEntity[CozifyHubCoordinator]):
    """Base entity for Cozify HUB devices."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: CozifyHubCoordinator,
        device_id: str,
    ) -> None:
        super().__init__(coordinator)
        self._device_id = device_id
        self._attr_unique_id = f"{DOMAIN}_{device_id}"

    @property
    def device_data(self) -> dict[str, Any]:
        """Return raw device data from coordinator."""
        return self.coordinator.data.get(self._device_id, {})

    @property
    def device_info(self) -> DeviceInfo:
        """Return device info."""
        data = self.device_data
        return DeviceInfo(
            identifiers={(DOMAIN, self._device_id)},
            name=data.get("name", self._device_id),
            manufacturer="Cozify",
            model=data.get("type", "Unknown"),
            sw_version=data.get("firmware"),
            via_device=(DOMAIN, self.coordinator.api._host),
        )
