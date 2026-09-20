"""Grow-light presets for the BBSolar Smart Grow Light integration.

Channel values are percentages of the preset level (0-100 each for the
white, red and blue LED strings). The ratios follow common horticultural
recommendations: blue-leaning for propagation/seedlings, balanced for
vegetative growth and leafy greens, red-dominant (roughly 3:1 to 4:1
red:blue) for flowering and fruiting.
"""

from __future__ import annotations

from typing import Any

PRESETS: tuple[dict[str, Any], ...] = (
    {
        "name": "Full Spectrum",
        "white": 100,
        "red": 80,
        "blue": 45,
        "level": 100,
    },
    {
        "name": "Warm White (factory)",
        "white": 100,
        "red": 83,
        "blue": 0,
        "level": 100,
    },
    {
        "name": "Seedlings & Clones",
        "white": 60,
        "red": 25,
        "blue": 75,
        "level": 50,
    },
    {
        "name": "Vegetative Growth",
        "white": 70,
        "red": 55,
        "blue": 70,
        "level": 80,
    },
    {
        "name": "Leafy Greens & Herbs",
        "white": 85,
        "red": 70,
        "blue": 55,
        "level": 75,
    },
    {
        "name": "Microgreens",
        "white": 60,
        "red": 45,
        "blue": 85,
        "level": 70,
    },
    {
        "name": "Bloom & Flowering",
        "white": 35,
        "red": 100,
        "blue": 25,
        "level": 100,
    },
    {
        "name": "Tomatoes & Peppers",
        "white": 55,
        "red": 100,
        "blue": 45,
        "level": 100,
    },
    {
        "name": "Succulents & Cacti",
        "white": 100,
        "red": 90,
        "blue": 70,
        "level": 100,
    },
    {
        "name": "Orchids & Houseplants",
        "white": 90,
        "red": 55,
        "blue": 45,
        "level": 60,
    },
    {
        "name": "Red Boost",
        "white": 30,
        "red": 100,
        "blue": 10,
        "level": 100,
    },
    {
        "name": "Blue Boost",
        "white": 30,
        "red": 10,
        "blue": 100,
        "level": 100,
    },
    {
        "name": "All LEDs (max)",
        "white": 100,
        "red": 100,
        "blue": 100,
        "level": 100,
    },
)

PRESET_BY_NAME = {preset["name"]: preset for preset in PRESETS}
PRESET_NAMES = tuple(PRESET_BY_NAME)

MATCH_TOLERANCE = 0.08


def _normalized(white: int, red: int, blue: int) -> tuple[float, float, float] | None:
    peak = max(white, red, blue)
    if peak <= 0:
        return None
    return (white / peak, red / peak, blue / peak)


def matches_preset(
    channels: tuple[int, int, int], preset: dict[str, Any]
) -> bool:
    current = _normalized(*channels)
    reference = _normalized(preset["white"], preset["red"], preset["blue"])
    if current is None or reference is None:
        return False
    return all(
        abs(current[index] - reference[index]) <= MATCH_TOLERANCE
        for index in range(3)
    )


def match_preset(strips: list[tuple[int, int, int]]) -> str | None:
    if not strips:
        return None
    for preset in PRESETS:
        if all(matches_preset(channels, preset) for channels in strips):
            return preset["name"]
    return None


def preset_channels(preset: dict[str, Any], level: int) -> dict[str, int]:
    return {
        color: round(preset[color] * level / 100)
        for color in ("white", "red", "blue")
    }
