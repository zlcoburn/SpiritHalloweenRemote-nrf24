import contextlib
import io
import json
import os
from pathlib import Path
import sys
import threading
import types
import unittest
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from spirit_nrf24.config import RadioConfig
from spirit_nrf24.protocol import PAYLOADS, ADDRESS
from spirit_nrf24.radio import SpiritRadio, radio_locks
from spirit_nrf24.cli import main

class TemplateTests(unittest.TestCase):
    def test_exact_captured_frames(self):
        expected = {
            'A':'dff04f813fa1cc24575e4b9c0ee9ea41aa360a547bf2',
            'B':'dff04f813fa1cc24575e4b9c0ee9fb40a2be7adc8ad1',
            'C':'dff04f813fa1cc24575e4b9c0ee9d9702abea2c22c34',
            'D':'dff04f813fa1cc24575e4b9c0ee9fa632abef22ca932'}
        self.assertEqual({k:v.hex() for k,v in PAYLOADS.items()},expected)
        self.assertEqual(ADDRESS,[204,204,204,204,221])

    def test_config_validation_and_power(self):
        self.assertEqual([RadioConfig(power=p).rf_setup for p in ('min','low','high','max')],[32,34,36,38])
        for kw in ({'bursts':0},{'burst_seconds':float('nan')},{'gap_seconds':-1},{'ce_gpio':-1},{'lock_files':()}):
            with self.subTest(kw=kw),self.assertRaises(ValueError):RadioConfig(**kw)

    def test_environment_and_cli_dry_run_no_hardware(self):
        out=io.StringIO()
        with patch.dict(os.environ,{'NRF24_SPI_BUS':'0','NRF24_CE_GPIO':'25'},clear=True),patch.object(sys,'argv',['spirit-nrf24','b','--power','low']),contextlib.redirect_stdout(out):
            main()
        result=json.loads(out.getvalue())
        self.assertEqual(result['config']['spi_bus'],0)
        self.assertEqual(result['config']['ce_gpio'],25)
        self.assertEqual(result['rf_setup_hex'],'22')
        self.assertEqual(result['body_hex'],PAYLOADS['B'].hex())
        self.assertIn('no hardware',result['mode'])

    def test_burst_and_gap_sequence(self):
        r=SpiritRadio();waits=[]
        with patch.object(r,'burst',return_value=2478) as burst,patch.object(r.stop,'wait',side_effect=lambda n:waits.append(n) or False):
            self.assertEqual(r.fire('D'),[2478]*3)
            self.assertEqual([c.args for c in burst.call_args_list],[('D',)]*3)
            self.assertEqual(waits,[2,2])

    def test_cancelled_or_invalid_never_sends(self):
        stop=threading.Event();stop.set();r=SpiritRadio(stop)
        with patch.object(r,'burst') as burst:
            with self.assertRaises(ValueError):r.fire('E')
            with self.assertRaises(InterruptedError):r.fire('A')
            burst.assert_not_called()

    def test_configure_and_readback_failure(self):
        class SPI:
            def __init__(self):self.regs={}
            def xfer2(self,a):
                if 0x20<=a[0]<0x40:
                    self.regs[a[0]&31]=a[1:];return [0]*len(a)
                return [0]+self.regs.get(a[0],[0]*(len(a)-1))
        r=SpiritRadio(config=RadioConfig(power='high'));r.spi=SPI()
        with patch('spirit_nrf24.radio.time.sleep'):r.configure()
        self.assertEqual(r.spi.regs[6],[0x24]);self.assertEqual(r.spi.regs[5],[65])
        self.assertEqual(r.spi.regs[0x10],ADDRESS);self.assertEqual(r.spi.regs[0],[2])
        with patch.object(r,'read',return_value=[255]),self.assertRaises(RuntimeError):r.configure()

    def test_lock_timeout_aborts_and_closes_file(self):
        fake=types.SimpleNamespace(LOCK_EX=2,LOCK_NB=4,flock=Mock(side_effect=BlockingIOError))
        stop=Mock();stop.is_set.return_value=False
        with patch.dict(sys.modules,{'fcntl':fake}),patch('builtins.open') as op,patch('spirit_nrf24.radio.time.monotonic',side_effect=[0,21]):
            with self.assertRaises(TimeoutError):
                with radio_locks(stop,('/tmp/example-radio.lock',)):
                    self.fail('lock failure allowed transmission')
            op.return_value.close.assert_called_once()

if __name__=='__main__':unittest.main()
