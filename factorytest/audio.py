import subprocess


def set_sound_device(name):
    script = 'reset\nset _verb HiFi\nset _enadev Earpiece\n'
    subprocess.run(['alsaucm', '-b', '-'])
