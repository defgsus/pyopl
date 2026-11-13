

class OPL3Chip:
    """
    Low-level wrapper around Nuked-OPL3 chip emulator.

    Original C source: https://github.com/nukeykt/Nuked-OPL3

    Example:
        from pyopl import OPL3Chip

        chip = OPL3Chip(sample_rate=48000, opl3=True)
        chip.write(0xA0, 0x20)
        ...
        buffer = chip.generate_stream(1000)

    """

    def __init__(self, sample_rate: int = 49716, opl3: bool = True):
        """
        Create a new chip instance.

        :param sample_rate: The rate at which you want to sample the chip.
            The chip's internal rate is always 49716 Hz.
            The methods `generate_stream` and `generate_stream_into` will
            generate samples at the specified frequency.
            The samples will be resampled from the chip's internal sample-rate of 49716Hz.
        :param opl3: Boolean to specify OPL3 mode. If False, the chip is in OPL2 mode.
        """

    @property
    def opl3(self) -> bool:
        """
        Returns True if the chip is in OPL3 mode.
        Returns False if the chip is in OPL2 mode.

        :return: bool
        """

    @property
    def sample_rate(self) -> int:
        """
        Return the specified sample rate.

        This is not necessarily the chip's internal sample rate but the rate
        specified in constructor or on last `reset()` call.

        :return: int
        """

    @property
    def current_sample(self) -> int:
        """
        Return the current sample position (in configured sample_rate)
        :return: int
        """

    def reset(self, sample_rate: int = 49716, opl3: bool = True) -> None:
        """
        Completely reset this chip, similar to creating a new instance.

        :param sample_rate: The rate at which you want to sample the chip.
            The chip's internal rate is always 49716 Hz.
            Methods like `generate_resampled` or `generate_stream` will
            generate samples at the specified frequency.
        :param opl3: Boolean to specify OPL3 mode. If False, the chip is in OPL2 mode.
        """

    def write(self, reg: int, value: int, sample: int = 0) -> None:
        """
        Write to a register.

        :param reg: The register, typically between 0x01 and 0x1F0
        :param value: The byte value to store in the register
        :param sample: If sample is 0, the write happens immediately.
            If sample is > 0 it defines the absolute sample position
            (in the configured sample_rate) when the register write takes place.
        """

    def write_buffered(self, reg: int, value: int) -> None:
        """
        Queue an OPL register write for cycle-accurate application during
        subsequent sample generation.

        More specifically, each buffered register write will happen 2 internal samples later,
        during execution of any of the `generate` functions.

        :param reg: The register, typically between 0x01 and 0x1F0
        :param value: The byte value to store in the register
        """

    def generate_stream(self, frames: int) -> bytes:
        """
        Render `frames` interleaved stereo int16 frames into a new bytes object.

        :param frames: Number of samples to produce
        :return: bytes
        """

    def generate_stream_into(self, frames: int, buffer: bytearray) -> None:
        """
        Render `frames` interleaved stereo int16 frames into a writable,
        C-contiguous buffer. The buffer must contain at least frames * 4 bytes.

        Example:
            buffer = bytearray(frames * 4)
            chip.generate_stream_into(frames, buffer)

        :param frames: Number of samples to produce
        :param buffer: A writeable, C-contiguous buffer of size of at least frames * 4
        """

    def delete_scheduled_writes(self) -> None:
        """
        Clear all currently scheduled writes.

        This removes all write() calls from the schedule that had sample > 0
        """
