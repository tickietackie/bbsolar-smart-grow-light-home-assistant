"""Config flow for the BBSolar Smart Grow Light integration."""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigFlow
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.device_registry import format_mac

from .cloud import (
    BBSolarCloudAuthError,
    BBSolarCloudError,
    async_list_devices,
    async_login,
    async_logout,
)
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

HOST_SUGGESTIONS = ("bbsolar",)


class BBSolarConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle the configuration of a BBSolar light."""

    VERSION = 1

    def __init__(self) -> None:
        self._discovery_host: str | None = None
        self._discovery_mac: str | None = None
        self._devices: list[dict[str, Any]] = []
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
            candidates.append(
                {
                    "host": host,
                    "key": key,
                    "uuid": data.get(MEROSS_LAN_DEVICE_ID) or "",
                    "title": entry.title,
                }
            )
        return candidates

    async def _async_create_entry(
        self, device: BBSolarDevice, host: str, key: str
    ) -> Any:
        await self.async_set_unique_id(device.uuid)
        self._abort_if_unique_id_configured(updates={CONF_HOST: host})
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

    async def _async_probe_and_create(
        self, host: str, key: str, errors: dict[str, str]
    ) -> Any | None:
        try:
            device = await self._async_probe(host, key)
        except BBSolarAuthError:
            errors["base"] = "invalid_key"
        except BBSolarProtocolError:
            errors["base"] = "not_supported"
        except BBSolarError:
            errors["base"] = "cannot_connect"
        else:
            return await self._async_create_entry(device, host, key)
        return None

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> Any:
        menu_options = ["cloud", "manual"]
        if self._find_meross_lan_devices():
            menu_options.insert(0, "meross_lan")
        return self.async_show_menu(step_id="user", menu_options=menu_options)

    async def async_step_dhcp(self, discovery_info: Any) -> Any:
        mac = format_mac(discovery_info.macaddress).replace(":", "")
        self._discovery_host = discovery_info.ip
        self._discovery_mac = mac
        await self.async_set_unique_id(mac, raise_on_progress=False)

        for entry in self.hass.config_entries.async_entries(DOMAIN):
            if not (entry.unique_id or "").lower().endswith(mac):
                continue
            if entry.data.get(CONF_HOST) == discovery_info.ip:
                return self.async_abort(reason="already_configured")
            try:
                device = await self._async_probe(
                    discovery_info.ip, entry.data[CONF_KEY]
                )
            except BBSolarError:
                return self.async_abort(reason="cannot_connect")
            if device.uuid.lower().endswith(mac):
                self.hass.config_entries.async_update_entry(
                    entry,
                    data={**entry.data, CONF_HOST: discovery_info.ip},
                )
                return self.async_abort(reason="already_configured")
            return self.async_abort(reason="cannot_connect")

        return await self.async_step_user()

    async def async_step_cloud(
        self, user_input: dict[str, Any] | None = None
    ) -> Any:
        errors: dict[str, str] = {}
        if user_input is not None:
            session = async_get_clientsession(self.hass)
            try:
                credentials = await async_login(
                    session, user_input["email"].strip(), user_input["password"]
                )
                devices = await async_list_devices(session, credentials)
                await async_logout(session, credentials)
            except BBSolarCloudAuthError:
                errors["base"] = "invalid_auth"
            except BBSolarCloudError:
                errors["base"] = "cannot_connect"
            else:
                self._devices = [device for device in devices if device.get("uuid")]
                if not self._devices:
                    errors["base"] = "no_devices"
                elif len(self._devices) == 1:
                    self._selected = self._devices[0]
                    return await self.async_step_host()
                else:
                    return await self.async_step_select_device()
        return self.async_show_form(
            step_id="cloud",
            data_schema=vol.Schema(
                {
                    vol.Required("email"): str,
                    vol.Required("password"): str,
                }
            ),
            errors=errors,
        )

    async def async_step_select_device(
        self, user_input: dict[str, Any] | None = None
    ) -> Any:
        if user_input is not None:
            selected = next(
                (
                    device
                    for device in self._devices
                    if device["uuid"] == user_input.get("device")
                ),
                None,
            )
            if selected is not None:
                self._selected = selected
                return await self.async_step_host()
            return self.async_abort(reason="cannot_connect")
        return self.async_show_form(
            step_id="select_device",
            data_schema=vol.Schema(
                {
                    vol.Required("device"): vol.In(
                        {
                            device["uuid"]: f"{device.get('devName')} "
                            f"({device.get('deviceType')})"
                            for device in self._devices
                        }
                    )
                }
            ),
        )

    async def async_step_host(
        self, user_input: dict[str, Any] | None = None
    ) -> Any:
        errors: dict[str, str] = {}
        if user_input is not None:
            result = await self._async_probe_and_create(
                user_input[CONF_HOST].strip(),
                self._selected["key"],
                errors,
            )
            if result is not None:
                return result
        mac = (self._selected.get("uuid") or "")[-12:].lower()
        suggested = (
            self._discovery_host
            if self._discovery_mac and mac == self._discovery_mac
            else None
        ) or HOST_SUGGESTIONS[0]
        return self.async_show_form(
            step_id="host",
            data_schema=vol.Schema(
                {vol.Required(CONF_HOST, default=suggested): str}
            ),
            errors=errors,
            description_placeholders={
                "name": str(self._selected.get("devName") or "")
            },
        )

    async def async_step_meross_lan(
        self, user_input: dict[str, Any] | None = None
    ) -> Any:
        candidates = self._find_meross_lan_devices()
        if not candidates:
            return self.async_abort(reason="cannot_connect")
        errors: dict[str, str] = {}
        if user_input is not None:
            selected = next(
                (
                    candidate
                    for candidate in candidates
                    if candidate["uuid"] == user_input.get("device", candidates[0]["uuid"])
                ),
                candidates[0],
            )
            if self._discovery_host and selected["uuid"][-12:].lower() == (
                self._discovery_mac or ""
            ):
                selected = {**selected, "host": self._discovery_host}
            return await self._async_probe_and_create(
                selected["host"], selected["key"], errors
            )
        schema: vol.Schema = vol.Schema({})
        if len(candidates) > 1:
            schema = vol.Schema(
                {
                    vol.Required("device"): vol.In(
                        {
                            candidate["uuid"]: candidate["title"]
                            for candidate in candidates
                        }
                    )
                }
            )
        return self.async_show_form(
            step_id="meross_lan",
            data_schema=schema,
            errors=errors,
            description_placeholders={"host": candidates[0]["host"]},
        )

    async def async_step_manual(
        self, user_input: dict[str, Any] | None = None
    ) -> Any:
        errors: dict[str, str] = {}
        if user_input is not None:
            result = await self._async_probe_and_create(
                user_input[CONF_HOST].strip(),
                user_input[CONF_KEY].strip(),
                errors,
            )
            if result is not None:
                return result
        return self.async_show_form(
            step_id="manual",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_HOST, default=self._discovery_host or HOST_SUGGESTIONS[0]
                    ): str,
                    vol.Required(CONF_KEY): str,
                }
            ),
            errors=errors,
        )
