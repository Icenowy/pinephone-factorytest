import time
import smbus
from factorytest.gpio import gpio, gpio_set, gpio_export, gpio_direction, remove_gpio_security


def set_camera_power(state):
    rear_reset = gpio('PD3')
    rear_powerdown = gpio('PC0')
    front_reset = gpio('PE16')
    front_powerdown = gpio('PE17')

    for pin in [rear_reset, front_reset, rear_powerdown, front_powerdown]:
        gpio_export(pin)
        gpio_direction(pin, 'out')

    # Powerdown is active high
    # Reset is active low

    if state == 'off':
        gpio_set(rear_powerdown, True)
        gpio_set(rear_reset, False)
        gpio_set(front_powerdown, True)
        gpio_set(front_reset, False)
    elif state == 'front':
        gpio_set(rear_powerdown, True)
        gpio_set(rear_reset, False)
        gpio_set(front_powerdown, False)
        gpio_set(front_reset, True)
    elif state == 'rear':
        gpio_set(rear_powerdown, False)
        gpio_set(rear_reset, True)
        gpio_set(front_powerdown, True)
        gpio_set(front_reset, False)
    else:
        raise Exception('Invalid camera power state {}'.format(state))


def check_ov5640(bus=2, address=0x3c):
    set_camera_power('rear')
    set_camera_power('off')


def check_gc(bus=2, address=0x3c):
    set_camera_power('front')
    bus = smbus.SMBus(bus)

    set_camera_power('off')
