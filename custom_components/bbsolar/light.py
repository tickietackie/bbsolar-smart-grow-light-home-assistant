"""Light platform for the BBSolar Smart Grow Light integration."""

from __future__ import annotations

from typing import Any

from homeassistant.components.light import (
    ATTR_BRIGHTNESS,
    ATTR_RGB_COLOR,
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


def _channels_from_rgb(rgb: tuple[int, int, int], level: int) -> dict[str, int]:
    red, green, blue = (component / 255 for component in rgb)
    peak = max(red, green, blue)
    if peak <= 0:
        return {"white": level, "red": 0, "blue": 0}
    red, green, blue = red / peak, green / peak, blue / peak
    return {
        "white": round(green * level),
        "red": round(max(0.0, red - green) * level),
        "blue": round(max(0.0, blue - green) * level),
    }


def _rgb_from_channels(white: int, red: int, blue: int) -> tuple[int, int, int]:
    raw = (white + red, white, white + blue)
    peak = max(raw)
    if peak <= 0:
        return (0, 0, 0)
    return tuple(round(255 * value / peak) for value in raw)


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
    _attr_supported_color_modes = {ColorMode.RGB}
    _attr_color_mode = ColorMode.RGB

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
        if not levels:
            return None
        return _to_ha_brightness(round(sum(levels) / len(levels)))

    @property
    def rgb_color(self) -> tuple[int, int, int] | None:
        if not self.is_on:
            return None
        colors = [
            _rgb_from_channels(
                self._luminance.get(strip["white"], 0),
                self._luminance.get(strip["red"], 0),
                self._luminance.get(strip["blue"], 0),
            )
            for strip in self._strips
        ]
        return tuple(
            round(sum(color[index] for color in colors) / len(colors))
            for index in range(3)
        )

    async def async_turn_on(self, **kwargs: Any) -> None:
        brightness = kwargs.get(ATTR_BRIGHTNESS)
        rgb = kwargs.get(ATTR_RGB_COLOR)

        if brightness is not None:
            level = _to_device_level(brightness)
        else:
            current = self.brightness
            level = _to_device_level(current) if current else DEVICE_LEVEL_MAX

        values: dict[int, int] = {}
        for strip in self._strips:
            white = self._luminance.get(strip["white"], 0)
            red = self._luminance.get(strip["red"], 0)
            blue = self._luminance.get(strip["blue"], 0)
            if rgb is not None:
                channels = _channels_from_rgb(rgb, level)
            else:
                factor = level / white if white > 0 else 1
                channels = {
                    "white": level,
                    "red": max(
                        0, min(DEVICE_LEVEL_MAX, round(red * factor))
                    ),
                    "blue": max(
                        0, min(DEVICE_LEVEL_MAX, round(blue * factor))
                    ),
                }
            values[strip["white"]] = channels["white"]
            values[strip["red"]] = channels["red"]
            values[strip["blue"]] = channels["blue"]

        if values:
            await self.coordinator.async_set_luminance(values)
        for strip in self._strips:
            if not self._toggles.get(strip["toggle"], False):
                await self.coordinator.async_set_toggle(strip["toggle"], True)

    async def async_turn_off(self, **kwargs: Any) -> None:
        for strip in self._strips:
            if self._toggles.get(strip["toggle"], False):
                await self.coordinator.async_set_toggle(strip["toggle"], False)
