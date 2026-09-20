"""Data update coordinator for the BBSolar Smart Grow Light integration."""

from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DOMAIN
from .device import BBSolarDevice, BBSolarError

_LOGGER = logging.getLogger(__name__)

UPDATE_INTERVAL = timedelta(seconds=10)


class BBSolarCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Poll the device and keep the state of its channels."""

    def __init__(self, hass: HomeAssistant, device: BBSolarDevice) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=UPDATE_INTERVAL,
        )
        self.device = device

    async def _async_update_data(self) -> dict[str, Any]:
        try:
            return await self.device.async_update()
        except BBSolarError as err:
            raise UpdateFailed(str(err)) from err

    async def async_set_toggle(self, channel: int, onoff: bool) -> None:
        await self.device.async_set_toggle(channel, onoff)
        self.data.setdefault("toggles", {})[channel] = onoff
        self.async_set_updated_data(self.data)

    async def async_set_luminance(self, values: dict[int, int]) -> None:
        await self.device.async_set_luminance(values)
        self.data.setdefault("luminance", {}).update(values)
        self.async_set_updated_data(self.data)
