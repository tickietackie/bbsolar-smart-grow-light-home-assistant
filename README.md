# BBSolar Smart Grow Light for Home Assistant

Local Home Assistant integration for the **BBSolar Smart Grow Light** (model `bgl120a`), the Meross sub-brand plant light that is otherwise only controllable through the BBSolar app.

The light speaks the Meross protocol locally, but dimming uses the `Appliance.Control.Luminance` namespace, which the [Meross LAN](https://github.com/krahabb/meross_lan) integration does not implement. This integration talks to the lamp directly — no cloud connection is needed after setup.

## Features

- Fully local: on/off, brightness and RGB colour
- Three light entities: **Main** (both strips), **Light A**, **Light B**
- Read-only diagnostic sensors for every LED channel (White, Blue, Red and the auxiliary channel), so changes made in the BBSolar app show up in Home Assistant and vice versa
- Setup via the BBSolar cloud account (looks up the local device key once) or manually with host + key
- DHCP discovery: the lamp can be configured straight from the *Discovered* card in Settings → Devices & Services

## Limitations

- Schedules, timers and the colour programs of the app are not re-implemented; use the app or Home Assistant automations
- The 4th ("Aux") LED channel is exposed read-only and is not modified

## Installation

[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=tickietackie&repository=bbsolar-smart-grow-light-home-assistant&category=integration)

1. Click the badge above, or add `https://github.com/tickietackie/bbsolar-smart-grow-light-home-assistant` as a custom repository in HACS (category *Integration*)
2. Install it and restart Home Assistant

<details>
<summary>Manual installation</summary>

Copy the `custom_components/bbsolar` folder into your `config/custom_components` directory and restart Home Assistant.
</details>

## Setup

Go to **Settings → Devices & Services → Add Integration → BBSolar Smart Grow Light**:

- **BBSolar cloud account** — sign in with the e-mail and password of the BBSolar app. The integration looks up the local device key from your account and then asks for the lamp's IP address or hostname.
- **Enter host and device key manually** — if you already have the device key (for example from an existing Meross LAN entry).
- **Discovered device** — if the lamp is found via DHCP, use the discovered card; the address is prefilled and the cloud login only needs the account credentials.

The cloud login is used once to read the device key; only the key is stored in Home Assistant. The lamp itself is then controlled entirely locally.

## How it works

The device is a Meross-protocol device hosted on the BBSolar cloud (`iotx-eu/us/ap.bbsolar.cc`) and exposes:

- `Appliance.Control.ToggleX` for on/off (channel 0 = both strips, 1 = Light A, 2 = Light B)
- `Appliance.Control.Luminance` for per-LED dimming (white/blue/red plus one auxiliary channel per strip)

Brightness maps to the white LED, RGB to the white/red/blue LEDs (the auxiliary channel is left untouched). Protocol insights came from the MerossIot work by [@jeremypm](https://github.com/jeremypm) (albertogeniola/MerossIot#414).

## Troubleshooting

- **Device not found via DHCP** — reboot the lamp or add it manually through the cloud account; the DHCP broadcast is only seen when the device renews its lease.
- **"The device rejected the key"** — sign in with the cloud account again; the key is tied to the account that owns the lamp in the BBSolar app.
- Enable debug logging for `custom_components.bbsolar` when opening an issue.
