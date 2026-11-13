import sounddevice
from pyopl import OPL3Chip


class AudioStream:
    """
    Simple audio device connection using `sounddevice` library.

    Example:

        import time
        from pyopl import OPL3Chip, OPL3State, AudioStream

        chip = OPL3Chip(48000)
        state = OPL3State(chip)

        # ... setup instruments, etc ...

        # use as context manager
        with AudioStream(chip):
            state.midi_note_on(0, 48)
            time.sleep(1.)
            state.note_off(0)
            time.sleep(1.)

        # or use start/stop
        stream = AudioStream(chip)
        stream.start()
        # ... do things ...
        stream.stop()

    """
    def __init__(
            self,
            chip: OPL3Chip,
            blocksize: int = 2048,
            **kwargs,
    ):
        """
        Create new instance.

        The audio stream will be using the OPL3Chip's configured sample-rate
        to render audio to a sound device.

        :param chip: OPL3Chip to render
        :param blocksize: int, the size of one block.
            Increase the size, if audio playback is dropping
        :param kwargs: optional arguments passed to `sounddevice.RawOutputStream`
        """
        self.chip = chip
        self.blocksize = blocksize
        self.stream: sounddevice.RawOutputStream | None = None
        self._device_kwargs = kwargs

    def start(self):
        """
        Start the audio stream.

        Does nothing if stream is already started.
        """
        if not self.stream:
            self.stream = sounddevice.RawOutputStream(
                samplerate=self.chip.sample_rate,
                channels=2,
                dtype="int16",
                callback=self._callback,
                blocksize=self.blocksize,
                **self._device_kwargs,
            )
        if self.stream.stopped:
            self.stream.start()

    def stop(self):
        """
        Stop the stream.

        Does nothing if stream was not started yet.
        """
        if self.stream and not self.stream.stopped:
            self.stream.stop()

    def __enter__(self):
        """
        Start the stream and enter context manager block.
        """
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """
        End context manager block and stop the stream.
        """
        self.stop()

    def _callback(self, outdata, frames, time_info, status):
        self.chip.generate_stream_into(frames, outdata)

