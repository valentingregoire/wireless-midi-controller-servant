import _thread
from machine import Pin
from machine import UART
import network
from network import WLAN
from utime import sleep_ms


SERVANT_IP = "192.168.169.1"
SERVANT_PORT = 18788
REMOTE_IP = "192.168.169.2"
REMOTE_PORT = 11686

# setup access point
ACCESS_POINT = WLAN(network.AP_IF)
ACCESS_POINT.active(False)
ACCESS_POINT.config(
    essid="Headrush Servant", authmode=4, password="dG4=ZWgXDaaj2Q-5", hidden=True
)
ACCESS_POINT.ifconfig((SERVANT_IP, "255.255.255.0", "192.168.178.1", "8.8.8.8"))
ACCESS_POINT.active(True)

_STATUS_LED = Pin(23, Pin.OUT, Pin.PULL_UP)
_STATUS_LED.value(1)

# some general setup
_MIDI_TX_PIN = 18


_COMMAND_MAP = {
    b"button_rig_up": (49).to_bytes(1, "big"),
    b"button_rig_down": (55).to_bytes(1, "big"),
    b"button_scene1": (56).to_bytes(1, "big"),
    b"button_scene2": (57).to_bytes(1, "big"),
    b"button_scene3": (58).to_bytes(1, "big"),
    b"button_scene4": (59).to_bytes(1, "big"),
    b"button_tap_tempo": (60).to_bytes(1, "big"),
}

_MIDI_MAX_VALUE_BYTES = b"FF"

_UART = UART(1, 31250, tx=18, rx=19)


def __blink_led(times: int, interval: int) -> None:
    counter = 0
    while counter < times:
        _STATUS_LED.value(1)
        sleep_ms(interval)
        _STATUS_LED.value(0)
        sleep_ms(50)
        counter += 1


def blink_led(times=1, interval=100) -> None:
    _thread.start_new_thread(__blink_led, (times, interval))
    # __blink_led(status)


def setup_socket():
    # first wait for the access point to be set up
    while not ACCESS_POINT.active():
        print("Setting up wifi access point.")
        sleep_ms(10)

    print("access_point ready...")
    # print(ACCESS_POINT.ifconfig())

    import socket

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind((SERVANT_IP, SERVANT_PORT))

    return sock


def send_midi(data: bytes) -> None:
    message_type = b"\xB0"
    message_control_value = None
    if data.startswith(b"POT"):
        values = data.split(b"|")
        message_control = int(values[1]).to_bytes(1, "big")
        message_control_value = int(values[2]).to_bytes(1, "big")
    elif data.startswith(b"RIG"):
        blink_led()
        rig = int(data.replace(b"RIG", b"")).to_bytes(1, "big")
        message_type = b"\xC0"
        message_control = rig
    else:
        blink_led()
        command = _COMMAND_MAP.get(data)
        message_control = command
        message_control_value = _MIDI_MAX_VALUE_BYTES

    _UART.write(message_type)
    _UART.write(message_control)
    if message_control_value:
        _UART.write(message_control_value)


def main() -> None:
    print("Listening for commands...")
    sock = setup_socket()
    while True:
        data, addr = sock.recvfrom(128)
        print("data: {}".format(data))
        print("addr: {}".format(addr))
        if addr[0] == REMOTE_IP:
            if data == b"Remote connected!":
                blink_led(5)
            else:
                send_midi(data)


if __name__ == "__main__":
    main()
