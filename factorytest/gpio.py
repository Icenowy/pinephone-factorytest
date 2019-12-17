import os
import subprocess


def remove_gpio_security(pin=None):
    path = '/sys/class/gpio'
    if pin:
        path = '/sys/class/gpio/gpio{}/'.format(pin)
    subprocess.check_output(['sudo', 'chown', '-R', 'demo', path])


def gpio(name):
    port = name[1]
    port = ord(port) - ord('A')
    pin = int(name[2:])
    return (port * 32) + pin


def gpio_set(pin, state):
    with open('/sys/class/gpio/gpio{}/value'.format(pin), 'w') as handle:
        if state:
            handle.write('1\n')
        else:
            handle.write('0\n')


def gpio_direction(pin, direction):
    dirfile = '/sys/class/gpio/gpio{}/direction'.format(pin)
    with open(dirfile) as handle:
        current = handle.read().strip()

    if current == direction:
        return

    with open(dirfile, 'w') as handle:
        handle.write('{}\n'.format(direction))


def gpio_export(pin):
    if os.path.isdir('/sys/class/gpio/gpio{}'.format(pin)):
        return
    with open('/sys/class/gpio/export', 'w') as handle:
        handle.write('{}\n'.format(pin))
