import subprocess


def take_snapshot(node, res, name, rotate, skip=5):
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
               '--stream-count=1', '--stream-skip={}'.format(skip)]
    p = subprocess.run(command, timeout=10)
    if p.returncode != 0:
        return False

    command = ['convert', '-size', res, 'uyvy:/tmp/frame.raw', '-rotate', rotate, '-resize', 'x330', name]
    p = subprocess.run(command, timeout=5)
    if p.returncode != 0:
        return False

    command = ['sudo', 'rm', '-rf', '/tmp/frame.raw']
    subprocess.run(command, timeout=5)

    return True


def set_route(camera):
    if camera == 'ov5640':
        links = [
            '"gc2145 3-003c":0->"sun6i-csi":0[0]',
            '"ov5640 3-004c":0->"sun6i-csi":0[1]'
        ]
    elif camera == 'gc2145':
        links = [
            '"ov5640 3-004c":0->"sun6i-csi":0[0]',
            '"gc2145 3-003c":0->"sun6i-csi":0[1]'
        ]
    else:
        raise Exception("Something wrong")
    for link in links:
        subprocess.run(['sudo', 'media-ctl', '-d', '/dev/media1', '--links', link])


def check_ov5640():
    raw = subprocess.check_output(['media-ctl', '-d', '/dev/media1', '-p'], universal_newlines=True)
    if 'ov5640' not in raw:
        return False

    set_route('ov5640')
    try:
        return take_snapshot('ov5640 3-004c', '1280x720', '/tmp/ov5640.png', '90')
    except Exception as e:
        print(e)
        return False


def check_gc2145():
    raw = subprocess.check_output(['media-ctl', '-d', '/dev/media1', '-p'], universal_newlines=True)
    if 'gc2145' not in raw:
        return False

    set_route('gc2145')
    try:
        return take_snapshot('gc2145 3-003c', '1280x720', '/tmp/gc2145.png', '270', skip=35)
    except Exception as e:
        print(e)
        return False
