import subprocess
import time


def init():
    # This is needed because the ALSA devs keep changing the fileformat every minor release, but the ucm files are kept
    # stable in postmarketOS because pulseaudio has it's own parser that doesn't constantly change

    subprocess.run(['sudo', 'mv', '/usr/share/alsa/ucm2/sun50i-a64-audio', '/usr/share/alsa/ucm2/sun50i-a64-audi'])
    subprocess.run(['sudo', 'mv', '/usr/share/alsa/ucm2/sun50i-a64-audi/sun50i-a64-audio.conf',
                    '/usr/share/alsa/ucm2/sun50i-a64-audi/sun50i-a64-audi.conf'])


def set_sound_device(names):
    init()
    command = ['alsaucm', 'set', '_verb', 'HiFi']
    for name in names:
        command.extend(['set', '_enadev', name])
    subprocess.run(command)


def set_control(name, value):
    name = 'name="{}"'.format(name)
    command = ['amixer', 'cset', name, value]
    subprocess.run(command)


def set_volume(control, level):
    subprocess.run(['amixer', 'set', control, level])


def speaker_test(channels=2):
    subprocess.run(['speaker-test', '-c', str(channels), '-t', 'wav', '-s', '1'])


def record(filename):
    subprocess.run(['arecord', '-d', '1', filename])


def playback(filename):
    subprocess.run(['aplay', filename])


def test_earpiece():
    set_sound_device(['Earpiece'])
    set_volume('Earpiece', '100%')
    speaker_test(2)


def test_headphones():
    set_sound_device(['Headphones'])
    set_volume('Headphone', '60%')
    speaker_test(2)


def test_speaker():
    set_sound_device(['Speaker'])
    set_volume('Line Out', '100%')
    speaker_test(2)


def test_mic():
    set_sound_device(['Headphones', 'Mic'])
    set_control('Headphone Source Playback Route', 'Mixer')
    set_control('Mic1 Playback Switch', 'on')
    time.sleep(3)
    set_control('Mic1 Playback Switch', 'off')
    set_control('Headphone Source Playback Route', 'DAC')
    set_sound_device(['Earpiece'])
