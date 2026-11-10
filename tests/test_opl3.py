import unittest
import wave

from pyopl import *


class TestOPL3(unittest.TestCase):

    def test_chip_init(self):
        chip = OPL3Chip()
        self.assertEqual(49716, chip.sample_rate)
        self.assertEqual(True, chip.opl3)
        chip = OPL3Chip(sample_rate=11000)
        self.assertEqual(11000, chip.sample_rate)
        self.assertEqual(True, chip.opl3)
        chip = OPL3Chip(sample_rate=11000, opl3=False)
        self.assertEqual(11000, chip.sample_rate)
        self.assertEqual(False, chip.opl3)
        chip = OPL3Chip(opl3=False)
        self.assertEqual(49716, chip.sample_rate)
        self.assertEqual(False, chip.opl3)

    def test_chip_reset(self):
        chip = OPL3Chip()
        self.assertEqual(49716, chip.sample_rate)
        self.assertEqual(True, chip.opl3)
        chip.reset()
        self.assertEqual(49716, chip.sample_rate)
        self.assertEqual(True, chip.opl3)
        chip.reset(sample_rate=11000)
        self.assertEqual(11000, chip.sample_rate)
        self.assertEqual(True, chip.opl3)
        chip.reset(sample_rate=11000, opl3=False)
        self.assertEqual(11000, chip.sample_rate)
        self.assertEqual(False, chip.opl3)
        chip.reset(opl3=False)
        self.assertEqual(49716, chip.sample_rate)
        self.assertEqual(False, chip.opl3)
        chip.reset()
        self.assertEqual(49716, chip.sample_rate)
        self.assertEqual(True, chip.opl3)
