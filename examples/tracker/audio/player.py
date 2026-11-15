import math
import threading
import queue
import time
import copy

from pyopl import *

from ..data import Song, Cell, Instrument, NOTE_OFF, Pattern


class Player:

    def __init__(
            self,
            song: Song,
            sample_rate: int = 48000,
            debug: bool = False,
    ):
        self.song = song
        self.debug = debug
        self._in_queue = queue.Queue()
        self.out_queue = queue.Queue()

        self.chip = OPL3Chip(sample_rate)
        self.chip_state = OPL3State(self.chip)
        self.stream = AudioStream(self.chip)
        self.thread: threading.Thread | None = None
        self._do_stop = False
        self.song_lock = threading.Lock()

        self._playing = False

        self._last_programmed_song_row = -1
        self._programmed_instruments: dict[int, int] = {}  # channel idx -> instr idx

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
    def playback_row(self) -> int:
        song_row = self.sample_to_row(self.chip.current_sample)
        return int(song_row) % 64  # TODO

    def play(self):
        self._in_queue.put_nowait({"play_song": True})

    def stop(self):
        self._playing = False

    def play_cell(self, channel: int, cell: Cell):
        self._in_queue.put_nowait({"play_cell": (channel, cell)})

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
        secs_per_row = self.row_to_sample(1) / self.chip.sample_rate
        if self.debug:
            print("ROW-secs:", secs_per_row)
        lookahead_time = secs_per_row * 5
        lookahead_samples = int(self.chip.sample_rate * lookahead_time)
        while not self._do_stop:
            while True:
                try:
                    message = self._in_queue.get_nowait()
                    self.process_input_message(message)
                except queue.Empty:
                    break

            if self._playing:
                sam = self.row_to_sample(self._last_programmed_song_row)
                if (sam - self.chip.current_sample) / self.chip.sample_rate < .1:
                    self.program_chip_playback(lookahead_samples)

            time.sleep(0.01)

    def sample_to_row(self, sample: int) -> float:
        sec = sample / self.chip.sample_rate
        beat = 4 * self.song.bpm / 60 * sec
        sig = self.song.signature
        row = beat * sig[0] / sig[1]
        return row

    def row_to_sample(self, row: int|float) -> int:
        sig = self.song.signature
        beat = row / sig[0] * sig[1]
        sec = beat / (self.song.bpm / 60 * 4)
        return int(sec * self.chip.sample_rate)

    def program_chip_playback(self, lookahead_samples: int):
        num_rows = int(math.ceil(self.sample_to_row(lookahead_samples)))
        current_sample = self.chip.current_sample
        song_row_start = int(self.sample_to_row(current_sample))

        if self.debug:
            print(f"row {song_row_start} - {song_row_start + num_rows}")

        for row_idx in range(num_rows):
            song_row = int(song_row_start + row_idx)
            if self._last_programmed_song_row and song_row <= self._last_programmed_song_row:
                continue

            pattern = self.song.patterns[0]
            pattern_length = pattern.length
            pattern_row = song_row % pattern_length

            self.program_chip_row(song_row, pattern_row, pattern)
            self._last_programmed_song_row = song_row

    def program_chip_row(self, song_row: int, pattern_row: int, pattern: Pattern):
        sample = self.row_to_sample(song_row)
        for channel in pattern.channels:
            self.program_cell(
                sample=sample,
                ch=channel.opl_channel,
                cell=channel.rows[pattern_row],
            )

    def program_cell(self, sample: int, ch: int, cell: Cell):
        # prepare instrument
        inst_idx = cell.instrument or 0
        if self._programmed_instruments.get(ch) != inst_idx:
            inst = self.song.instruments[inst_idx]
            self.chip_state.write_channel(ch, inst.channel_settings[0], sample=sample)
            self.chip_state.write_operators(ch, *inst.operators[:inst.num_operators], sample=sample)
            self._programmed_instruments[ch] = inst_idx

        if cell.note == NOTE_OFF:
            self.chip_state.note_off(ch, sample=sample + 2)
        elif cell.note is not None:
            if self.debug:
                print(f"note: sample={sample}, cur_sample={self.chip.current_sample}")
            self.chip_state.note_off(ch, sample=sample + 2)
            self.chip_state.midi_note_on(ch, cell.note, sample=sample + 4)

    def process_input_message(self, message: dict):
        sample = self.chip.current_sample

        if msg := message.get("play_cell"):
            ch, cell = msg
            self.program_cell(sample, ch, cell)

        if "play_song" in message:
            self._playing = True
            self.chip.reset(self.chip.sample_rate)
            self._programmed_instruments.clear()
            self._last_programmed_song_row = -1

        if "panic" in message:
            self.chip.delete_scheduled_writes()
            for ch in range(18):
                self.chip_state.note_off(ch)

        if "update_instruments" in message:
            self._programmed_instruments.clear()
