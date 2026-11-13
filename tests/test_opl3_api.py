import unittest
from contextlib import redirect_stdout
from io import StringIO

from pyopl import *


class TestOPL3Api(unittest.TestCase):

    def test_chip_init(self):
        chip = OPL3Chip()
        self.assertEqual(DEFAULT_SAMPLE_RATE, chip.sample_rate)
        self.assertEqual(True, chip.opl3)
        chip = OPL3Chip(sample_rate=11000)
        self.assertEqual(11000, chip.sample_rate)
        self.assertEqual(True, chip.opl3)
        chip = OPL3Chip(sample_rate=11000, opl3=False)
        self.assertEqual(11000, chip.sample_rate)
        self.assertEqual(False, chip.opl3)
        chip = OPL3Chip(opl3=False)
        self.assertEqual(DEFAULT_SAMPLE_RATE, chip.sample_rate)
        self.assertEqual(False, chip.opl3)

    def test_chip_reset(self):
        chip = OPL3Chip()
        self.assertEqual(DEFAULT_SAMPLE_RATE, chip.sample_rate)
        self.assertEqual(True, chip.opl3)
        chip.reset()
        self.assertEqual(DEFAULT_SAMPLE_RATE, chip.sample_rate)
        self.assertEqual(True, chip.opl3)
        chip.reset(sample_rate=11000)
        self.assertEqual(11000, chip.sample_rate)
        self.assertEqual(True, chip.opl3)
        chip.reset(sample_rate=11000, opl3=False)
        self.assertEqual(11000, chip.sample_rate)
        self.assertEqual(False, chip.opl3)
        chip.reset(opl3=False)
        self.assertEqual(DEFAULT_SAMPLE_RATE, chip.sample_rate)
        self.assertEqual(False, chip.opl3)
        chip.reset()
        self.assertEqual(DEFAULT_SAMPLE_RATE, chip.sample_rate)
        self.assertEqual(True, chip.opl3)

    def test_chip_doc_strings(self):
        # Check for attribution
        self.assertIn(
            "https://github.com/nukeykt/Nuked-OPL3",
            OPL3Chip.__doc__,
        )
        # Check for __init__ signature
        self.assertIn(
            "__init__(sample_rate: int = 49716, opl3: bool = True)",
            OPL3Chip.__doc__,
        )
        # Check if special abs.collections.Buffer type is correctly parsed
        buf = StringIO()
        with redirect_stdout(buf):
            help(OPL3Chip.generate_stream_into)
        self.assertIn(
            "generate_stream_into(frames: int, buffer: Buffer)",
            buf.getvalue(),
        )

    def test_chip_generate_stream(self):
        chip = OPL3Chip()
        self.assertEqual(
            b"\x00\x00\x00\x00",
            chip.generate_stream(1)
        )

    def test_chip_write_opl3(self):
        chip = OPL3Chip()
        self.assertEqual(True, chip.opl3)
        chip.write(0x105, 0)
        self.assertEqual(False, chip.opl3)
        chip.write(value=1, reg=0x105)
        self.assertEqual(True, chip.opl3)

    def test_chip_write_opl3_buffered(self):
        chip = OPL3Chip()
        self.assertEqual(True, chip.opl3)
        chip.write_buffered(0x105, 0)
        self.assertEqual(True, chip.opl3)
        chip.generate_stream(4)
        self.assertEqual(False, chip.opl3)
        chip.write_buffered(value=1, reg=0x105)
        self.assertEqual(False, chip.opl3)
        chip.generate_stream(4)
        self.assertEqual(True, chip.opl3)

    def test_chip_write_opl3_scheduled(self):
        chip = OPL3Chip()
        self.assertEqual(True, chip.opl3)
        chip.write(0x105, 0, 1000)
        self.assertEqual(True, chip.opl3)
        chip.generate_stream(4)
        self.assertEqual(True, chip.opl3)
        chip.generate_stream(1000)
        self.assertEqual(False, chip.opl3)
        chip.write(sample=2000, value=1, reg=0x105)
        self.assertEqual(False, chip.opl3)
        chip.generate_stream(4)
        self.assertEqual(False, chip.opl3)
        chip.generate_stream(1000)
        self.assertEqual(True, chip.opl3)

    def test_chip_write_opl3_scheduled_clear(self):
        chip = OPL3Chip()
        self.assertEqual(True, chip.opl3)
        chip.write(0x105, 0, 1000)
        self.assertEqual(True, chip.opl3)
        chip.delete_scheduled_writes()
        chip.generate_stream(2000)
        self.assertEqual(True, chip.opl3)

    def test_chip_current_sample_generate_stream(self):
        chip = OPL3Chip()
        self.assertEqual(0, chip.current_sample)
        chip.generate_stream(23)
        self.assertEqual(23, chip.current_sample)
        chip.generate_stream(5)
        self.assertEqual(28, chip.current_sample)

    def test_chip_current_sample_generate_stream_into(self):
        chip = OPL3Chip()
        self.assertEqual(0, chip.current_sample)
        buffer = bytearray(100)
        chip.generate_stream_into(23, buffer)
        self.assertEqual(23, chip.current_sample)
        chip.generate_stream_into(5, buffer)
        self.assertEqual(28, chip.current_sample)
