"""Sensor platform for Cozify HUB."""
from __future__ import annotations

from homeassistant.components.sensor import (
    SensorDeviceClass, SensorEntity, SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    PERCENTAGE, LIGHT_LUX, CONCENTRATION_PARTS_PER_MILLION,
    SIGNAL_STRENGTH_DECIBELS_MILLIWATT, EntityCategory,
    UnitOfEnergy, UnitOfPower, UnitOfPressure, UnitOfTemperature, UnitOfVolume,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import CozifyHubCoordinator
from .entity import CozifyHubEntity

# (data_key, name_suffix, device_class, unit, state_class, entity_category)
SENSOR_TYPES: list[tuple] = [
    ("temperature", "Temperature", SensorDeviceClass.TEMPERATURE, UnitOfTemperature.CELSIUS, SensorStateClass.MEASUREMENT, None),
    ("humidity", "Humidity", SensorDeviceClass.HUMIDITY, PERCENTAGE, SensorStateClass.MEASUREMENT, None),
    ("pressure", "Pressure", SensorDeviceClass.ATMOSPHERIC_PRESSURE, UnitOfPressure.PA, SensorStateClass.MEASUREMENT, None),
    ("lux", "Illuminance", SensorDeviceClass.ILLUMINANCE, LIGHT_LUX, SensorStateClass.MEASUREMENT, None),
    ("co2_ppm", "CO₂", SensorDeviceClass.CO2, CONCENTRATION_PARTS_PER_MILLION, SensorStateClass.MEASUREMENT, None),
    ("voc_ppm", "VOC", SensorDeviceClass.VOLATILE_ORGANIC_COMPOUNDS_PARTS, CONCENTRATION_PARTS_PER_MILLION, SensorStateClass.MEASUREMENT, None),
    ("active_power", "Power", SensorDeviceClass.POWER, UnitOfPower.WATT, SensorStateClass.MEASUREMENT, None),
    ("power", "Power", SensorDeviceClass.POWER, UnitOfPower.WATT, SensorStateClass.MEASUREMENT, None),
    ("total_power", "Energy", SensorDeviceClass.ENERGY, UnitOfEnergy.KILO_WATT_HOUR, SensorStateClass.TOTAL_INCREASING, None),
    ("power_today", "Energy Today", SensorDeviceClass.ENERGY, UnitOfEnergy.KILO_WATT_HOUR, SensorStateClass.TOTAL_INCREASING, None),
    ("battery", "Battery", SensorDeviceClass.BATTERY, PERCENTAGE, SensorStateClass.MEASUREMENT, EntityCategory.DIAGNOSTIC),
    ("battery_v", "Battery Voltage", SensorDeviceClass.VOLTAGE, "V", SensorStateClass.MEASUREMENT, EntityCategory.DIAGNOSTIC),
    ("rssi", "Signal Strength", SensorDeviceClass.SIGNAL_STRENGTH, SIGNAL_STRENGTH_DECIBELS_MILLIWATT, SensorStateClass.MEASUREMENT, EntityCategory.DIAGNOSTIC),
    ("flow", "Water Flow", None, "l/h", SensorStateClass.MEASUREMENT, None),
    ("flow_volume", "Water Volume", SensorDeviceClass.WATER, UnitOfVolume.LITERS, SensorStateClass.TOTAL_INCREASING, None),
    ("flow_temperature", "Water Temperature", SensorDeviceClass.TEMPERATURE, UnitOfTemperature.CELSIUS, SensorStateClass.MEASUREMENT, None),
    ("fresh_temperature", "Fresh Air Temp", SensorDeviceClass.TEMPERATURE, UnitOfTemperature.CELSIUS, SensorStateClass.MEASUREMENT, None),
    ("supply_temperature", "Supply Air Temp", SensorDeviceClass.TEMPERATURE, UnitOfTemperature.CELSIUS, SensorStateClass.MEASUREMENT, None),
    ("extract_temperature", "Extract Air Temp", SensorDeviceClass.TEMPERATURE, UnitOfTemperature.CELSIUS, SensorStateClass.MEASUREMENT, None),
    ("heating_demand", "Heating Demand", None, PERCENTAGE, SensorStateClass.MEASUREMENT, None),
]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry,
                             async_add_entities: AddEntitiesCallback) -> None:
    coordinator: CozifyHubCoordinator = hass.data[DOMAIN][entry.entry_id]
    entities = []
    for device_id, device in coordinator.data["devices"].items():
        for key, name_suffix, dc, unit, sc, cat in SENSOR_TYPES:
            if device.get(key) is not None:
                entities.append(CozifyHubSensor(
                    coordinator, device_id, key, name_suffix, dc, unit, sc, cat))
    async_add_entities(entities)


class CozifyHubSensor(CozifyHubEntity, SensorEntity):
    """Generic Cozify HUB sensor."""

    def __init__(self, coordinator, device_id, key, name_suffix,
                 device_class, unit, state_class, entity_category) -> None:
        super().__init__(coordinator, device_id)
        self._key = key
        self._attr_unique_id = f"{device_id}_{key}"
        self._attr_name = f"{self._device.get('name', device_id)} {name_suffix}"
        self._attr_device_class = device_class
        self._attr_native_unit_of_measurement = unit
        self._attr_state_class = state_class
        self._attr_entity_category = entity_category

    @property
    def native_value(self):
        value = self._device.get(self._key)
        if self._key == "heating_demand" and value is not None:
            return round(value * 100, 1)
        return value
