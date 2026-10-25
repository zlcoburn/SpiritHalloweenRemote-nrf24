"""Single-owner nRF24 Spirit transmitter. No micro:bit traffic or receiver acknowledgement."""
import contextlib
import logging
import threading
import time

from .protocol import PAYLOADS, ADDRESS
from .config import RadioConfig
log = logging.getLogger('spirit')

@contextlib.contextmanager
def radio_locks(stop, lock_files):
    import fcntl
    acquired = []
    try:
        for path in lock_files:
            timeout = 20
            f = open(path, 'a')
            acquired.append(f)
            deadline = time.monotonic() + timeout
            while True:
                if stop.is_set():
                    raise InterruptedError('service stopping')
                try:
                    fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)
                    break
                except BlockingIOError:
                    if time.monotonic() >= deadline:
                        raise TimeoutError('radio busy: ' + path)
                    stop.wait(.02)
        yield
    finally:
        for f in reversed(acquired):
            f.close()

class SpiritRadio:
    def __init__(self, stop=None, config=None):
        self.config = config or RadioConfig()
        self.stop = stop if stop is not None else threading.Event()
        self.spi = self.gpio = self.hw = None

    def write(self, reg, value):
        self.spi.xfer2([0x20 | reg] + (value if isinstance(value, list) else [value]))

    def read(self, reg, size=1):
        return self.spi.xfer2([reg] + [255] * size)[1:]

    def configure(self):
        if self.spi is None:
            import spidev, lgpio
            self.hw = lgpio
            self.spi = spidev.SpiDev()
            try:
                self.spi.open(self.config.spi_bus, self.config.spi_device)
                self.spi.max_speed_hz = 4000000
                self.spi.mode = 0
                self.gpio = lgpio.gpiochip_open(self.config.gpio_chip)
                lgpio.gpio_claim_output(self.gpio, self.config.ce_gpio, 0)
            except Exception:
                self.close()
                raise
        settings = {0: 0, 1: 0, 2: 0, 3: 3, 4: 0, 5: 65, 6: self.config.rf_setup, 0x1c: 0, 0x1d: 0}
        for reg, value in settings.items():
            self.write(reg, value)
        self.write(0x10, ADDRESS)
        for reg, value in settings.items():
            if self.read(reg)[0] != value:
                raise RuntimeError(f'radio register {reg:#x} readback mismatch')
        if self.read(0x10, 5) != ADDRESS:
            raise RuntimeError('radio address readback mismatch')
        self.spi.xfer2([0xe1])
        self.spi.xfer2([0xe2])
        self.write(7, 0x70)
        self.write(0, 2)
        time.sleep(.005)

    def burst(self, button):
        count = 0
        with radio_locks(self.stop, self.config.lock_files):
            try:
                self.configure()
                start = time.monotonic()
                deadline = start + self.config.burst_seconds
                next_send = start
                while time.monotonic() + .025 < deadline:
                    if self.stop.wait(max(0, next_send - time.monotonic())):
                        raise InterruptedError('service stopping')
                    if time.monotonic() + .025 >= deadline:
                        break
                    self.write(7, 0x70)
                    self.spi.xfer2([0xe1])
                    self.spi.xfer2([0xa0] + list(PAYLOADS[button]))
                    self.hw.gpio_write(self.gpio, self.config.ce_gpio, 1)
                    time.sleep(.00002)
                    self.hw.gpio_write(self.gpio, self.config.ce_gpio, 0)
                    limit = time.monotonic() + .02
                    while True:
                        status = self.read(7)[0]
                        if status & 0x10:
                            raise RuntimeError('unexpected MAX_RT')
                        if status & 0x20:
                            break
                        if self.stop.is_set() or time.monotonic() >= limit:
                            raise RuntimeError('TX completion timeout or stopping')
                    count += 1
                    next_send = max(next_send + self.config.period, time.monotonic())
            finally:
                self.power_down()
        return count

    def fire(self, button):
        if button not in PAYLOADS:
            raise ValueError('button must be A, B, C or D')
        counts = []
        try:
            for i in range(self.config.bursts):
                if self.stop.is_set():
                    raise InterruptedError('service stopping')
                counts.append(self.burst(button))
                log.info('button=%s burst=%d/%d packets=%d', button, i + 1, self.config.bursts, counts[-1])
                # Release both RF/power locks during silent gaps so fog can proceed.
                if i + 1 < self.config.bursts and self.stop.wait(self.config.gap_seconds):
                    raise InterruptedError('service stopping')
        except Exception:
            self.close()
            raise
        return counts

    def power_down(self):
        if self.gpio is not None and self.hw is not None:
            self.hw.gpio_write(self.gpio, self.config.ce_gpio, 0)
        if self.spi is not None:
            self.write(0, 0)
            self.spi.xfer2([0xe1])

    def close(self):
        try:
            self.power_down()
        finally:
            if self.spi is not None:
                self.spi.close()
            if self.gpio is not None and self.hw is not None:
                self.hw.gpiochip_close(self.gpio)
            self.spi = self.gpio = None
