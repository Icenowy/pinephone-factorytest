import subprocess


def take_snapshot(node, res, name):
    command = ['sudo', 'media-ctl', '-d', '/dev/media1', '--set-v4l2', '"{}":0[fmt:UYVY8_2X8/{}]'.format(node, res)]
    p = subprocess.run(command, timeout=5)
    if p.returncode != 0:
        return False

    width, height = res.split('x')
    fmt = ['width=' + width, 'height=' + height, 'pixelformat=UYVY']
    command = ['sudo', 'v4l2-ctl', '--device', '/dev/video1', '--set-fmt-video={}'.format(','.join(fmt))]
    p = subprocess.run(command, timeout=5)
    if p.returncode != 0:
        return False

    command = ['sudo', 'v4l2-ctl', '--device', '/dev/video1', '--stream-mmap', '--stream-to=/tmp/frame.raw',
               '--stream-count=1']
    p = subprocess.run(command, timeout=10)
    if p.returncode != 0:
        return False

    command = ['convert', '-size', res, 'uyvy:/tmp/frame.raw', '-rotate', '90', '-resize', 'x350', name]
    p = subprocess.run(command, timeout=5)
    if p.returncode != 0:
        return False

    command = ['sudo', 'rm', '-rf', '/tmp/frame.raw']
    subprocess.run(command, timeout=5)

    return True


def check_ov5640():
    raw = subprocess.check_output(['media-ctl', '-d', '/dev/media1', '-p'], universal_newlines=True)
    try:
        take_snapshot('ov5640 3-004c', '1280x720', '/tmp/ov5640.png')
    except Exception as e:
        return False

    return 'ov5640' in raw
