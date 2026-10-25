# Spirit Halloween Remote — nRF24

> **Created with AI assistance.** Claude and OpenAI ChatGPT/Codex assisted with signal analysis, code generation, documentation, and packaging. The project owner operated the hardware and confirmed the reported receiver responses. AI assistance does not establish compatibility beyond the documented tests.

**`SpiritHalloweenRemote-nrf24`** is a Raspberry Pi transmitter template for firing the tested Spirit Halloween Multi-Prop receivers and compatible connected props.

Trigger the tested Spirit Halloween Multi-Prop receiver family from a Raspberry Pi and an nRF24L01+ radio. Includes captured **A, B, C and D** commands, a command-line transmitter, and an optional Home Assistant bridge with dashboard buttons.

**All four commands activated receivers in the original test setup.** The A receiver also activated a connected pumpkin prop at an unmeasured distance in three consecutive tests using spaced bursts. Compatibility with another retail unit or hardware revision is **not yet established**. This is a community template, not a universal transmitter for all Halloween products.

An SDR and downconverter were used to discover the messages. **Neither is needed to transmit them.** The radio sends the complete captured bodies; interpreting their checksum or scrambling is unnecessary for the demonstrated replay.

## What you need

- A Raspberry Pi running Linux with SPI and GPIO access. Tested on a Pi 3 with Raspberry Pi OS Bookworm.
- An nRF24L01+ capable of **250 kbit/s**. The original setup used a PA+LNA module with an SMA antenna. Other variants have not been range-tested here.
- A matching Spirit Multi-Prop receiver, powered and connected to its prop as intended by its manufacturer.
- A reliable supply appropriate for your radio module. The bare nRF24 supply is 3.3 V; do not apply 5 V to its VCC. Follow your specific breakout/adapter's input specification.

The supplied commands are for the tested receiver protocol. Activating other props depends on those props accepting the receiver's output; this project does not define a general-purpose relay interface.

## Wire the radio

Defaults reproduce the tested **SPI1** setup, not the more common SPI0 setup. GPIO numbers below use BCM numbering; physical pins refer to the 40-pin Pi header.

| nRF24 signal | BCM GPIO | Physical pin |
|---|---:|---:|
| CE | 22 | 15 |
| CSN (SPI1 CE0) | 18 | 12 |
| SCK | 21 | 40 |
| MOSI | 20 | 38 |
| MISO | 19 | 35 |
| VCC | 3.3 V supply | supply-dependent |
| GND | Ground | e.g. 6 |
| IRQ | unused | — |

Enable SPI1 with `dtoverlay=spi1-1cs` in the applicable Pi boot configuration and reboot when convenient. Verify that `/dev/spidev1.0` exists. See the [official Raspberry Pi configuration documentation](https://www.raspberrypi.com/documentation/computers/configuration.html).

An SPI0 example is `--spi-bus 0 --spi-device 0 --ce-gpio 25`, wired to SPI0's MOSI/MISO/SCLK/CE0 and a separate CE GPIO. Changing CLI numbers does not reconfigure the Pi's pin mux. GPIO-chip numbering can vary by Pi model/kernel; `--gpio-chip` is configurable. Pi 5 has not been verified.

## Install

Clone or extract this repository on the Pi, then from its root:

```sh
sudo apt update
sudo apt install python3-venv python3-dev build-essential
python3 -m venv .venv
.venv/bin/python -m pip install -e '.[hardware,ha]'
```

The Linux account running the transmitter needs access to the SPI and GPIO devices, commonly through the `spi` and `gpio` groups. Confirm your OS permissions rather than running a second radio owner as root.

## First transmission

Preview the settings without opening SPI or GPIO:

```sh
.venv/bin/spirit-nrf24 A
```

Set the receiver to A, connect a suitable prop, and explicitly transmit:

```sh
.venv/bin/spirit-nrf24 A --send
```

Replace A with B, C or D for the other captured commands. Defaults send **three four-second bursts with two-second silent gaps**, approximately 16 seconds total excluding lock waits. Multiple activations are possible depending on the receiver/prop. Defaults use the highest chip power setting; actual PA+LNA antenna output is not measured.

```sh
# One short test at lower power:
.venv/bin/spirit-nrf24 B --send --bursts 1 --burst-seconds 4 --power low
# Alternate SPI/CE wiring:
.venv/bin/spirit-nrf24 A --spi-bus 0 --spi-device 0 --ce-gpio 25
```

Only run **one process owning the nRF24 CE GPIO**. Stop an existing radio bridge in coordination with its owner before using the standalone CLI. A lock protects each burst, but a lock does not release another process's GPIO claim. The Home Assistant bridge owns the radio and serializes commands internally; do not launch the CLI beside it.

## Home Assistant

1. Create four Button helpers with entity IDs `input_button.prop_remote_a` through `input_button.prop_remote_d`, or merge [helpers.yaml](examples/home-assistant/helpers.yaml) into your HA configuration. Do not duplicate an existing YAML `input_button:` key. Validate/reload or restart as appropriate.
2. Add [dashboard.yaml](examples/home-assistant/dashboard.yaml) as a section in your dashboard's `sections` view. It uses standard HA cards, without custom frontend dependencies. For a card-based view, add its individual button cards instead.
3. Create a Home Assistant long-lived access token in your profile. Save it **on the Pi**, e.g. `/etc/spirit-nrf24/ha-token`, readable only by the bridge's account. Do not commit it.
4. Copy [the environment example](examples/systemd/spirit-nrf24.env.example) to `/etc/spirit-nrf24/bridge.env` and edit `HA_URL`, `HA_TOKEN_FILE`, and your wiring settings. For a foreground run, export those environment variables in your shell; the program does not automatically load an env file.
5. Start `.venv/bin/spirit-ha-bridge` in that environment, or install the [systemd example](examples/systemd/spirit-nrf24.service). Adjust `User`, groups and `/opt/spirit-nrf24` paths to your installation, then run `sudo systemctl daemon-reload` and `sudo systemctl enable --now spirit-nrf24`.
6. Press a dashboard button or call `input_button.press`. [automation.yaml](examples/home-assistant/automation.yaml) is an example HA script body.

The bridge listens via HA's [WebSocket API](https://contributors.home-assistant.io/core/internals/websocket-api/) and uses the [Button helper's timestamp state](https://www.home-assistant.io/integrations/input_button/). Reconnecting does not replay old presses. Different letters serialize in a bounded queue, repeated requests for an already-pending letter coalesce, and queued commands expire after 45 seconds.

Optional: set `PUMPKIN_TRIGGER_ENTITY=input_boolean.pumpkin_scare` to preserve an existing boolean-based automation. Turning it on sends A; the bridge resets it afterward. The default leaves this compatibility path disabled. Add your own arming and scheduling conditions to automations; direct dashboard buttons intentionally fire directly.

`sensor.spirit_prop_remote_bridge` shows transmission activity, last command and packet counts. **It cannot confirm reception or measure receiver battery health.** Its state is reported by this process and is not a guaranteed independent watchdog if the Pi crashes.

If another transmitter shares a supply, configure shared lock files consistently in every program (example provided in the env file). Locks are released during silent gaps. Lock timeout aborts rather than transmitting unlocked.

## Protocol and evidence

The demonstrated settings are **channel 65 (~2465 MHz), 250 kbit/s, address register bytes `CC CC CC CC DD`, CRC disabled, auto-ack disabled**, and the 22-byte command bodies in [protocol.py](src/spirit_nrf24/protocol.py). The resulting observed wire header is `AA DD CC CC CC CC`.

Read [protocol.md](docs/protocol.md) for the exact four bodies and [findings.md](docs/findings.md) for discovery, validation and limits. Two short packets observed in the native cycle and a common body were **not required for successful replay in the tested setup**. Field meanings, native checksum and chip identity remain unresolved.

## Troubleshooting and contributing

- Start nearby and compare with the original remote from the same position. Confirm the receiver's letter, power, prop connection and remote battery.
- `TX_DS` means the nRF24 finished sending; it does not mean the prop acted.
- If GPIO is busy, find the existing owner. Do not remove a lock file to bypass it.
- If readback fails, check wiring, SPI device selection and module supply.
- If range is intermittent, compare antenna placement and orientation, power, supply stability and RF conditions. A longer uninterrupted transmission was less consistent than spaced bursts in this setup; the cause is not established.
- If the original remote works but this does not, record the board/product revision and repeat controlled tests before concluding that every unit uses different codes.

Please report compatibility with the product name/year, board markings if available without modifying it, Pi/radio model, power setting, approximate distance/obstacles, original-remote comparison, and success count out of a stated number of trials. Never attach HA tokens, private keys or full private HA configuration.

```sh
python -m unittest discover -s tests -v
```

Tests use simulated hardware; they do not activate props. The reusable package preserves the demonstrated settings, but configurable variants require your own hardware validation. MIT licensed; no manufacturer affiliation.

