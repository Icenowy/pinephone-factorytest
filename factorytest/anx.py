import os
import subprocess


def test_anx():
    klog = subprocess.check_output('dmesg')
    if 'OCM firmware loaded' not in klog:
        return 'Not plugged in'
    return os.path.isdir('/sys/class/typec/port0')


def run_firmware_update():
    subprocess.run(['sudo', 'sh -c "echo 1 > /sys/class/typec/port0/device/flash_eeprom"'])
