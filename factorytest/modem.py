import subprocess
import time
import serial
import logging
from factorytest.gpio import gpio, gpio_export, gpio_direction, gpio_set, remove_gpio_security

port = None
logger = logging.getLogger("modem")
logger.setLevel(logging.DEBUG)
fh = logging.FileHandler("/tmp/modem.log")
fh.setLevel(logging.DEBUG)
logger.addHandler(fh)


def check_usb_exists(vid, pid):
    output = subprocess.check_output(['lsusb'], universal_newlines=True)
    return '{}:{}'.format(vid, pid) in output


def fix_tty_permissions():
    logger.debug("fix_tty_permissions")
    subprocess.check_output(['sudo', 'chmod', '777', '/dev/ttyUSB2'])


def try_poweron():
    """ Do the power trigger required by the 1.0 kits """
    global port
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
            port = serial.Serial("/dev/ttyUSB2", 115200, timeout=5)
            return True
        time.sleep(1)
    return False


def get_att_data(command, multiline=False):
    global port
    if port is None:
        port = serial.Serial("/dev/ttyUSB2", 115200, timeout=5)
    logger.debug("> {}".format(command.decode()))
    port.write(command + b'\r')

    echo = port.readline().decode().strip()
    if multiline:
        response = []
        while True:
            raw = port.readline().decode().strip()
            logger.debug("< {}".format(raw))
            if "ERROR" in raw:
                status = "ERROR"
                break
            if raw == "OK":
                status = "OK"
                break
            if raw == "RING":
                continue
            if raw == command.decode():
                continue
            if len(raw) > 0:
                response.append(raw)
    else:
        response = port.readline().decode().strip()
        logger.debug("< {}".format(response))
        port.readline()
        status = port.readline().decode().strip()
    return status, response


def test_sim():
    status, imsi = get_imsi()
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


def get_operator():
    try:
        status, raw = get_att_data(b'AT+QSPN')
        if status != "OK":
            return "Not registered"
        raw = raw.replace("+QSPN: ", "")
        fnn, snn, spn, alphabet, rplmn = raw.split(',')
        return fnn.strip().replace('"', '')
    except:
        return "???"


def set_auto_answer():
    get_att_data(b'ATS0=1')


def get_call_info():
    # Get call info
    status, raw = get_att_data(b'AT+CLCC', multiline=True)
    if len(raw) < 2:
        return None

    # For some reason the first call listed is a dummy
    raw = raw[1]  # assumptions, assumptions
    part = raw.replace("+CLCC: ", "").split(",")

    direction = "incoming" if part[1] == "1" else "outgoing"
    states = {
        "0": "active",
        "1": "held",
        "2": "dialing",
        "3": "alerting",
        "4": "incoming",
        "5": "waiting"
    }
    state = states[part[2]]
    mode = "VoLTE" if part[3] == "1" else "Fallback"
    number = part[5].replace('"', "").strip()
    return {
        "direction": direction,
        "state": state,
        "mode": mode,
        "number": number
    }


def do_dtmf(numbers):
    get_att_data(b'AT+VTS="' + str(numbers).encode() + b'"')


def test_eg25():
    if not check_usb_exists('2c7c', '0125'):
        if not try_poweron():
            return "No modem"

    fix_tty_permissions()
    result = check_usb_exists('2c7c', '0125')
    if not result:
        return "No modem comm"
    if test_sim():
        return True
    else:
        return "No sim"
