"""
Micro Python Midi
This module implements channel commands according to the midi specification.
Each midi message consists of 3 bytes.
The first byte is the sum of the command and the midi channel (1-16 > 0-F).
the value of bytes 2 and 3 (data 1 and 2) are dependant on the command.
command     data1                   data2                  Description
-------     -----                   -----                  -----------
0x80-0x8F   Key # (0-127)           Off Velocity (0-127)   Note Off
0x90-0x90   Key # (0-127)           On Velocity (0-127)    Note On
0xA0-0xA0   Key # (0-127)           Pressure (0-127)       Poly Pressure
0xB0-0xB0   Control # (0-127)       Control Value (0-127)  Control
0xC0-0xC0   Program # (0-127)       Not Used (send 0)      Program Change
0xD0-0xD0   Pressure Value (0-127)  Not Used (send 0)      Channel Pressure
0xE0-0xE0   Range LSB (0-127)       Range MSB (0-127)      Pitch Bend
http://www.midi.org/techspecs/midimessages.php
"""


COMMANDS = (
    0x80,  # Note Off
    0x90,  # Note On
    0xA0,  # Poly Pressure
    0xB0,  # Control Change
    0xC0,  # Program Change
    0xD0,  # Mono Pressure
    0xE0,  # Pich Bend
)


class MidiInteger:
    """A midi message sends data as 7 bit values between 0 and 127."""

    def __init__(self, value):
        if 0 <= value < 2 ** 7:
            self.value = value
        else:
            raise ValueError(
                "Invalid midi data value: {}".format(value),
                "A midi data value must be an integer between 0 and 127",
            )

    def __repr__(self):
        return "<MidiInteger: {}>".format(self.value)


class BigMidiInteger:
    """Some messages use 14 bit values, these need to be spit down to
    msb and lsb before being sent."""

    def __init__(self, value):
        if 0 <= value <= 2 ** 14:
            self.msb = value // 2 ** 7
            self.lsb = value % 2 ** 7
        else:
            raise ValueError(
                "Invalid midi data value: {}".format(value),
                "A midi datavalue must be an integer between0"
                " and {}".format(2 ** 14),
            )

    def __repr__(self):
        return "<BigMidiInteger: lsb={}, msb={}>".format(self.lsb, self.msb)


def send_message(self, command, data1, data2=0):
    """Send a midi message to the serial device."""
    if command not in self.COMMANDS:
        raise ValueError("Invalid Command: {}".format(command))

    command += self.channel - 1

    self.port.send(command, timeout=self.timeout)
    self.port.send(MidiInteger(data1).value, timeout=self.timeout)
    self.port.send(MidiInteger(data2).value, timeout=self.timeout)


def control_change(self, control, value):
    """Send a control e.g. modulation or pedal message."""
    self.send_message(0xB0, control, value)


def program_change(self, value, bank=None):
    """Send a program change message, include bank if provided."""
    if bank:
        bank = BigMidiInteger(bank)
        self.control_change(32, bank.lsb)
        self.control_change(0, bank.msb)
    self.send_message(0xC0, value)
