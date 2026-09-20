"""Minimal client for the BBSolar cloud (Meross-based) account API."""

from __future__ import annotations

import base64
import hashlib
import json
import random
import string
import time
from typing import Any

import aiohttp

SECRET = "23x17ahWarFH6w29"
CLOUD_ENDPOINTS = (
    "https://iotx-eu.bbsolar.cc",
    "https://iotx-us.bbsolar.cc",
    "https://iotx-ap.bbsolar.cc",
)
REQUEST_TIMEOUT = aiohttp.ClientTimeout(total=15)

STATUS_OK = 0
STATUS_UNEXISTING_ACCOUNT = 1002
STATUS_WRONG_CREDENTIALS = 1004
STATUS_WRONG_EMAIL = 1008
STATUS_REDIRECT_REGION = 1030
STATUS_MFA_REQUIRED = 1033


class BBSolarCloudError(Exception):
    """Base error for the BBSolar cloud API."""


class BBSolarCloudAuthError(BBSolarCloudError):
    """Raised on invalid credentials or MFA requirements."""


def _encode_params(parameters: dict[str, Any]) -> str:
    return base64.b64encode(json.dumps(parameters).encode()).decode()


def _sign(timestamp: int, nonce: str, encoded_params: str) -> str:
    return hashlib.md5(
        f"{SECRET}{timestamp}{nonce}{encoded_params}".encode()
    ).hexdigest()


async def _async_post(
    session: aiohttp.ClientSession,
    url: str,
    params: dict[str, Any],
    token: str | None = None,
) -> dict[str, Any]:
    nonce = "".join(
        random.SystemRandom().choice(string.ascii_uppercase + string.digits)
        for _ in range(16)
    )
    timestamp = int(round(time.time() * 1000))
    encoded = _encode_params(params)
    payload = {
        "params": encoded,
        "sign": _sign(timestamp, nonce, encoded),
        "timestamp": timestamp,
        "nonce": nonce,
    }
    headers = {
        "AppVersion": "1.0.0",
        "AppType": "MerossIOT",
        "AppLanguage": "EN",
        "vendor": "bbsolar",
        "vender": "bbsolar",
        "Content-Type": "application/json",
        "Authorization": "Basic" + (f" {token}" if token else ""),
    }
    try:
        async with session.post(
            url, json=payload, headers=headers, timeout=REQUEST_TIMEOUT
        ) as response:
            data = await response.json(content_type=None)
    except (aiohttp.ClientError, TimeoutError) as err:
        raise BBSolarCloudError(str(err)) from err
    if not isinstance(data, dict):
        raise BBSolarCloudError("unexpected cloud response")
    return data


async def async_login(
    session: aiohttp.ClientSession, email: str, password: str
) -> dict[str, Any]:
    """Log in and return the cloud credentials, retrying on region redirects."""
    data = {
        "email": email,
        "password": hashlib.md5(password.encode()).hexdigest(),
        "accountCountryCode": "de",
        "encryption": 1,
        "agree": 1,
        "mobileInfo": {
            "deviceModel": "HomeAssistant",
            "mobileOsVersion": "1",
            "mobileOs": "Linux",
            "uuid": "bbsolar-homeassistant",
            "carrier": "",
        },
    }
    endpoints = list(CLOUD_ENDPOINTS)
    while endpoints:
        endpoint = endpoints.pop(0)
        response = await _async_post(
            session, f"{endpoint}/v1/Auth/signIn", data
        )
        status = response.get("apiStatus")
        if status == STATUS_OK:
            return response["data"]
        if status == STATUS_REDIRECT_REGION:
            domain = (response.get("data") or {}).get("domain")
            if domain:
                endpoints.insert(0, domain.rstrip("/"))
                continue
        if status in (
            STATUS_WRONG_CREDENTIALS,
            STATUS_WRONG_EMAIL,
            STATUS_UNEXISTING_ACCOUNT,
            STATUS_MFA_REQUIRED,
        ):
            raise BBSolarCloudAuthError(response.get("info") or "invalid credentials")
        raise BBSolarCloudError(response.get("info") or f"apiStatus {status}")
    raise BBSolarCloudError("no usable cloud endpoint")


async def async_list_devices(
    session: aiohttp.ClientSession, credentials: dict[str, Any]
) -> list[dict[str, Any]]:
    domain = (credentials.get("domain") or CLOUD_ENDPOINTS[0]).rstrip("/")
    response = await _async_post(
        session,
        f"{domain}/v1/Device/devList",
        {},
        token=credentials.get("token"),
    )
    status = response.get("apiStatus")
    if status != STATUS_OK:
        raise BBSolarCloudError(response.get("info") or f"apiStatus {status}")
    devices = response.get("data") or response.get("devList") or []
    if isinstance(devices, dict):
        devices = devices.get("devList") or devices.get("data") or []
    for device in devices:
        if not device.get("key"):
            device["key"] = credentials.get("key")
    return devices


async def async_logout(
    session: aiohttp.ClientSession, credentials: dict[str, Any]
) -> None:
    domain = (credentials.get("domain") or CLOUD_ENDPOINTS[0]).rstrip("/")
    try:
        await _async_post(
            session,
            f"{domain}/v1/Profile/logout",
            {},
            token=credentials.get("token"),
        )
    except BBSolarCloudError:
        pass
