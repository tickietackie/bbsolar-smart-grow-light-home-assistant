"""Light platform for the BBSolar Smart Grow Light integration."""

from __future__ import annotations

from typing import Any

from homeassistant.components.light import (
    ATTR_BRIGHTNESS,
    ColorMode,
    LightEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, LIGHTS
from .coordinator import BBSolarCoordinator

DEVICE_LEVEL_MAX = 100


def _to_device_level(brightness: int) -> int:
    return max(1, min(DEVICE_LEVEL_MAX, round(brightness / 255 * DEVICE_LEVEL_MAX)))


def _to_ha_brightness(level: int) -> int:
    return max(0, min(255, round(level / DEVICE_LEVEL_MAX * 255)))


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: BBSolarCoordinator = entry.runtime_data
    async_add_entities(
        BBSolarLight(coordinator, description) for description in LIGHTS
    )


class BBSolarLight(CoordinatorEntity[BBSolarCoordinator], LightEntity):
    """A light strip (or the main channel controlling both strips)."""

    _attr_has_entity_name = True
    _attr_supported_color_modes = {ColorMode.BRIGHTNESS}
    _attr_color_mode = ColorMode.BRIGHTNESS

    def __init__(
        self, coordinator: BBSolarCoordinator, description: dict[str, Any]
    ) -> None:
        super().__init__(coordinator)
        self._strips = description["strips"]
        self._attr_name = description["name"]
        self._attr_unique_id = f"{coordinator.device.uuid}_{description['key']}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, coordinator.device.uuid)},
            manufacturer="BBSolar",
            model=coordinator.device.model or "Smart Grow Light",
            name="BBSolar Smart Grow Light",
            sw_version=coordinator.device.sw_version,
            configuration_url=f"http://{coordinator.device.host}/",
        )

    @property
    def _toggles(self) -> dict[int, bool]:
        return self.coordinator.data.get("toggles") or {}

    @property
    def _luminance(self) -> dict[int, int]:
        return self.coordinator.data.get("luminance") or {}

    @property
    def is_on(self) -> bool:
        return any(self._toggles.get(strip["toggle"], False) for strip in self._strips)

    @property
    def brightness(self) -> int | None:
        levels = [
            self._luminance.get(strip["white"], 0)
            for strip in self._strips
            if self._toggles.get(strip["toggle"], False)
        ] or [self._luminance.get(strip["white"], 0) for strip in self._strips]
        levels = [level for level in levels if level is not None]
        if not levels:
            return None
        return _to_ha_brightness(round(sum(levels) / len(levels)))

    async def async_turn_on(self, **kwargs: Any) -> None:
        brightness = kwargs.get(ATTR_BRIGHTNESS)
        values: dict[int, int] = {}
        if brightness is not None:
            target = _to_device_level(brightness)
            for strip in self._strips:
                values[strip["white"]] = target
                current_white = self._luminance.get(strip["white"], 0)
                for color in ("red", "blue"):
                    current = self._luminance.get(strip[color], 0)
                    if current_white > 0 and current > 0:
                        values[strip[color]] = max(
                            0,
                            min(
                                DEVICE_LEVEL_MAX,
                                round(current * target / current_white),
                            ),
                        )
        if values:
            await self.coordinator.async_set_luminance(values)
        for strip in self._strips:
            if not self._toggles.get(strip["toggle"], False):
                await self.coordinator.async_set_toggle(strip["toggle"], True)

    async def async_turn_off(self, **kwargs: Any) -> None:
        for strip in self._strips:
            if self._toggles.get(strip["toggle"], False):
                await self.coordinator.async_set_toggle(strip["toggle"], False)
