import _thread
import time

import bluetooth
from machine import Pin
from machine import UART
import machine
from micropython import const
from network import WLAN
from utime import sleep_ms

from ble_advertising import decode_name
from ble_advertising import decode_services

WLAN(0).active(False)
WLAN(1).active(False)

machine.freq(240000000)

_MIDI_TX_PIN = 19

_STATUS_LED = Pin(13, Pin.OUT, Pin.PULL_UP)
_STATUS_LED.value(0)


_COMMAND_MAP = {
    "button_rig_up": (49).to_bytes(1, "big"),
    "button_rig_down": (55).to_bytes(1, "big"),
    "button_scene1": (56).to_bytes(1, "big"),
    "button_scene2": (57).to_bytes(1, "big"),
    "button_scene3": (58).to_bytes(1, "big"),
    "button_scene4": (59).to_bytes(1, "big"),
    "button_tap_tempo": (60).to_bytes(1, "big")
}

_MIDI_MAX_VALUE_BYTES = b"FF"

_UART = UART(1, 31250, tx=18, rx=19)

_IRQ_CENTRAL_CONNECT = const(1)
_IRQ_CENTRAL_DISCONNECT = const(2)
_IRQ_GATTS_WRITE = const(3)
_IRQ_GATTS_READ_REQUEST = const(4)
_IRQ_SCAN_RESULT = const(5)
_IRQ_SCAN_DONE = const(6)
_IRQ_PERIPHERAL_CONNECT = const(7)
_IRQ_PERIPHERAL_DISCONNECT = const(8)
_IRQ_GATTC_SERVICE_RESULT = const(9)
_IRQ_GATTC_SERVICE_DONE = const(10)
_IRQ_GATTC_CHARACTERISTIC_RESULT = const(11)
_IRQ_GATTC_CHARACTERISTIC_DONE = const(12)
_IRQ_GATTC_DESCRIPTOR_RESULT = const(13)
_IRQ_GATTC_DESCRIPTOR_DONE = const(14)
_IRQ_GATTC_READ_RESULT = const(15)
_IRQ_GATTC_READ_DONE = const(16)
_IRQ_GATTC_WRITE_DONE = const(17)
_IRQ_GATTC_NOTIFY = const(18)
_IRQ_GATTC_INDICATE = const(19)

_ADV_IND = const(0x00)
_ADV_DIRECT_IND = const(0x01)
_ADV_SCAN_IND = const(0x02)
_ADV_NONCONN_IND = const(0x03)

# org.bluetooth.service.environmental_sensing
_ENV_SENSE_UUID = bluetooth.UUID("7a47b14d-04c5-440c-b701-c5ed67789dff")
# org.bluetooth.characteristic.temperature
_TEMP_UUID = bluetooth.UUID("588f33e0-4039-4373-a2f5-776a1ff38993")
_TEMP_CHAR = (
    _TEMP_UUID,
    bluetooth.FLAG_READ | bluetooth.FLAG_NOTIFY,
)
_ENV_SENSE_SERVICE = (
    _ENV_SENSE_UUID,
    (_TEMP_CHAR,),
)


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


class BLEHeadrushServant:
    def __init__(self, ble):
        self._ble = ble
        self._ble.active(True)
        self._ble.irq(self._irq)

        self._reset()

    def _reset(self):
        # Cached name and address from a successful scan.
        self._name = None
        self._addr_type = None
        self._addr = None

        # Cached value (if we have one)
        self._value = None

        # Callbacks for completion of various operations.
        # These reset back to None after being invoked.
        self._scan_callback = None
        self._conn_callback = None
        self._read_callback = None

        # Persistent callback for when new data is notified from the device.
        self._notify_callback = None

        # Connected device.
        self._conn_handle = None
        self._start_handle = None
        self._end_handle = None
        self._value_handle = None

    def _irq(self, event, data):
        if event == _IRQ_SCAN_RESULT:
            addr_type, addr, adv_type, rssi, adv_data = data
            if adv_type in (_ADV_IND, _ADV_DIRECT_IND) and _ENV_SENSE_UUID in decode_services(
                adv_data
            ):
                # Found a potential device, remember it and stop scanning.
                self._addr_type = addr_type
                self._addr = bytes(
                    addr
                )  # Note: addr buffer is owned by caller so need to copy it.
                self._name = decode_name(adv_data) or "?"
                self._ble.gap_scan(None)

        elif event == _IRQ_SCAN_DONE:
            if self._scan_callback:
                if self._addr:
                    # Found a device during the scan (and the scan was explicitly stopped).
                    self._scan_callback(self._addr_type, self._addr, self._name)
                    self._scan_callback = None
                else:
                    # Scan timed out.
                    self._scan_callback(None, None, None)

        elif event == _IRQ_PERIPHERAL_CONNECT:
            # Connect successful.
            conn_handle, addr_type, addr = data
            if addr_type == self._addr_type and addr == self._addr:
                self._conn_handle = conn_handle
                self._ble.gattc_discover_services(self._conn_handle)

        elif event == _IRQ_PERIPHERAL_DISCONNECT:
            # Disconnect (either initiated by us or the remote end).
            conn_handle, _, _ = data
            if conn_handle == self._conn_handle:
                # If it was initiated by us, it'll already be reset.
                self._reset()

        elif event == _IRQ_GATTC_SERVICE_RESULT:
            # Connected device returned a service.
            conn_handle, start_handle, end_handle, uuid = data
            if conn_handle == self._conn_handle and uuid == _ENV_SENSE_UUID:
                self._start_handle, self._end_handle = start_handle, end_handle

        elif event == _IRQ_GATTC_SERVICE_DONE:
            # Service query complete.
            if self._start_handle and self._end_handle:
                self._ble.gattc_discover_characteristics(
                    self._conn_handle, self._start_handle, self._end_handle
                )
            else:
                print("Failed to find remote service.")

        elif event == _IRQ_GATTC_CHARACTERISTIC_RESULT:
            # Connected device returned a characteristic.
            conn_handle, def_handle, value_handle, properties, uuid = data
            if conn_handle == self._conn_handle and uuid == _TEMP_UUID:
                self._value_handle = value_handle

        elif event == _IRQ_GATTC_CHARACTERISTIC_DONE:
            # Characteristic query complete.
            if self._value_handle:
                # We've finished connecting and discovering device, fire the connect callback.
                if self._conn_callback:
                    self._conn_callback()
            else:
                print("Failed to find remote characteristic.")

        elif event == _IRQ_GATTC_READ_RESULT:
            # A read completed successfully.
            conn_handle, value_handle, char_data = data
            if conn_handle == self._conn_handle and value_handle == self._value_handle:
                self._update_value(char_data)
                if self._read_callback:
                    self._read_callback(self._value)
                    self._read_callback = None
                    self._value = None

        elif event == _IRQ_GATTC_READ_DONE:
            # Read completed (no-op).
            conn_handle, value_handle, status = data

        elif event == _IRQ_GATTC_NOTIFY:
            # Received command from remote.
            conn_handle, value_handle, notify_data = data
            if conn_handle == self._conn_handle and value_handle == self._value_handle:
                self._update_value(notify_data)
                if self._notify_callback:
                    self._notify_callback(self._value)

    # Returns true if we've successfully connected and discovered characteristics.
    def is_connected(self):
        return self._conn_handle is not None and self._value_handle is not None

    # Find a device advertising the environmental sensor service.
    def scan(self, callback=None):
        self._addr_type = None
        self._addr = None
        self._scan_callback = callback
        self._ble.gap_scan(2000, 30000, 30000)

    # Connect to the specified device (otherwise use cached address from a scan).
    def connect(self, addr_type=None, addr=None, callback=None):
        self._addr_type = addr_type or self._addr_type
        self._addr = addr or self._addr
        self._conn_callback = callback
        if self._addr_type is None or self._addr is None:
            return False
        self._ble.gap_connect(self._addr_type, self._addr)
        return True

    # Disconnect from current device.
    def disconnect(self):
        if not self._conn_handle:
            return
        self._ble.gap_disconnect(self._conn_handle)
        self._reset()

    # Issues an (asynchronous) read, will invoke callback with data.
    def read(self, callback):
        if not self.is_connected():
            return
        self._read_callback = callback
        self._ble.gattc_read(self._conn_handle, self._value_handle)

    # Sets a callback to be invoked when the device notifies us.
    def on_notify(self, callback):
        self._notify_callback = callback

    def _update_value(self, data):
        # self._value = struct.unpack("<h", data)[0] /
        command_received_fallback(data)
        self._value = data
        return self._value

    def value(self):
        return self._value


def command_received_fallback(data: bytes) -> None:
    if data:
        data_str = data.decode()
        print("data: {}".format(data_str))
        message_type = b"\xB0"
        # message_control = None
        # message_control_value = None

        if data_str.startswith("POT"):
            values = data_str.split("|")
            message_control = int(values[1]).to_bytes(1, "big")
            message_control_value = int(values[2]).to_bytes(1, "big")
        else:
            blink_led(2)
            command = _COMMAND_MAP.get(data_str)
            if data_str in ["button_rig_up", "button_rig_down"]:
                message_type = b"\xC0"

            message_control = command
            message_control_value = _MIDI_MAX_VALUE_BYTES

        # print("message: {}{}{}".format(message_type, message_control, message_control_value))
        _UART.write(message_type)
        _UART.write(message_control)
        _UART.write(message_control_value)


def main():
    ble = bluetooth.BLE()
    servant = BLEHeadrushServant(ble)

    def on_scan(addr_type, addr, name):
        if addr_type is not None:
            print("Remote found:", addr_type, addr, name)
            servant.connect()
        else:
            print("Remote not found.")

    # Wait for connection...
    while not servant.is_connected():
        print("scanning for remote...")
        servant.scan(callback=on_scan)
        sleep_ms(2500)

    blink_led(1, 4)
    print("Connected")

    # Explicitly issue reads, using "print" as the callback.
    # while servant.is_connected():
    #     servant.read(callback=command_received_fallback)
    #     time.sleep_ms(2000)

    # Alternative to the above, just show the most recently notified value.
    # while servant.is_connected():
    #     # command_received_fallback(servant.value())
    #     sleep_ms(100)

    print("Disconnected")


if __name__ == "__main__":
    main()
