import subprocess
import time


def fix_led_permissions():
    for led in ['red', 'green', 'blue']:
        subprocess.check_output(['sudo', 'chmod', '777', '/sys/class/leds/{}:indicator/brightness'.format(led)])
    subprocess.check_output(['sudo', 'chmod', '777', '/sys/class/leds/white:flash/brightness'.format(led)])
    subprocess.check_output(['sudo', 'chmod', '777', '/sys/class/leds/white:flash/flash_strobe'.format(led)])


def write_led(color, on=False):
    ltype = 'indicator'
    if color == 'white':
        ltype = 'flash'
    with open('/sys/class/leds/{}:{}/brightness'.format(color, ltype), 'w') as handle:
        if on:
            handle.write('1\n')
        else:
            handle.write('0\n')


def test_flash():
    fix_led_permissions()
    with open('/sys/class/leds/white:flash/flash_strobe', 'w') as handle:
        handle.write('1\n')


def test_torch():
    fix_led_permissions()
    write_led('white', on=True)
    time.sleep(2)
    write_led('white', on=False)


def test_notification_led():
    write_led('red', True)
    write_led('green', False)
    write_led('blue', False)
    time.sleep(0.5)
    write_led('red', False)
    write_led('green', True)
    write_led('blue', False)
    time.sleep(0.5)
    write_led('red', False)
    write_led('green', False)
    write_led('blue', True)
    time.sleep(0.5)
    write_led('red', True)
    write_led('green', True)
    write_led('blue', True)
    time.sleep(0.5)
    write_led('red', False)
    write_led('green', False)
    write_led('blue', False)
