# Discovery and validation

## What was tested

One original four-button Spirit Multi-Prop remote and the associated receiver setup. Notes identify transmitter PCB `YJ129-002` and receiver PCB `XJ078-002`; the receiver marking comes from the handoff notes rather than a new independent board inspection. An unmarked radio chip and a 16 MHz reference crystal do not establish its manufacturer or RF frequency. No soldering or remote modification was needed for this replay.

The original deployment uses a Pi 3, nRF24L01+ PA+LNA on SPI1, CE BCM22, Raspberry Pi OS Bookworm, spidev 3.5 and lgpio 0.2.2. All A–D receiver commands produced user-confirmed clicks. Receiver A connected to a pumpkin prop activated in three consecutive spaced-burst range sequences. Exact distance and per-individual-burst success were not recorded.

## How the decoding changed

Early nRF24 sniffing located activity near 2465 MHz but produced incomplete and misleading fragments. An apparent 2 Mbit alternating wake-up sequence was not established. Earlier 315 MHz results belonged to an unrelated transmitter and were excluded.

An RTL-SDR plus a Ham It Down downconverter recorded the native 2.4 GHz signal at about 965 MHz IF. A conventional RTL-SDR cannot directly receive this 2.4 GHz signal. Ham It Up is not a substitute for the downconverter. Powering the downconverter is essential; one unpowered calibration was flat and excluded.

The older decoder assumed approximately 1 Mbit/s and used a peak/median-power gate that rejected much of the sustained, high-duty-cycle signal. A blind timing search instead favored **250 kbit/s**. A fixed-clock, two-level FSK decoder then produced stable repeated data. Native frames previously interpreted as variable became overwhelmingly identical templates. The decoder does not replace packets with a known template.

## Independent checks

| Recording/check | Result |
|---|---|
| Wide A–D recording | 6,791 long packets with exact common header; complete modal bodies: A 875, B 718, C 884, D 871, common 3,428 |
| Separate A-only recording | A body exact 1,325 times; common body exact 788 times |
| Separate A–D recording | A 1,788; B 1,253; C 988; D 619; common 3,127 exact complete bodies |
| Known nRF24 reference | 30/30 payload + CRC correct at 1 Mbit/s; 30/30 at 2 Mbit/s |
| New 250 kbit/s reference | 97/100 candidate packets with exact known 32-byte payload and CRC16 |
| Simultaneous SDR capture of A replay | 96/100 candidate packets match entire preamble/address/body exactly |
| Physical A, B, C and D replay | Each corresponding receiver clicked, confirmed by user |
| A with connected pumpkin at range | Three consecutive successful 3-burst sequences, after intermittent continuous-burst results |

These are candidate/observed counts from particular recordings, not an RF bit-error-rate study. Integrated-symbol frequency estimates were similar between nRF24 and remote; they are not calibrated settled-tone deviation measurements.

## Limits

- No second independently purchased remote/receiver set has been tested. Shared codes across every unit are not proven.
- Chip identity, native field meanings, checksum and possible scrambling remain unresolved. Complete captured-body replay works without resolving them.
- No receiver acknowledgement exists in this implementation. Sending successfully is not proof that a prop moved.
- Three successful sequences support this operating pattern; they do not establish why gaps helped or guarantee range.
- Generic package configuration options and the stock-card dashboard example are adaptations of the working deployment. A–D replay and the deployed HA bridge were tested; each new installation still needs hardware validation.

## Included evidence

`evidence/command-templates.json` contains the four exact bodies and counts above, plus the shared observed header. Raw IQ recordings, personal network configuration, original private HA dashboards and unrelated captures are deliberately not included. The evidence is sufficient to document the transmitted messages, but does not independently reproduce every DSP analysis from the original raw recordings.
