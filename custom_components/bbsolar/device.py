"""Local HTTP client for BBSolar devices (Meross protocol, bbsolar vendor)."""

from __future__ import annotations

import asyncio
import hashlib
import time
from typing import Any
from uuid import uuid4

import aiohttp

from .const import (
    LUMINANCE_CHANNELS,
    METHOD_GET,
    METHOD_SET,
    NS_ABILITY,
    NS_ALL,
    NS_LUMINANCE,
    NS_TOGGLEX,
    TOGGLE_CHANNEL_ALL,
)

REQUEST_TIMEOUT = aiohttp.ClientTimeout(total=10)


class BBSolarError(Exception):
    """Base error for BBSolar devices."""


class BBSolarConnectionError(BBSolarError):
    """Raised when the device cannot be reached."""


class BBSolarAuthError(BBSolarError):
    """Raised when the device rejects the key."""


class BBSolarProtocolError(BBSolarError):
    """Raised when the device reports an error."""


class BBSolarDevice:
    """Talk to a BBSolar light over the local Meross HTTP protocol."""

    def __init__(self, host: str, key: str, session: aiohttp.ClientSession) -> None:
        self.host = host
        self.uuid: str = ""
        self.model: str = ""
        self.sw_version: str = ""
        self._key = key
        self._session = session

    def _build_message(
        self, namespace: str, method: str, payload: dict[str, Any]
    ) -> dict[str, Any]:
        message_id = uuid4().hex
        timestamp = int(time.time())
        sign = hashlib.md5(
            f"{message_id}{self._key}{timestamp}".encode()
        ).hexdigest()
        return {
            "header": {
                "messageId": message_id,
                "namespace": namespace,
                "method": method,
                "payloadVersion": 1,
                "triggerSrc": "meross_lan",
                "from": "/appliance/meross_lan/publish",
                "timestamp": timestamp,
                "timestampMs": 0,
                "sign": sign,
            },
            "payload": payload,
        }

    async def async_request(
        self, namespace: str, method: str, payload: dict[str, Any]
    ) -> dict[str, Any]:
        message = self._build_message(namespace, method, payload)
        try:
            async with self._session.post(
                f"http://{self.host}/config",
                json=message,
                timeout=REQUEST_TIMEOUT,
            ) as response:
                if response.status != 200:
                    raise BBSolarConnectionError(
                        f"HTTP {response.status} from {self.host}"
                    )
                data = await response.json(content_type=None)
        except aiohttp.ClientError as err:
            raise BBSolarConnectionError(str(err)) from err
        except asyncio.TimeoutError as err:
            raise BBSolarConnectionError("request timed out") from err

        if not isinstance(data, dict):
            raise BBSolarProtocolError("malformed response")

        response_payload = data.get("payload") or {}
        error = response_payload.get("error")
        if error:
            if error.get("code") == 5001:
                raise BBSolarAuthError("invalid device key")
            raise BBSolarProtocolError(
                f"{error.get('code')}: {error.get('detail')}"
            )
        return response_payload

    async def async_probe(self) -> dict[str, Any]:
        ability_response = await self.async_request(NS_ABILITY, METHOD_GET, {})
        ability = ability_response.get("ability") or {}
        all_response = await self.async_request(NS_ALL, METHOD_GET, {})
        all_data = all_response.get("all") or {}
        system = all_data.get("system") or {}
        hardware = system.get("hardware") or {}
        firmware = system.get("firmware") or {}
        self.uuid = hardware.get("uuid") or ""
        self.model = hardware.get("type") or ""
        self.sw_version = firmware.get("version") or ""
        return ability

    async def async_update(self) -> dict[str, Any]:
        togglex_response = await self.async_request(
            NS_TOGGLEX, METHOD_GET, {"togglex": {"channel": TOGGLE_CHANNEL_ALL}}
        )
        toggles = {
            item["channel"]: bool(item.get("onoff"))
            for item in togglex_response.get("togglex") or []
        }

        luminance_response = await self.async_request(
            NS_LUMINANCE,
            METHOD_GET,
            {"control": [{"channel": channel} for channel in LUMINANCE_CHANNELS]},
        )
        luminance = {
            item["channel"]: item.get("value", 0)
            for item in luminance_response.get("control") or []
        }
        return {"toggles": toggles, "luminance": luminance}

    async def async_set_toggle(self, channel: int, onoff: bool) -> None:
        await self.async_request(
            NS_TOGGLEX,
            METHOD_SET,
            {"togglex": {"channel": channel, "onoff": 1 if onoff else 0}},
        )

    async def async_set_luminance(self, values: dict[int, int]) -> None:
        await self.async_request(
            NS_LUMINANCE,
            METHOD_SET,
            {
                "control": [
                    {"channel": channel, "value": int(value)}
                    for channel, value in values.items()
                ]
            },
        )
