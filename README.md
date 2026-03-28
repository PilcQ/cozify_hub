[![Current release](https://img.shields.io/github/v/release/PilcQ/cozify_hub?style=plastic&label=Current%20release&include_prereleases)](https://github.com/PilcQ/cozify_hub)
[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg?style=plastic)](https://github.com/hacs/integration)
[![Stars](https://img.shields.io/github/stars/PilcQ/cozify_hub?style=plastic)](https://github.com/PilcQ/cozify_hub/stargazers)
[![Last Commit](https://img.shields.io/github/last-commit/PilcQ/cozify_hub?style=plastic)](https://github.com/PilcQ/cozify_hub/commits/main)
[![License](https://img.shields.io/github/license/PilcQ/cozify_hub?style=plastic)](https://github.com/PilcQ/cozify_hub/blob/main/LICENSE)
<br />

This is still a work in progress, once more complite will be moved to official GitRepo. Still please try and let us know what you think.

# Cozify HUB — Home Assistant HACS Integration

A Home Assistant custom integration for the **Cozify HUB** smart home hub, installable via [HACS](https://hacs.xyz/).

## Features

- **Lights** — on/off, brightness, color (HS), color temperature
- **Sensors** — temperature, humidity, pressure, power monitoring
- **Binary Sensors** — motion, door/contact
- **Locks** — lock/unlock
- **Covers** — blinds/shades open, close, stop, set position
- Local polling every 30 seconds (no cloud dependency after setup)
- UI-based configuration via Settings → Integrations

![Example view of the Cozify HUB Home Assistant](images/Cozify_HUB_Home_Assistant.png)

## Requirements

- Home Assistant 2024.1.0 or newer
- Cozify HUB on your local network
- A Cozify account (email + OTP login)

## Installation via HACS

1. Open HACS in Home Assistant
2. Go to **Integrations** → click the three-dot menu → **Custom repositories**
3. Add `https://github.com/PilcQ/cozify_hub` as an **Integration**
4. Search for **Cozify HUB** and install it
5. Restart Home Assistant

## Manual Installation

1. Copy the `custom_components/cozify_hub` folder into your HA `config/custom_components/` directory
2. Restart Home Assistant

## Configuration

1. Go to **Settings → Devices & Services → Add Integration**
2. Search for **Cozify HUB**
3. Enter your **Cozify account email** and the **local IP address** of your hub (e.g. `192.168.1.75`)
4. Check your email — an OTP code will be sent to you
5. Enter the OTP code in the next step
6. The integration will connect, verify your hub and save everything automatically

> **Note:** The OTP is single-use and expires quickly. Enter it promptly after receiving it.

## How Authentication Works

The integration uses a two-step authentication flow:

1. Your email and hub IP are verified — the hub is pinged locally and an OTP is sent to your email via the Cozify cloud (`cloud2.cozify.fi`)
2. You enter the OTP — the integration logs in to get a cloud token, then fetches a hub-specific local token from the cloud
3. The hub-specific token is stored and used for all local API calls to your hub

After setup, all device communication happens **locally** on your network. No cloud dependency for normal operation.

## Supported Device Types

| Capability | Platform |
|---|---|
| ON_OFF + BRIGHTNESS / COLOR_HS / COLOR_TEMPERATURE | `light` |
| TEMPERATURE | `sensor` |
| HUMIDITY | `sensor` |
| PRESSURE | `sensor` |
| ACTIVE_POWER | `sensor` |
| MEASURE_POWER | `sensor` |
| MOTION | `binary_sensor` |
| CONTACT | `binary_sensor` |
| LOCK | `lock` |
| COVER | `cover` |

## Troubleshooting

- **Cannot connect** — make sure your Cozify HUB is reachable at the IP you entered. Try `http://<ip>:8893/hub` in your browser — it should return JSON.
- **Invalid OTP** — OTPs are single-use and expire quickly. Start the setup again to request a new one.
- **Already configured** — if you see this, the integration was already set up successfully. Close the dialog and check Settings → Devices & Services.
- Check Home Assistant logs under **Settings → System → Logs** and filter for `cozify_hub` for detailed errors.

## Debug Logging

Add to `configuration.yaml` for detailed logs:

```yaml
logger:
  default: warning
  logs:
    custom_components.cozify_hub: debug
```

## Contributing

Pull requests are welcome! Please open an issue first to discuss what you'd like to change.

## Cozify HUB

Cozify HAN is a Nordic, Finnish key-flag product that supports the most modern wireless automation technologies and traditional property automation standards. 
The hardware and software configurations are modularly selectable and will vary between different models (DIN, ZEN, ION).

### Key features

- System maintains operational capability in case of errors with the help of HW-level watchdog. Built-in HW watchdog self-heals the system from sw/hw jams
- Offers two-way, real-time, expandable, and continuously increasing support for different building automation technologies
- Internal backup battery for electrical outages
- Example protocols: BACnet/IP, oBIX, KNX, System vendors' HTTP/REST- and Websocket-interfaces
- No cloud dependency for normal operation
- More: `https://en.cozify.fi/pages/iot-controllers`

### Wireless protocols

- Z-Wave, Zigbee 3.0, On/Off Keying, Somfy RTS

### Wired protocol

- Modbus RTU, M-Bus, BACnet/IP, HTTPS/REST

### External connectors

- 2 x 10/100 Mbps Ethernet, RS-232, RS-485, M-Bus, DI (3-12V / GND), USB 2.0 Host, Type A

### Radios

-4 x 2.5Ghz, Z-Wave, 433Mhz, 868Mhz, Optional 4/5G Cellular modem
-External antennas for selected radios

### Internal Connectors

-PCIe Connector, Raspberry Pi 40 pin GPIO header

### Development and Support

This is a community-driven integration. If you find any bugs or want to improve it further, please create an "Issue" on GitHub.

---
*Note: This integration is (SOON) officially supported by Cozify Oy. You are already welcome to try this...*
