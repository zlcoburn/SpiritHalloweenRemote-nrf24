"""Radio configuration. Defaults reproduce the tested SPI1/GPIO22 setup."""
from dataclasses import dataclass
import math
import os

@dataclass(frozen=True)
class RadioConfig:
    spi_bus: int = 1
    spi_device: int = 0
    ce_gpio: int = 22
    gpio_chip: int = 0
    power: str = 'max'
    bursts: int = 3
    burst_seconds: float = 4.0
    gap_seconds: float = 2.0
    period: float = .00160235
    lock_files: tuple = ('/tmp/nrf24.lock',)

    def __post_init__(self):
        if self.power not in ('min', 'low', 'high', 'max'):
            raise ValueError('power must be min, low, high or max')
        if any(v < 0 for v in (self.spi_bus, self.spi_device, self.ce_gpio, self.gpio_chip)):
            raise ValueError('bus, device and GPIO values must be nonnegative')
        if not 1 <= self.bursts <= 10:
            raise ValueError('bursts must be 1..10')
        if not math.isfinite(self.burst_seconds) or not .05 <= self.burst_seconds <= 30:
            raise ValueError('burst seconds must be .05..30')
        if not math.isfinite(self.gap_seconds) or not 0 <= self.gap_seconds <= 60:
            raise ValueError('gap seconds must be 0..60')
        if not math.isfinite(self.period) or self.period < .001:
            raise ValueError('packet period must be at least .001 seconds')
        if not self.lock_files or any(not p.startswith('/') for p in self.lock_files):
            raise ValueError('at least one absolute lock path is required')

    @property
    def rf_setup(self):
        return 0x20 | {'min': 0, 'low': 2, 'high': 4, 'max': 6}[self.power]

    @classmethod
    def from_env(cls):
        return cls(spi_bus=int(os.getenv('NRF24_SPI_BUS', '1')),
            spi_device=int(os.getenv('NRF24_SPI_DEVICE', '0')),
            ce_gpio=int(os.getenv('NRF24_CE_GPIO', '22')),
            gpio_chip=int(os.getenv('NRF24_GPIO_CHIP', '0')),
            power=os.getenv('NRF24_POWER', 'max'),
            bursts=int(os.getenv('PROP_BURSTS', '3')),
            burst_seconds=float(os.getenv('PROP_BURST_SECONDS', '4')),
            gap_seconds=float(os.getenv('PROP_GAP_SECONDS', '2')),
            lock_files=tuple(p.strip() for p in os.getenv('NRF24_LOCK_FILES', '/tmp/nrf24.lock').split(',') if p.strip()))
