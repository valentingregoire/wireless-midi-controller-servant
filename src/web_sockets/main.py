import _thread
from machine import Pin
from machine import UART
import machine
from micropython import const
import network
from utime import sleep_ms

# network.WLAN(network.AP_IF).active(True)
# network.WLAN(1).active(True)
# WLAN(0).active(False)
# WLAN(1).active(False)

machine.freq(240000000)

# setup access point
ACCESS_POINT = network.WLAN(network.AP_IF)
ACCESS_POINT.active(False)
ACCESS_POINT.config(essid="Headrush Servant", hidden=True)
# ACCESS_POINT.config(authmode=4)
ACCESS_POINT.active(True)
# ACCESS_POINT.config(essid="Headrush Servant", password="lol")#, hidden=True)

# some general setup
_MIDI_TX_PIN = 19

_STATUS_LED = Pin(13, Pin.OUT, Pin.PULL_UP)
_STATUS_LED.value(0)


_COMMAND_MAP = {
    b"button_rig_up": (49).to_bytes(1, "big"),
    b"button_rig_down": (55).to_bytes(1, "big"),
    b"button_scene1": (56).to_bytes(1, "big"),
    b"button_scene2": (57).to_bytes(1, "big"),
    b"button_scene3": (58).to_bytes(1, "big"),
    b"button_scene4": (59).to_bytes(1, "big"),
    b"button_tap_tempo": (60).to_bytes(1, "big")
}

_MIDI_MAX_VALUE_BYTES = b"FF"

_UART = UART(1, 31250, tx=18, rx=19)


def __blink_led(status=1, times=1, interval=150) -> None:
    """
    Blinks the status led.
    :param status:
        1: blue
        2: green
        3: orange
        4: red
    :return:
    """

    for _ in range(times):
        _STATUS_LED.value(1)
        sleep_ms(interval)
        _STATUS_LED.value(0)
        sleep_ms(75)


def blink_led(status=1, times=1, interval=100) -> None:
    _thread.start_new_thread(__blink_led, (status, times, interval))
    # __blink_led(status)


def setup_socket():
    # first wait for the access point to be set up
    while not ACCESS_POINT.active():
        print("Setting up wifi access point.")
        sleep_ms(10)

    print("access_point ready...")
    # print(ACCESS_POINT.ifconfig())

    import socket
    # addr = socket.getaddrinfo("0.0.0.0", 80)[0][-1]
    ip = ACCESS_POINT.ifconfig()[0]
    # print(addr)
    print("binding ip {}".format(ip))

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    # sock.bind(addr)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind((ip, 10086))
    # sock.listen()

    return sock


def main() -> None:
    print("Listening for commands...")
    sock = setup_socket()
    while True:
        # c1, addr = sock.accept()
        data, addr = sock.recvfrom(1024)
        print("data: {}".format(data))
        print("addr: {}".format(addr))


if __name__ == "__main__":
    main()
