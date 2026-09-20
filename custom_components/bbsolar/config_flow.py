"""Config flow for the BBSolar Smart Grow Light integration."""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigFlow
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import (
    CONF_HOST,
    CONF_KEY,
    CONF_MODEL,
    CONF_SW_VERSION,
    CONF_UUID,
    DOMAIN,
    MEROSS_LAN_DEVICE_ID,
    MEROSS_LAN_DOMAIN,
    MEROSS_LAN_HOST,
    MEROSS_LAN_KEY,
    MEROSS_LAN_PAYLOAD,
    NS_LUMINANCE,
)
from .device import BBSolarAuthError, BBSolarDevice, BBSolarError, BBSolarProtocolError


class BBSolarConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle the configuration of a BBSolar light."""

    VERSION = 1

    def __init__(self) -> None:
        self._candidates: list[dict[str, Any]] = []
        self._selected: dict[str, Any] | None = None

    async def _async_probe(self, host: str, key: str) -> BBSolarDevice:
        device = BBSolarDevice(host, key, async_get_clientsession(self.hass))
        ability = await device.async_probe()
        if NS_LUMINANCE not in ability:
            raise BBSolarProtocolError("device does not support luminance control")
        return device

    def _find_meross_lan_devices(self) -> list[dict[str, Any]]:
        candidates: list[dict[str, Any]] = []
        for entry in self.hass.config_entries.async_entries(MEROSS_LAN_DOMAIN):
            data = entry.data
            payload = data.get(MEROSS_LAN_PAYLOAD) or {}
            ability = payload.get("ability") or {}
            if NS_LUMINANCE not in ability:
                continue
            host = data.get(MEROSS_LAN_HOST)
            key = data.get(MEROSS_LAN_KEY)
            if not host or not key:
                continue
            uuid = data.get(MEROSS_LAN_DEVICE_ID) or ""
            candidates.append(
                {
                    "host": host,
                    "key": key,
                    "uuid": uuid,
                    "title": entry.title,
                }
            )
        return candidates

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> Any:
        self._candidates = self._find_meross_lan_devices()
        if self._candidates:
            self._selected = self._candidates[0]
            return await self.async_step_confirm()
        return await self.async_step_manual()

    async def async_step_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> Any:
        errors: dict[str, str] = {}
        if user_input is not None:
            selected = self._selected
            if len(self._candidates) > 1:
                selected = next(
                    (
                        candidate
                        for candidate in self._candidates
                        if candidate["uuid"] == user_input["device"]
                    ),
                    None,
                )
            if selected is not None:
                try:
                    device = await self._async_probe(selected["host"], selected["key"])
                except BBSolarAuthError:
                    errors["base"] = "invalid_key"
                except BBSolarError:
                    errors["base"] = "cannot_connect"
                else:
                    return await self._async_create_entry(
                        device, selected["host"], selected["key"]
                    )

        schema: vol.Schema = vol.Schema({})
        if len(self._candidates) > 1:
            schema = vol.Schema(
                {
                    vol.Required("device"): vol.In(
                        {
                            candidate["uuid"]: candidate["title"]
                            for candidate in self._candidates
                        }
                    )
                }
            )
        return self.async_show_form(
            step_id="confirm",
            data_schema=schema,
            errors=errors,
            description_placeholders={
                "host": self._selected["host"] if self._selected else ""
            },
        )

    async def async_step_manual(
        self, user_input: dict[str, Any] | None = None
    ) -> Any:
        errors: dict[str, str] = {}
        if user_input is not None:
            try:
                device = await self._async_probe(
                    user_input[CONF_HOST].strip(), user_input[CONF_KEY].strip()
                )
            except BBSolarAuthError:
                errors["base"] = "invalid_key"
            except BBSolarError:
                errors["base"] = "cannot_connect"
            else:
                return await self._async_create_entry(
                    device, user_input[CONF_HOST].strip(), user_input[CONF_KEY].strip()
                )
        return self.async_show_form(
            step_id="manual",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_HOST): str,
                    vol.Required(CONF_KEY): str,
                }
            ),
            errors=errors,
        )

    async def _async_create_entry(
        self, device: BBSolarDevice, host: str, key: str
    ) -> Any:
        await self.async_set_unique_id(device.uuid)
        self._abort_if_unique_id_configured()
        return self.async_create_entry(
            title=f"BBSolar {device.model or 'Smart Grow Light'} ({device.uuid[-12:]})",
            data={
                CONF_HOST: host,
                CONF_KEY: key,
                CONF_UUID: device.uuid,
                CONF_MODEL: device.model,
                CONF_SW_VERSION: device.sw_version,
            },
        )
