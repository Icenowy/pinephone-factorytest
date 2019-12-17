import subprocess
import time
import serial

from factorytest.gpio import gpio, gpio_export, gpio_direction, gpio_set, remove_gpio_security


def check_usb_exists(vid, pid):
    output = subprocess.check_output(['lsusb'], universal_newlines=True)
    return '{}:{}'.format(vid, pid) in output


def fix_tty_permissions():
    subprocess.check_output(['sudo', 'chmod', '777', '/dev/ttyUSB2'])


def try_poweron():
    """ Do the power trigger required by the 1.0 kits """
    print("Using devkit 1.0 procedure to boot the modem")

    remove_gpio_security()
    # Setup gpio
    power_button = gpio('PB3')
    for pin in [power_button, 68, 232]:
        gpio_export(pin)
        remove_gpio_security(pin)
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


def test_sim():
    port = serial.Serial("/dev/ttyUSB2", 115200, timeout=5)
    port.write(b'AT+CIMI\r')

    """Excepted response:
    b'AT+CIMI\r\r\n'
    b'204080510000000\r\n'
    b'\r\n'
    b'OK\r\n'
    """

    echo = port.readline().decode().strip()
    imsi = port.readline().decode().strip()
    port.readline()
    status = port.readline().decode().strip()
    return status == "OK" and int(imsi) > 1000


def test_eg25():
    if not check_usb_exists('2c7c', '0125'):
        if not try_poweron():
            return False

    fix_tty_permissions()
    result = check_usb_exists('2c7c', '0125')
    if not result:
        return False
    return test_sim()
