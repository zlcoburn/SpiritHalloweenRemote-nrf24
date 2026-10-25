import argparse
from dataclasses import asdict, replace
import json
import logging
import signal
import threading
from .config import RadioConfig
from .protocol import PAYLOADS, ADDRESS

def main():
    p = argparse.ArgumentParser(description='Spirit A–D transmitter. Defaults to a dry run; --send accesses hardware.')
    p.add_argument('button', type=str.upper, choices=list(PAYLOADS))
    p.add_argument('--send', action='store_true')
    p.add_argument('--power', choices=['min','low','high','max'])
    p.add_argument('--bursts', type=int)
    p.add_argument('--burst-seconds', type=float)
    p.add_argument('--gap-seconds', type=float)
    for name in ('spi-bus','spi-device','ce-gpio','gpio-chip'):
        p.add_argument('--'+name, type=int)
    a = p.parse_args()
    try:
        cfg = RadioConfig.from_env()
        cfg = replace(cfg, **{k:v for k,v in vars(a).items() if k not in ('button','send') and v is not None})
    except ValueError as exc:
        p.error(str(exc))
    plan = dict(button=a.button, mode='send' if a.send else 'dry-run; no hardware accessed',
        config=asdict(cfg), channel=65, rate_bps=250000, rf_setup_hex=f'{cfg.rf_setup:02x}',
        tx_address_register_hex=bytes(ADDRESS).hex(), wire_header_hex='aaddcccccccc',
        body_hex=PAYLOADS[a.button].hex(), receiver_acknowledgement=False)
    print(json.dumps(plan, indent=2), flush=True)
    if not a.send:
        return
    from .radio import SpiritRadio
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(message)s')
    stop = threading.Event()
    for sig in (signal.SIGINT, signal.SIGTERM):
        signal.signal(sig, lambda *_: stop.set())
    radio = SpiritRadio(stop, cfg)
    try:
        counts = radio.fire(a.button)
        print(json.dumps({'burst_packets':counts,'result':'transmitted; observe receiver to confirm activation'}))
    finally:
        radio.close()

if __name__ == '__main__':
    main()
