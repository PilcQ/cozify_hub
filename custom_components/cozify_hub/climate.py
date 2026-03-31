"""Climate platform for Cozify HUB."""
from __future__ import annotations

from typing import Any

from homeassistant.components.climate import (
    ClimateEntity, ClimateEntityFeature, HVACMode, HVACAction,
    PRESET_COMFORT, PRESET_ECO,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import CozifyHubCoordinator
from .entity import CozifyHubEntity

COZIFY_MODE_TO_HVAC = {0: HVACMode.OFF, 1: HVACMode.AUTO, 2: HVACMode.HEAT, 3: HVACMode.COOL}
HVAC_TO_COZIFY = {v: k for k, v in COZIFY_MODE_TO_HVAC.items()}
COZIFY_PRESET_MAP = {0: PRESET_COMFORT, 1: PRESET_ECO, 2: "fireplace"}
PRESET_TO_COZIFY = {v: k for k, v in COZIFY_PRESET_MAP.items()}


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry,
                             async_add_entities: AddEntitiesCallback) -> None:
    coordinator: CozifyHubCoordinator = hass.data[DOMAIN][entry.entry_id]
    entities = []
    for device_id, device in coordinator.data["devices"].items():
        caps = device.get("capabilities", [])
        if any(c in caps for c in ("THERMOSTAT", "HVAC", "CONTROL_TEMPERATURE", "AIRCON")):
            entities.append(CozifyHubClimate(coordinator, device_id))
    async_add_entities(entities)


class CozifyHubClimate(CozifyHubEntity, ClimateEntity):
    """Cozify HUB climate entity."""

    _attr_temperature_unit = UnitOfTemperature.CELSIUS
    _attr_target_temperature_step = 0.5
    _attr_min_temp = 5.0
    _attr_max_temp = 30.0

    def __init__(self, coordinator: CozifyHubCoordinator, device_id: str) -> None:
        super().__init__(coordinator, device_id)
        self._attr_unique_id = device_id
        self._attr_name = self._device.get("name", device_id)
        caps = self._device.get("capabilities", [])
        features = ClimateEntityFeature.TARGET_TEMPERATURE
        if "CONTROL_PRESET" in caps:
            features |= ClimateEntityFeature.PRESET_MODE
            self._attr_preset_modes = list(COZIFY_PRESET_MAP.values())
        self._attr_supported_features = features
        if "CONTROL_MODE" in caps or "AIRCON" in caps:
            self._attr_hvac_modes = [HVACMode.OFF, HVACMode.AUTO, HVACMode.HEAT, HVACMode.COOL]
        else:
            self._attr_hvac_modes = [HVACMode.OFF, HVACMode.HEAT]

    @property
    def current_temperature(self) -> float | None:
        return self._device.get("temperature")

    @property
    def target_temperature(self) -> float | None:
        return self._device.get("target_temperature")

    @property
    def hvac_mode(self) -> HVACMode:
        mode = self._device.get("hvac_mode")
        if mode is not None:
            return COZIFY_MODE_TO_HVAC.get(mode, HVACMode.OFF)
        return HVACMode.HEAT if self._device.get("is_on") else HVACMode.OFF

    @property
    def hvac_action(self) -> HVACAction | None:
        demand = self._device.get("heating_demand")
        if demand is not None:
            return HVACAction.HEATING if demand > 0 else HVACAction.IDLE
        return None

    @property
    def preset_mode(self) -> str | None:
        preset = self._device.get("hvac_preset")
        return COZIFY_PRESET_MAP.get(preset) if preset is not None else None

    async def async_set_temperature(self, **kwargs: Any) -> None:
        temp = kwargs.get("temperature")
        if temp is not None:
            await self.coordinator.api.set_target_temperature(self._device_id, temp)
            await self.coordinator.async_request_refresh()

    async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        caps = self._device.get("capabilities", [])
        if "CONTROL_MODE" in caps or "AIRCON" in caps:
            await self.coordinator.api.set_climate_mode(self._device_id, HVAC_TO_COZIFY.get(hvac_mode, 0))
        else:
            if hvac_mode == HVACMode.HEAT:
                await self.coordinator.api.turn_on(self._device_id)
            else:
                await self.coordinator.api.turn_off(self._device_id)
        await self.coordinator.async_request_refresh()

    async def async_set_preset_mode(self, preset_mode: str) -> None:
        cozify_preset = PRESET_TO_COZIFY.get(preset_mode)
        if cozify_preset is not None:
            await self.coordinator.api.set_climate_preset(self._device_id, cozify_preset)
            await self.coordinator.async_request_refresh()
