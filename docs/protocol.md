# Observed command format

All hex below uses the decoder's positive-frequency-shift = 1 convention. These bytes were independently recovered from raw recordings, then transmitted using an nRF24 and observed to activate the corresponding receivers.

| Setting | Demonstrated value |
|---|---|
| RF channel | 65, nominally 2465 MHz |
| Bit rate | 250 kbit/s; 4 microseconds per bit |
| RF_SETUP, maximum chip power | `0x26` |
| Address width | 5 bytes |
| TX_ADDR register byte sequence | `CC CC CC CC DD` |
| Observed preamble + address on air | `AA DD CC CC CC CC` |
| Body length | 22 bytes / 176 bits |
| nRF24 CRC / auto-ack / retransmissions | disabled |
| Target packet-start period within a burst | 1.60235 ms; Linux scheduling is not hard real-time |
| Tested range sequence | 3 × 4 s bursts, with 2 s silence between |

## Complete bodies

```text
A  DF F0 4F 81 3F A1 CC 24 57 5E 4B 9C 0E E9 EA 41 AA 36 0A 54 7B F2
B  DF F0 4F 81 3F A1 CC 24 57 5E 4B 9C 0E E9 FB 40 A2 BE 7A DC 8A D1
C  DF F0 4F 81 3F A1 CC 24 57 5E 4B 9C 0E E9 D9 70 2A BE A2 C2 2C 34
D  DF F0 4F 81 3F A1 CC 24 57 5E 4B 9C 0E E9 FA 63 2A BE F2 2C A9 32
```

A fifth common body observed around button-specific intervals was:

```text
DF F0 4F 81 3F A1 CC 24 57 5E 4B 9C 0E E9 EA 50 2A BE 5D 73 35 4D
```

Its purpose is unresolved. The replay sends only the selected button-specific body. Do not label individual differing bytes as the button ID, checksum, rolling code or encryption without further evidence. The constant portion may include device-specific information; cross-unit compatibility has not been tested.

Native remote recordings contain roughly 228 microsecond short packets and 996 microsecond long packets. Short packets principally contain the same header. A typical cycle has two short and four long packets over about 8 ms. The successful replay repeats long frames and omits short frames, the common body, and exact native carrier lead-in behavior.

The configured nRF24 frame is legacy ShockBurst-like (auto-ack disabled), not an ESB transaction requiring a receiver acknowledgement. Do not insert a nine-bit packet-control field or enable nRF24 CRC around the captured body. Known reference captures from this configured radio place payload immediately after the address.

The Nordic chip power steps are −18/−12/−6/0 dBm (`min/low/high/max`). An external PA or a compatible clone can change actual radiated output. See the [Nordic nRF24L01+ specification](https://docs-be.nordicsemi.com/bundle/nRF24L01P_PS_v1.0/raw/resource/enus/nRF24L01P_PS_v1.0.pdf).
