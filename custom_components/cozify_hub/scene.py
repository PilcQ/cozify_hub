"""Scene platform for Cozify HUB."""
from __future__ import annotations

from typing import Any

from homeassistant.components.scene import Scene
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, MANUFACTURER
from .coordinator import CozifyHubCoordinator


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry,
                             async_add_entities: AddEntitiesCallback) -> None:
    coordinator: CozifyHubCoordinator = hass.data[DOMAIN][entry.entry_id]
    entities = [
        CozifyHubScene(coordinator, scene_id, scene_data)
        for scene_id, scene_data in coordinator.data.get("scenes", {}).items()
    ]
    async_add_entities(entities)


class CozifyHubScene(Scene):
    """Cozify HUB scene."""

    _attr_has_entity_name = False

    def __init__(self, coordinator: CozifyHubCoordinator,
                 scene_id: str, scene_data: dict) -> None:
        self._coordinator = coordinator
        self._scene_id = scene_id
        self._attr_unique_id = f"{DOMAIN}_scene_{scene_id}"
        self._attr_name = scene_data.get("name", scene_id)

    async def async_activate(self, **kwargs: Any) -> None:
        await self._coordinator.api.activate_scene(self._scene_id)
