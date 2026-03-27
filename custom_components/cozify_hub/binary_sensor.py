"""Binary sensor platform for Cozify HUB."""
from __future__ import annotations

import logging

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import CozifyHubConfigEntry
from .const import CAP_CONTACT, CAP_MOTION, DOMAIN
from .coordinator import CozifyHubCoordinator
from .entity import CozifyHubEntity

_LOGGER = logging.getLogger(__name__)

BINARY_SENSOR_DESCRIPTIONS: dict[str, BinarySensorEntityDescription] = {
    CAP_MOTION: BinarySensorEntityDescription(
        key="motion",
        device_class=BinarySensorDeviceClass.MOTION,
    ),
    CAP_CONTACT: BinarySensorEntityDescription(
        key="contact",
        device_class=BinarySensorDeviceClass.DOOR,
    ),
}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: CozifyHubConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Cozify HUB binary sensors."""
    coordinator = entry.runtime_data
    entities: list[CozifyHubBinarySensor] = []

    for device_id, device in coordinator.data.items():
        caps = device.get("capabilities", [])
        for cap, description in BINARY_SENSOR_DESCRIPTIONS.items():
            if cap in caps:
                entities.append(
                    CozifyHubBinarySensor(coordinator, device_id, cap, description)
                )

    async_add_entities(entities)


class CozifyHubBinarySensor(CozifyHubEntity, BinarySensorEntity):
    """Binary sensor entity for a Cozify HUB device."""

    def __init__(
        self,
        coordinator: CozifyHubCoordinator,
        device_id: str,
        capability: str,
        description: BinarySensorEntityDescription,
    ) -> None:
        super().__init__(coordinator, device_id)
        self.entity_description = description
        self._capability = capability
        self._attr_unique_id = f"{DOMAIN}_{device_id}_{description.key}"

    @property
    def is_on(self) -> bool | None:
        state = self.device_data.get("state", {})
        value = state.get(self.entity_description.key)
        if self._capability == CAP_CONTACT:
            # contact=True means closed (door shut) → not triggered
            return not value if value is not None else None
        return value
