import os
import subprocess
import time


# Fresh phone:
# boot firmware load failed

# Phone with firmware:
# OCM firmware loaded

# Cable plug-in
# cable inserted

# CC shorted because of missing CC fix
# cc_status changed to CC1 = SRC.Ra CC2 = SRC.Ra

def test_anx():
    klog = subprocess.check_output('dmesg', universal_newlines=True)
    if 'OCM firmware loaded' in klog:
        if 'cc_status changed to CC1 = SRC.Ra CC2 = SRC.Ra' in klog:
            return 'No CC fix'
        return os.path.isdir('/sys/class/typec/port0')
    if 'boot firmware load failed' in klog:
        run_firmware_update()
        return test_anx()
    return "No USB cable"


def run_firmware_update():
    subprocess.run(['sudo', 'sh', '-c', 'echo 1 > /sys/class/typec/port0/device/flash_eeprom'])
    time.sleep(2)
