"""The BBSolar Smart Grow Light integration."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import CONF_HOST, CONF_KEY, CONF_MODEL, CONF_SW_VERSION, CONF_UUID
from .coordinator import BBSolarCoordinator
from .device import BBSolarDevice

PLATFORMS = [Platform.LIGHT, Platform.SELECT]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    device = BBSolarDevice(
        entry.data[CONF_HOST],
        entry.data[CONF_KEY],
        async_get_clientsession(hass),
    )
    device.uuid = entry.data[CONF_UUID]
    device.model = entry.data.get(CONF_MODEL, "")
    device.sw_version = entry.data.get(CONF_SW_VERSION, "")

    coordinator = BBSolarCoordinator(hass, device)
    await coordinator.async_config_entry_first_refresh()

    entry.runtime_data = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
