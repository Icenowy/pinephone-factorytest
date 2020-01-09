import subprocess


def set_sound_device(name):
    subprocess.run(['alsaucm', 'set', '_verb', 'HiFi', 'set', '_enadev', name])


def set_volume(control, level):
    subprocess.run(['amixer', 'set', control, level])


def speaker_test(channels=1):
    subprocess.run(['speaker-test', '-c', str(channels), '-t', 'wav', '-s', '1'])


def test_earpiece():
    set_sound_device('Earpiece')
    set_volume('Earpiece', '100%')
    speaker_test(1)


def test_headphones():
    set_sound_device('Headphone')
    set_volume('Headphone', '50%')
    speaker_test(2)


def test_speaker():
    set_sound_device('Speaker')
    set_volume('Line Out', '100%')
    speaker_test(1)
