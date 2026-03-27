"""Cover platform for Cozify HUB."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.cover import (
    ATTR_POSITION,
    CoverDeviceClass,
    CoverEntity,
    CoverEntityFeature,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import CozifyHubConfigEntry
from .const import CAP_COVER
from .coordinator import CozifyHubCoordinator
from .entity import CozifyHubEntity

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: CozifyHubConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Cozify HUB covers."""
    coordinator = entry.runtime_data
    entities = [
        CozifyHubCover(coordinator, device_id)
        for device_id, device in coordinator.data.items()
        if CAP_COVER in device.get("capabilities", [])
    ]
    async_add_entities(entities)


class CozifyHubCover(CozifyHubEntity, CoverEntity):
    """Cover entity for a Cozify HUB device (blinds, shades)."""

    _attr_name = None
    _attr_device_class = CoverDeviceClass.BLIND
    _attr_supported_features = (
        CoverEntityFeature.OPEN
        | CoverEntityFeature.CLOSE
        | CoverEntityFeature.STOP
        | CoverEntityFeature.SET_POSITION
    )

    @property
    def current_cover_position(self) -> int | None:
        """Return current position 0-100 (100 = fully open)."""
        state = self.device_data.get("state", {})
        return state.get("position")

    @property
    def is_closed(self) -> bool | None:
        pos = self.current_cover_position
        if pos is None:
            return None
        return pos == 0

    async def async_open_cover(self, **kwargs: Any) -> None:
        await self.coordinator.api.device_command(self._device_id, {"position": 100})
        await self.coordinator.async_request_refresh()

    async def async_close_cover(self, **kwargs: Any) -> None:
        await self.coordinator.api.device_command(self._device_id, {"position": 0})
        await self.coordinator.async_request_refresh()

    async def async_stop_cover(self, **kwargs: Any) -> None:
        await self.coordinator.api.device_command(self._device_id, {"stop": True})
        await self.coordinator.async_request_refresh()

    async def async_set_cover_position(self, **kwargs: Any) -> None:
        position = kwargs.get(ATTR_POSITION, 0)
        await self.coordinator.api.device_command(
            self._device_id, {"position": position}
        )
        await self.coordinator.async_request_refresh()
