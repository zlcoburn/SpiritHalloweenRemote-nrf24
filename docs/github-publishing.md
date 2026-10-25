# Publishing this template

Repository name: `SpiritHalloweenRemote-nrf24`

Repository description: `Trigger Spirit Halloween Multi-Prop receivers from a Raspberry Pi nRF24 radio. Verified A–D commands, Home Assistant dashboard template, wiring, protocol notes, and tests.`

Repository: https://github.com/zlcoburn/SpiritHalloweenRemote-nrf24

This folder is the repository root. It contains an MIT license, Python package, tests, GitHub Actions workflow, protocol evidence and generic HA/systemd examples.

For contributors publishing a separate copy, review the README and license, create an empty repository in your own account, then adapt these commands from this folder:

```sh
git init -b main
git add .
git commit -m "Add verified Spirit A-D nRF24 replay template"
# Replace OWNER and REPOSITORY with your repository details:
git remote add origin https://github.com/zlcoburn/SpiritHalloweenRemote-nrf24.git
git push -u origin main
```

Suggested first-release text:

> Initial template for the tested Spirit Multi-Prop receiver family. Captured A–D bodies each activated a receiver using an nRF24 at 250 kbit/s. Includes a dry-run-first CLI, configurable wiring/power/timing, a Home Assistant bridge, dashboard examples, and protocol notes. Spaced bursts activated a connected pumpkin at range in three consecutive observed sequences. Compatibility with independently purchased units is unverified; reports are welcome. Receiver acknowledgements are not available.

Suggested topics: `home-assistant`, `halloween`, `nrf24l01`, `raspberry-pi`, `reverse-engineering`.

