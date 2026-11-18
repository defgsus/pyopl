import math
import threading
import queue
import time
import traceback

from pyopl import *

from ..data import Song, Cell, Pattern
from .opl3pool import OPL3Pool


class Player:

    def __init__(
            self,
            song: Song,
            sample_rate: int = 48000,
            debug: bool = False,
    ):
        self.song = song
        self.sample_rate = sample_rate
        self.debug = debug
        self.pool = OPL3Pool(self.sample_rate, self.song, debug=self.debug)

        self._in_queue = queue.Queue()
        self.out_queue = queue.Queue()

        self.stream = AudioStream(*self.pool.chips)
        self.thread: threading.Thread | None = None
        self._do_stop = False
        self.song_lock = threading.Lock()

        self._playing = False

        self._start_sample = 0
        self._last_programmed_song_row = -1
        self._percussion_notes: dict[str, int] = {}

    # ---- threadsafe API -----

    def start_audio(self):
        self._start_thread()
        self.stream.start()

    def stop_audio(self):
        self.stream.stop()
        self._stop_thread()

    @property
    def is_running(self) -> bool:
        return bool(self.thread and self.thread.is_alive())

    @property
    def is_playing(self) -> bool:
        return self._playing

    @property
    def current_song_sample(self) -> int:
        return self.pool.current_sample - self._start_sample

    @property
    def current_song_row(self) -> int:
        return int(self.sample_to_row(self.current_song_sample))

    @property
    def playback_row(self) -> int:
        song_row = self.sample_to_row(self.current_song_sample)
        return int(song_row) % 64  # TODO

    def play(self):
        self._in_queue.put_nowait({"play_song": True})

    def stop(self):
        self._playing = False

    def play_cell(self, channel: int, cell: Cell):
        self._in_queue.put_nowait({"play_cell": (channel, cell)})

    def play_cells(self, cells: list[tuple[int, Cell]]):
        self._in_queue.put_nowait({"play_cells": cells})

    def panic(self):
        """All notes off"""
        self._in_queue.put_nowait({"panic": True})

    def update_instruments(self):
        self._in_queue.put_nowait({"update_instruments": True})

    # ---- internal API ----

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
        secs_per_row = self.row_to_sample(1) / self.sample_rate
        if self.debug:
            print("ROW-secs:", secs_per_row)
        lookahead_time = secs_per_row * 5
        lookahead_samples = int(self.sample_rate * lookahead_time)
        try:
            while not self._do_stop:
                while True:
                    try:
                        message = self._in_queue.get_nowait()
                        self.process_input_message(message)
                    except queue.Empty:
                        break

                if self._playing:
                    sam = self.row_to_sample(self._last_programmed_song_row)
                    if (sam - self.current_song_sample) / self.sample_rate < .1:
                        self._program_chip_playback(lookahead_samples)

                time.sleep(0.01)
        except Exception as e:
            traceback.print_exc()
            self.out_queue.put_nowait({"exception": f"{type(e).__name__}: {e}"})

    def sample_to_row(self, sample: int) -> float:
        sec = sample / self.sample_rate
        beat = 4 * self.song.bpm / 60 * sec
        sig = self.song.signature
        row = beat * sig[0] / sig[1]
        return row

    def row_to_sample(self, row: int|float) -> int:
        sig = self.song.signature
        beat = row / sig[0] * sig[1]
        sec = beat / (self.song.bpm / 60 * 4)
        return int(sec * self.sample_rate)

    def _program_chip_playback(self, lookahead_samples: int):
        num_rows = int(math.ceil(self.sample_to_row(lookahead_samples)))
        current_song_sample = self.current_song_sample
        song_row_start = int(self.sample_to_row(current_song_sample))

        if self.debug:
            print(f"row {song_row_start} - {song_row_start + num_rows}")

        for row_idx in range(num_rows):
            song_row = int(song_row_start + row_idx)
            if self._last_programmed_song_row and song_row <= self._last_programmed_song_row:
                continue

            pattern = self.song.patterns[0]
            pattern_length = pattern.length
            pattern_row = song_row % pattern_length

            self._program_chip_row(song_row, pattern_row, pattern)
            self._last_programmed_song_row = song_row

    def _program_chip_row(self, song_row: int, pattern_row: int, pattern: Pattern):
        sample = self.row_to_sample(song_row) + self._start_sample
        self.pool.start_program_row(sample)
        for ch, channel in enumerate(pattern.channels):
            cell = channel.rows[pattern_row]
            if cell.needs_programming:
                self.pool.program_cell(
                    tracker_channel=ch,
                    cell=cell,
                    sample=sample + 2,
                )
        self.pool.end_program_row(sample + 4)

    def process_input_message(self, message: dict):
        sample = self.pool.current_sample

        if "play_song" in message:
            self.pool.initialize()
            self._start_sample = sample
            self._last_programmed_song_row = -1
            self._playing = True

        if "panic" in message:
            self.pool.delete_scheduled_writes()
            self.pool.all_notes_off()

        if "update_instruments" in message:
            self.pool._programmed_instrument_per_chipchan.clear()

        if msg := message.get("play_cell"):
            ch, cell = msg
            ahead = self.sample_rate // 16
            self.pool.start_program_row(sample + ahead)
            self.pool.program_cell(ch, cell, sample + ahead + 2)
            self.pool.end_program_row(sample + ahead + 4)

        if msg := message.get("play_cells"):
            ahead = self.sample_rate // 16
            for ch, cell in msg:
                self.pool.start_program_row(sample + ahead)
                self.pool.program_cell(ch, cell, sample + ahead + 2)
                self.pool.end_program_row(sample + ahead + 4)

