import sounddevice
from pyopl import OPL3Chip


class AudioStream:
    """
    Simple audio device connection using `sounddevice` library.

    Use like:
    ```
    import time
    from pyopl import OPL3Chip, OPL3State, AudioStream
    chip = OPL3Chip(SR)
    state = OPL3State(chip)

    # ... setup instruments, etc ...

    with AudioStream(chip):
        state.midi_note_on(0, 48)
        time.sleep(1.)
        state.note_off(0)
        time.sleep(1.)
    ```
    """
    def __init__(
            self,
            chip: OPL3Chip,
            blocksize: int = 2048,
    ):
        self.chip = chip
        self.blocksize = blocksize
        self.stream: sounddevice.RawOutputStream | None = None

    def start(self):
        if not self.stream:
            self.stream = sounddevice.RawOutputStream(
                samplerate=self.chip.sample_rate,
                channels=2,
                dtype="int16",
                callback=self._callback,
                blocksize=self.blocksize,
            )
        if self.stream.stopped:
            self.stream.start()

    def stop(self):
        if self.stream and not self.stream.stopped:
            self.stream.stop()

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop()

    def _callback(self, outdata, frames, time_info, status):
        self.chip.generate_stream_into(frames, outdata)

