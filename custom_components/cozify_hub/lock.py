"""Lock platform for Cozify HUB."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.lock import LockEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import CozifyHubConfigEntry
from .const import CAP_LOCK
from .coordinator import CozifyHubCoordinator
from .entity import CozifyHubEntity

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: CozifyHubConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Cozify HUB locks."""
    coordinator = entry.runtime_data
    entities = [
        CozifyHubLock(coordinator, device_id)
        for device_id, device in coordinator.data.items()
        if CAP_LOCK in device.get("capabilities", {}).get("values", [])
    ]
    async_add_entities(entities)


class CozifyHubLock(CozifyHubEntity, LockEntity):
    """Lock entity for a Cozify HUB device."""

    _attr_name = None

    @property
    def is_locked(self) -> bool | None:
        state = self.device_data.get("state", {})
        return state.get("locked")

    async def async_lock(self, **kwargs: Any) -> None:
        """Lock the device."""
        await self.coordinator.api.device_command(self._device_id, {"locked": True})
        await self.coordinator.async_request_refresh()

    async def async_unlock(self, **kwargs: Any) -> None:
        """Unlock the device."""
        await self.coordinator.api.device_command(self._device_id, {"locked": False})
        await self.coordinator.async_request_refresh()
