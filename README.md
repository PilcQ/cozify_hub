# Cozify HUB — Home Assistant HACS Integration

A Home Assistant custom integration for the **Cozify HUB** smart home hub, installable via [HACS](https://hacs.xyz/).

## Features

- **Lights** — on/off, brightness, color (HS), color temperature
- **Sensors** — temperature, humidity
- **Binary Sensors** — motion, door/contact
- **Locks** — lock/unlock
- **Covers** — blinds/shades open, close, stop, set position
- Local polling (no cloud required after setup)
- UI-based configuration via Settings → Integrations

## Requirements

- Home Assistant 2024.1.0 or newer
- Cozify HUB on your local network
- Hub Token from the Cozify app

## Getting the Hub Token

1. Open the Cozify app or Web UI (`webui.cozify.fi`)
2. Go to **Settings → Hub**
3. Copy the **Hub Token** (also called the local API token)

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
3. Enter:
   - **Hub IP Address** — local IP of your Cozify HUB (e.g. `192.168.1.100`)
   - **Hub Token** — from the Cozify app
   - **Port** — default is `8893`

## Supported Device Types

| Capability | Platform |
|---|---|
| ON_OFF + BRIGHTNESS / COLOR_HS / COLOR_TEMPERATURE | `light` |
| TEMPERATURE | `sensor` |
| HUMIDITY | `sensor` |
| MOTION | `binary_sensor` |
| CONTACT | `binary_sensor` |
| LOCK | `lock` |
| COVER | `cover` |

## Troubleshooting

- Make sure your Cozify HUB is reachable at the IP you entered (try `ping <ip>`)
- Verify the hub token is correct — you can find it in the Cozify Web UI under Settings
- Check Home Assistant logs under **Settings → System → Logs** for detailed errors

## Contributing

Pull requests are welcome! Please open an issue first to discuss what you'd like to change.

## License

MIT
