#!/usr/bin/env python3
"""HA pumpkin trigger -> Spirit receiver A; dashboard input buttons -> A–D.

Configure HA_URL and HA_TOKEN_FILE. Radio owner serializes all
commands; three 4 s bursts with 2 s silent gaps. No micro:bit polling or traffic.
"""
import asyncio
import datetime
import json
import logging
import os
from urllib.parse import urlsplit, urlunsplit
import signal
import threading
import time
import urllib.request
from pathlib import Path
import websockets
from .radio import SpiritRadio
from .config import RadioConfig

BASE = os.environ.get('HA_URL', 'http://homeassistant.local:8123').rstrip('/')
parts = urlsplit(BASE)
if parts.scheme not in ('http', 'https') or not parts.netloc or parts.username or parts.password:
    raise ValueError('HA_URL must be an http(s) URL without embedded credentials')
WS = urlunsplit(('wss' if parts.scheme == 'https' else 'ws', parts.netloc, parts.path + '/api/websocket', '', ''))
TOKEN = Path(os.environ.get('HA_TOKEN_FILE', '/etc/spirit-nrf24/ha-token')).expanduser().read_text().strip()
if not TOKEN:
    raise ValueError('HA_TOKEN_FILE is empty')
PUMPKIN = os.environ.get('PUMPKIN_TRIGGER_ENTITY', '').strip()
PREFIX = os.environ.get('PROP_BUTTON_PREFIX', 'prop_remote')
BUTTONS = {f'input_button.{PREFIX}_{b.lower()}': b for b in 'ABCD'}
STATUS = 'sensor.spirit_prop_remote_bridge'
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(message)s')
log = logging.getLogger('pumpkin')

def rest(path, data):
    req = urllib.request.Request(BASE + path, data=json.dumps(data).encode(),
        headers={'Authorization': 'Bearer ' + TOKEN, 'Content-Type': 'application/json'})
    with urllib.request.urlopen(req, timeout=10) as response:
        return json.load(response)

class Bridge:
    def __init__(self):
        self.stop = threading.Event()
        self.radio = SpiritRadio(self.stop, RadioConfig.from_env())
        self.queue = asyncio.Queue(maxsize=4)
        self.pending = set()
        self.last = {}
        self.state = 'connecting'

    async def status(self, state=None, **attrs):
        if state is not None:
            self.state = state
        data = {'friendly_name': 'Prop Remote', 'icon': 'mdi:remote',
                'transport': 'Spirit nRF24', 'receiver_acknowledgement': False,
                'pending_buttons': sorted(self.pending), **self.last, **attrs}
        try:
            await asyncio.to_thread(rest, '/api/states/' + STATUS, {'state': self.state, 'attributes': data})
        except Exception as exc:
            log.warning('status update failed: %s', exc)

    async def reset_pumpkin(self):
        if not PUMPKIN:
            return
        try:
            await asyncio.to_thread(rest, '/api/services/input_boolean/turn_off', {'entity_id': PUMPKIN})
        except Exception as exc:
            log.warning('cannot reset pumpkin request: %s', exc)

    async def enqueue(self, button):
        if button in self.pending:
            log.info('coalesced duplicate button=%s', button)
            return
        if self.queue.full():
            log.warning('request queue full; ignoring button=%s', button)
            if button == 'A':
                await self.reset_pumpkin()
            return
        self.pending.add(button)
        self.queue.put_nowait((button, time.monotonic()))
        log.info('accepted button=%s pending=%s', button, sorted(self.pending))

    async def worker(self):
        while True:
            button, requested = await self.queue.get()
            try:
                if self.stop.is_set():
                    raise InterruptedError('service stopping; request discarded')
                if time.monotonic() - requested > 45:
                    raise TimeoutError('queued request expired; not transmitted')
                await self.status('transmitting', active_button=button)
                counts = await asyncio.to_thread(self.radio.fire, button)
                self.last = {'last_button': button, 'last_transmitted': datetime.datetime.now(datetime.timezone.utc).isoformat(),
                             'last_burst_packets': counts, 'last_result': 'transmitted; receiver response unconfirmed'}
                log.info('completed button=%s packets=%s (no receiver acknowledgement)', button, counts)
            except Exception as exc:
                self.last = {'last_button': button, 'last_result': 'error', 'last_error': str(exc)}
                log.exception('button=%s failed', button)
            finally:
                self.pending.discard(button)
                self.queue.task_done()
                if button == 'A':
                    await self.reset_pumpkin()
                await self.status('error' if self.last.get('last_result') == 'error' else 'idle')

    async def heartbeat(self):
        while not self.stop.is_set():
            await self.status()
            await asyncio.sleep(30)

    async def session(self):
        async with websockets.connect(WS, ping_interval=20, ping_timeout=20) as ws:
            await ws.recv()
            await ws.send(json.dumps({'type': 'auth', 'access_token': TOKEN}))
            if json.loads(await ws.recv())['type'] != 'auth_ok':
                raise RuntimeError('HA authentication failed')
            subscriptions = {}
            entities = {**({PUMPKIN: 'A'} if PUMPKIN else {}), **BUTTONS}
            for i, (entity, button) in enumerate(entities.items(), 1):
                trigger = {'platform': 'state', 'entity_id': entity}
                if entity == PUMPKIN:
                    trigger['to'] = 'on'
                await ws.send(json.dumps({'id': i, 'type': 'subscribe_trigger', 'trigger': trigger}))
                result = json.loads(await ws.recv())
                if not result.get('success'):
                    raise RuntimeError('subscription failed: ' + str(result.get('error')))
                subscriptions[i] = (entity, button)
            # Do not replay stale button presses or a restored pumpkin boolean after reconnect.
            if 'A' not in self.pending:
                await self.reset_pumpkin()
            if self.state == 'connecting':
                await self.status('idle')
            log.info('connected; pumpkin -> Spirit A; prop buttons A–D ready')
            async for raw in ws:
                msg = json.loads(raw)
                if msg.get('type') != 'event' or msg.get('id') not in subscriptions:
                    continue
                entity, button = subscriptions[msg['id']]
                trigger = msg.get('event', {}).get('variables', {}).get('trigger', {})
                old, new = trigger.get('from_state'), trigger.get('to_state')
                if not old or not new or old.get('state') == new.get('state'):
                    continue
                if new.get('state') in ('unknown', 'unavailable'):
                    continue
                if entity == PUMPKIN and new['state'] != 'on':
                    continue
                await self.enqueue(button)

    async def run(self):
        loop = asyncio.get_running_loop()
        exiting = asyncio.Event()
        def shutdown():
            self.stop.set()
            exiting.set()
        for sig in (signal.SIGINT, signal.SIGTERM):
            loop.add_signal_handler(sig, shutdown)
        worker = asyncio.create_task(self.worker())
        heartbeat = asyncio.create_task(self.heartbeat())
        async def connect():
            while not self.stop.is_set():
                try:
                    await self.session()
                except Exception as exc:
                    log.warning('HA disconnected: %s; reconnect in 10 s', exc)
                await asyncio.sleep(10)
        connection = asyncio.create_task(connect())
        await exiting.wait()
        connection.cancel()
        heartbeat.cancel()
        # Let the hardware thread see stop and lower CE before closing its handles.
        if self.pending:
            try:
                await asyncio.wait_for(self.queue.join(), timeout=15)
            except asyncio.TimeoutError:
                log.error('shutdown timed out waiting for transmitter')
        worker.cancel()
        await asyncio.gather(connection, heartbeat, worker, return_exceptions=True)
        self.radio.close()
        await self.status('offline')

def main():
    asyncio.run(Bridge().run())

if __name__ == '__main__':
    main()
