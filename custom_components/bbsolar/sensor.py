"""Read-only sensors exposing the current LED channel values."""

from __future__ import annotations

from typing import Any

from homeassistant.components.sensor import (
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import PERCENTAGE, EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, LUMINANCE_CHANNELS, STRIPS
from .coordinator import BBSolarCoordinator

CHANNEL_COLORS = {0: "white", 1: "blue", 2: "red"}
CHANNEL_LABELS = {"white": "White", "blue": "Blue", "red": "Red"}
AUX_LABEL = "Aux"
STRIP_NAMES = {1: "Light A", 2: "Light B"}


def _sensor_description(strip: dict[str, int], offset: int) -> dict[str, Any]:
    color = CHANNEL_COLORS.get(offset)
    if color:
        label = CHANNEL_LABELS[color]
    else:
        label = AUX_LABEL
    return {
        "key": f"{strip['toggle']}_{offset}",
        "name": f"{STRIP_NAMES[strip['toggle']]} {label}",
        "channel": strip["white"] + offset,
    }


SENSORS = tuple(
    _sensor_description(strip, offset)
    for strip in STRIPS
    for offset in range(4)
    if strip["white"] + offset in LUMINANCE_CHANNELS
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: BBSolarCoordinator = entry.runtime_data
    async_add_entities(
        BBSolarChannelSensor(coordinator, description) for description in SENSORS
    )


class BBSolarChannelSensor(CoordinatorEntity[BBSolarCoordinator], SensorEntity):
    """Current level of a single luminance channel."""

    _attr_has_entity_name = True
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_native_unit_of_measurement = PERCENTAGE
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_icon = "mdi:led-on"

    def __init__(
        self, coordinator: BBSolarCoordinator, description: dict[str, Any]
    ) -> None:
        super().__init__(coordinator)
        self._channel = description["channel"]
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
    def native_value(self) -> int | None:
        luminance = self.coordinator.data.get("luminance") or {}
        return luminance.get(self._channel)
