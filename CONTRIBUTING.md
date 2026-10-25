# Contributing

Compatibility reports from independently purchased units are particularly useful. Include the product/year, board markings if known, radio/Pi model, wiring, CLI dry-run output, power level and trial counts. State whether the original remote works at the same position. Separate observations from proposed explanations.

Do not upload tokens, private keys, private Home Assistant configuration, or unrelated RF captures. Keep raw recordings outside Git; describe their sample format/rate/center frequency and provide selected anonymized evidence if sharing.

Before changing the payloads, preserve the captured defaults and add evidence for a separate profile. Do not generalize from a working nRF24-compatible replay to an identified radio chip, checksum or universal cross-unit compatibility.

Run `python -m unittest discover -s tests -v`. New transmitter behavior should include simulated-hardware checks. Hardware validation should be explicitly coordinated with the person observing the prop. No tests in CI should touch GPIO or transmit.
