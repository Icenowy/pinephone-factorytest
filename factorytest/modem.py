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


def get_att_data(command):
    port = serial.Serial("/dev/ttyUSB2", 115200, timeout=5)
    port.write(command + b'\r')

    echo = port.readline().decode().strip()
    response = port.readline().decode().strip()
    port.readline()
    status = port.readline().decode().strip()
    return status, response


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


def get_firmware():
    return get_att_data(b'AT+GMR')


def get_imei():
    return get_att_data(b'AT+GSN')


def get_imsi():
    return get_att_data(b'AT+CIMI')


def get_signal():
    status, raw = get_att_data(b'AT+CSQ')
    if status != "OK":
        return None
    raw = raw.replace("+CSQ: ", "")
    raw = raw.strip()
    rssi, ber = raw.split(',')
    rssi = int(rssi.strip())
    ber = int(ber.strip())

    if rssi < 32:
        dbm = 113 - (2 * rssi)
        rssi = '-{}dBm'.format(dbm)
    elif rssi == 99:
        rssi = "Unknown"
    elif rssi > 99 and rssi < 192:
        dbm = 116 - (rssi - 100)
        rssi = "-{}dBm".format(dbm)
    elif rssi == 199:
        rssi = "Unknown"
    return rssi, ber

def get_network():
    status, raw = get_att_data(b'AT+QNWINFO')
    if status != "OK":
        return None
    raw = raw.replace("+QNWINFO: ", "")
    return raw

def test_eg25():
    if not check_usb_exists('2c7c', '0125'):
        if not try_poweron():
            return False

    fix_tty_permissions()
    result = check_usb_exists('2c7c', '0125')
    if not result:
        return False
    return test_sim()
