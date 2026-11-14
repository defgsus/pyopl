import threading
import time
import copy
from typing import Callable

from pyopl import *

from ..data import Song


class Player:

    def __init__(
            self,
            song: Song,
            sample_rate: int = 48000,
    ):
        self.song = song
        self.playback_row = 0

        self.chip = OPL3Chip(sample_rate)
        self.stream = AudioStream(self.chip)
        self.thread: threading.Thread | None = None
        self._do_stop = False
        self.song_lock = threading.Lock()
        self._last_programmed_row = None
        self._row_callback: Callable | None = None

    @property
    def is_playing(self) -> bool:
        return bool(self.thread and self.thread.is_alive())

    def start(self):
        self._start_thread()
        self.stream.start()

    def stop(self):
        self.stream.stop()
        self._stop_thread()

    def set_row_callback(self, callable: Callable):
        self._row_callback = callable

    def _start_thread(self):
        if not self.thread:
            self.thread = threading.Thread(target=self._thread_main_loop, name="opl-controller")
        if not self.thread.is_alive():
            self._do_stop = False
            self.thread.start()

    def _stop_thread(self):
        if self.thread:
            self._do_stop = True
            self.thread.join()
            self.thread = None

    def _thread_main_loop(self):
        window_time = .1
        sample_window = int(self.chip.sample_rate * window_time)
        while not self._do_stop:
            self.program_chip(sample_window)
            time.sleep(window_time * .9)

    def sample_to_row(self, sample: int) -> float:
        sec = sample / self.chip.sample_rate
        beat = self.song.bpm / 60 * sec * 4
        sig = self.song.signature
        row = beat * sig[0] / sig[1]
        return row

    def program_chip(self, sample_window: int):
        current_sample = self.chip.current_sample
        playback_row = self.sample_to_row(current_sample)
        playback_row = int(playback_row)
        if playback_row == self._last_programmed_row:
            return

        # make a thread-safe copy of the current row
        with self.song_lock:
            pattern = self.song.patterns[0]
            pattern_length = pattern.length
            playback_row = playback_row % pattern_length
            row = [
                copy.copy(chan.rows[playback_row])
                for chan in pattern.channels
            ]

        self._last_programmed_row = playback_row
        self.playback_row = playback_row
        if self._row_callback:
            self._row_callback()

