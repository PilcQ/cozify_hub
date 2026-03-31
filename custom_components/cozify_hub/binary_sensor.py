"""Binary sensor platform for Cozify HUB."""
from __future__ import annotations

from homeassistant.components.binary_sensor import BinarySensorDeviceClass, BinarySensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import CozifyHubCoordinator
from .entity import CozifyHubEntity

BINARY_SENSOR_TYPES: list[tuple] = [
    ("motion", "Motion", BinarySensorDeviceClass.MOTION),
    ("open", "Contact", BinarySensorDeviceClass.DOOR),
    ("alert", "Smoke", BinarySensorDeviceClass.SMOKE),
    ("moisture", "Moisture", BinarySensorDeviceClass.MOISTURE),
    ("twilight", "Twilight", BinarySensorDeviceClass.LIGHT),
    ("low_temp", "Low Temperature", BinarySensorDeviceClass.COLD),
    ("co_detected", "Carbon Monoxide", BinarySensorDeviceClass.CO),
    ("battery_low", "Battery Low", BinarySensorDeviceClass.BATTERY),
    ("siren_on", "Siren", BinarySensorDeviceClass.SOUND),
]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry,
                             async_add_entities: AddEntitiesCallback) -> None:
    coordinator: CozifyHubCoordinator = hass.data[DOMAIN][entry.entry_id]
    entities = []
    for device_id, device in coordinator.data["devices"].items():
        for key, name_suffix, dc in BINARY_SENSOR_TYPES:
            if device.get(key) is not None:
                entities.append(CozifyHubBinarySensor(coordinator, device_id, key, name_suffix, dc))
    async_add_entities(entities)


class CozifyHubBinarySensor(CozifyHubEntity, BinarySensorEntity):
    """Generic Cozify HUB binary sensor."""

    def __init__(self, coordinator, device_id, key, name_suffix, device_class) -> None:
        super().__init__(coordinator, device_id)
        self._key = key
        self._attr_unique_id = f"{device_id}_{key}"
        self._attr_name = f"{self._device.get('name', device_id)} {name_suffix}"
        self._attr_device_class = device_class

    @property
    def is_on(self) -> bool | None:
        return self._device.get(self._key)
