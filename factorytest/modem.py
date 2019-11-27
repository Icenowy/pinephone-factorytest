import subprocess
import time

from factorytest.gpio import gpio, gpio_export, gpio_direction, gpio_set


def check_usb_exists(vid, pid):
    output = subprocess.check_output(['lsusb'], universal_newlines=True)
    return '{}:{}'.format(vid, pid) in output


def remove_gpio_security():
    subprocess.check_output(['sudo', 'chmod', '-R', '777', '/sys/class/gpio'])


def try_poweron():
    """ Do the power trigger required by the 1.0 kits """
    print("Using devkit 1.0 procedure to boot the modem")

    remove_gpio_security()
    # Setup gpio
    power_button = gpio('PB3')
    for pin in [power_button, 68, 232]:
        gpio_export(pin)
        remove_gpio_security()
        gpio_direction(pin, 'out')
        gpio_set(pin, False)

    # Trigger power button
    gpio_set(power_button, True)
    time.sleep(2)
    gpio_set(power_button, False)

    print("Waiting for modem to boot")
    for i in range(0, 60):
        if check_usb_exists('2c7c', '0125'):
            print("Booted in {} seconds".format(i))
            return True
        time.sleep(1)
    return False


def test_eg25():
    if not check_usb_exists('2c7c', '0125'):
        if not try_poweron():
            return False
    # TODO: test all modem functionality
    # - use AT command socket to check if sim is detected
    # - use AT commands to check if networks are found
    return check_usb_exists('2c7c', '0125')
