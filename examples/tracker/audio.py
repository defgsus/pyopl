import threading
import time
from dataclasses import dataclass

from pyopl import *

from examples.tracker.__main__ import TrackerState, STEPS


@dataclass
class ScheduledEvent:
    sample: int
    active: tuple


class OPL3Engine:
    def __init__(self, tracker_state: TrackerState, sample_rate: int = 48000):
        self.tracker_state = tracker_state
        self.sample_rate = sample_rate

        self.chip = OPL3Chip(sample_rate)
        self.state = OPL3State(self.chip)
        self.stream = AudioStream(self.chip)

        self.state.set_rhythm_mode(True)

        self.playing = False
        self.pattern_dirty = True

        self.pattern_start_sample = 0
        self.next_event_index = 0
        self.scheduled_events = []

        self.lock = threading.Lock()

        self.setup_rhythm_instruments()
        self.setup_rhythm_channels()

    OPERATORS = {
        "BD1": 12,
        "BD2": 15,
        "SD": 16,
        "TT": 14,
        "CY": 17,
        "HH": 13,
    }
    def setup_rhythm_instruments(self):
        for inst in self.tracker_state.instruments.values():
            op = Operator(
                output_level=inst.volume,
                freq_multiplier=inst.freq_mult,
                attack=inst.attack,
                decay=inst.decay,
                sustain_on=inst.sustain_on,
                sustain=inst.sustain,
                release=inst.release,
                waveform=inst.waveform,
            )
            op.write(self.chip, self.OPERATORS[inst.name])

    CHANNELS = {
        "CH1": 6,
        "CH2": 7,
        "CH3": 8,
    }
    def setup_rhythm_channels(self):
        for chan in self.tracker_state.channels.values():
            index = self.CHANNELS[chan.name]
            self.state.write_channel(index, Channel(fm=chan.fm, feedback=chan.feedback))
            self.state.midi_note_on(index, note=chan.midi_note, note_on=False)

    def samples_per_step(self):
        return int(round(
            (60.0 / self.tracker_state.bpm / 4.0) * self.sample_rate
        ))

    def mark_dirty(self):
        with self.lock:
            self.pattern_dirty = True

    def start(self):
        with self.lock:
            if self.playing:
                return

            self.playing = True
            self.pattern_start_sample = self.chip.current_sample
            self.next_event_index = 0
            self.pattern_dirty = True

        self.stream.start()

    def stop(self):
        with self.lock:
            self.playing = False
            self.chip.delete_scheduled_writes()
            self.scheduled_events.clear()
            self.next_event_index = 0

    def schedule_ahead(self, lookahead_seconds: float = 0.1):
        """Schedule pattern events that will occur within the lookahead window."""
        with self.lock:
            if not self.playing:
                return

            current_sample = self.chip.current_sample
            horizon = current_sample + int(
                lookahead_seconds * self.sample_rate
            )

            step_samples = self.samples_per_step()

            # Rebuild future events after a pattern edit.
            if self.pattern_dirty:
                self.chip.delete_scheduled_writes()
                self.scheduled_events.clear()

                # Keep events that have already been rendered.
                self.next_event_index = max(
                    0,
                    (current_sample - self.pattern_start_sample) // step_samples,
                )

                self.pattern_dirty = False

            while True:
                step = self.next_event_index
                event_sample = (
                    self.pattern_start_sample
                    + int(
                        step + .0 * (step % 4)
                    ) * step_samples
                )

                if event_sample >= horizon:
                    break

                active = self.active_flags_for_step(step)

                self.scheduled_events.append(
                    ScheduledEvent(
                        sample=event_sample,
                        active=active,
                    )
                )

                event_sample = int(
                    event_sample + self.tracker_state.swing / 100 * (step % 4) * step_samples
                )

                self.state.rhythm_on(sample=event_sample)
                self.state.rhythm_on(*active, sample=event_sample + 1)

                self.next_event_index += 1

    def active_flags_for_step(self, step: int):
        return tuple(
            self.tracker_state.patterns[name][step % STEPS]
            for name in ("BD", "SD", "TT", "CY", "HH")
        )
