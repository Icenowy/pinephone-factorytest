import subprocess


def check_ov5640():
    raw = subprocess.check_output(['media-ctl', '-d', '/dev/media1', '-p'], universal_newlines=True)
    return 'ov5640' in raw
