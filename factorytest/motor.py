import fcntl
import time
from glob import glob
import array
import os

from factorytest.ioctl.ff_structure import ff_effect, input_event
from factorytest.ioctl.input import EVIOCGBIT, EV_FF, FF_MAX, FF_RUMBLE, IOC, IOC_WRITE
import ctypes


def find_motor():
    SOUC = ctypes.sizeof(ctypes.c_ubyte)
    ffFeatures = array.array("B", [0] * (1 + FF_MAX // 8 // SOUC))
    for device in glob('/dev/input/event*'):
        print("testing {}".format(device))
        with open(device, 'w') as handle:
            try:
                fcntl.ioctl(handle, EVIOCGBIT(EV_FF, len(ffFeatures) * SOUC), ffFeatures)
            except OSError as e:
                print(e)
                # Inappropriate ioctl for device, not the motor
                continue
            if sum(ffFeatures) == 0:
                # No FF features supported
                continue
            return device, ffFeatures


def upload_rumble(handle):
    effect = ff_effect()
    effect.type = FF_RUMBLE
    effect.id = -1
    effect.u.rumble.strong_magnitude = 0
    effect.u.rumble.weak_magnitude = 0xc000
    effect.replay.length = 3000
    effect.replay.delay = 0

    EVIOCSFF = IOC(IOC_WRITE, 'E', 0x80, ctypes.sizeof(ff_effect))
    fcntl.ioctl(handle, EVIOCSFF, effect)
    return effect.id


def play_effect(handle, effect_id):
    play = input_event()
    play.type = EV_FF
    play.code = effect_id
    play.value = 1

    if os.write(handle.fileno(), play) != ctypes.sizeof(play):
        print("Could not play effect")


def test_motor():
    device, features = find_motor()
    with open(device, 'w') as handle:
        effect = upload_rumble(handle)
        play_effect(handle, effect)
        time.sleep(5)


if __name__ == '__main__':
    test_motor()
