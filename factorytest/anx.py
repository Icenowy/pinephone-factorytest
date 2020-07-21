import os
import subprocess
import time


# Fresh phone:
# boot firmware load failed

# Phone with firmware:
# OCM firmware loaded

# Cable plug-in
# cable inserted


def test_anx():
    klog = subprocess.check_output('dmesg', universal_newlines=True)
    if 'OCM firmware loaded' in klog:
        return os.path.isdir('/sys/class/typec/port0')
    if 'boot firmware load failed' in klog:
        run_firmware_update()
        return test_anx()
    return "No USB cable"


def run_firmware_update():
    subprocess.run(['sudo', 'sh', '-c', 'echo 1 > /sys/class/typec/port0/device/flash_eeprom'])
    time.sleep(2)
