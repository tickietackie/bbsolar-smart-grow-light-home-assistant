"""Preset select entity for the BBSolar Smart Grow Light integration."""

from __future__ import annotations

from typing import Any

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, STRIPS
from .coordinator import BBSolarCoordinator
from .presets import PRESET_BY_NAME, PRESET_NAMES, match_preset, preset_channels

CUSTOM_OPTION = "Custom"


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: BBSolarCoordinator = entry.runtime_data
    async_add_entities([BBSolarPresetSelect(coordinator)])


class BBSolarPresetSelect(CoordinatorEntity[BBSolarCoordinator], SelectEntity):
    """Applies a grow preset to the whole lamp."""

    _attr_has_entity_name = True
    _attr_name = "Preset"
    _attr_icon = "mdi:flower"

    def __init__(self, coordinator: BBSolarCoordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.device.uuid}_preset"
        self._attr_options = [CUSTOM_OPTION, *PRESET_NAMES]
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, coordinator.device.uuid)},
            manufacturer="BBSolar",
            model=coordinator.device.model or "Smart Grow Light",
            name="BBSolar Smart Grow Light",
            sw_version=coordinator.device.sw_version,
            configuration_url=f"http://{coordinator.device.host}/",
        )

    @property
    def current_option(self) -> str:
        luminance = self.coordinator.data.get("luminance") or {}
        strips = [
            (
                luminance.get(strip["white"], 0),
                luminance.get(strip["red"], 0),
                luminance.get(strip["blue"], 0),
            )
            for strip in STRIPS
        ]
        return match_preset(strips) or CUSTOM_OPTION

    async def async_select_option(self, option: str) -> None:
        preset = PRESET_BY_NAME.get(option)
        if preset is None:
            return
        level = preset["level"]
        values: dict[int, int] = {}
        for strip in STRIPS:
            channels = preset_channels(preset, level)
            values[strip["white"]] = channels["white"]
            values[strip["red"]] = channels["red"]
            values[strip["blue"]] = channels["blue"]
        await self.coordinator.async_set_luminance(values)
        toggles = self.coordinator.data.get("toggles") or {}
        for strip in STRIPS:
            if not toggles.get(strip["toggle"], False):
                await self.coordinator.async_set_toggle(strip["toggle"], True)
