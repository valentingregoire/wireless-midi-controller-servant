import machine
from machine import UART, Pin, ADC
from utime import sleep_ms

uart = UART(1, 31250, tx=18, rx=19)
hex_128 = b"\x80"
command = 55
hex_command = hex(command)[1:]
print("hex_command:{}".format(hex_command))

# hex_message = b"\x80\x80\xb0\x37\x7f"
# hex_message = hex_128 + hex_128 + b"\xB0" + hex_command + b"\x7f"
# hex_message = b"\xB0" + hex_command + b"\x7f"
hex_message = b"\xb0\x37\x7f"
print("hex_message: {}".format(hex_message))
# uart.init(31250, bits=8, parity=None, stop=1)  # init with given parameters
cc_channel = 0xB0
cc_channel += 0
# uart.write(hex_message)

var_127 = 127
led = Pin(13, Pin.OUT, Pin.PULL_UP)
scene1 = 56
scene2 = 57
scene1_bin = scene1.to_bytes(1, "big")
scene2_bin = scene2.to_bytes(1, "big")
# while var_127 < 256:
#     print(var_127)
#     led.value(0)
#     # uart.write(b"\xb0")
#     # # uart.write(b"\x37")
#     # uart.write(command.to_bytes(1, "big"))
#     # uart.write(var_127.to_bytes(1, "big"))
#     var_127_bin = var_127.to_bytes(1, "big")
#     uart.write(b"\xb0" + scene1_bin + var_127_bin)
#     sleep_ms(250)
#     uart.write(b"\xb0" + scene2_bin + var_127_bin)
#     sleep_ms(250)
#     var_127 += 1
#     led.value(1)
#     # uart.write(b"\x7f")
program = 55
uart.write(b"\xc0" + program.to_bytes(1, "big"))

pot = ADC(Pin(33))
pot.atten(ADC.ATTN_11DB)
while True:
    # van 0 tot en met 4095
  pot_value = pot.read()
  print(pot_value)
  # sleep_ms(100)
