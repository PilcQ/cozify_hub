"""Sensor platform for Cozify HUB."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import PERCENTAGE, UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import CozifyHubConfigEntry
from .const import CAP_HUMIDITY, CAP_TEMPERATURE
from .coordinator import CozifyHubCoordinator
from .entity import CozifyHubEntity

_LOGGER = logging.getLogger(__name__)

SENSOR_DESCRIPTIONS: dict[str, SensorEntityDescription] = {
    CAP_TEMPERATURE: SensorEntityDescription(
        key="temperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
    ),
    CAP_HUMIDITY: SensorEntityDescription(
        key="humidity",
        device_class=SensorDeviceClass.HUMIDITY,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=PERCENTAGE,
    ),
}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: CozifyHubConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Cozify HUB sensors."""
    coordinator = entry.runtime_data
    entities: list[CozifyHubSensor] = []

    for device_id, device in coordinator.data.items():
        caps = device.get("capabilities", [])
        for cap, description in SENSOR_DESCRIPTIONS.items():
            if cap in caps:
                entities.append(CozifyHubSensor(coordinator, device_id, cap, description))

    async_add_entities(entities)


class CozifyHubSensor(CozifyHubEntity, SensorEntity):
    """Sensor entity for a Cozify HUB device."""

    def __init__(
        self,
        coordinator: CozifyHubCoordinator,
        device_id: str,
        capability: str,
        description: SensorEntityDescription,
    ) -> None:
        super().__init__(coordinator, device_id)
        self.entity_description = description
        self._capability = capability
        self._attr_unique_id = f"{DOMAIN}_{device_id}_{description.key}"

    @property
    def native_value(self) -> float | None:
        state = self.device_data.get("state", {})
        return state.get(self.entity_description.key)


# Needed for unique_id in sensor
from .const import DOMAIN
